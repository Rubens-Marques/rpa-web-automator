#!/usr/bin/env python3
"""Cursor → Canonical Core bridge. Fail-open if the attested engine is absent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ENGINE_HOOK = (
    Path.home()
    / ".nexus-harness"
    / "install"
    / "4.0.0-rc2"
    / "hooks"
    / "nexus_event.py"
)

EVENT_MAP = {
    "sessionStart": "SessionStart",
    "preToolUse": "PreToolUse",
    "stop": "Stop",
    "preCompact": "PreCompact",
    "sessionEnd": "SessionEnd",
    "SessionStart": "SessionStart",
    "PreToolUse": "PreToolUse",
    "Stop": "Stop",
    "PreCompact": "PreCompact",
    "SessionEnd": "SessionEnd",
}


def _payload() -> dict:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("cwd", os.getcwd())
    return data


def _engine_python() -> str:
    for candidate in (
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        sys.executable,
    ):
        if Path(candidate).is_file():
            return candidate
    return "python3"


def main() -> int:
    incoming = sys.argv[1] if len(sys.argv) > 1 else "preToolUse"
    event = EVENT_MAP.get(incoming, incoming)
    if not ENGINE_HOOK.is_file():
        return 0
    payload = json.dumps(_payload(), ensure_ascii=False)
    proc = subprocess.run(
        [_engine_python(), str(ENGINE_HOOK), "--event", event],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    if event == "SessionStart":
        capsule = ""
        try:
            out = json.loads(proc.stdout or "{}")
            if isinstance(out, dict):
                capsule = str(out.get("capsule") or "")
        except json.JSONDecodeError:
            capsule = ""
        json.dump(
            {"additional_context": capsule} if capsule else {},
            sys.stdout,
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        return 0
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
