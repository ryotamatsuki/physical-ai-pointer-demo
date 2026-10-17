"""Static notebook checks; actual SmolVLA inference requires user's Colab GPU."""
import ast
import json
import unittest
from pathlib import Path


class NotebookTest(unittest.TestCase):
    def test_notebook_is_valid_and_python_cells_parse(self):
        path = Path(__file__).parent / "01_smolvla_2axis_preflight.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        cells = notebook["cells"]
        python = "\n\n".join("".join(cell["source"]) for cell in cells if cell["cell_type"] == "code")
        ast.parse(python)
        self.assertIn("SmolVLAPolicy.from_pretrained", python)
        self.assertIn("predict_action_chunk", python)
        self.assertIn("FeatureType.ACTION,shape=(2,)", python)
        self.assertIn("FeatureType.STATE,shape=(2,)", python)
        self.assertIn("assert result.ndim == 3", python)
        self.assertIn("赤い丸を指して", python)
        self.assertIn("青い丸を指して", python)

    def test_real_gpu_notebook_structure(self):
        path = Path(__file__).parent / "02_real_smolvla_gpu_smoke.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        python = "\n\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
        ast.parse(python)
        self.assertIn("SmolVLAPolicy.from_pretrained", python)
        self.assertIn("predict_action_chunk", python)
        self.assertIn("shape=(2,)", python)
        self.assertIn('assert torch.cuda.is_available()', python)
        self.assertIn("赤い丸を指して", python)
        self.assertIn("青い丸を指して", python)


if __name__ == "__main__":
    unittest.main()
