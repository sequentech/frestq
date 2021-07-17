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

setup(
    name='frestq',
    version='20.01',
    author='nVotes Team',
    author_email='contact@nvotes.com',
    packages=['frestq'],
    scripts=[],
    url='http://pypi.python.org/pypi/frestq/',
    license='LGPL-3.0',
    description='simple federated rest task queue',
    long_description=open('README.md').read(),
    install_requires=[
        'apscheduler==3.7.0',
        'requests==2.22.0',
        'Flask==1.0.0',
        'Flask-SQLAlchemy==2.4.4',
        'Jinja2==2.11.3',
        'MarkupSafe==0.23',
        'SQLAlchemy==1.3.23',
        'Werkzeug==1.0.1',
        'argparse==1.2.1',
        'cffi==1.14.4',
        'ipdb==0.13.9',
        'ipython==7.9.0',
        'itsdangerous==0.24',
        'prettytable==0.7.2',
        'pycparser==2.10',
        'uwsgi==2.0.18',
        'cryptography==3.3.2',
        'pyOpenSSL==18.0.0',
        'enum34==1.1.6',
        'ipaddress==1.0.22'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"
    ],
    python_requires='>=3.5',
    dependency_links = []
)
