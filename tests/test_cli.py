import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mesh_workbench.cli import main


class HostCLI(unittest.TestCase):
    def test_missing_recipe(self):
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as result,
        ):
            main(["run", "this-recipe-does-not-exist.json", "--output", "unused"])
        self.assertEqual(result.exception.code, 2)

    def test_existing_output(self):
        recipe = Path(__file__).resolve().parents[1] / "examples/assembly.json"
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as result,
        ):
            main(["run", str(recipe), "--output", str(recipe.parent)])
        self.assertEqual(result.exception.code, 2)

    def test_blender_missing(self):
        recipe = Path(__file__).resolve().parents[1] / "examples/assembly.json"
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as result,
        ):
            main(
                [
                    "run",
                    str(recipe),
                    "--output",
                    "nonexistent-output-mw",
                    "--blender",
                    "definitely-missing-blender-executable",
                ]
            )
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
