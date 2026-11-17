#!/usr/bin/env python3
"""Build build/lambda.zip: app code + corpus + runtime deps for Lambda (Python 3.12, arm64).

Deps are installed as manylinux aarch64 wheels so this works from macOS, Windows or x86 Linux.
The zip is deterministic (sorted entries, fixed timestamps): unchanged code -> unchanged hash ->
Terraform does not redeploy the function.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
PKG = BUILD / "package"
ZIP = BUILD / "lambda.zip"
FIXED_TIME = (2020, 1, 1, 0, 0, 0)


def main() -> None:
    shutil.rmtree(BUILD, ignore_errors=True)
    PKG.mkdir(parents=True)
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--quiet", "-r", str(ROOT / "requirements.txt"),
        "--target", str(PKG), "--platform", "manylinux2014_aarch64", "--implementation", "cp",
        "--python-version", "3.12", "--only-binary=:all:", "--no-compile",
    ], check=True)
    shutil.copytree(ROOT / "app", PKG / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data", PKG / "data")

    files = sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(PKG).as_posix(), FIXED_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    print(f"{ZIP.relative_to(ROOT)}: {len(files)} files, {ZIP.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
