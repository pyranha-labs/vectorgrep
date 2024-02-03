"""Set up configuration and dependencies for the hypergrep library."""

import os
from pathlib import Path

from setuptools import find_packages
from setuptools import setup

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))


def _find_version(module_path: str, file: str = "__init__.py") -> str:
    """Locate semantic version from a text file in a compatible format with setuptools."""
    # Do not import the module within the library, as this can cause an infinite import. Read manually.
    init_file = os.path.join(ROOT_DIR, module_path, file)
    with open(init_file, "rt", encoding="utf-8") as file_in:
        for line in file_in.readlines():
            if "__version__" in line:
                # Example:
                # __version__ = "1.2.3" -> 1.2.3
                version = line.split()[2].replace('"', "")
    return version


def read_requirements_file(extra_type: str | None) -> list[str]:
    """Read local requirement file basic on the type."""
    extra_type = f"-{extra_type}" if extra_type else ""
    with open(f"requirements{extra_type}.txt", encoding="utf-8") as input_file:
        lines = (line.strip() for line in input_file)
        return [req for req in lines if req and not req.startswith("#")]


setup(
    name="hypergrep",
    description="Utilities for rapid text file processing using Intel Hyperscan in Python",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    version=_find_version("hypergrep"),
    author="David Fritz",
    url="https://github.com/pyranha-labs/hypergrep",
    project_urls={
        "Issue Tracker": "https://github.com/pyranha-labs/hypergrep/issues",
        "Source Code": "https://github.com/pyranha-labs/hypergrep",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development",
        "Topic :: Scientific/Engineering",
        "Typing :: Typed",
        "Operating System :: POSIX :: Linux",
    ],
    platforms=[
        "Linux",
    ],
    test_suite="pytest",
    packages=find_packages(ROOT_DIR, include=["hypergrep*"], exclude=["*test", "tests*"]),
    include_package_data=True,
    python_requires=">=3.10",
    extras_require={
        "dev": [
            *read_requirements_file("dev"),
        ],
    },
    entry_points={
        "console_scripts": [
            "hypergrep = hypergrep.multiscanner:main",
        ]
    },
)
