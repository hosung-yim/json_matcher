#!/usr/env/bin python
# -*- coding: utf-8 -*-
import os
import setuptools

module_path = os.path.join(os.path.dirname(__file__), 'json_matcher/__init__.py')

# scripts
scripts = ['bin/json_match', 'bin/jrep']

# packages
packages = setuptools.find_packages(exclude=['tests'])

setuptools.setup(
    name="json_matcher",
    version="0.0.9",
    url="https://github.com/hosung-yim/json_matcher",
    dowload_url="https://github.com/hosung-yim/json_matcher/archive/refs/tags/0.0.9.tar.gz",

    author="Greg.YIM",
    author_email="greg.yim@kakaocorp.com",

    description="Match json with lucece-like query",
    long_description=open('README.md').read(),

    scripts=scripts,
    packages=packages,
    platforms='any',

    install_requires=['pydash', 'pyparsing', 'six'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
