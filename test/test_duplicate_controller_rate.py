#!/usr/bin/env python3
"""Issue 15: the dgap controller rate has a single definition.

costmap_nav.launch includes mbf_<local_planner>.launch first and then loads
configs/mbf/move_base_params.yaml into the move_base_flex node, so the planner
file's copies of these keys were always overridden. This test checks the
effective values with `roslaunch --dump-params` (no ROS master needed) and that
only one of the files loaded for dgap defines each key.
"""

import os
import shutil
import subprocess
import unittest

import yaml

PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "/rto"
MODEL = "rto"

# Same args task_generator's robot_manager passes to robot.launch.
ROBOT_LAUNCH_ARGS = [
    "SIMULATOR:=flatland",
    "model:=" + MODEL,
    "name:=" + MODEL,
    "namespace:=" + NS,
    "frame:=" + MODEL + "/",
    "inter_planner:=bypass",
    "complexity:=1",
    "train_mode:=false",
    "agent_name:=" + MODEL,
]

EXPECTED = {
    "controller_frequency": 10.0,
    "controller_patience": 5.0,
    "planner_frequency": 5.0,
}

# Files loaded into move_base_flex (and move_base_legacy_relay) for dgap.
DGAP_FILES = [
    "configs/mbf/move_base_params.yaml",
    "entities/robots/" + MODEL + "/configs/mbf/move_base_params.yaml",
    "configs/mbf/local/dgap_local_planner_params.yaml",
    "entities/robots/" + MODEL + "/configs/mbf/dgap_local_planner_params.yaml",
]


def dump_params(local_planner):
    out = subprocess.run(
        ["roslaunch", "--dump-params", "arena_bringup", "robot.launch",
         "local_planner:=" + local_planner] + ROBOT_LAUNCH_ARGS,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        universal_newlines=True, check=True, timeout=120,
    ).stdout
    return yaml.safe_load(out)


def load_yaml(rel_path):
    with open(os.path.join(PKG_DIR, rel_path)) as f:
        return yaml.safe_load(f) or {}


class TestSingleSourceInFiles(unittest.TestCase):

    def test_each_key_defined_once_for_dgap(self):
        for key in EXPECTED:
            sources = [p for p in DGAP_FILES if key in load_yaml(p)]
            self.assertEqual(sources, ["configs/mbf/move_base_params.yaml"],
                             "%s defined in %s" % (key, sources))

    def test_move_base_params_values(self):
        data = load_yaml("configs/mbf/move_base_params.yaml")
        for key, value in EXPECTED.items():
            self.assertEqual(data[key], value, key)


@unittest.skipUnless(shutil.which("roslaunch"), "roslaunch not on PATH")
class TestEffectiveParams(unittest.TestCase):

    def _check(self, local_planner):
        params = dump_params(local_planner)
        for node in ("move_base_flex", "move_base_legacy_relay"):
            for key, value in EXPECTED.items():
                name = "%s/%s/%s" % (NS, node, key)
                self.assertIn(name, params)
                self.assertEqual(params[name], value, name)

    def test_dgap(self):
        self._check("dgap")

    def test_teb(self):
        self._check("teb")

    def test_dwa(self):
        self._check("dwa")


if __name__ == "__main__":
    unittest.main()
