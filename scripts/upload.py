#!/usr/bin/env python3
"""Compatibility wrapper for the pre-1.1 SilentFlow upload command."""

from __future__ import annotations

import argparse

from silentflow import main


def compatibility_main() -> int:
    parser = argparse.ArgumentParser(description="Upload a file to SilentFlow.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--api-url")
    parser.add_argument("--strict-ssl", action="store_true", help="TLS verification is already the default")
    parser.add_argument("--insecure", action="store_true")
    args = parser.parse_args()

    forwarded: list[str] = []
    if args.api_url:
        forwarded.extend(["--api-url", args.api_url])
    if args.insecure:
        forwarded.append("--insecure")
    forwarded.extend(["upload", args.file])
    return main(forwarded)


if __name__ == "__main__":
    raise SystemExit(compatibility_main())
