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
    START = 1
    COMMAND = 2
    BANK = 3
    PORT = 4
    CHAIN = 5
    TERMINAL = 6


class PowerCommands(Enum):
    """
    Enum values for representing the power commands
    """
    OFF = 7
    ON = 8
    CYCLE = 9



class ParserKvmSequence(BaseParser):
    """
    Parser to turn string sequence into a command
    """
    def __init__(self):
        super().__init__()

        self.text = None
        self.text_pos = None
        self.text_len = None

        self.tokens = []
        self.logic = []

        self.state = None

    def parse(self, text: str) -> dict:
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

        self.logic = []

        self.state = KvmSequenceStates.INIT
        self.start()

        # Transforms token list into PduCmdLogicNode object and return
        return self.logic

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
                    self.match('rule_token_start')

                # A command token can appear after either the start token (DD)
                # or a chain token (D*)
                case KvmSequenceStates.START | KvmSequenceStates.CHAIN:
                    command_token = self.match('rule_token_command')
                    self.logic.append({
                        'Command': 'On' if command_token == 'on' else 'Off',
                        'Bank': -1,
                        'Port': -1
                    })
                case KvmSequenceStates.COMMAND:
                    bank_token = self.match('rule_token_bank')
                    self.logic[-1]['Bank'] = bank_token
                case KvmSequenceStates.BANK:
                    port_token = self.match('rule_token_port')
                    self.logic[-1]['Port'] = port_token

                # The port token can be followed by the terminal token (DquitD)
                # or a chain token (D*)
                case KvmSequenceStates.PORT:
                    self.match('rule_token_terminal',
                               'rule_token_chain')
                case KvmSequenceStates.TERMINAL:
                    return

    def rule_token_start(self) -> str:
        """
        Parser rule that looks for the start token as a keyword

        Returns:
            Matched keyword
        """
        logger.debug('Looking for start token')
        start_token = self.keyword('DD')
        self.state = KvmSequenceStates.START
        logger.info('Found start token')
        return start_token

    def rule_token_terminal(self) -> str:
        """
        Parser rule that looks for the terminal token as a keyword

        Returns:
            Matched keyword

        """
        logger.debug('Looking for terminal token')
        terminal_token = self.keyword('DquitD')
        self.state = KvmSequenceStates.TERMINAL
        logger.info('Found terminal token')
        return terminal_token


    def rule_token_command(self) -> str:
        """
        Parser rule that looks for the command tokens as a keyword

        Possible values: [on, of]. No typo: 'off' with 1 'f'

        Returns:
            Matched keyword
        """
        logger.debug('Looking for command token')
        command_token = self.keyword('on', 'of')
        self.state = KvmSequenceStates.COMMAND
        logger.info('Found command token')
        return command_token

    def rule_token_bank(self) -> str:
        """
        Parser rule that looks for a bank token as a keyword

        Possible values: [1, 2, 3, 4, 5]

        Returns:
            Matched keyword
        """
        logger.debug('Looking for bank token')
        bank_token = self.keyword('1', '2', '3', '4', '5')
        self.state = KvmSequenceStates.BANK
        logger.info('Found bank token')
        return bank_token

    def rule_token_port(self) -> str:
        """
        Parser rule that looks for a port token as a keyword

        Possible values: 0[0-8]
        Note: this assumes that each bank has 8 ports (True as of writing).

        Returns:
            Matched keyword
        """
        logger.debug('Looking for port token')
        keywords = ['01', '02', '03', '04', '05', '06', '07', '08']
        port_token = self.keyword(*keywords)
        self.state = KvmSequenceStates.PORT
        logger.info('Found port token')
        return port_token

    def rule_token_chain(self) -> str:
        """
        Parser rule that looks for a chain token as a keyword

        Used for restart sequence, where bank-port is turned off then on

        Returns:
            Matched keyword
        """
        logger.debug('Looking for chain token')
        chain_token = self.keyword('D*')
        self.state = KvmSequenceStates.CHAIN
        logger.info('Found chain token')
        return chain_token
