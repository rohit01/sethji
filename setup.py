#!/usr/bin/env python
#
# Python installation script
# Author - @rohit01

import os.path
import setuptools


VERSION = '0.1'
CLASSIFIERS = [
    "Programming Language :: Python",
    "Operating System :: OS Independent",
    "Intended Audience :: System Administrators",
    "Development Status :: 4 - Beta",
    "Environment :: Web Environment",
    "Topic :: System :: Systems Administration",
    "License :: OSI Approved :: MIT License",
]

# read requirements
fname = os.path.join(os.path.dirname(__file__), 'requirements.txt')
with open(fname) as f:
    requires = list(map(lambda l: l.strip(), f.readlines()))

setuptools.setup(
    name = "sethji",
    version = VERSION,
    description = "SethJi: A flask application to generate AWS account price"
                  " reports based on tags",
    author = "Rohit Gupta",
    author_email = "hello@rohit.io",
    url = "https://github.com/rohit01/sethji",
    keywords = ["sethji", "price", "tags", "ec2", "aws"],
    install_requires = requires,
    packages=["sethji", ],
    classifiers = CLASSIFIERS,
    long_description = """
        SethJi: A flask application to generate AWS account price reports
        based on tags
    """,
)
