#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a reproducible, offline release bundle (Prompt 31).

What this script does — and what it deliberately does **not** do:

* creates a *portable* bundle (source + launcher + docs + checksums) that runs
  on any machine with Python 3.8+ — no installer, no admin rights, no network;
* writes the SBOM (components + licences) and the release notes next to it;
* computes SHA-256 checksums for every shipped file;
* optionally builds the PyInstaller EXE with ``--exe``.  If PyInstaller is not
  installed the script reports ``EXE: NOT RUN`` and continues — the EXE is
  never faked.

The user data directory is never part of the bundle: the application stores
its data outside the installation (see ``sorting_os/paths.py``).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE_DIR = os.path.join(ROOT, "dist")
STAGE_NAME = "SORTING-OS-{version}"

#: components that are shipped, with their licence
COMPONENTS = [
    ("Python runtime", ">=3.8", "PSF License", "system (not bundled)"),
    ("tkinter / Tcl-Tk", "bundled with CPython", "BSD-like (Tcl/Tk)", "system"),
    ("sqlite3", "standard library", "Public Domain", "system"),
    ("sorting_os (this repository)", "0.2.0", "see LICENSE file", "bundled"),
]

LAUNCHER = """@echo off
rem SORTING OS - portable launcher (Windows)
setlocal
set "APPDIR=%~dp0"
cd /d "%APPDIR%desktop"
if "%SORTING_OS_HOME%"=="" set "SORTING_OS_HOME=%LOCALAPPDATA%\\SortingOS"
python -m sorting_os --gui
if errorlevel 1 (
  echo.
  echo اجرا ناموفق بود. با python -m sorting_os --doctor جزئیات را بررسی کنید.
  pause
)
endlocal
"""

RELEASE_NOTES = """# SORTING OS {version} — Release Notes

تاریخ ساخت: {date}
منبع: commit {commit}

## این بسته چیست
بستهٔ «portable» از سورس SORTING OS: بدون نصب‌کننده، بدون نیاز به دسترسی admin و بدون
هرگونه اتصال شبکه. برای اجرا Python 3.8+ (همراه tkinter) لازم است.

## مسیر داده
داده‌های کاربر در مسیر دادهٔ محلی سیستم‌عامل ذخیره می‌شود و با بسته مخلوط نمی‌شود:
- Windows: `%LOCALAPPDATA%\\SortingOS`
- Linux/macOS: `$XDG_DATA_HOME/sorting-os` یا `~/.local/share/sorting-os`
- بازنویسی با متغیر محیطی `SORTING_OS_HOME` ممکن است.

## مهاجرت و ارتقا
نسخهٔ schema در جدول `schema_meta` نگهداری می‌شود و با اجرای برنامه به‌صورت خودکار و
تراکنشی ارتقا می‌یابد. پیش از هر ارتقای نسخه، یک backup بگیرید:
`python -m sorting_os --doctor` و سپس از صفحهٔ پشتیبان‌گیری استفاده کنید.

## محدودیت‌های شناخته‌شده
- سازگاری با Windows 7 SP1 x64 هنوز **تأیید نشده** (NOT VERIFIED ON TARGET OS).
- رابط گرافیکی در محیط ساخت این بسته اجرا نشده است.
- تصمیم‌های تجاری (درصد صافی، مدل مالکیت کالا، بهای تمام‌شده، کدینگ نهایی، سال مالی)
  تأیید نشده‌اند و در `docs/open-decisions.md` فهرست شده‌اند.
"""


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


def read_version():
    init_file = os.path.join(ROOT, "desktop", "sorting_os", "__init__.py")
    with open(init_file, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.0.0"


def copy_tree(source, target, ignore=("__pycache__", "*.pyc", ".git")):
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*ignore))


def build_bundle(version, commit, date):
    stage = os.path.join(RELEASE_DIR, STAGE_NAME.format(version=version))
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    # application code
    copy_tree(os.path.join(ROOT, "desktop"), os.path.join(stage, "desktop"))
    # documentation that must travel with the bundle
    for name in ("README.md", "LICENSE", "CHANGELOG.md"):
        source = os.path.join(ROOT, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(stage, name))
    for folder in ("docs", "contracts"):
        source = os.path.join(ROOT, folder)
        if os.path.isdir(source):
            copy_tree(source, os.path.join(stage, folder))

    with open(os.path.join(stage, "run_app.bat"), "w", encoding="utf-8", newline="\r\n") as handle:
        handle.write(LAUNCHER)
    with open(os.path.join(stage, "RELEASE_NOTES.md"), "w", encoding="utf-8") as handle:
        handle.write(RELEASE_NOTES.format(version=version, date=date, commit=commit))

    # SBOM
    sbom = ["# SBOM — SORTING OS %s" % version, "",
            "| Component | Version | Licence | Bundled |", "|---|---|---|---|"]
    for name, ver, licence, bundled in COMPONENTS:
        sbom.append("| %s | %s | %s | %s |" % (name, ver, licence, bundled))
    sbom.extend(["", "Third-party runtime dependencies: **none** (standard library only).",
                 "", "Fonts and icons: no network assets; the UI uses the fonts of the operating system."])
    with open(os.path.join(stage, "SBOM.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(sbom) + "\n")

    # checksums for every shipped file
    entries = []
    for dirpath, _dirnames, filenames in os.walk(stage):
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if name == "SHA256SUMS.txt":
                continue
            entries.append("%s  %s" % (sha256(path),
                                       os.path.relpath(path, stage).replace(os.sep, "/")))
    with open(os.path.join(stage, "SHA256SUMS.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(entries)) + "\n")

    # zip the bundle
    archive = os.path.join(RELEASE_DIR, STAGE_NAME.format(version=version) + ".zip")
    if os.path.exists(archive):
        os.remove(archive)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for dirpath, _dirnames, filenames in os.walk(stage):
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                zip_file.write(path, os.path.relpath(path, RELEASE_DIR))
    return stage, archive


def build_exe(version):
    """Try to build the PyInstaller EXE.  Never fakes success."""
    spec = os.path.join(ROOT, "desktop", "sorting_os.spec")
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        return "EXE: NOT RUN — PyInstaller is not installed in this environment."
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", spec]
    result = subprocess.run(command, cwd=os.path.join(ROOT, "desktop"),
                            capture_output=True, text=True)
    if result.returncode != 0:
        return "EXE: FAILED — %s" % (result.stderr.strip().splitlines()[-1:] or ["unknown"])
    return "EXE: built (verify on the target machine before release)"


def main(argv=None):
    global RELEASE_DIR  # the builders use the module level path

    default_out = RELEASE_DIR
    parser = argparse.ArgumentParser(description="Build the SORTING OS release bundle")
    parser.add_argument("--exe", action="store_true",
                        help="also try to build the PyInstaller EXE")
    parser.add_argument("--out", default=default_out, help="output directory")
    args = parser.parse_args(argv)

    RELEASE_DIR = os.path.abspath(args.out)
    os.makedirs(RELEASE_DIR, exist_ok=True)

    version = read_version()
    commit = git_commit()
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    stage, archive = build_bundle(version, commit, date)
    print("bundle:  %s" % stage)
    print("archive: %s" % archive)
    print("sha256:  %s" % sha256(archive))
    print("size:    %d bytes" % os.path.getsize(archive))
    if args.exe:
        print(build_exe(version))
    else:
        print("EXE: NOT RUN — use --exe on a machine that has PyInstaller installed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
