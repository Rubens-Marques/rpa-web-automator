#!/usr/bin/env python3
"""RPA Web Automator adapter for Nexus Harness v4 Quality/Security gates.

Does not call ``nexus quality run --profile standard`` (Biome). Full-app lint,
typecheck, unit, build, and deploy stay on legacy CI. This adapter runs the
gate contract test plus ``py_compile`` of itself, then canonical Trivy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _discover_harness_src() -> Path:
    env = (os.environ.get("NEXUS_HARNESS_ROOT") or "").strip()
    candidates: list[Path] = []
    if env:
        p = Path(env)
        candidates.append(p)
        candidates.append(p / "src")
    for entry in (os.environ.get("PYTHONPATH") or "").split(os.pathsep):
        if entry.strip():
            candidates.append(Path(entry.strip()))
    home = Path.home()
    install = home / ".nexus-harness" / "install"
    if install.is_dir():
        versions = sorted(
            (
                child
                for child in install.iterdir()
                if child.is_dir() and "rollback" not in child.name
            ),
            key=lambda item: item.name,
            reverse=True,
        )
        for version in versions:
            candidates.append(version / "src")
    candidates.extend(
        [
            home / ".nexus-harness" / "runtime" / "src",
            Path("/opt/nexus-harness/src"),
            Path("/opt/nexus-harness/current/src"),
        ]
    )
    for candidate in candidates:
        if (candidate / "nexus_harness" / "__init__.py").is_file():
            return candidate
    raise SystemExit(
        "nexus_harness not found. Set NEXUS_HARNESS_ROOT to the engine root "
        "(directory containing src/nexus_harness)."
    )


def _ensure_harness() -> Path:
    src = _discover_harness_src()
    sys.path.insert(0, str(src))
    return src


def _run(argv: list[str], *, cwd: Path = ROOT) -> int:
    completed = subprocess.run(argv, cwd=cwd, check=False)
    return int(completed.returncode)


def _repo_identity():
    try:
        from nexus_harness.identity import IdentityError, resolve_repo_identity
    except ImportError as exc:
        raise SystemExit(
            "change identity fail-closed: nexus_harness.identity is not installed"
        ) from exc

    try:
        identity = resolve_repo_identity(env=os.environ, cwd=ROOT)
    except IdentityError as exc:
        raise SystemExit(f"change identity fail-closed: {exc}") from exc
    print(f"checkout_sha={identity.checkout_sha}")
    print(f"change_head_sha={identity.change_head_sha}")
    print("freshness_target=change_head_sha")
    if identity.base_sha:
        print(f"base_sha={identity.base_sha}")
    if identity.merge_sha:
        print(f"merge_sha={identity.merge_sha}")
    return identity


def _diff_hash(identity=None) -> str:
    if identity is None:
        identity = _repo_identity()
    return hashlib.sha256(identity.change_head_sha.encode("utf-8")).hexdigest()


def _identity_fields(identity) -> dict:
    payload = {
        "change_head_sha": identity.change_head_sha,
        "checkout_sha": identity.checkout_sha,
        "freshness_target": "change_head_sha",
        "diff_hash": _diff_hash(identity),
    }
    if identity.base_sha:
        payload["base_sha"] = identity.base_sha
    if identity.merge_sha:
        payload["merge_sha"] = identity.merge_sha
    return payload


def cmd_affected(base: str, head: str, output: Path) -> int:
    src = _ensure_harness()
    identity = _repo_identity()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    env.setdefault(
        "NEXUS_CI_PROFILE", str(ROOT / "profiles" / "projects" / "rpa-web-automator.toml")
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-P",
            "-m",
            "nexus_harness",
            "ci",
            "affected",
            "--base",
            base,
            "--head",
            head,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        check=False,
    )
    if int(completed.returncode) == 0:
        print(
            f"identity checkout_sha={identity.checkout_sha} "
            f"change_head_sha={identity.change_head_sha}"
        )
    return int(completed.returncode)


def _load_plan(path: Path) -> dict:
    if not path.is_file():
        return {"components": [], "checks": [], "images": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _plan_empty(plan: dict) -> bool:
    return not (plan.get("components") or plan.get("checks") or plan.get("images"))


def cmd_quality(from_affected: Path) -> int:
    _ensure_harness()
    from nexus_harness.quality import Metric, evaluate_report
    from nexus_harness.serialize import dumps_report

    identity = _repo_identity()
    plan = _load_plan(from_affected)
    if _plan_empty(plan):
        report = evaluate_report(
            [],
            profile="standard",
            diff_hash=_diff_hash(identity),
            change_head_sha=identity.change_head_sha,
            checkout_sha=identity.checkout_sha,
        )
        (ROOT / "quality-report.json").write_text(
            dumps_report(
                {
                    "gate": report.gate,
                    "steps": [],
                    "empty_affected": True,
                    **_identity_fields(identity),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        print("Quality Gate aggregate: PASS (empty affected set)")
        return 0

    steps: list[str] = []
    metrics: list[Metric] = []
    failed = False
    checks = {str(item).lower() for item in (plan.get("checks") or ())}

    def _has(*needles: str) -> bool:
        return any(any(needle in check for needle in needles) for check in checks)

    if _has("gate-contract", "contract"):
        code = _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "test_nexus_quality_gate.py"),
            ]
        )
        steps.append("gate-contract")
        metrics.append(
            Metric(
                "failing_tests",
                current=0 if code == 0 else 1,
                threshold=0,
                mode="absolute",
                direction="lower",
                required=True,
            )
        )
        if code != 0:
            failed = True
        code = _run(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(ROOT / "scripts" / "nexus_quality_gate.py"),
            ]
        )
        steps.append("py_compile")
        metrics.append(
            Metric(
                "adapter_syntax",
                current=0 if code == 0 else 1,
                threshold=0,
                mode="absolute",
                direction="lower",
                required=True,
            )
        )
        if code != 0:
            failed = True

    quality = evaluate_report(
        metrics,
        profile="standard",
        diff_hash=_diff_hash(identity),
        change_head_sha=identity.change_head_sha,
        checkout_sha=identity.checkout_sha,
    )
    if failed and quality.gate == "PASS":
        gate = "FAIL"
    else:
        gate = quality.gate
    payload = {
        "gate": gate,
        "steps": steps,
        "affected": plan,
        **_identity_fields(identity),
    }
    (ROOT / "quality-report.json").write_text(
        dumps_report(payload) + "\n", encoding="utf-8"
    )
    print(f"Quality Gate aggregate: {gate}")
    print("steps:", ", ".join(steps) or "(none)")
    return 0 if gate == "PASS" else 1


def _trivy_bin() -> str:
    env = (os.environ.get("TRIVY") or "").strip()
    if env and Path(env).is_file() and os.access(env, os.X_OK):
        return env
    found = shutil.which("trivy")
    if found:
        return found
    for candidate in (Path("/tmp/trivy"), Path.home() / "bin" / "trivy"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise SystemExit(
        "trivy not found on PATH. Install it on the nexus-ci runner "
        "(do not download via curl|sh from this job)."
    )


def cmd_security() -> int:
    _ensure_harness()
    from nexus_harness.security import normalize_trivy
    from nexus_harness.serialize import dumps_report

    identity = _repo_identity()
    trivy = _trivy_bin()
    out = ROOT / "trivy.json"
    code = subprocess.run(
        [
            trivy,
            "fs",
            "--scanners",
            "vuln,secret,misconfig",
            "--format",
            "json",
            "--skip-dirs",
            "node_modules",
            "--skip-dirs",
            "vendor",
            "--skip-dirs",
            "venv",
            "--skip-dirs",
            ".bundle",
            "--skip-dirs",
            ".worktrees",
            "--output",
            str(out),
            ".",
        ],
        cwd=ROOT,
        check=False,
    )
    # Trivy exits 0/1 depending on findings; canonical gate is normalize_trivy.
    if code.returncode not in (0, 1) or not out.is_file():
        print("Security Gate: FAIL (trivy did not produce JSON)")
        return 1
    payload = json.loads(out.read_text(encoding="utf-8") or "{}")
    report = normalize_trivy(
        payload,
        diff_hash=_diff_hash(identity),
        change_head_sha=identity.change_head_sha,
        checkout_sha=identity.checkout_sha,
    )
    (ROOT / "security-report.json").write_text(
        dumps_report(report.to_dict()) + "\n", encoding="utf-8"
    )
    print(f"Security Gate: {report.gate}")
    print("counts:", json.dumps(report.counts))
    return 0 if report.gate == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--affected-only", action="store_true")
    parser.add_argument("--security-only", action="store_true")
    parser.add_argument("--from-affected", type=Path, default=ROOT / "affected.json")
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    parser.add_argument("--output", type=Path, default=ROOT / "affected.json")
    args = parser.parse_args()
    if args.affected_only:
        return cmd_affected(args.base, args.head, args.output)
    if args.security_only:
        return cmd_security()
    return cmd_quality(args.from_affected)


if __name__ == "__main__":
    raise SystemExit(main())
