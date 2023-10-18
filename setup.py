from setuptools import setup, find_packages


setup(
    name="codesave",
    version="0.0.3",
    packages=find_packages(),
    entry_points={"console_scripts": ["codesave=codesave.app:main"]},
)
