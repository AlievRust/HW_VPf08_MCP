from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from cli_client.config import ConfigError, load_config


class ConfigTest(unittest.TestCase):
    def test_missing_required_variables_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OPENAI_MODEL=gpt-5.4\n", encoding="utf-8")
            original_api_key = os.environ.pop("OPENAI_API_KEY", None)
            original_model = os.environ.pop("OPENAI_MODEL", None)
            try:
                with self.assertRaises(ConfigError):
                    load_config(env_path)
            finally:
                if original_api_key is not None:
                    os.environ["OPENAI_API_KEY"] = original_api_key
                if original_model is not None:
                    os.environ["OPENAI_MODEL"] = original_model

    def test_valid_env_file_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "OPENAI_MODEL=gpt-5.4",
                        "OPENAI_BASE_URL=https://api.openai.com/v1",
                        "MCP_SERVER_URL=http://127.0.0.1:8000",
                    ]
                ),
                encoding="utf-8",
            )
            original_values = {key: os.environ.pop(key, None) for key in [
                "OPENAI_API_KEY",
                "OPENAI_MODEL",
                "OPENAI_BASE_URL",
                "MCP_SERVER_URL",
                "CHAT_HISTORY_LIMIT",
            ]}
            try:
                config = load_config(env_path)
                self.assertEqual(config.openai_api_key, "test-key")
                self.assertEqual(config.openai_model, "gpt-5.4")
                self.assertEqual(config.chat_history_limit, 10)
            finally:
                for key, value in original_values.items():
                    if value is not None:
                        os.environ[key] = value

    def test_custom_history_limit_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "OPENAI_MODEL=gpt-5.4",
                        "CHAT_HISTORY_LIMIT=7",
                    ]
                ),
                encoding="utf-8",
            )
            original_values = {key: os.environ.pop(key, None) for key in [
                "OPENAI_API_KEY",
                "OPENAI_MODEL",
                "CHAT_HISTORY_LIMIT",
            ]}
            try:
                config = load_config(env_path)
                self.assertEqual(config.chat_history_limit, 7)
            finally:
                for key, value in original_values.items():
                    if value is not None:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
