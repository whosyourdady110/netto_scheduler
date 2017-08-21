#!/usr/bin/env python3
# coding=utf-8

from setuptools import setup

setup(
    name="netto_scheduler_web",
    version="1.0",
    author="sylink",
    author_email="sylink@163.com",
    description=("netto scheduler web"),
    license="GPLv3",
    packages=["scripts"],
    # 需要安装的依赖
    install_requires=[
        'redis>=2.10.5'
    ]
)
