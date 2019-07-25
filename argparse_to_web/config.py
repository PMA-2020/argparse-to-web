"""Utility functions"""
import os

PKG_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT_DIR = os.path.join(PKG_DIR, '..')
TEMP_FILES_ROOT_DIR: str = os.path.join(PROJECT_ROOT_DIR, 'temp')
# TODO (low priority): Option strings support as dropdown list input widget.
DEL_ATTRS: tuple = (
    'container', 'option_strings', 'const', 'dest', 'metavar', 'cli_type',
    'nargs')
EXCLUDE_ACTIONS: tuple = ('_HelpAction', '_VersionAction')
MULTIPLE_INPUT_TYPES: tuple = ('_AppendAction', '_AppendConstAction')
TYPE_CONVERSIONS = {
    '_AppendAction': 'text',
    '_StoreAction': 'text',
    '_CountAction': 'text',
    '_StoreTrueAction': 'checkbox',
    '_StoreConstAction': 'checkbox',
    '_StoreFalseAction': 'checkbox',
    '_AppendConstAction': 'checkbox',
}
COUNT_TYPE_ERR_MSG: str = (
    'ArgeParseToWebform tried to ascertain the type of option "{}", but was '
    'not able to logically reconcile this option being designated as a "count"'
    ' type action while datatype was stipulated to be "{}".')
NO_TITLE_ERR_MSG: str = (
    'Unable to render webform, as no title was found. A title must be provided'
    ' by one of the following means: a. Set the "prog" attribute of the '
    'ArgumentParser object, or b. Provide a title parameter to the argeparse '
    'to webform function.')
