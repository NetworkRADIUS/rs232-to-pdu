import unittest

from rs232_to_tripplite.parsers.base import ParseError
from rs232_to_tripplite.parsers.kvmseq import ParserKvmSequence


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

    def test_parser_sequences(self):
        self.assertEqual(self.parser.parse('on 1 1\r'), ('on', 1, 1))
        self.assertEqual(self.parser.parse('of 1 1\r'), ('of', 1, 1))
        self.assertEqual(self.parser.parse('cy 1 1\r'), ('cy', 1, 1))
        self.assertEqual(self.parser.parse('quit\r')[0], 'quit')
        self.assertEqual(self.parser.parse('\r')[0], '')

        self.assertRaises(ParseError, self.parser.parse, 'on 1 1')
        self.assertRaises(ParseError, self.parser.parse, 'on 256 1\r')
        self.assertRaises(ParseError, self.parser.parse, 'on 1 256\r')
        self.assertRaises(ParseError, self.parser.parse, 'of on 1 1\r')
        self.assertRaises(ParseError, self.parser.parse, '1 1\r')
        self.assertRaises(ParseError, self.parser.parse, 'on -1 1\r')
        self.assertRaises(ParseError, self.parser.parse, 'on 1 -1\r')
        self.assertRaises(ParseError, self.parser.parse, 'shutdown 1 1\r')
        self.assertRaises(ParseError, self.parser.parse, 'on11\r')
