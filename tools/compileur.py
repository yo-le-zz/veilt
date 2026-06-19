#!/usr/bin/env python3
"""
VEIL build orchestrator (replaces the old compile.py).

Builds the standalone `veilt` CLI executable with Nuitka for BOTH Windows
and Linux, in separate threads with clearly prefixed, live, colored
progress so both builds are easy to follow side by side in one terminal.

Important, honest limitation: Nuitka is not a cross-compiler. It always
needs the native C toolchain of the platform you're building FOR. So:

  - The platform you're currently running this script on is built
    LOCALLY, in its own thread, streaming real Nuitka output.
  - The OTHER platform cannot be produced on this machine. Instead, this
    script's thread for that platform dispatches the matching job in
    .github/workflows/release.yml (which runs on a real windows-latest /
    ubuntu-latest GitHub Actions runner) and prints a direct link to
    watch it - so from a single Ubuntu box you still kick off, and see
    progress for, both Windows and Linux builds in one run of this tool.

Usage
-----
    python tools/compileur.py                    # build host platform + dispatch the other
    python tools/compileur.py --target linux      # local Linux build only
    python tools/compileur.py --target windows    # local Windows build only (run ON Windows)
    GITHUB_TOKEN=ghp_xxx python tools/compileur.py --target all
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist" / "standalone"
ASSETS_DIR = ROOT / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"
ENTRY_SCRIPT = ROOT / "src" / "veilt" / "cli" / "main.py"

VERSION = "1.0.0"
AUTHOR = "yolezz"

GITHUB_REPO = "yo-le-zz/veilt"
GITHUB_API = "https://api.github.com"

_print_lock = threading.Lock()
_COLORS = {"LINUX": "\033[92m", "WINDOWS": "\033[94m", "SUMMARY": "\033[93m"}
_RESET = "\033[0m"


def log(channel: str, message: str) -> None:
    """Thread-safe, prefixed, colored log line - this is what makes the
    two parallel builds 'easily visible' in a single terminal."""
    color = _COLORS.get(channel, "")
    with _print_lock:
        ts = time.strftime("%H:%M:%S")
        print(f"{color}[{ts}] [{channel:^8}]{_RESET} {message}", flush=True)


@dataclass
class BuildResult:
    target: str
    success: bool
    detail: str = ""
    artifact: Optional[Path] = None


# =========================================================
# LOCAL NUITKA BUILD (only valid for target == current host platform)
# =========================================================
def build_local(target: str, result_queue: "queue.Queue[BuildResult]") -> None:
    log(target.upper(), "Starting local Nuitka build...")
    out_dir = DIST_DIR / target
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        f"--output-dir={out_dir}",
        "--include-package=veilt",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--company-name=yolezz",
        "--product-name=VEIL",
        f"--product-version={VERSION}",
        "--file-description=VEIL Secure Vault CLI",
    ]
    if target == "windows" and ICON_PATH.exists():
        cmd.append(f"--windows-icon-from-ico={ICON_PATH}")
    if target == "linux" and ICON_PATH.exists():
        cmd.append(f"--linux-icon={ICON_PATH}")
    cmd.append(str(ENTRY_SCRIPT))

    try:
        process = subprocess.Popen(
            cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log(target.upper(), line.rstrip())
        process.wait()
        if process.returncode == 0:
            log(target.upper(), f"Build finished successfully -> {out_dir}")
            result_queue.put(BuildResult(target, True, artifact=out_dir))
        else:
            log(target.upper(), f"Build FAILED (exit code {process.returncode}).")
            result_queue.put(BuildResult(target, False, detail=f"exit code {process.returncode}"))
    except FileNotFoundError:
        log(target.upper(), "Nuitka is not installed. Run: pip install nuitka")
        result_queue.put(BuildResult(target, False, detail="nuitka not installed"))
    except Exception as exc:  # noqa: BLE001 - report, never crash the other thread
        log(target.upper(), f"Unexpected error: {exc}")
        result_queue.put(BuildResult(target, False, detail=str(exc)))


# =========================================================
# REMOTE DISPATCH (GitHub Actions builds the OTHER platform natively)
# =========================================================
def build_remote(target: str, result_queue: "queue.Queue[BuildResult]") -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log(target.upper(),
            "Cannot build this platform locally (wrong host OS) and no "
            "GITHUB_TOKEN was provided to dispatch it remotely.")
        log(target.upper(),
            "Push a tag (git tag vX.Y.Z && git push --tags) and "
            ".github/workflows/release.yml will build this target on its "
            "own native runner automatically - or re-run with "
            "GITHUB_TOKEN=ghp_xxx to trigger + watch it from here.")
        result_queue.put(BuildResult(target, False, detail="no GITHUB_TOKEN - skipped"))
        return

    try:
        log(target.upper(), "Dispatching .github/workflows/release.yml on GitHub Actions...")
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/actions/workflows/release.yml/dispatches"
        payload = json.dumps({"ref": "main", "inputs": {"target": target}}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "veilt-compileur",
        })
        urllib.request.urlopen(req, timeout=15)
        log(target.upper(), "Dispatched. Live logs:")
        log(target.upper(), f"  https://github.com/{GITHUB_REPO}/actions")
        result_queue.put(BuildResult(target, True, detail="dispatched to GitHub Actions"))
    except Exception as exc:  # noqa: BLE001
        log(target.upper(), f"Failed to dispatch remote build: {exc}")
        result_queue.put(BuildResult(target, False, detail=str(exc)))


# =========================================================
# ORCHESTRATION
# =========================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="Build the VEIL standalone CLI executable (Windows + Linux).")
    parser.add_argument("--target", choices=["linux", "windows", "all"], default="all")
    args = parser.parse_args()

    host = "windows" if platform.system() == "Windows" else "linux"
    targets = ["linux", "windows"] if args.target == "all" else [args.target]

    print("=" * 72)
    print(f"  VEIL build orchestrator  -  v{VERSION}  -  author: {AUTHOR}")
    print(f"  Host platform detected : {host}")
    print(f"  Targets requested      : {', '.join(targets)}")
    print("=" * 72)

    result_queue: "queue.Queue[BuildResult]" = queue.Queue()
    threads = []

    for target in targets:
        worker = build_local if target == host else build_remote
        t = threading.Thread(target=worker, args=(target, result_queue), name=f"veilt-build-{target}")
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("=" * 72)
    log("SUMMARY", "Build summary:")
    all_ok = True
    while not result_queue.empty():
        r = result_queue.get()
        status = "OK" if r.success else "FAILED"
        all_ok = all_ok and r.success
        extra = r.artifact or r.detail or ""
        log("SUMMARY", f"  {r.target.upper():<8} {status:<7} {extra}")
    print("=" * 72)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
