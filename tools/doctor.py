#!/usr/bin/env python3
"""Check that this install can actually run, on any machine.

    python tools/doctor.py          # checks and a verdict
    python tools/doctor.py --json   # machine-readable

A fresh clone fails in a few boring ways, and every one of them looks like a
broken app. This says which one it is, in plain words:

  - python packages that are not installed
  - the skill library missing (it is shipped code; .gitignore must not hide it)
  - the frontend not built, or its layout data missing
  - projects/ not writable

Exit code is 0 when everything is fine, 1 when something must be fixed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "app" / "backend"))
sys.stdout.reconfigure(encoding="utf-8")

CHECKS = [
    ("python", lambda: sys.version_info >= (3, 10),
     f"Python {sys.version.split()[0]} — 3.10 or newer is required"),
    ("node", lambda: shutil.which("node") is not None or shutil.which("node.exe") is not None,
     "Node.js on PATH (the frontend needs it)"),
    ("skills", None, "the skill library shipped with the repo"),
    ("frontend-deps", None, "frontend dependencies installed"),
    ("layout-data", None, "the drawn layout data the picker loads"),
    ("projects-writable", None, "projects/ is writable"),
]

REQUIRED_PY = ("fastapi", "uvicorn", "pydantic", "httpx")


def run() -> list[dict]:
    out: list[dict] = []

    def add(name: str, ok: bool, detail: str, fix: str = "") -> None:
        out.append({"name": name, "ok": bool(ok), "detail": detail, "fix": fix})

    py_ok = sys.version_info >= (3, 10)
    add("python", py_ok, f"Python {sys.version.split()[0]}",
        "install Python 3.10 or newer" if not py_ok else "")

    node = shutil.which("node") or shutil.which("node.exe")
    add("node", node is not None, str(node or "not found"),
        "install Node.js 18 or newer" if not node else "")

    missing = [m for m in REQUIRED_PY
               if importlib.util.find_spec(m) is None]
    add("python-packages", not missing,
        "all backend packages import" if not missing else "missing: " + ", ".join(missing),
        f"run: python -m pip install -r {REPO / 'app' / 'backend' / 'requirements.txt'}"
        if missing else "")

    # the skill library — code that ships, not local state
    from app import skills

    pf = skills.preflight()
    add("skill-library", pf["ok"],
        f"{pf['assets']} files under {pf['origin']}",
        "the clone is incomplete — .opencode/skills is being ignored. Remove "
        "'.opencode/' from .gitignore and commit .opencode/skills"
        if not pf["ok"] else "")

    fe = REPO / "app" / "frontend"
    add("frontend-deps", (fe / "node_modules").is_dir(),
        "node_modules present" if (fe / "node_modules").is_dir() else "node_modules missing",
        "run: cd app/frontend && npm install" if not (fe / "node_modules").is_dir() else "")

    layouts = fe / "public" / "layouts.json"
    add("layout-data", layouts.is_file() and layouts.stat().st_size > 1000,
        f"{layouts.name} {layouts.stat().st_size if layouts.is_file() else 0} bytes"
        if layouts.is_file() else "layouts.json missing",
        "run: python tools/dump_layouts.py" if not layouts.is_file() else "")

    # projects/ must exist and be writable — the app stores every artifact there
    proj = REPO / "projects"
    try:
        proj.mkdir(parents=True, exist_ok=True)
        probe = proj / ".write-test"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        ok, detail = True, str(proj)
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, str(exc)
    add("projects-writable", ok, detail,
        "create the folder and grant write access" if not ok else "")

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = run()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            mark = "ok  " if r["ok"] else "FAIL"
            print(f"[{mark}] {r['name']:<18} {r['detail']}")
            if not r["ok"] and r["fix"]:
                print(f"       → {r['fix']}")
        bad = [r for r in rows if not r["ok"]]
        print()
        print("ready to run." if not bad else f"{len(bad)} thing(s) to fix before running.")
    return 1 if any(not r["ok"] for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
