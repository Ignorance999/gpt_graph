# -*- coding: utf-8 -*-
"""
Created on Fri Mar 29 11:12:02 2024

@author: User
"""

# setup.py
import os
from setuptools import setup, find_packages

setup(
    name="gpt_graph",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "gpt_graph": [
            "config/*.toml",
            "tests/inputs/*.txt",
        ],
    },
    include_package_data=True,
)
