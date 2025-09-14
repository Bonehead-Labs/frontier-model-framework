import json
import os
import sys
import tempfile
import time
import unittest


class TestArtefactIndexRetention(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_index_and_retention(self):
        from fmf.processing.persist import update_index, apply_retention, ensure_dir

        with tempfile.TemporaryDirectory() as tmp:
            # create 3 fake run dirs
            runs = []
            for i in range(3):
                rd = os.path.join(tmp, f"run{i}")
                ensure_dir(rd)
                runs.append(rd)
                update_index(tmp, {"run_id": f"run{i}", "run_dir": rd, "run_yaml": os.path.join(rd, "run.yaml")})
                # ensure distinct mtimes
                time.sleep(0.01)
            # apply retention to keep last 1
            apply_retention(tmp, 1)
            # only the most recent should remain
            remaining = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
            self.assertEqual(len(remaining), 1)


if __name__ == "__main__":
    unittest.main()

