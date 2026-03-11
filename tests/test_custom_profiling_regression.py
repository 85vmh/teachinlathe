import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "src" / "teachinlathe" / "widgets" / "conversational_qml" / "gcode_builder"
PROGRAM = ROOT / "conversational" / "program1.json"


def _load_custom_profiling_module():
    module_order = [
        ("x.config", BASE / "config.py"),
        ("x.operations.custom_profiling_types", BASE / "operations" / "custom_profiling_types.py"),
        ("x.operations.custom_profiling_geometry", BASE / "operations" / "custom_profiling_geometry.py"),
        ("x.operations.custom_profiling_planner", BASE / "operations" / "custom_profiling_planner.py"),
        ("x.operations.custom_profiling", BASE / "operations" / "custom_profiling.py"),
    ]

    for fullname, path in module_order:
        spec = importlib.util.spec_from_file_location(fullname, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        spec.loader.exec_module(module)
    return sys.modules["x.operations.custom_profiling"]


class CustomProfilingRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.custom_profiling = _load_custom_profiling_module()
        operations = json.loads(PROGRAM.read_text())["operations"]
        cls.profile = next(op for op in operations if op.get("type") == "defineProfile" and op.get("profile_id") == 5)
        cls.rough = next(op for op in operations if op.get("type") == "customProfiling" and op.get("profiling_options", {}).get("strategy") == "rough")
        cls.finish = next(op for op in operations if op.get("type") == "customProfiling" and op.get("profiling_options", {}).get("strategy") == "finish")

    def _generate(self, operation):
        operation = dict(operation)
        operation["_resolved_profile"] = self.profile
        return self.custom_profiling.generate_custom_profiling_gcode(operation)

    def test_roughing_output_snapshot(self):
        self.assertEqual(self._generate(self.rough), [
            "G97 M3 S1000.0",
            "G95 F1.0",
            "G0 X53.000 Z0.000",
            "G0 X50.500",
            "G1 Z-58.500",
            "G0 X51.500 Z-57.500",
            "G0 Z0.000",
            "G0 X49.000",
            "G1 Z-58.500",
            "G0 X50.000 Z-57.500",
            "G0 Z0.000",
            "G0 X47.500",
            "G1 Z-58.500",
            "G0 X48.500 Z-57.500",
            "G0 Z0.000",
            "G0 X46.000",
            "G1 Z-58.500",
            "G0 X47.000 Z-57.500",
            "G0 Z0.000",
            "G0 X44.500",
            "G1 Z-58.500",
            "G0 X45.500 Z-57.500",
            "G0 Z0.000",
            "G0 X43.000",
            "G1 Z-58.500",
            "G0 X44.000 Z-57.500",
            "G0 Z0.000",
            "G0 X41.500",
            "G1 Z-57.500",
            "G0 X42.500 Z-56.500",
            "G0 Z0.000",
            "G0 X40.000",
            "G1 Z-38.551",
            "G0 X41.000 Z-37.551",
            "G0 Z0.000",
            "G0 X38.500",
            "G1 Z-38.039",
            "G0 X39.500 Z-37.039",
            "G0 Z0.000",
            "G0 X37.000",
            "G1 Z-37.430",
            "G0 X38.000 Z-36.430",
            "G0 Z0.000",
            "G0 X35.500",
            "G1 Z-36.500",
            "G0 X36.500 Z-35.500",
            "G0 Z0.000",
            "G0 X34.000",
            "G1 Z-35.114",
            "G0 X35.000 Z-34.114",
            "G0 Z0.000",
            "G0 X32.500",
            "G1 Z-32.859",
            "G0 X33.500 Z-31.859",
            "G0 Z0.000",
            "G0 X31.000",
            "G1 Z-28.374",
            "G0 X32.000 Z-27.374",
            "G0 Z0.000",
            "G0 X29.500",
            "G1 Z-27.500",
            "G0 X30.500 Z-26.500",
            "G0 Z0.000",
            "G0 X28.000",
            "G1 Z-26.750",
            "G0 X29.000 Z-25.750",
            "G0 Z0.000",
            "G0 X26.500",
            "G1 Z-26.000",
            "G0 X27.500 Z-25.000",
            "G0 Z0.000",
            "G0 X25.000",
            "G1 Z-25.250",
            "G0 X26.000 Z-24.250",
            "G0 Z0.000",
            "G0 X23.500",
            "G1 Z-24.500",
            "G0 X24.500 Z-23.500",
            "G0 Z0.000",
            "G0 X22.000",
            "G1 Z-23.587",
            "G0 X23.000 Z-22.587",
            "G0 Z0.000",
            "G0 X21.500",
            "G1 Z-22.264",
            "G0 X22.500 Z-21.264",
            "G0 Z0.000",
            "G0 X53.000",
            "",
            "( contour pass: stock_x=1.500 stock_z=1.500 )",
            "G0 X21.500 Z0.000",
            "G1 X21.500 Z-22.264",
            "G2 X22.606 Z-24.053 I2.000 K0.000",
            "G1 X30.462 Z-27.981",
            "G3 X31.556 Z-29.558 I-0.894 K-1.789",
            "G2 X39.192 Z-38.230 I9.944 K1.058",
            "G3 X41.500 Z-41.149 I-0.692 K-2.919",
            "G1 X41.500 Z-57.500",
            "G1 X42.500 Z-58.500",
            "G1 X51.500 Z-58.500",
            "G0 X53.000 Z0.000",
        ])

    def test_finishing_output_snapshot(self):
        self.assertEqual(self._generate(self.finish), [
            "G97 M3 S1000.0",
            "G95 F0.1",
            "G0 X53.000 Z0.000",
            "G0 X21.000 Z0.000",
            "G1 X21.000 Z-22.764",
            "G2 X22.106 Z-24.553 I2.000 K0.000",
            "G1 X29.962 Z-28.481",
            "G3 X31.056 Z-30.058 I-0.894 K-1.789",
            "G2 X38.692 Z-38.730 I9.944 K1.058",
            "G3 X41.000 Z-41.649 I-0.692 K-2.919",
            "G1 X41.000 Z-58.000",
            "G1 X42.000 Z-59.000",
            "G1 X51.000 Z-59.000",
            "G0 X53.000 Z0.000",
            "G0 X20.500 Z0.000",
            "G1 X20.500 Z-23.264",
            "G2 X21.606 Z-25.053 I2.000 K0.000",
            "G1 X29.462 Z-28.981",
            "G3 X30.556 Z-30.558 I-0.894 K-1.789",
            "G2 X38.192 Z-39.230 I9.944 K1.058",
            "G3 X40.500 Z-42.149 I-0.692 K-2.919",
            "G1 X40.500 Z-58.500",
            "G1 X41.500 Z-59.500",
            "G1 X50.500 Z-59.500",
            "G0 X53.000 Z0.000",
            "G0 X20.000 Z0.000",
            "G1 X20.000 Z-23.764",
            "G2 X21.106 Z-25.553 I2.000 K0.000",
            "G1 X28.962 Z-29.481",
            "G3 X30.056 Z-31.058 I-0.894 K-1.789",
            "G2 X37.692 Z-39.730 I9.944 K1.058",
            "G3 X40.000 Z-42.649 I-0.692 K-2.919",
            "G1 X40.000 Z-59.000",
            "G1 X41.000 Z-60.000",
            "G1 X50.000 Z-60.000",
            "G0 X53.000 Z0.000",
            "G0 X20.000 Z0.000",
            "G1 X20.000 Z-23.764",
            "G2 X21.106 Z-25.553 I2.000 K0.000",
            "G1 X28.962 Z-29.481",
            "G3 X30.056 Z-31.058 I-0.894 K-1.789",
            "G2 X37.692 Z-39.730 I9.944 K1.058",
            "G3 X40.000 Z-42.649 I-0.692 K-2.919",
            "G1 X40.000 Z-59.000",
            "G1 X41.000 Z-60.000",
            "G1 X50.000 Z-60.000",
            "G0 X53.000 Z0.000",
        ])


if __name__ == "__main__":
    unittest.main()
