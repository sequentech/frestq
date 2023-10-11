# Copyright (C) 2014-2021  Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

from setuptools import setup

setup(
    name='frestq',
    version='10.0.1',
    author='Sequent Tech Inc',
    author_email='legal@sequentech.io',
    packages=['frestq'],
    scripts=[],
    url='http://pypi.python.org/pypi/frestq/',
    license='AGPL-3.0',
    description='simple federated rest task queue',
    long_description=open('README.md').read(),
    install_requires=[
        'apscheduler==3.7.0',
        'requests==2.31.0',
        'Flask==2.3.2',
        'Flask-SQLAlchemy==2.5.1',
        'Jinja2==3.1.2',
        'MarkupSafe==2.1.1',
        'SQLAlchemy==1.3.23',
        'Werkzeug==2.3.3',
        'argparse==1.2.1',
        'cffi==1.14.4',
        'ipdb==0.13.9',
        'ipython==8.10.0',
        'itsdangerous==2.1.2',
        'prettytable==0.7.2',
        'pycparser==2.10',
        'uwsgi==2.0.22',
        'cryptography==41.0.4',
        'pyOpenSSL==23.2.0',
        'enum34==1.1.6',
        'ipaddress==1.0.22',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "OSI Approved :: GNU Affero General Public License v3"
    ],
    python_requires='>=3.5',
    dependency_links = []
)
