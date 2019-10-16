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
    install_requires=[
        'apscheduler @ https://github.com/edulix/apscheduler/archive/master.zip',
        'requests @ https://github.com/agoravoting/requests/archive/agora.zip',
        'Flask==0.10.1', 
        'Flask-SQLAlchemy==1.0',
        'Jinja2==2.7.2',
        'MarkupSafe==0.18',
        'SQLAlchemy==0.9.3',
        'Werkzeug==0.9.4',
        'argparse==1.2.1',
        'cffi==1.11.5',
        'ipdb==0.8',
        'ipython==1.2.1',
        'itsdangerous==0.23',
        'prettytable==0.7.2',
        'pycparser==2.10',
        'six==1.5.2',
        'uWSGI==2.0.17.1',
        'wsgiref==0.1.2',
        'cryptography==2.4.2',
        'pyOpenSSL==19.0.0',
        'enum34==1.1.6',
        'ipaddress==1.0.22'
    ],
    dependency_links = []
)
