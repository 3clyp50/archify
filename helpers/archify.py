"""Archify runtime bridge: render typed JSON candidates into standalone HTML diagrams."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from helpers import files

PLUGIN_NAME = "archify"
ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime" / "archify"
CLI = RUNTIME / "bin" / "archify.mjs"
DIAGRAM_TYPES = (
    "architecture", "workflow", "sequence", "dataflow", "lifecycle",
    "erd", "class", "tree", "timeline", "waterfall",
)
QUALITIES = ("showcase", "standard")
ID_RE = re.compile(r"^[a-z]+-[a-z0-9-]{1,48}-\d{8}-\d{6}(?:-\d+)?$")
DEFAULTS = {
    "chat_results": True,
    "canvas_enabled": False,
    "auto_open_canvas": False,
    "inline_preview": True,
    "quality": "showcase",
    "output_dir": "usr/workdir/archify",
}
RENDER_TIMEOUT = 120


def effective_config(config: dict | None) -> dict:
    merged = {**DEFAULTS, **{k: v for k, v in (config or {}).items() if v is not None}}
    if merged["quality"] not in QUALITIES:
        merged["quality"] = DEFAULTS["quality"]
    if not merged["canvas_enabled"]:
        merged["auto_open_canvas"] = False
    return merged


def node_binary() -> str | None:
    return shutil.which("node") or shutil.which("nodejs")


def node_version(binary: str | None = None) -> tuple[int, int, int] | None:
    binary = binary or node_binary()
    if not binary:
        return None
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", out.strip())
    return tuple(int(x) for x in match.groups()) if match else None  # type: ignore[return-value]


def runtime_status() -> dict:
    binary = node_binary()
    version = node_version(binary)
    return {
        "node": binary,
        "node_version": ".".join(map(str, version)) if version else None,
        "node_ok": bool(version and version[0] >= 18),
        "cli_ok": CLI.is_file(),
        "archify_version": _archify_version(),
    }


def _archify_version() -> str | None:
    try:
        return json.loads((RUNTIME / "package.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return None


def output_root(config: dict) -> Path:
    relative = str(config.get("output_dir") or DEFAULTS["output_dir"]).strip().lstrip("/")
    usr = Path(files.get_abs_path("usr")).resolve()
    target = Path(files.get_abs_path(relative)).resolve()
    if target != usr and usr not in target.parents:
        target = Path(files.get_abs_path(DEFAULTS["output_dir"])).resolve()
    return target


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:40].strip("-") or "diagram")


def new_diagram_dir(root: Path, diagram_type: str, title: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{diagram_type}-{slugify(title)}-{stamp}"
    candidate = root / base
    n = 1
    while candidate.exists():
        n += 1
        candidate = root / f"{base}-{n}"
    candidate.mkdir(parents=True)
    return candidate


def diagram_title(diagram: dict, fallback: str = "") -> str:
    meta = diagram.get("meta") if isinstance(diagram.get("meta"), dict) else {}
    for value in (fallback, meta.get("title"), diagram.get("title"), meta.get("subtitle")):
        if isinstance(value, str) and value.strip():
            return value.strip()[:120]
    return "Archify diagram"


async def _run(args: list[str], cwd: Path) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args, cwd=str(cwd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env={**_clean_env(), "NO_COLOR": "1", "ARCHIFY_NO_UPDATE_CHECK": "1"},
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), RENDER_TIMEOUT)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 124, "", f"Archify timed out after {RENDER_TIMEOUT}s"
    return process.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def _clean_env() -> dict:
    import os
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR")
    return {k: os.environ[k] for k in keep if k in os.environ}


def _parse_receipt(stdout: str) -> dict | None:
    text = stdout.strip()
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except ValueError:
        return None


def _diagnostics(receipt: dict | None, stdout: str, stderr: str) -> list[str]:
    found: list[str] = []

    def walk(value, depth=0):
        if depth > 6 or len(found) >= 25:
            return
        if isinstance(value, dict):
            message = value.get("message") or value.get("msg")
            if isinstance(message, str):
                where = value.get("path") or value.get("instancePath") or value.get("pointer") or value.get("code") or value.get("rule") or ""
                found.append(f"{where}: {message}".strip(": ") if where else message)
            for key in ("errors", "issues", "diagnostics", "findings", "validation", "warnings"):
                if key in value:
                    walk(value[key], depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, str) and depth > 0:
            found.append(value)

    walk(receipt)
    if not found:
        tail = (stderr.strip() or stdout.strip())[-2000:]
        if tail:
            found.append(tail)
    seen, unique = set(), []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item[:400])
    return unique[:25]


async def render(diagram_type: str, diagram: dict, title: str, config: dict) -> dict:
    """Validate and render a candidate. Returns a result dict with ok/errors and diagram metadata."""
    if diagram_type not in DIAGRAM_TYPES:
        raise ValueError(f"type must be one of: {', '.join(DIAGRAM_TYPES)}")
    if not isinstance(diagram, dict) or not diagram:
        raise ValueError("diagram must be a non-empty Archify JSON object")
    status = runtime_status()
    if not status["node_ok"] or not status["cli_ok"]:
        raise RuntimeError("Archify needs Node.js 18+ and the bundled runtime. Reinstall or update the plugin from Plugins.")

    quality = config["quality"]
    meta = diagram.setdefault("meta", {}) if isinstance(diagram.get("meta", {}), dict) else {}
    meta.setdefault("quality_profile", quality)
    quality = meta.get("quality_profile") if meta.get("quality_profile") in QUALITIES else quality

    name = diagram_title(diagram, title)
    root = output_root(config)
    root.mkdir(parents=True, exist_ok=True)
    folder = new_diagram_dir(root, diagram_type, name)
    slug = slugify(name)
    candidate = folder / "candidate.json"
    output = folder / f"{slug}.html"
    meta["output"] = output.name
    candidate.write_text(json.dumps(diagram, ensure_ascii=False, indent=2))

    code, stdout, stderr = await _run(
        [status["node"], str(CLI), "deliver", diagram_type, candidate.name, output.name, "--json", "--quality", quality],
        folder,
    )
    receipt = _parse_receipt(stdout)
    ok = code == 0 and output.is_file() and (receipt is None or receipt.get("ok") is not False)
    validation = (receipt or {}).get("validation") or {}
    record = {
        "id": folder.name,
        "type": diagram_type,
        "title": name,
        "quality": quality,
        "ok": ok,
        "created": datetime.now().isoformat(timespec="seconds"),
        "folder": str(folder),
        "candidate": str(candidate),
        "html": str(output) if output.is_file() else None,
        "bytes": output.stat().st_size if output.is_file() else 0,
        "checks": f"{validation.get('checksPassed', 0)}/{validation.get('checkCount', 0)}" if validation else None,
        "warnings": validation.get("warnings", 0) if validation else 0,
        "archify_version": status["archify_version"],
    }
    if not ok:
        record["errors"] = _diagnostics(receipt, stdout, stderr)
    (folder / "archify.a0.json").write_text(json.dumps(record, indent=2))
    return record


def find_diagram(diagram_id: str, config: dict) -> dict | None:
    if not isinstance(diagram_id, str) or not ID_RE.match(diagram_id):
        return None
    root = output_root(config)
    folder = (root / diagram_id).resolve()
    if folder.parent != root.resolve():
        return None
    try:
        record = json.loads((folder / "archify.a0.json").read_text())
    except (OSError, ValueError):
        return None
    html = Path(record.get("html") or "")
    if not record.get("ok") or not html.is_file() or html.resolve().parent != folder:
        return None
    record["html"] = str(html.resolve())
    return record


def list_diagrams(config: dict, limit: int = 30) -> list[dict]:
    root = output_root(config)
    if not root.is_dir():
        return []
    items = []
    for meta in root.glob("*/archify.a0.json"):
        try:
            record = json.loads(meta.read_text())
        except (OSError, ValueError):
            continue
        if record.get("ok") and record.get("html") and Path(record["html"]).is_file():
            items.append({k: record.get(k) for k in ("id", "type", "title", "created", "html", "bytes")})
    items.sort(key=lambda r: r.get("created") or "", reverse=True)
    return items[:limit]
