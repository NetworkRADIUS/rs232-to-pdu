import unittest

from sersnmpparsers.parse_kvmseq import ParserKvmSequence
from sersnmpparsers.parse_base import ParseError

class TestKvmParser(unittest.TestCase):
    """
    Contains test cases for the KVM parser
    """

    @classmethod
    def setUpClass(cls):
        """
        Initiate new parser before every testcase
        """
        cls.parser = ParserKvmSequence()

    def test_valid_on_sequence_success(self):
        """
        Test case for valid ON sequence
        """
        self.assertEqual(self.parser.parse('on 1 1\r'), ('on', 1, 1))

    def test_valid_of_sequence_success(self):
        """
        Test case for valid OF sequence
        """
        self.assertEqual(self.parser.parse('of 1 1\r'), ('of', 1, 1))

    def test_valid_cy_sequence_success(self):
        """
        Test case for valid CY sequence
        """
        self.assertEqual(self.parser.parse('cy 1 1\r'), ('cy', 1, 1))

    def test_valid_quit_sequence_success(self):
        """
        Test case for valid QUIT sequence
        """
        self.assertEqual(self.parser.parse('quit\r')[0], 'quit')

    def test_valid_empty_sequence_success(self):
        """
        Test case for valid EMPTY sequence
        """
        self.assertEqual(self.parser.parse('\r')[0], '')

    def test_missing_term_char_raises_error(self):
        """
        Test case for if the sequence is missing \r the term char
        """
        self.assertRaises(ParseError, self.parser.parse, 'on 1 1')

    def test_large_bank_raises_error(self):
        """
        Test case for when the bank number is larger than uint8 (256)
        """
        self.assertRaises(ParseError, self.parser.parse, 'on 256 1\r')

    def test_large_port_raises_error(self):
        """
        Test case for when the port number is larger than uint8 (256)
        """
        self.assertRaises(ParseError, self.parser.parse, 'on 1 256\r')

    def test_mulitple_cmd_one_outlet_raises_error(self):
        """
        Test case for when two commands are entered at once for a single outlet
        """
        self.assertRaises(ParseError, self.parser.parse, 'of on 1 1\r')

    def test_missing_cmd_raises_error(self):
        """
        Test case for when the seq is missing a cmd token at the start
        """
        self.assertRaises(ParseError, self.parser.parse, '1 1\r')

    def test_negative_bank_raises_error(self):
        """
        Test case for when the given bank number is negative
        """
        self.assertRaises(ParseError, self.parser.parse, 'on -1 1\r')

    def test_negative_port_raises_error(self):
        """
        Test case for when the given port number is negative
        """
        self.assertRaises(ParseError, self.parser.parse, 'on 1 -1\r')

    def test_unknown_command_raises_error(self):
        """
        Test case for when the cmd token is not [on, of, cy, quit, or '']
        """
        self.assertRaises(ParseError, self.parser.parse, 'shutdown 1 1\r')

    def test_no_spaces_raises_error(self):
        """
        Test case for when the whitespace in the seq has been removed
        """
        self.assertRaises(ParseError, self.parser.parse, 'on11\r')
