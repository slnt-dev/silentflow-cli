from __future__ import annotations

import sys
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import silentflow  # noqa: E402


class SilentFlowCliTests(unittest.TestCase):
    def test_does_not_discover_a_repository_local_legacy_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".baoyu-skills" / "silentflow-client" / "config.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps({"api_url": "https://attacker.example"}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import json, sys; "
                        f"sys.path.insert(0, {str(SCRIPT_DIR)!r}); "
                        "import silentflow; "
                        "print(silentflow.load_config().get('api_url', ''))"
                    ),
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "HOME": str(root / "empty-home")},
            )

        self.assertNotEqual(result.stdout.strip(), "https://attacker.example")

    def test_compatibility_wrapper_rejects_keys_in_command_arguments(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "upload.py"),
                "--file",
                "missing.png",
                "--api-key",
                "sentinel-not-a-real-key",
            ],
            capture_output=True,
            text=True,
            env={key: value for key, value in os.environ.items() if key != "SILENTFLOW_API_KEY"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments: --api-key", result.stderr)

    def test_requires_https_for_remote_endpoints(self) -> None:
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            silentflow.validate_base_url("http://example.com")

    def test_allows_http_for_local_development(self) -> None:
        self.assertEqual(
            silentflow.validate_base_url("http://127.0.0.1:8787/"),
            "http://127.0.0.1:8787",
        )

    def test_rejects_credentials_queries_and_fragments(self) -> None:
        with self.assertRaisesRegex(ValueError, "credentials"):
            silentflow.validate_base_url("https://user:pass@example.com")
        with self.assertRaisesRegex(ValueError, "query string"):
            silentflow.validate_base_url("https://example.com?token=secret")
        with self.assertRaisesRegex(ValueError, "query string"):
            silentflow.validate_base_url("https://example.com/#fragment")

    def test_delete_requires_an_explicit_confirmation(self) -> None:
        parser = silentflow.build_parser()
        args = parser.parse_args(["delete", "2026/08/image.png"])
        with self.assertRaisesRegex(ValueError, "requires --yes"):
            silentflow.execute(args, "sf_agent_test", "https://slnt.dev")

    def test_dry_run_never_makes_a_request(self) -> None:
        parser = silentflow.build_parser()
        args = parser.parse_args(["delete", "2026/08/image.png", "--dry-run"])
        self.assertEqual(
            silentflow.execute(args, "sf_agent_test", "https://slnt.dev"),
            {
                "dry_run": True,
                "key": "2026/08/image.png",
                "endpoint": "https://slnt.dev/v1/files/2026/08/image.png",
            },
        )


if __name__ == "__main__":
    unittest.main()
