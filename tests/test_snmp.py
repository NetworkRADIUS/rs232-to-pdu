from sersnmprequests.powerchangecmd import PowerChangeCmd
import pysnmp.hlapi.asyncio as pysnmp
from pysnmp.error import PySnmpError
from sersnmprequests.healthcheckcmd import HealthcheckCmd
import asyncio
import unittest
from socket import gaierror
import subprocess
import os
import time
import signal
import configparser
import pathlib




class TestSnmpCmds(unittest.TestCase):
    @classmethod
    def setUp(cls):
        config_file = pathlib.Path('tests/test_config.ini')
        config = configparser.ConfigParser()
        config.read(config_file)
        
        cls.target_ip = str(config['SNMP AGENT LOCATION']['ip'])
        cls.target_port = int(config['SNMP AGENT LOCATION']['port'])

        cls.username = config['SNMP USER']['username']
        cls.authpass = config['SNMP USER']['authpass']
        cls.privpass = config['SNMP USER']['privpass']
        cls.authprot = pysnmp.usmHMACMD5AuthProtocol if config['SNMP USER']['authprot'] == 'MD5' else None
        cls.privprot = pysnmp.usmAesCfb128Protocol if config['SNMP USER']['privprot'] == 'AES' else None
        cls.target_obj = ('SNMPv2-MIB', 'sysName', 0)
        cls.timeout = int(config['SNMP AGENT LOCATION']['timeout'])
        cls.max_attempts = int(config['SNMP AGENT LOCATION']['max_attempts'])
        cls.retry_delay = int(config['SNMP AGENT LOCATION']['retry_delay'])
        cls.outlet_bank = 1
        cls.outlet_port = 1

    def test_get_cmd_success(self):
        cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, self.privpass,
                             self.authprot, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj)
    
        self.assertTrue(asyncio.run(cmd.run_cmd()))

    def test_wrong_username(self):
        cmd = HealthcheckCmd(self.target_ip, self.target_port, 'wrongUn',
                             self.authpass, self.privpass,
                             self.authprot, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj)
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))
        
    def test_wrong_auth_get_cmd(self):
        cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                             'wrongAuth', self.privpass,
                             self.authprot, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj)
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))
        
    def test_wrong_priv_get_cmd(self):
        cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, 'wrongPriv',
                             self.authprot, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj)
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))

    def test_wrong_auth_prot_get_cmd(self):
        cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, self.privpass,
                             pysnmp.usmHMAC128SHA224AuthProtocol, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj)
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))

    def test_wrong_priv_prot_get_cmd(self):
        cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, self.privpass,
                             self.authprot, pysnmp.usmDESPrivProtocol,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj)
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))

    def test_set_cmd(self):
        first_get_cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                                       self.authpass, self.privpass,
                                       self.authprot, self.privprot,
                                       self.timeout, self.max_attempts, self.retry_delay,
                                       1, self.target_obj)
        

        
        pre_value = asyncio.run(first_get_cmd.run_cmd())[0][1]._value.decode()
        new_value = '1234' if pre_value == '123' else '123'

        set_cmd = PowerChangeCmd(self.target_ip, self.target_port, self.username,
                                 self.authpass, self.privpass,
                                 self.authprot, self.privprot, self.timeout,
                                 self.max_attempts, self.retry_delay,
                                 new_value, self.target_obj,
                                 self.outlet_bank, self.outlet_port, 2)

        asyncio.run(set_cmd.run_cmd())
        
        second_get_cmd = HealthcheckCmd(self.target_ip, self.target_port, self.username,
                                        self.authpass, self.privpass,
                                        self.authprot, self.privprot,
                                        self.timeout, self.max_attempts, self.retry_delay,
                                        3, self.target_obj)

        post_value = asyncio.run(second_get_cmd.run_cmd())[0][1]._value.decode()

        self.assertNotEquals(pre_value, post_value)

    def test_wrong_auth_set_cmd(self):
        cmd = PowerChangeCmd(self.target_ip, self.target_port, self.username,
                             'wrongAuth', self.privpass,
                             self.authprot, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj, self.outlet_bank, self.outlet_port, 1)
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))
        
    def test_wrong_priv_set_cmd(self):
        cmd = PowerChangeCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, 'wrongPriv',
                             self.authprot, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj, self.outlet_bank, self.outlet_port, 1)    
        
        self.assertFalse(asyncio.run(cmd.run_cmd()))

    def test_wrong_auth_prot_set_cmd(self):
        cmd = PowerChangeCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, self.privpass,
                             pysnmp.usmHMAC128SHA224AuthProtocol, self.privprot,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj, self.outlet_bank, self.outlet_port, 1)    
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))

    def test_wrong_priv_prot_set_cmd(self):
        cmd = PowerChangeCmd(self.target_ip, self.target_port, self.username,
                             self.authpass, self.privpass,
                             self.authprot, pysnmp.usmDESPrivProtocol,
                             self.timeout, self.max_attempts, self.retry_delay,
                             1, self.target_obj, self.outlet_bank, self.outlet_port, 1)    
    
        self.assertFalse(asyncio.run(cmd.run_cmd()))
