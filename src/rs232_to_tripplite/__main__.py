"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
from rs232_to_tripplite.rs232tripplite import SerialListener

if __name__ == '__main__':
    serial_listener = SerialListener()
    serial_listener.start()
