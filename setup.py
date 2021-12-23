import setuptools


name = 'dataclass-type-validator'
version = '0.1.2'
description = 'Dataclass Type Validator Library'
dependencies = []

with open("README.md", "r") as fh:
    long_description = fh.read()

packages = [
    package for package in setuptools.find_packages(exclude=["tests"])
]

setuptools.setup(
    name=name,
    version=version,
    author="Levii, inc",
    author_email="contact+oss@levii.co.jp",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/levii/dataclass-type-validator",
    packages=packages,
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=dependencies,
)
