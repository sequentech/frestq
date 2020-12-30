# This file is part of frestq.
# Copyright (C) 2013-2020  Agora Voting SL <agora@agoravoting.com>

# frestq is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# frestq  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with frestq.  If not, see <http://www.gnu.org/licenses/>.
from setuptools import setup

from pip._internal.req import parse_requirements

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements("requirements.txt", session='hack')

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.requirement) for ir in install_reqs]

setup(
    name='frestq',
    version='20.01',
    author='nVotes Team',
    author_email='contact@nvotes.com',
    packages=['frestq'],
    scripts=[],
    url='http://pypi.python.org/pypi/frestq/',
    license='LICENSE.LGPL3',
    description='simple federated rest task queue',
    long_description=open('README.md').read(),
    install_requires=reqs,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"
    ],
    python_requires='>=3.5',
    dependency_links = []
)
