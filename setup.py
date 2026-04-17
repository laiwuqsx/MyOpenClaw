from setuptools import find_packages, setup


def parse_requirements(filename: str) -> list[str]:
    with open(filename, "r", encoding="utf-8") as fh:
        return [
            line.strip()
            for line in fh
            if line.strip() and not line.startswith("#")
        ]


setup(
    name="myopenclaw",
    version="0.1.0",
    description="A transparent local agent runtime for controllable AI workflows.",
    packages=find_packages(),
    install_requires=parse_requirements("requirements.txt"),
    entry_points={
        "console_scripts": [
            "myopenclaw=entry.cli:main",
        ],
    },
)
