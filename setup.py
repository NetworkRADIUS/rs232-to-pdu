"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.

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
