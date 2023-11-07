from setuptools import setup, find_packages


setup(
    name="codesave",
    version="0.0.4",
    packages=find_packages(),
    entry_points={"console_scripts": [
        "codesave=codesave.app:codesave_app",
        "code_from_wandb=codesave.app:wandb_app",
        "make_pyz=codesave.app:make_pyz_app"
    ]},)
