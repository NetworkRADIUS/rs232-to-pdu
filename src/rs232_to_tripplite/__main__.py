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

Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import pathlib

import yaml

from rs232_to_tripplite.rs232tripplite import Rs2323ToTripplite
from rs232_to_tripplite.device import FactoryDevice

# Read and setup configs
CONFIG_FILE = pathlib.Path('config.yaml')
with open(CONFIG_FILE, 'r', encoding='utf-8') as fileopen:
    config = yaml.load(fileopen, Loader=yaml.FullLoader)

factory = FactoryDevice()
devices = factory.devices_from_configs(config)

if __name__ == '__main__':
    serial_listener = Rs2323ToTripplite(
        config['serial']['device'],
        config['serial']['timeout'],
        config['snmp']['retry']['max_attempts'],
        config['snmp']['retry']['delay'],
        config['snmp']['retry']['timeout'],
        devices,
        config['healthcheck']['frequency'],
        config['power_states']['cy_delay']
    )
    serial_listener.start()
