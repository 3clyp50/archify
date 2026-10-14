"""Archify lifecycle: verify the bundled Node runtime; preserve user diagrams on uninstall."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = ROOT / "runtime" / "archify" / "bin" / "archify.mjs"
SAMPLE = ROOT / "runtime" / "archify" / "examples" / "holiday-planning.workflow.json"


def _node() -> str:
    node = shutil.which("node") or shutil.which("nodejs")
    if not node:
        raise RuntimeError("Archify requires Node.js 18+ on PATH in the Agent Zero runtime.")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    major = int(version.lstrip("v").split(".")[0] or 0)
    if major < 18:
        raise RuntimeError(f"Archify requires Node.js 18+; found {version}.")
    return node


def install():
    node = _node()
    if not CLI.is_file():
        raise RuntimeError("Bundled Archify runtime is missing; reinstall the plugin.")
    if SAMPLE.is_file():
        with tempfile.TemporaryDirectory(prefix="archify-install-") as tmp:
            result = subprocess.run(
                [node, str(CLI), "validate", "workflow", str(SAMPLE), "--json"],
                cwd=tmp, capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError("Archify runtime self-check failed: " + (result.stderr or result.stdout)[-500:])


def pre_update():
    return None


def uninstall():
    # The plugin owns no services or external dependencies. Rendered diagrams under the
    # configured output directory (default usr/workdir/archify) are user data and are kept.
    return None
