# Copyright (C) 2014-2021  Sequent Tech Inc <legal@sequentech.io>
#
# SPDX-License-Identifier: AGPL-3.0-only

from setuptools import setup

setup(
    name='frestq',
    version='6.1.0',
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
        'ipython==7.31.1',
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
        "OSI Approved :: GNU Affero General Public License v3"
    ],
    python_requires='>=3.5',
    dependency_links = []
)
