# This file is part of frestq.
# Copyright (C) 2013-2016  Agora Voting SL <agora@agoravoting.com>

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

# parse_requirements() returns generator of pip.req.InstallRequirement objects
with open('requirements.txt') as f:
    install_requires = f.read().strip().split('\n')

setup(
    name='frestq',
    version='103111.8',
    author='Agora Voting Team',
    author_email='agora@agoravoting.com',
    packages=['frestq'],
    scripts=[],
    url='http://pypi.python.org/pypi/frestq/',
    license='LICENSE.AGPL3',
    description='simple federated rest task queue',
    long_description=open('README.md').read(),
    install_requires=install_requires,
    dependency_links = [
        'hg+https://edulix@bitbucket.org/edulix/apscheduler#egg=apscheduler',
        'git+https://github.com/agoravoting/requests.git@agora#egg=requests'
    ]
)
