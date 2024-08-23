"""
Contains the base parser class that contains important parsing functions

Author: Patrick Guo
Date: 2024-08-13
"""
import nrlogging.loggingfactory as nrlogfac


# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)


class ParseError(Exception):
    """
    An error that occurs when parsing goes unexpected
    """
    def __init__(self, text: str, pos: int, msg: str):
        """
        Args:
            text (str): Text attempted to be parsed
            pos (int): Position of text when parsing error occured
            msg (str): Message describing the error
        """
        self.pos = pos
        self.text = text
        self.msg = msg

    def __str__(self) -> str:
        return f'{self.msg} occured at position {self.pos} of text {self.text}'


class BaseParser:
    """
    Base parser class
    """
    def __init__(self):
        self.text = ''
        self.text_pos = 0
        self.text_len = 0

        self.tokens = []

    def parse(self, text: str) -> None:
        """
        Entry point for parsing

        Sets initial state for state machine
        To be overriden in child class

        Args:
            Text (str): string to be parsed
        """
        raise NotImplementedError

    def start(self) -> None:
        """
        Defines state machine

        To be overriden in child class
        """
        raise NotImplementedError

    def remove_leading_whitespace(self) -> None:
        """
        Moves parser cursor to next non-whitespace character

        If already at a non-whitespace character, no movement occurs
        """
        logger.debug('Removing leading whitespace characters')
        whitespace_tokens = [' ']
        while True:
            # Stop if at last position
            if self.text_pos == self.text_len:
                break

            # Stop if encountered non-whitespace character
            if self.text[self.text_pos] not in whitespace_tokens:
                break

            self.text_pos += 1

    def match(self, *rules: str) -> str:
        """
        Attempts to match parser based on given rules

        Args:
            rules: array of strings representing function names
        
        Returns:
            Matched token (str)
        
        Raises:
            ParseError: raised if none of the rules matched
        """
        # In the case of multiple rules producing an error message, we want to
        # produce the error message for the rule that reached the furthest
        furthest_error_pos = -1
        furthest_exception = None
        furthest_errored_rules = []

        for rule in rules:
            logger.debug('Attempting to match rule %s', rule)
            init_pos = self.text_pos
            try:
                # Get function with same name as inputted rule
                extract_func = getattr(self, rule)
                ret_val = extract_func()
                logger.debug('%s rule matched for %s', rule, ret_val)
                return ret_val

            # rules will fail if could not find match
            except ParseError as e:
                logger.debug('%s rule failed to match', rule)

                # reset cursor position to prior to matching the rule
                self.text_pos = init_pos

                if e.pos > furthest_error_pos:
                    furthest_error_pos = e.pos
                    furthest_exception = e

                    furthest_errored_rules.clear()
                    furthest_errored_rules.append(rule)
                # In event of multiple rules reaching same position, report all
                elif e.pos == furthest_error_pos:
                    furthest_errored_rules.append(rule)

        # If all rules failed, raise exception caused by furthest reaching rule
        if len(furthest_errored_rules) == 1:
            raise furthest_exception
        if len(furthest_errored_rules) > 1:
            error_msg = (f'{", ".join(furthest_errored_rules)} '
                         f'all failed to match')
            raise ParseError(self.text, self.text_pos, error_msg)
        return ''

    def keyword(self, *keywords: tuple[str,...],
                remove_leading_whitespace: bool = True) -> str:
        """
        Looks for matching keywords at current cursor position

        Args:
            keywords (str): list of string to look for
        
        Return:
            String of the keyword that matched
        """
        # remove whitespace if desired
        if remove_leading_whitespace:
            self.remove_leading_whitespace()

        for keyword in keywords:
            logger.debug('Looking for %s at position %s of %s',
                         keyword, self.text_pos, self.text)
            # Calculate starting and ending position of keyword if present at
            # current location
            start_pos = self.text_pos
            end_pos = start_pos + len(keyword)

            # Then check if the slice matches the keyword
            # Will NOT raise index-out-of-bounds errors
            if self.text[start_pos: end_pos] == keyword:
                self.text_pos += len(keyword)

                logger.debug('Matched %s', keyword)
                # returns the keyword that matched
                return keyword

        logger.warning('No keywords [%s] found at position %s of %s',
                       ','.join(keywords), self.text_pos, self.text)
        # if none of the keywords were found, raise error
        raise ParseError(self.text, self.text_pos,
                         f"No keywords: [{','.join(keywords)}] found")

    def search_number(self) -> int:
        """
        Looks for a number at current cursor position

        Stops at first non-numerical value (i.e., anything not [0-9]).

        Args:
            None
        
        Returns:
            int representing the number found
        
        Raises:
            ParseError if no number was detected
        """
        self.remove_leading_whitespace()

        curr_pos= self.text_pos

        number_as_chars = []

        # Parse until end of text reached
        while curr_pos < self.text_len:
            curr_char = self.text[curr_pos]

            # we stop parsing upon encountering a non-numerical character
            if not curr_char.isnumeric():
                break

            number_as_chars.append(curr_char)
            curr_pos += 1

        # if no numbers were found (i.e., first char was non-numerical), we
        # raise error as this should be unexpected
        if not number_as_chars:
            raise ParseError(self.text, self.text_pos, 'No number found')

        # Update cursor position and return the integer as an int (rather than
        # a list of chars)
        self.text_pos = curr_pos
        return int(''.join(number_as_chars))


    def search_uint8(self) -> int:
        """
        Looks for a uint8 number at current cursor position

        Args:
            None

        Returns:
            int within range of a uint8
        
        Raises:
            ParseError if the integer parsed is larger than 256 (uint8)
        """
        start_pos = self.text_pos

        parsed_number = self.search_number()
        if parsed_number > 256:
            # reset staring pos and raise error if integer parsed is larger
            # than 256
            self.text_pos = start_pos
            raise ParseError(self.text, start_pos,
                             'Parsed integer larger than a uint8')

        return parsed_number
