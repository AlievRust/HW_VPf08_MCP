from __future__ import annotations

import unittest

from cli_client.llm_client import LLMClient


class LlmClientTest(unittest.TestCase):
    def test_string_input_is_converted_to_message_list(self) -> None:
        payload = LLMClient._normalize_input("покажи все заметки")

        self.assertEqual(
            payload,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "покажи все заметки",
                        }
                    ],
                }
            ],
        )

    def test_list_input_passes_through(self) -> None:
        payload = [{"type": "function_call_output", "call_id": "call_123", "output": "{}"}]

        self.assertIs(LLMClient._normalize_input(payload), payload)

    def test_stream_request_uses_streaming_and_store_flag(self) -> None:
        params = LLMClient._build_stream_request_params(
            model="gpt-5.4",
            instructions="system prompt",
            input=[{"role": "user", "content": "покажи все заметки"}],
            tools=[{"type": "function", "name": "list_notes"}],
        )

        self.assertEqual(
            params,
            {
                "model": "gpt-5.4",
                "instructions": "system prompt",
                "input": [{"role": "user", "content": "покажи все заметки"}],
                "tools": [{"type": "function", "name": "list_notes"}],
                "stream": True,
                "store": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
