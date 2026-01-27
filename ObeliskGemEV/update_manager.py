"""
Self-update helper for ObeliskFarm Windows EXE builds.

Flow:
- Query GitHub Releases for latest stable release
- If newer, download latest EXE next to current EXE
- Spawn a temporary .cmd that waits for the app to exit, swaps the EXE,
  and relaunches.
"""

from __future__ import annotations

import json
import os
import sys
import time
import tempfile
import urllib.request
from pathlib import Path


def _parse_version(v: str) -> tuple[int, ...]:
    v = (v or "").strip()
    if v.startswith("v"):
        v = v[1:]
    parts: list[int] = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            # Ignore non-numeric suffixes (e.g. "1.2.3-beta")
            num = ""
            for ch in p:
                if ch.isdigit():
                    num += ch
                else:
                    break
            if num:
                parts.append(int(num))
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def get_latest_release_info(repo: str, timeout_s: int = 10) -> dict | None:
    """Return latest release info dict or None on failure."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ObeliskFarm",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    tag = data.get("tag_name") or ""
    assets = data.get("assets") or []
    exe_url = None
    for a in assets:
        name = (a.get("name") or "").lower()
        if name.endswith(".exe") and "obeliskfarm" in name:
            exe_url = a.get("browser_download_url")
            break

    if not exe_url:
        # Fallback: pick any EXE
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".exe"):
                exe_url = a.get("browser_download_url")
                break

    if not exe_url:
        return None

    return {
        "version": tag.lstrip("v"),
        "tag": tag,
        "exe_url": exe_url,
        "html_url": data.get("html_url") or f"https://github.com/{repo}/releases/latest",
    }


def _download(url: str, dest: Path, timeout_s: int = 60) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ObeliskFarm"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        tmp = dest.with_suffix(dest.suffix + ".download")
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        tmp.replace(dest)


def perform_self_update(exe_url: str, latest_version: str, current_pid: int) -> None:
    """Download the new EXE and spawn a swap script, then exit."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Self-update is only available in the frozen EXE build.")

    current_exe = Path(sys.executable).resolve()
    install_dir = current_exe.parent

    new_exe = install_dir / f"ObeliskFarm_v{latest_version}.exe"
    _download(exe_url, new_exe)

    # Swap-in to the currently running filename (whatever it is called).
    target_exe = current_exe

    # Create a temp cmd script to wait for exit, replace, relaunch, then delete itself.
    script_dir = Path(tempfile.gettempdir())
    script_path = script_dir / f"obeliskfarm_update_{int(time.time())}.cmd"

    # Use tasklist to wait for PID to vanish.
    script = f"""@echo off
setlocal enableextensions
set "PID={current_pid}"
set "NEW={new_exe}"
set "TARGET={target_exe}"

:wait
for /f "tokens=2 delims=," %%A in ('tasklist /FO CSV /NH /FI "PID eq %PID%" 2^>nul') do (
  rem still running
  timeout /t 1 /nobreak >nul
  goto wait
)

rem try replace (handle AV/file locks with a few retries)
set /a tries=0
:replace
set /a tries+=1
move /y "%NEW%" "%TARGET%" >nul 2>&1
if errorlevel 1 (
  if %tries% LSS 10 (
    timeout /t 1 /nobreak >nul
    goto replace
  )
)

start "" "%TARGET%"
del "%~f0" >nul 2>&1
endlocal
"""
    script_path.write_text(script, encoding="utf-8")

    # Launch updater script detached, then terminate current process.
    os.spawnl(os.P_NOWAIT, os.environ.get("COMSPEC", "cmd.exe"), "cmd.exe", "/c", "start", "", str(script_path))
    os._exit(0)

