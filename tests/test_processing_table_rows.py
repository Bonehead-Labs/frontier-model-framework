import io
import os
import sys
import unittest


class TestProcessingTableRows(unittest.TestCase):
    def setUp(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_iter_table_rows_csv_text_and_passthrough(self):
        from fmf.processing.table_rows import iter_table_rows

        csv_data = "user_id,free_text,score\n1,Hello world,5\n2,Great product!,4\n".encode("utf-8")
        rows = list(
            iter_table_rows(
                filename="survey.csv",
                data=csv_data,
                text_column="free_text",
                pass_through=["user_id", "score", "free_text"],
            )
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["user_id"], "1")
        self.assertEqual(rows[0]["free_text"], "Hello world")
        self.assertEqual(rows[0]["text"], "Hello world")
        self.assertIn("score", rows[0])


if __name__ == "__main__":
    unittest.main()

