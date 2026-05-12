#!/usr/bin/env python3
"""
🔧 VEIL Compilation Script
Compile VEIL with Nuitka, handle DLL paths, and automatic cleanup
"""

import os
import sys
import shutil
import subprocess
import glob
from pathlib import Path

# =========================================================
# CONFIGURATION
# =========================================================

# Version and metadata
VERSION = "1.0.0"
AUTHOR = "yo-le-zz"
COMPANY = "VEIL Security"
DESCRIPTION = "Military-Grade Secure In-Memory Vault"

# Paths
SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src"
DIST_DIR = SCRIPT_DIR / "dist"
BUILD_DIR = SCRIPT_DIR / "build"
ASSETS_DIR = SCRIPT_DIR / "assets"
DLL_SOURCE = SRC_DIR / "native" / "ram" / "build"
DLL_TARGET = DIST_DIR / "veil"

# Icon path
ICON_PATH = ASSETS_DIR / "icon.ico"

# =========================================================
# PATH DETECTION UTILITIES
# =========================================================

def get_dll_paths():
    """Detect DLL paths for different compilation modes"""
    dll_paths = []
    
    # Development mode - source directory
    if (SRC_DIR / "native" / "ram" / "ram.dll").exists():
        dll_paths.append(SRC_DIR / "native" / "ram" / "ram.dll")
    
    # Build directory
    if (DLL_SOURCE / "ram.dll").exists():
        dll_paths.append(DLL_SOURCE / "ram.dll")
    
    # Compiled mode - dist directory
    if (DLL_TARGET / "ram.dll").exists():
        dll_paths.append(DLL_TARGET / "ram.dll")
    
    # Current directory
    current_dll = Path.cwd() / "ram.dll"
    if current_dll.exists():
        dll_paths.append(current_dll)
    
    return dll_paths

def detect_execution_mode():
    """Detect if running from source, compiled onefile, or onedir"""
    executable_path = Path(sys.executable)
    
    # Check if we're running from compiled executable
    if hasattr(sys, 'frozen'):
        if getattr(sys, '_MEIPASS', None):
            # PyInstaller onefile mode
            return "pyinstaller_onefile"
        else:
            # PyInstaller onedir mode
            return "pyinstaller_onedir"
    else:
        # Development mode
        return "development"

def get_dll_path_for_mode():
    """Get appropriate DLL path based on execution mode"""
    mode = detect_execution_mode()
    
    if mode == "development":
        # Development: look in source/native/ram/build
        dll_path = SRC_DIR / "native" / "ram" / "build" / "ram.dll"
        if not dll_path.exists():
            dll_path = SRC_DIR / "native" / "ram" / "ram.dll"
        return dll_path
    
    elif mode == "pyinstaller_onedir":
        # OneDir: look in executable directory
        return Path(sys.executable).parent / "ram.dll"
    
    elif mode == "pyinstaller_onefile":
        # OneFile: look in temp directory
        import tempfile
        temp_dir = Path(getattr(sys, '_MEIPASS', ''))
        return temp_dir / "ram.dll"
    
    else:
        # Default: current directory
        return Path.cwd() / "ram.dll"

# =========================================================
# CLEANUP FUNCTIONS
# =========================================================

def cleanup_build_artifacts():
    """Clean up build artifacts (project only, not venv)"""
    print("🧹 Cleaning up build artifacts...")
    
    # Remove build directory
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"   ✅ Removed {BUILD_DIR}")
    
    # Remove dist directory
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        print(f"   ✅ Removed {DIST_DIR}")
    
    # Remove .spec files (project only)
    for spec_file in SCRIPT_DIR.glob("*.spec"):
        spec_file.unlink()
        print(f"   ✅ Removed {spec_file}")
    
    # Remove __pycache__ directories (project only)
    for pycache in SCRIPT_DIR.rglob("__pycache__"):
        # Skip venv directory
        if "env" not in str(pycache) and "venv" not in str(pycache):
            shutil.rmtree(pycache)
            print(f"   ✅ Removed {pycache}")
    
    # Remove .pyc files (project only)
    for pyc_file in SCRIPT_DIR.rglob("*.pyc"):
        # Skip venv directory
        if "env" not in str(pyc_file) and "venv" not in str(pyc_file):
            pyc_file.unlink()
    
    print("✅ Cleanup completed!")

# =========================================================
# DLL MANAGEMENT
# =========================================================

def ensure_dll_exists():
    """Ensure RAM DLL exists and copy if necessary"""
    dll_source = DLL_SOURCE / "ram.dll"
    dll_targets = [
        SRC_DIR / "native" / "ram" / "ram.dll",
        DLL_TARGET / "ram.dll"
    ]
    
    if dll_source.exists():
        for target in dll_targets:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dll_source, target)
                print(f"📦 Copied DLL to {target}")
        return True
    else:
        print(f"❌ DLL not found at {dll_source}")
        return False

