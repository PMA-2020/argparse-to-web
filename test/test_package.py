#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for  package."""
import os
import subprocess
import unittest
from glob import glob

from pmix.borrow import borrow as borrow_api, parser as borrow_parser

from argparse_to_web import ArgparseToWeb
# from argparse_to_web.argparse_to_web import create_app
from test.config import TEST_STATIC_DIR, TEST_PACKAGES
from test.utils import get_args, get_test_suite


class StandardInputOutputTest(unittest.TestCase):
    """Base class for package tests."""

    @classmethod
    def files_dir(cls):
        """Return name of test class."""
        return TEST_STATIC_DIR + cls.__name__

    def input_path(self):
        """Return path of input file folder for test class."""
        return self.files_dir() + '/input/'

    def output_path(self):
        """Return path of output file folder for test class."""
        return self.files_dir() + '/output/'

    def input_files(self, directory=''):
        """Return paths of input files in given directory.

        Args:
            directory (str): Path to target directory including input files.

        Returns:
            list: Input files.
        """
        path = self.input_path() + directory + '/'
        all_files = glob(path + '*')
        # With sans_temp_files, you can have XlsForms open while testing.
        sans_temp_files = [x for x in all_files
                           if not x[len(path):].startswith('~$')]
        return sans_temp_files

    def output_files(self):
        """Return paths of input files for test class."""
        return glob(self.output_path() + '*')

    @staticmethod
    def _dict_options_to_list(options):
        """Converts a dictionary of options to a list.

        Args:
            options (dict): Options in dictionary form, e.g. {
                'OPTION_NAME': 'VALUE',
                'OPTION_2_NAME': ...
            }

        Returns:
            list: A single list of strings of all options of the form
            ['--OPTION_NAME', 'VALUE', '--OPTION_NAME', ...]

        """
        new_options = []

        for k, v in options.items():
            new_options += ['--'+k, v]

        return new_options

    def standard_test(self, options={}):
        """Checks standard convert success.

        Args:
            options (dict): Options in dictionary form, e.g. {
                'OPTION_NAME': 'VALUE',
                'OPTION_2_NAME': ...
            }

        Side effects:
            assertEqual()
        """
        out_dir = self.output_path()

        subprocess.call(['rm', '-rf', out_dir])
        os.makedirs(out_dir)
        defaults = {
            'merge': self.input_files('target'),
            'merge_all': None,
            'correct': None,
            'no_diverse': None,
            'diverse': None,
            'add': None,
            'ignore': None,
            'carry': None,
            'outpath': self.output_path(),
            'xlsxfile': self.input_files('source')
        }
        kwargs = defaults if not options else {**defaults, **options}
        borrow_api(**kwargs)

        expected = 'N files: ' + str(len(self.input_files('target')))
        actual = 'N files: ' + str(len(self.output_files()))

        # Consider maybe this instead?
        # import pandas as pd
        # df1 = pd.read_excel('excel1.xlsx')
        # df2 = pd.read_excel('excel2.xlsx')
        # difference = df1[df1 != df2]

        self.assertEqual(expected, actual)


# class Merge(StandardInputOutputTest):
#     """A standard test case"""
#
#     def test_convert(self):
#         """Test that works as expected."""
#         self.standard_test()

class Borrow(unittest.TestCase):
    """Borrow test"""

    def test_run(self):
        """Test that it runs"""
        app = ArgparseToWeb(
            parser=borrow_parser,
            python_api=borrow_api,
            debug=True,
            title='XLSForm Borrow',
            subtitle='Generates translation summary files and merges '
                     'translations between XLSForms.',
            upload_options=['xlsxfiles', 'merge'],
            ignore_options=['outfile', 'outdir', 'merge_all'],
            advanced_options=[
                'no_diverse', 'carry', 'correct', 'add', 'ignore', 'diverse'],
            option_order=['xlsxfiles', 'merge'],
            send_files_option='outdir',
            label_overrides={
                'xlsxfiles': 'Source files',
                'merge': 'Target files',
                'correct': 'Trusted files',
                'no_diverse': 'Exclude translations with duplicates',
                'diverse': 'Enumerate duplicates*',
                'add': 'Add languages',
                'ignore': 'Ignore languages',
                'carry': 'Carry over',
            },
            help_overrides={
                'xlsxfiles': 'One or more XLSForms. If no "target files" are '
                'provided, then a translation file will be generated based on'
                ' the contents of these forms. If "target files" are provided'
                ', then new versions of those target files will be created, '
                'with translations from these files imported.',
                'merge': 'One or more XLSForms that receives the translations '
                'from provided "source files".',
                'correct': 'One or more file names of the provided '
                '"source files" to mark as "trusted". This is a way to give '
                'some source files precedence over others. If an English  '
                'string of text has multiple translations for the same '
                'language between forms that are marked trusted and forms not '
                'marked trusted, the non-trusted ones will be ignored.',
                'no_diverse': 'If there are multiple'
                ' translations for a single English string of text in a given '
                'language, exclude all of them.',
                'diverse': 'Supply a language. Creates a worksheet that shows '
                'only strings with duplicate translations for the language. '
                '*Can only use when not providing any "target files".',
                'add': 'Add one or more languages. The translation file will '
                'have an additional column for each language. Or, the merged '
                'XLSForm will include columns for that language and have '
                'translations for them if possible.',
                'ignore': 'One or more languages to ignore.',
                'carry': 'If translations are missing, carry over the same '
                'text from the source language. If this option is not turned '
                'on, no translation will be supplied.',
            },)
        app.serve()
        # TODO: For now this is smoke testing
        self.assertTrue(True)


if __name__ == '__main__':
    PARAMS = get_args()
    TEST_SUITE = get_test_suite(TEST_PACKAGES)
    unittest.TextTestRunner(verbosity=1).run(TEST_SUITE)

    if not PARAMS.doctests_only:
        unittest.main()
