#!/usr/env/bin python
#-*- coding: utf-8 -*-
import os
import setuptools

module_path = os.path.join(os.path.dirname(__file__), 'json_matcher/__init__.py')
version_line = [line for line in open(module_path)
                if line.startswith('__version__')][0]

__version__ = version_line.split('__version__ = ')[-1][1:][:-2]

# scripts
scripts = [ 'bin/json_match', 'bin/jrep' ]

# packages
packages = setuptools.find_packages(exclude=['tests'])

setuptools.setup(
    name="json_matcher",
    version=__version__,
    url="https://github.daumkakao.com/greg.yim/json_matcher",

    author="Greg.YIM",
    author_email="greg.yim@kakaocorp.com",

    description="Match json with lucece-like query",
    long_description=open('README.md').read(),

    scripts=scripts,
    packages=packages,
    platforms='any',

    install_requires=[ 'pydash', 'pyparsing', 'six' ],

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
