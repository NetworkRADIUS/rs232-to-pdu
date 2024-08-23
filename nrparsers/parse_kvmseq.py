"""
Contains parser class that converts string sequences to a dictionary 
representing a SNMP command

Author: Patrick Guo
Date: 2024-08-13
"""
from enum import Enum

import nrlogging.loggingfactory as nrlogfac
from nrparsers.parse_base import BaseParser

# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)


class KvmSequenceStates(Enum):
    """
    Enum values for representing KVM parser states

    State names represent the last encountered token (except INIT & TERMINAL)
    Example:
        - COMMAND = parser just parsed a command token (on, of) and is now
                    looking for a bank token
        - PORT = parser just parsed a port token and is now looking for either
                 a terminal or chain token
    """
    INIT = 0
    COMMAND = 1
    BANK = 2
    PORT = 3


class ParserKvmSequence(BaseParser):
    """
    Parser to turn string sequence into a command
    """
    def __init__(self):
        super().__init__()

        self.text = None
        self.text_pos = None
        self.text_len = None

        self.command = None
        self.bank = None
        self.port = None

        self.state = None

    def parse(self, text: str) -> list[str, int, int]:
        """
        Entry point for parsing

        Sets initial state to INIT

        Args:
            text (str): string to be parsed
        
        Returns:
            Returns a dictionary with format: {
                command: <str>
                bank: <str>
                port: <str>
            }
        """
        logger.debug('Parsing %s', text)

        self.text = text
        self.text_pos = 0
        self.text_len = len(text)

        self.command = None
        self.bank = None
        self.port = None

        self.state = KvmSequenceStates.INIT
        self.start()

        return self.command, self.bank, self.port

    def start(self) -> None:
        """
        Defines state machine

        Returns:
            None
        """
        while True:
            logger.debug('Parser currently in %s state', self.state)
            match self.state:
                case KvmSequenceStates.INIT:
                    command = self.match('rule_token_command')
                    self.command = command
                case KvmSequenceStates.COMMAND:
                    bank_value = self.match('rule_token_bank')
                    self.bank = bank_value
                case KvmSequenceStates.BANK:
                    port_value = self.match('rule_token_port')
                    self.port = port_value
                case KvmSequenceStates.PORT:
                    return

    def rule_token_command(self) -> str:
        """
        Parser rule that looks for the command tokens as a keyword

        Possible values: [on, of]. No typo here: actually 'off' with 1 'f'

        Returns:
            Matched keyword
        """
        logger.debug('Looking for command token')
        command_token = self.keyword('on', 'of')
        self.state = KvmSequenceStates.COMMAND
        logger.info('Found command token')
        return command_token

    def rule_token_bank(self) -> int:
        """
        Parser rule that looks for a bank token as uint8 value

        Possible values: [1-256]

        Returns:
            Integer in uint8 range
        """
        logger.debug('Looking for bank token')
        bank_value = self.search_uint8()
        self.state = KvmSequenceStates.BANK
        logger.info('Found bank token')
        return bank_value

    def rule_token_port(self) -> int:
        """
        Parser rule that looks for a port token as uint8 value

        Possible values: [1-256]

        Returns:
            Integer in uint8 range
        """
        logger.debug('Looking for port token')
        port_value = self.search_uint8()
        self.state = KvmSequenceStates.PORT
        logger.info('Found port token')
        return port_value
