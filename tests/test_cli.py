from __future__ import annotations

import unittest

from cli_client.cli import _trim_history


class CliHistoryTest(unittest.TestCase):
    def test_trim_history_keeps_last_messages(self) -> None:
        history = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "user", "content": "three"},
            {"role": "assistant", "content": "four"},
        ]

        self.assertEqual(
            _trim_history(history, 2),
            [
                {"role": "user", "content": "three"},
                {"role": "assistant", "content": "four"},
            ],
        )

    def test_trim_history_with_non_positive_limit_returns_empty_list(self) -> None:
        self.assertEqual(_trim_history([{"role": "user", "content": "one"}], 0), [])


if __name__ == "__main__":
    unittest.main()
