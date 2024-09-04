"""
Contains parser class that converts string sequences to a dictionary 
representing a SNMP command

Author: Patrick Guo
Date: 2024-08-13
"""
from enum import Enum

import sersnmplogging.loggingfactory as nrlogfac
from sersnmpparsers.parse_base import BaseParser

# Set up logger for this module
logger = nrlogfac.create_logger(__name__)


class KvmSequenceStates(Enum):
    """
    Enum values for representing KVM parser states

    State names represent the token the parser is expecting next
    Example:
        - COMMAND = parser is looking for 'on', 'of', etc.
        - PORT = parser just parsed a bank token and is now looking for a
                 port token
    """
    COMMAND = 1
    BANK = 2
    PORT = 3
    TERMINAL = 4


class ParserKvmSequence(BaseParser):
    """
    Parser to turn string sequence into a command
    """

    def parse(self, buffer: str) -> list[str, int, int]:
        """
        Entry point for parsing

        Args:
            buffer (str): string to be parsed
        
        Returns:
            Returns a list containing: 
                command: <str>
                bank: <str>
                port: <str>
        """
        logger.debug('Attempting to parse "%s"', buffer)

        self.buffer = buffer
        self.cursor_pos = 0

        return self.match_rule(self.rule_token_command)

    # def start(self) -> None:
    #     """
    #     Defines state machine

    #     Returns:
    #         None
    #     """
    #     return self.match_rule(self.rule_token_command)

    def rule_token_command(self) -> str:
        """
        Parser rule that looks for the command tokens as a keyword

        Possible values: [on, of]. No typo here: actually 'off' with 1 'f'

        Returns:
            Matched keyword
        """
        logger.debug('Looking for command token for "%s" at position %s',
                     self.buffer, self.cursor_pos)
        command_token = self.keyword('on', 'of', 'cy', 'quit', '')
        if command_token in ['quit', '']:
            return None, None, None

        return command_token, *self.match_rule(self.rule_token_bank)

    def rule_token_bank(self) -> int:
        """
        Parser rule that looks for a bank token as uint8 value

        Possible values: [1-256]

        Returns:
            Integer in uint8 range
        """
        logger.debug('Looking for bank token for "%s" at position %s',
                     self.buffer, self.cursor_pos)
        bank_value = self.search_uint8()
        return bank_value, self.match_rule(self.rule_token_port)

    def rule_token_port(self) -> int:
        """
        Parser rule that looks for a port token as uint8 value

        Possible values: [1-256]

        Returns:
            Integer in uint8 range
        """
        logger.debug('Looking for port token for "%s" at position %s',
                     self.buffer, self.cursor_pos)
        port_value = self.search_uint8()
        return port_value
