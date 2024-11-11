"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import pathlib

import yaml

import rs232_to_tripplite.logfactory as logfac
from rs232_to_tripplite.rs232tripplite import Rs2323ToTripplite

# Read and setup configs
CONFIG_FILE = pathlib.Path('config.yaml')
with open(CONFIG_FILE, 'r', encoding='utf-8') as fileopen:
    config = yaml.load(fileopen, Loader=yaml.FullLoader)

if 'log' in config:
    if len(tuple(config['log'].keys())) > 1:
        raise ValueError('More than one log file found')

    for i, key in enumerate(config['log']):
        logfac.setup_logging(key, config['log'][key])
else:
    # default to stdout
    logfac.setup_logging('stream', 'stdout')

if __name__ == '__main__':
    serial_listener = Rs2323ToTripplite(
        config['serial']['device'],
        config['serial']['timeout'],
        config['snmp']['retry']['max_attempts'],
        config['snmp']['retry']['delay'],
        config['snmp']['retry']['timeout'],
        config['devices'],
        config['healthcheck']['frequency'],
        config['power_states']['cy_delay']
    )
    serial_listener.start()