def setup_dll_paths():
    """Setup DLL paths for VEIL to find the RAM library"""
    print("🔧 Setting up DLL paths...")
    
    # Update VEIL's ram.py to use correct DLL path
    ram_py_path = SRC_DIR / "vault" / "ram.py"
    
    if ram_py_path.exists():
        with open(ram_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add DLL path detection logic
        dll_detection_code = '''
# DLL Path Detection
def get_dll_path():
    """Get RAM DLL path based on execution mode"""
    import sys
    from pathlib import Path
    
    # Check if running from compiled executable
    if hasattr(sys, 'frozen'):
        if getattr(sys, '_MEIPASS', None):
            # PyInstaller one-file mode
            return Path(sys._MEIPASS) / "ram.dll"
        else:
            # PyInstaller one-dir mode
            return Path(sys.executable).parent / "ram.dll"
    else:
        # Development mode
        dll_paths = [
            Path(__file__).parent / "native" / "ram" / "build" / "ram.dll",
            Path(__file__).parent / "native" / "ram" / "ram.dll",
            Path.cwd() / "ram.dll"
        ]
        for path in dll_paths:
            if path.exists():
                return path
        return Path("ram.dll")  # Fallback

# Use detected DLL path
DLL_PATH = get_dll_path()
'''
        
        # Check if DLL detection code already exists
        if "def get_dll_path():" not in content:
            # Insert after imports
            lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_idx = i + 1
                elif line.strip() == '' and insert_idx > 0:
                    break
            
            lines.insert(insert_idx, dll_detection_code)
            
            with open(ram_py_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print("✅ Updated DLL path detection in ram.py")
        
        return True
    
    return False

# =========================================================
# COMPILATION FUNCTIONS
# =========================================================

def compile_with_nuitka():
    """Compile VEIL with Nuitka"""
    print("🔨 Compiling VEIL with Nuitka...")
    
    # Ensure DLL exists
    if not ensure_dll_exists():
        return False
    
    # Setup DLL paths
    if not setup_dll_paths():
        return False
    
    # Nuitka command - use current Python (venv)
    cmd = [
        sys.executable, "-m", "nuitka",
        
        "--standalone",
        f"--output-dir={DIST_DIR}",

        "--include-package=vault",
        "--include-package=logique",
        "--include-package=commands",
        "--include-package=config",

        "--include-package=typer",
        "--include-package=cryptography",
        "--include-package=rich",

        "--windows-icon-from-ico=" + str(ICON_PATH),

        "--remove-output",

        str(SRC_DIR / "veil.py")
    ]
    
    # Add icon if exists
    if ICON_PATH.exists():
        cmd.insert(-1, f"--windows-icon-from-ico={ICON_PATH}")
        print(f"🎨 Using icon: {ICON_PATH}")
    else:
        print("⚠️ No icon found, proceeding without icon")
    
    # Add DLL
    dll_path = get_dll_paths()[0] if get_dll_paths() else None
    if dll_path and dll_path.exists():
        cmd.insert(-1, f"--include-data-files={dll_path}=ram.dll")
        print(f"📦 Including DLL: {dll_path}")
    
    try:
        print("🚀 Running Nuitka compilation...")
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Compilation successful!")
            
            # Copy DLL to dist directory
            if dll_path and dll_path.exists():
                dist_dll = DIST_DIR / "veil" / "ram.dll"
                dist_dll.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dll_path, dist_dll)
                print(f"📦 Copied DLL to {dist_dll}")
            
            return True
        else:
            print(f"❌ Compilation failed!")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        return False

def install_dependencies():
    """Install required dependencies including Nuitka"""
    print("📦 Installing dependencies...")
    
    try:
        # Install requirements
        subprocess.run([
            "pip", "install", "-r", str(SRC_DIR / "requirements.txt")
        ], check=True, capture_output=True)
        
        # Ensure Nuitka is installed
        subprocess.run([
            "pip", "install", "nuitka>=1.4.0"
        ], check=True, capture_output=True)
        
        print("✅ Dependencies installed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

# =========================================================
# MAIN FUNCTION
# =========================================================

def main():
    """Main compilation function"""
    print("🛡️ VEIL Compilation Script")
    print("=" * 50)
    print(f"📦 Version: {VERSION}")
    print(f"👤 Author: {AUTHOR}")
    print(f"🏢 Company: {COMPANY}")
    print(f"📝 Description: {DESCRIPTION}")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not SRC_DIR.exists():
        print(f"❌ Source directory not found: {SRC_DIR}")
        return False
    
    # Check if main script exists
    main_script = SRC_DIR / "veil.py"
    if not main_script.exists():
        print(f"❌ Main script not found: {main_script}")
        return False
    
    # Clean up previous builds
    cleanup_build_artifacts()
    
    # Compile
    if compile_with_nuitka():
        print("\n🎉 Compilation completed successfully!")
        print(f"📁 Output directory: {DIST_DIR}")
        print(f"🚀 Executable: {DIST_DIR / 'veil' / 'veil.exe'}")
        
        # Show DLL info
        dll_paths = get_dll_paths()
        if dll_paths:
            print(f"📦 DLL paths found: {[str(p) for p in dll_paths]}")
        else:
            print("⚠️ No DLL paths found - make sure ram.dll is available")
        
        return True
    else:
        print("\n❌ Compilation failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
