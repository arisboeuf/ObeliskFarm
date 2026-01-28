#!/usr/bin/env python3
"""
Build script for ObeliskFarm executable.

Usage:
    python build_exe.py

Requirements:
    pip install pyinstaller

Output:
    dist/ObeliskFarm_vX.X.X.exe
"""

import subprocess
import sys
import shutil
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OBELISK_DIR = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / 'dist'
BUILD_DIR = PROJECT_ROOT / 'build'
SPEC_FILE = OBELISK_DIR / 'ObeliskGemEV.spec'


def get_version():
    """Read version from __init__.py"""
    init_file = OBELISK_DIR / '__init__.py'
    with open(init_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"\'')
    return '0.0.0'


def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])


def clean_build():
    """Remove previous build artifacts"""
    print("Cleaning previous build...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)


def build_exe():
    """Build the executable using PyInstaller"""
    version = get_version()
    print(f"Building ObeliskFarm v{version}...")
    
    # Run PyInstaller with spec file
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', str(SPEC_FILE), '--clean'],
        cwd=PROJECT_ROOT
    )
    
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)
    
    # Check output
    exe_name = f'ObeliskFarm_v{version}.exe'
    exe_path = DIST_DIR / exe_name
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\nBuild successful!")
        print(f"Output: {exe_path}")
        print(f"Size: {size_mb:.1f} MB")
    else:
        print(f"Warning: Expected output not found at {exe_path}")


def main():
    print("=" * 50)
    print("ObeliskFarm Build Script")
    print("=" * 50)
    
    # Check/install PyInstaller
    if not check_pyinstaller():
        install_pyinstaller()
    
    # Clean and build
    clean_build()
    build_exe()
    
    print("\nDone!")


if __name__ == '__main__':
    main()
