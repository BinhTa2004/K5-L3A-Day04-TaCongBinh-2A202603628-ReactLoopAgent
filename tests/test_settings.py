import os
import unittest
from pathlib import Path
from unittest.mock import patch

from settings import load_env


class EnvTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_load_values_without_shell_execution(self):
        content = '# comment\nPROVIDER=openrouter\nexport MODEL="example/model"\nOPENROUTER_API_KEY=demo=a\nVALUE=$(example)\n'
        with patch.object(Path, 'is_file', return_value=True), patch.object(Path, 'read_text', return_value=content):
            load_env()
        self.assertEqual(os.environ['PROVIDER'], 'openrouter')
        self.assertEqual(os.environ['MODEL'], 'example/model')
        self.assertEqual(os.environ['OPENROUTER_API_KEY'], 'demo=a')
        self.assertEqual(os.environ['VALUE'], '$(example)')

    @patch.dict(os.environ, {'MODEL': 'from-terminal'}, clear=True)
    def test_terminal_takes_priority(self):
        with patch.object(Path, 'is_file', return_value=True), patch.object(Path, 'read_text', return_value='MODEL=from-file'):
            load_env()
        self.assertEqual(os.environ['MODEL'], 'from-terminal')

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_file_is_optional(self):
        with patch.object(Path, 'is_file', return_value=False), patch.object(Path, 'read_text') as read:
            load_env()
        read.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    def test_skip_invalid_lines(self):
        with patch.object(Path, 'is_file', return_value=True), patch.object(Path, 'read_text', return_value='invalid\nBAD-NAME=x\n =x\nVALID=ok'):
            load_env()
        self.assertEqual(dict(os.environ), {'VALID': 'ok'})
