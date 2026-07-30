from __future__ import annotations

from pathlib import Path
from setuptools import Extension, setup
import numpy as np
from Cython.Build import cythonize

ROOT = Path(__file__).resolve().parent

extra_compile_args = ["-O3", "-DNDEBUG", "-std=c++17", "-fvisibility=hidden"]
extra_link_args = []

plant_dir = ROOT / "apps" / "simulated" / "plant_models"
plant_extensions = [
    Extension(
        f"apps.simulated.plant_models.{path.stem}",
        [str(path)],
        include_dirs=[np.get_include()],
        language="c++",
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
    for path in sorted(plant_dir.glob("*.py"))
    if path.stem != "__init__"
]

extensions = [
    Extension(
        "common._mlp_mpc_native",
        [str(ROOT / "native" / "mlp_mpc_native.cpp")],
        include_dirs=[np.get_include()], language="c++",
        extra_compile_args=extra_compile_args, extra_link_args=extra_link_args,
    ),
    Extension(
        "common._honu_mpc_native",
        [str(ROOT / "native" / "honu_mpc_native.cpp")],
        include_dirs=[np.get_include()], language="c++",
        extra_compile_args=extra_compile_args, extra_link_args=extra_link_args,
    ),
    Extension(
        "common._direct_mpc_native",
        [str(ROOT / "native" / "direct_mpc_native.pyx")],
        include_dirs=[np.get_include()], language="c++",
        extra_compile_args=extra_compile_args, extra_link_args=extra_link_args,
    ),
    Extension(
        "common._physical_ode_native",
        [str(ROOT / "native" / "physical_ode_native.pyx")],
        include_dirs=[np.get_include()], language="c++",
        extra_compile_args=extra_compile_args, extra_link_args=extra_link_args,
    ),
] + plant_extensions

setup(
    name="siso-honu-native",
    version="1.1.0",
    description="Native C++ kernels and compiled physical plant models for SISO Adaptive Control",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
        },
        nthreads=0,
    ),
)
