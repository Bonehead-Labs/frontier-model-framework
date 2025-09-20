from __future__ import annotations

import sys
import unittest
from unittest import mock


class TestCliExitCodes(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
        src_path = __import__("os").path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def test_connector_error_maps_exit_code(self) -> None:
        from fmf.cli import main
        from fmf.core.errors import ConnectorError

        with mock.patch("fmf.cli._cmd_connect_ls", side_effect=ConnectorError("boom")):
            rc = main(["connect", "ls", "demo"])
        self.assertEqual(rc, 4)

    def test_unexpected_error_returns_one(self) -> None:
        from fmf.cli import main

        with mock.patch("fmf.cli.build_parser") as patched:
            fake_parser = mock.Mock()
            fake_parser.parse_args.side_effect = RuntimeError("boom")
            patched.return_value = fake_parser
            rc = main([])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
