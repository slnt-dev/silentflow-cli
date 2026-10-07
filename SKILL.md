---
name: silentflow-client
description: Upload, list, inspect, and delete user-authorized SilentFlow images, check usage, or manage scoped AI agent keys through the bundled JSON CLI. Use for SilentFlow asset operations; do not use for unrelated image generation or editing.
---

# SilentFlow Client

Use `scripts/silentflow.py` as the single client for SilentFlow's versioned HTTP API. It prints JSON on stdout so results can be consumed directly by an agent.

## Authentication

Read the key from `SILENTFLOW_API_KEY` or `~/.config/silentflow/config.json`. Never ask the user to paste a key into chat, put it in a command argument, commit it, or echo it in logs.

Prefer a scoped `sf_agent_...` key with only the permissions needed for the task. A legacy `sk_...` account key is required only to create, list, or revoke agent keys.

```bash
export SILENTFLOW_API_KEY='...'
python3 <skill_dir>/scripts/silentflow.py usage
```

The default API base is `https://slnt.dev`. Respect `SILENTFLOW_API_URL` or `--api-url` when the user supplies another deployment. Always use the public URL returned by the service; do not construct it from the API hostname.

TLS verification is enabled by default. Use `--insecure` only when the user explicitly accepts the certificate risk for a specific request.

## Operations

```bash
# Upload one local regular image (v1 intentionally rejects podcast formats)
python3 <skill_dir>/scripts/silentflow.py upload /absolute/path/image.png

# List assets and inspect account state
python3 <skill_dir>/scripts/silentflow.py list --limit 20
python3 <skill_dir>/scripts/silentflow.py usage
python3 <skill_dir>/scripts/silentflow.py me

# Create a least-privilege agent key; the secret is returned once
python3 <skill_dir>/scripts/silentflow.py keys create \
  --name codex-local --scope files:read --scope files:write
python3 <skill_dir>/scripts/silentflow.py keys list
python3 <skill_dir>/scripts/silentflow.py keys revoke 12
```

Upload only the exact local file the user placed in scope. The CLI rejects symbolic links and directories. Do not add URL-fetching behavior; the service intentionally avoids server-side URL imports.

## Destructive operation

Before deletion, show the exact `public_key` and get explicit confirmation from the user. Use `--dry-run` while identifying the target. Add `--yes` only after confirmation; never infer it from a general request to inspect or manage files.

```bash
python3 <skill_dir>/scripts/silentflow.py delete '2026/08/23/example.png' --dry-run
python3 <skill_dir>/scripts/silentflow.py delete '2026/08/23/example.png' --yes
```

On failure, report the JSON `status` and `details` without retrying writes automatically. A retry of upload or delete requires the user-visible outcome to be unknown and a reasoned decision that duplicate effects are safe.
