#!/usr/bin/env python3
"""AI-friendly SilentFlow CLI with JSON output and no third-party dependencies."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Iterable


VERSION = "1.1.0"
DEFAULT_API_URL = "https://slnt.dev"
DEFAULT_CONFIG = Path.home() / ".config" / "silentflow" / "config.json"
LEGACY_CONFIGS = (
    Path.home() / ".baoyu-skills" / "silentflow-client" / "config.json",
)
VALID_SCOPES = ("files:read", "files:write", "files:delete")
REQUEST_TIMEOUT_SECONDS = 30


class ApiError(RuntimeError):
    def __init__(self, status: int | None, detail: Any):
        self.status = status
        self.detail = detail
        message = f"HTTP {status}" if status else "Network error"
        super().__init__(message)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward bearer credentials through redirects."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def load_config(path: Path | None = None) -> dict[str, Any]:
    candidates = [path] if path else [DEFAULT_CONFIG, *LEGACY_CONFIGS]
    for candidate in candidates:
        if candidate and candidate.is_file():
            with candidate.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            if not isinstance(value, dict):
                raise ValueError(f"Config must be a JSON object: {candidate}")
            return value
    return {}


def ssl_context(insecure: bool) -> ssl.SSLContext:
    if insecure:
        print(
            "warning: TLS certificate verification is disabled for this request",
            file=sys.stderr,
        )
        return ssl._create_unverified_context()
    return ssl.create_default_context()


def parse_json(raw: bytes) -> Any:
    if not raw:
        return {}
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"detail": text}


def request_json(
    method: str,
    endpoint: str,
    token: str,
    *,
    body: bytes | None = None,
    content_type: str | None = None,
    insecure: bool = False,
) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": f"silentflow-cli/{VERSION}",
    }
    if content_type:
        headers["Content-Type"] = content_type

    request = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method=method,
    )

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl_context(insecure)),
        NoRedirect(),
    )

    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return parse_json(response.read())
    except urllib.error.HTTPError as error:
        raise ApiError(error.code, parse_json(error.read())) from None
    except urllib.error.URLError as error:
        raise ApiError(None, str(error.reason)) from None


def json_body(value: dict[str, Any]) -> tuple[bytes, str]:
    return json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json"


def multipart_file(path: Path) -> tuple[bytes, str]:
    boundary = f"----SilentFlow{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    filename = path.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
    return prefix + path.read_bytes() + suffix, f"multipart/form-data; boundary={boundary}"


def endpoint(base_url: str, path: str, query: dict[str, Any] | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        present = {key: value for key, value in query.items() if value is not None}
        if present:
            url = f"{url}?{urllib.parse.urlencode(present)}"
    return url


def validate_base_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    is_local = parsed.hostname in ("localhost", "127.0.0.1")
    if parsed.username or parsed.password:
        raise ValueError("API URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("API URL must not contain a query string or fragment")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_local):
        raise ValueError("API URL must use HTTPS (HTTP is allowed only for localhost)")
    if not parsed.hostname:
        raise ValueError("API URL must include a hostname")
    return value.rstrip("/")


def require_regular_file(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_symlink():
        raise ValueError("Refusing to upload a symbolic link")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"Not a regular file: {resolved}")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="silentflow",
        description="Manage SilentFlow images with machine-readable JSON output.",
    )
    parser.add_argument("--api-url", help=f"API base URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--config", type=Path, help=f"Config JSON (default: {DEFAULT_CONFIG})")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS verification (unsafe)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--version", action="version", version=VERSION)

    commands = parser.add_subparsers(dest="command", required=True)

    upload = commands.add_parser("upload", help="Upload one local image")
    upload.add_argument("file")

    listing = commands.add_parser("list", help="List uploaded files")
    listing.add_argument("--limit", type=int, default=20)
    listing.add_argument("--cursor", type=int)
    listing.add_argument("--date-from")

    commands.add_parser("usage", help="Show storage and traffic usage")
    commands.add_parser("me", help="Show the authenticated account")

    delete = commands.add_parser("delete", help="Permanently delete one file")
    delete.add_argument("key")
    delete.add_argument("--yes", action="store_true", help="Confirm permanent deletion")
    delete.add_argument("--dry-run", action="store_true", help="Show the target without deleting")

    keys = commands.add_parser("keys", help="Manage scoped AI agent keys")
    key_commands = keys.add_subparsers(dest="key_command", required=True)
    key_commands.add_parser("list", help="List agent keys (never returns secret values)")
    create = key_commands.add_parser("create", help="Create an agent key; secret is returned once")
    create.add_argument("--name", required=True)
    create.add_argument(
        "--scope",
        action="append",
        choices=VALID_SCOPES,
        default=[],
        help="Repeat for each scope; defaults to read + write",
    )
    revoke = key_commands.add_parser("revoke", help="Revoke an agent key")
    revoke.add_argument("id", type=int)

    return parser


def execute(args: argparse.Namespace, token: str, base_url: str) -> Any:
    if args.command == "upload":
        path = require_regular_file(args.file)
        body, content_type = multipart_file(path)
        return request_json(
            "POST",
            endpoint(base_url, "/v1/files"),
            token,
            body=body,
            content_type=content_type,
            insecure=args.insecure,
        )

    if args.command == "list":
        return request_json(
            "GET",
            endpoint(
                base_url,
                "/v1/files",
                {"limit": args.limit, "cursor": args.cursor, "date_from": args.date_from},
            ),
            token,
            insecure=args.insecure,
        )

    if args.command in ("usage", "me"):
        return request_json(
            "GET",
            endpoint(base_url, f"/v1/{args.command}"),
            token,
            insecure=args.insecure,
        )

    if args.command == "delete":
        target = endpoint(base_url, f"/v1/files/{urllib.parse.quote(args.key, safe='/')}")
        if args.dry_run:
            return {"dry_run": True, "key": args.key, "endpoint": target}
        if not args.yes:
            raise ValueError("Deletion requires --yes after the user confirms the exact key")
        return request_json("DELETE", target, token, insecure=args.insecure)

    if args.command == "keys":
        if args.key_command == "list":
            return request_json(
                "GET",
                endpoint(base_url, "/v1/agent-keys"),
                token,
                insecure=args.insecure,
            )
        if args.key_command == "create":
            scopes: Iterable[str] = args.scope or ("files:read", "files:write")
            body, content_type = json_body({"name": args.name, "scopes": list(scopes)})
            return request_json(
                "POST",
                endpoint(base_url, "/v1/agent-keys"),
                token,
                body=body,
                content_type=content_type,
                insecure=args.insecure,
            )
        if args.key_command == "revoke":
            return request_json(
                "DELETE",
                endpoint(base_url, f"/v1/agent-keys/{args.id}"),
                token,
                insecure=args.insecure,
            )

    raise ValueError(f"Unsupported command: {args.command}")


def emit(value: Any, pretty: bool) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2 if pretty else None))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        token = str(os.environ.get("SILENTFLOW_API_KEY") or config.get("api_key") or "").strip()
        if not token:
            raise ValueError(
                "Missing SILENTFLOW_API_KEY. Set it in the environment or the config file; "
                "do not paste secrets into chat."
            )
        configured_url = args.api_url or os.environ.get("SILENTFLOW_API_URL") or config.get("api_url") or DEFAULT_API_URL
        base_url = validate_base_url(str(configured_url))
        result = execute(args, token, str(base_url))
        emit(result, args.pretty)
        return 0
    except ApiError as error:
        emit({"error": str(error), "status": error.status, "details": error.detail}, args.pretty)
        return 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        emit({"error": str(error)}, args.pretty)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
