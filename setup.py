"""
setup.py script for building packages
"""
from setuptools import setup, find_packages

setup(
    name='rs232-to-tripplite-pdu',
    version='1.0.10',
    packages=find_packages(where="src"),
    package_dir={"": "src"},

    long_description=open('README.md', encoding='utf-8').read(), # pylint: disable=consider-using-with
    long_description_content_type='text/markdown',

    install_requires=[
        'APScheduler==3.10.4',
        'astroid',
        'certifi',
        'cffi',
        'charset-normalizer',
        'cryptography',
        'dill',
        'idna',
        'isort',
        'Jinja2',
        'MarkupSafe',
        'mccabe',
        'platformdirs',
        'ply',
        'pyasn1==0.6.0',
        'pycparser',
        'pyserial==3.5',
        'pysmi',
        'pysnmp==6.2.5',
        'pysnmpcrypto',
        'pytz',
        'requests',
        'six',
        'snmpsim',
        'systemd-watchdog==0.9.0',
        'tomlkit',
        'tzlocal',
        'urllib3',
        'watchdog==5.0.0',
        'pyyaml'
    ]
)
