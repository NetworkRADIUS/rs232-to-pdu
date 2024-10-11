"""
Contains parser class that converts string sequences to a dictionary 
representing a SNMP command

Author: Patrick Guo
Date: 2024-08-13
"""
from enum import Enum

import ser2snmp.logging.loggingfactory as nrlogfac
from ser2snmp.parsers.parse_base import BaseParser

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

    def __init__(self):
        super().__init__()

        self.parse_funcs = {
            'on': self.parse_on_sequence,
            'of': self.parse_of_sequence,
            'cy': self.parse_cy_sequence,
            'quit': self.parse_qu_sequence,
            '': self.parse_em_sequence
        }

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

        # Find which command sequence we are looking for
        command = self.keyword('on', 'of', 'cy', 'quit', '')
        self.remove_leading_whitespace()

        # Call the appropriate function to parse for speicifc sequence
        # and store the tokens parsed
        sequence_tokens = self.parse_funcs[command]()

        # Check if sequence is terminated by \r
        self.keyword('\r')

        # Return command and sequence tokens
        # Unzip sequence tokens to return 1D list containing all tokens
        return command, *sequence_tokens

    def parse_on_sequence(self):
        """
        Method for finding an ON sequence

        returns:
            bank (int)
            port (int)
        """
        return self.search_for_bank(), self.search_for_port()

    def parse_of_sequence(self):
        """
        Method for finding an OF sequence

        returns:
            bank (int)
            port (int)
        """

        return self.search_for_bank(), self.search_for_port()

    def parse_cy_sequence(self):
        """
        Method for finding a CY sequence

        returns:
            bank (int)
            port (int)
        """
        return self.search_for_bank(), self.search_for_port()

    def parse_qu_sequence(self):
        """
        Method for finding a QUIT sequence

        returns:
            None
        """
        return None,

    def parse_em_sequence(self):
        """
        Method for finding an EMPTY sequence

        returns:
            None
        """
        return None,

    def search_for_bank(self):
        """
        Method for finding a bank token

        returns:
            bank (int)
        """
        return self.search_uint8()

    def search_for_port(self):
        """
        Method for finding a port token

        returns:
            port (int)
        """
        return self.search_uint8()
