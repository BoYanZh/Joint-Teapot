import os
import re
from typing import List

from setuptools import find_packages, setup


def get_version(package: str) -> str:
    """
    Return package version as listed in `__version__` in `__main__.py`.
    """
    path = os.path.join(package, "__main__.py")
    main_py = open(path, "r", encoding="utf8").read()
    match = re.search("__version__ = ['\"]([^'\"]+)['\"]", main_py)
    if match is None:
        return "0.0.0"
    return match.group(1)


def get_long_description() -> str:
    """
    Return the README.
    """
    return open("README.md", "r", encoding="utf8").read()


def get_install_requires() -> List[str]:
    return open("requirements.txt").read().splitlines()


setup(
    name="joint-teapot",
    version=get_version("joint_teapot"),
    url="https://github.com/BoYanZh/joint-teapot",
    license="MIT",
    description="A handy tool for TAs in JI to handle stuffs through Gitea, Canvas, and JOJ.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="BoYanZh",
    author_email="bomingzh@sjtu.edu.cn",
    maintainer="BoYanZh",
    maintainer_email="bomingzh@sjtu.edu.cn",
    packages=find_packages(),
    python_requires=">=3.6",
    entry_points={"console_scripts": ["joint-teapot=joint_teapot:main"]},
    install_requires=get_install_requires(),
)
