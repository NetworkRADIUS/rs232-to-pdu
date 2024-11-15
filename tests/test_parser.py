"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.

"""
import unittest

from rs232_to_tripplite.parsers.base import ParseError # pylint: disable=import-error
from rs232_to_tripplite.parsers.kvmseq import ParserKvmSequence # pylint: disable=import-error


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

    def test_parser_sequences(self):  # pylint: disable=missing-function-docstring
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
