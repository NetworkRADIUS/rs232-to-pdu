# pylint: disable='missing-module-docstring
import shutil

from setuptools import setup
from setuptools.command.install import install


class CustomInstall(install):  # pylint: disable='missing-class-docstring
    def run(self):
        shutil.copytree('./src/rs232_to_pdu/devices/',
                        '/tmp/rs232-to-pdu/devices/',
                        dirs_exist_ok=True)

        super().run()

with open('README.md', encoding='utf-8') as readme:
    setup(
        name='rs232-to-pdu',
        version='1.1.5',
        author='InkBridge Networks',

        package_dir={'': 'src'},
        package_data={'': ['*.*']},
        include_package_data=True,

        description='Converts RS232 serial data to SNMP commands to control PDUs.',
        long_description=readme.read(),
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
        ],
        cmdclass={'install': CustomInstall},
    )
