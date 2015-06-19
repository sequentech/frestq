from setuptools import setup
from pip.req import parse_requirements

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements("requirements.txt", session=False)

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='frestq',
    version='0.0.1',
    author='Eduardo Robles Elvira',
    author_email='edulix@wadobo.com',
    packages=['frestq'],
    scripts=[],
    url='http://pypi.python.org/pypi/frestq/',
    license='LICENSE.txt',
    description='simple federated rest task queue',
    long_description=open('README.md').read(),
    install_requires=reqs,
    dependency_links = [
        'hg+https://edulix@bitbucket.org/edulix/apscheduler#egg=apscheduler',
        'git+https://github.com/edulix/requests.git#egg=requests'
    ]
)
