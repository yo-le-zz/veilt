"""
Build glue for the native extension only. All package metadata lives in
pyproject.toml (PEP 621) - this file's sole job is to compile
src/veilt/native/engine.cpp into the `veilt._veilt_native` extension module
and build the `vault` RAM shared library before packaging.
"""
from pathlib import Path
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import find_packages, setup
import subprocess
import sys

class BuildExtWithRam(build_ext):
    def run(self):
        self.build_ram_shared()
        super().run()

    def build_ram_shared(self):
        root = Path(__file__).resolve().parent
        ram_src = root / "src" / "native" / "ram" / "ram.cpp"
        target_dir = root / "src" / "vault" / "native" / "ram" / "build"
        target_dir.mkdir(parents=True, exist_ok=True)

        if sys.platform == "win32":
            lib_name = "ram.dll"
            compile_cmd = [
                "g++",
                "-shared",
                "-o",
                str(target_dir / lib_name),
                str(ram_src),
                "-O2",
                "-s",
                "-std=c++17",
            ]
        else:
            lib_name = "ram.so"
            compile_cmd = [
                "g++",
                "-shared",
                "-o",
                str(target_dir / lib_name),
                str(ram_src),
                "-O2",
                "-s",
                "-std=c++17",
                "-fPIC",
            ]

        self.announce(f"Compiling RAM shared library: {' '.join(compile_cmd)}", level=3)
        subprocess.check_call(compile_cmd)

cpp_args = []
link_args = []

if sys.platform == "win32":
    # /EHsc: standard C++ exception handling (required by pybind11)
    # /O2  : optimize for speed (release builds)
    cpp_args = ["/EHsc", "/O2", "/std:c++17"]
else:
    cpp_args = ["-O3", "-std=c++17", "-fvisibility=hidden"]
    if sys.platform != "darwin":
        # Statically link the C++ runtime where reasonable to avoid
        # "missing DLL/.so" issues on minimal target systems - this is
        # exactly the class of bug that broke the previous MSI builds.
        link_args = []

ext_modules = [
    Pybind11Extension(
        "veilt._veilt_native",
        ["src/native/engine.cpp"],
        cxx_std=17,
        extra_compile_args=cpp_args,
        extra_link_args=link_args,
    ),
]

setup(
    package_dir={"veilt": "src"},
    packages=["veilt"] + [f"veilt.{pkg}" for pkg in find_packages(where="src", exclude=["tests", "tests.*"])],
    include_package_data=True,
    ext_modules=ext_modules,
    cmdclass={"build_ext": BuildExtWithRam},
)
