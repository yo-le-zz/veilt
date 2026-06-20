"""
Build glue for the native extension only. All package metadata lives in
pyproject.toml (PEP 621) - this file's sole job is to compile
src/veilt/native/engine.cpp into the `veilt._veilt_native` pybind11
extension module.
"""
import sys

from pybind11.setup_helpers import Pybind11Extension
from setuptools import find_packages, setup

cpp_args = []
link_args = []

if sys.platform == "win32":
    cpp_args = ["/EHsc", "/O2", "/std:c++17"]
else:
    cpp_args = ["-O3", "-std=c++17", "-fvisibility=hidden"]

ext_modules = [
    Pybind11Extension(
        "veilt._veilt_native",
        ["src/veilt/native/engine.cpp"],
        cxx_std=17,
        extra_compile_args=cpp_args,
        extra_link_args=link_args,
    ),
]

setup(
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    ext_modules=ext_modules,
)
