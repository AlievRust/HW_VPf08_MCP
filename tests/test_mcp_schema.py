from __future__ import annotations

import unittest

from cli_client.mcp_client import MCPClient
from mcp.types import Tool


class McpSchemaTest(unittest.TestCase):
    def test_tool_definition_is_converted_for_openai(self) -> None:
        tool = Tool(
            name="create_note",
            description="Создает заметку.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "tags": {"type": "string"},
                },
                "required": ["title", "content", "tags"],
                "additionalProperties": False,
            },
        )

        spec = MCPClient._tool_to_spec(tool)
        payload = spec.as_openai_tool()

        self.assertEqual(payload["type"], "function")
        self.assertEqual(payload["name"], "create_note")
        self.assertTrue(payload["strict"])
        self.assertIn("parameters", payload)
        self.assertFalse(payload["parameters"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
