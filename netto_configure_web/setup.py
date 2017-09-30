# -*- coding: UTF-8 -*-

from setuptools import setup

setup(
    name="netto_configure_web",
    version="1.0",
    author="sylink",
    author_email="sylink@163.com",
    description=("netto configure web"),
    license="GPLv3",
    packages=["scripts"],
    # 需要安装的依赖
    install_requires=[
        'redis>=2.10.5',
        'pymysql'
    ]
)
