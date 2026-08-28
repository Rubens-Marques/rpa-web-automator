#!/usr/bin/env python3
"""Contract tests for the Nexus Harness v4 Quality Gate adapter (no Node)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".github" / "workflows" / "nexus-quality-gate.yml"
ADAPTER = ROOT / "scripts" / "nexus_quality_gate.py"
PROJECT = ROOT / "PROJECT.md"
PROFILE_DIR = ROOT / "profiles" / "projects"


class NexusQualityGateContract(unittest.TestCase):
    def test_workflow_is_self_hosted_nexus_ci(self) -> None:
        self.assertTrue(GATE.is_file())
        workflow = GATE.read_text(encoding="utf-8")
        self.assertRegex(workflow, r"(?m)^name: Nexus Quality Gate$")
        self.assertIn("needs: runner-smoke", workflow)
        self.assertEqual(
            workflow.count(
                "github.event_name == 'workflow_dispatch' || github.event.pull_request.head.repo.full_name == github.repository"
            ),
            2,
        )
        self.assertNotIn("ubuntu-latest", workflow)
        self.assertNotIn("testcontainers", workflow.lower())
        self.assertNotIn("secrets.", workflow)
        self.assertIn(
            "/home/nexus-ci/.nexus-harness/install/4.0.0-rc2-pr-identity-09a19ed",
            workflow,
        )
        self.assertIn('root="${install}/src"', workflow)
        self.assertIn("nexus_harness/identity.py", workflow)
        self.assertIn("09a19edce78fa0ab726007f5b45380e83aabaa8f", workflow)
        self.assertIn(
            "1d2ad1798549d8605a3db2351c6b3f30421181ec77132e6cbf27abf8923d0b54",
            workflow,
        )
        self.assertIn("sha256sum", workflow)
        self.assertIn("CORE_ENGINE_HASHES=PASS", workflow)
        self.assertIn(
            "PYTHONPYCACHEPREFIX: /tmp/nexus-python-cache-${{ github.run_id }}-${{ github.run_attempt }}",
            workflow,
        )
        self.assertIn('! -path "*/__pycache__"', workflow)
        self.assertEqual(
            workflow.count('python3 -I -X "pycache_prefix=${PYTHONPYCACHEPREFIX}"'),
            6,
        )
        self.assertIn("identity_module.__file__", workflow)
        self.assertIn("python3 -I -", workflow)
        self.assertNotIn("${NEXUS_HARNESS_ROOT:-}", workflow)
        self.assertNotIn("if command -v trivy", workflow)
        self.assertIn(
            'echo "TRIVY=${RUNNER_TEMP}/bin/trivy" >> "$GITHUB_ENV"',
            workflow,
        )
        self.assertLess(
            workflow.index("Verify canonical identity"),
            workflow.index("Re-attest Canonical Core"),
        )
        script = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("resolve_repo_identity(env=os.environ, cwd=ROOT)", script)
        self.assertNotRegex(script, r"curl\s+-sfL")
        self.assertNotIn("install.sh", script)
        self.assertNotIn('["npm", "run", "lint"]', script)
        self.assertNotIn('["npm", "test"]', script)
        self.assertNotIn("vitest", script)

    def test_project_identity(self) -> None:
        project = PROJECT.read_text(encoding="utf-8")
        profiles = list(PROFILE_DIR.glob("*.toml"))
        self.assertTrue(profiles, "missing profiles/projects/*.toml")
        text = profiles[0].read_text(encoding="utf-8")
        repo = None
        project_id = None
        for line in text.splitlines():
            if line.startswith("repository"):
                repo = line.split("=", 1)[1].strip().strip('"')
            if line.startswith("id "):
                project_id = line.split("=", 1)[1].strip().strip('"')
        self.assertIsNotNone(repo)
        self.assertIsNotNone(project_id)
        self.assertIn(repo, project)
        self.assertIn(f"projects.{project_id}", project)

    def test_forwards_github_pr_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nexus-identity-") as harness_root:
            package = Path(harness_root) / "nexus_harness"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "identity.py").write_text(
                """from types import SimpleNamespace

class IdentityError(ValueError):
    pass

def resolve_repo_identity(env=None, *, cwd=None):
    if env is None or env.get("GITHUB_EVENT_NAME") != "pull_request":
        raise IdentityError("GitHub PR environment was not forwarded")
    return SimpleNamespace(
        checkout_sha=env["EXPECTED_CHECKOUT"],
        change_head_sha=env["EXPECTED_HEAD"],
        base_sha=env["EXPECTED_BASE"],
        merge_sha=env["EXPECTED_CHECKOUT"],
    )
""",
                encoding="utf-8",
            )
            program = r"""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "gate_adapter", Path("scripts/nexus_quality_gate.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
identity = module._repo_identity()
print(json.dumps(module._identity_fields(identity), sort_keys=True))
"""
            checkout = "95f68f9b1d40ecef6ad8ea3f92eca4310b183bb6"
            head = "8839831d83a0bdcc9520af98cafc544af7e84f1f"
            base = "ac1e79591457f99befc4df55a75669c49734851d"
            env = os.environ.copy()
            env["PYTHONPATH"] = harness_root
            env["GITHUB_EVENT_NAME"] = "pull_request"
            env["EXPECTED_CHECKOUT"] = checkout
            env["EXPECTED_HEAD"] = head
            env["EXPECTED_BASE"] = base
            completed = subprocess.run(
                [sys.executable, "-c", program],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            fields = json.loads(completed.stdout.strip().splitlines()[-1])
            self.assertEqual(fields["checkout_sha"], checkout)
            self.assertEqual(fields["change_head_sha"], head)
            self.assertEqual(fields["base_sha"], base)
            self.assertEqual(fields["merge_sha"], checkout)
            self.assertEqual(fields["freshness_target"], "change_head_sha")

    def test_isolated_python_bytecode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nexus-pycache-") as cache_root:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-X",
                    f"pycache_prefix={cache_root}",
                    "-c",
                    "import sys; print(sys.pycache_prefix)",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), cache_root)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    raise SystemExit(0 if result.result.wasSuccessful() else 1)
