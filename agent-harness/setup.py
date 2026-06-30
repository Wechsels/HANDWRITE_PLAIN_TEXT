from setuptools import setup, find_namespace_packages

with open("cli_anything/handwrite/__init__.py", encoding="utf-8") as f:
    for line in f:
        if "__version__" in line:
            VERSION = line.split('"')[1]
            break
    else:
        VERSION = "1.0.0"

setup(
    name="cli-anything-handwrite",
    version=VERSION,
    description="Agent-usable CLI for the HandWrite Plain Text generator (renders text as handwritten PNGs via the real Node pipeline)",
    author="Yurui He (GitHub: Wechsels)",
    license="WNCPL-1.0",
    python_requires=">=3.11",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-handwrite=cli_anything.handwrite.handwrite_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "cli_anything.handwrite": [
            "scripts/*.mjs",
            "skills/*.md",
        ],
    },
)
