"""App"""
import os
from argparse import ArgumentParser
from datetime import datetime
from typing import List, Dict
from zipfile import ZipFile

from flask import Flask, render_template, request, send_file
from pmix.borrow import borrow as python_api, parser

# noinspection PyProtectedMember
from werkzeug.datastructures import FileStorage

from utils import upload_file
from config import TEMP_FILES_ROOT_DIR

app = Flask(__name__)


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


def argeparse_to_webform(
    arg_parser: ArgumentParser,
    title: str = None,
    subtitle: str = '',
    upload_options: List[str] = '',
    ignore_options: List[str] = '',
    advanced_options: List[str] = '',
    option_order: List[str] = None,
    advanced_option_order: List[str] = '',
    help_overrides: Dict[str, str] = '',
    label_overrides: Dict[str, str] = '',
) -> Dict:
    """Convert Argeparse CLI to a web form

    In the documentation, whenever you see reference to an option's "name", it
    is technically referring to what is known in Argeparse as the option's
    "dest".

    Args:
        arg_parser (ArgumentParser): Argeparse obj
        title (str): Name of the program/form. Displayed as header.
        subtitle (str): Description of program/form. Displayed below header.
        upload_options (list): List of names of options that are for uploading
            files.
        ignore_options (list): List of names of options to not render.
        advanced_options (list): List of names of options to marked as advanced
            for the purpose of rendering inside of an 'advanced options'
            expandable section.
        option_order (list): List of option names, in order of how they should
            be rendered in the web form from top to bottom.
        advanced_option_order (list): List of option names, in order of how
            they should be rendered in the web form from top to bottom.
        help_overrides (dict): Map of option names to the a string of help text
            to be substituted for whatever was supplied by the CLI originally.
        help_overrides (dict): Map of option names to the a string label
            to be substituted for what would otherwise be the CLI option name.

    Return:
        dict: {'fields': [...], ...}
    """
    spec: Dict = {}
    spec['fields']: List[Dict] = []
    spec['advanced_fields']: List[Dict] = []
    ordered_advanced_options: List[str] = \
        advanced_option_order if advanced_option_order \
        else advanced_options if advanced_options \
        else []
    # noinspection PyProtectedMember,PyUnresolvedReferences
    cli: List = [x for x in arg_parser._actions]

    # Get title
    spec['title']: str = title if title \
        else arg_parser.prog \
        if hasattr(arg_parser, 'prog') and arg_parser.prog else ''
    if not spec['title']:
        raise ValueError(NO_TITLE_ERR_MSG)

    # Get subtitle
    spec['subtitle']: str = subtitle if subtitle \
        else arg_parser.description \
        if hasattr(arg_parser, 'description') and arg_parser.description \
        else ''

    # Generate CLI option dicts
    for idx, obj in enumerate(cli):
        option = {}
        option['cli_type'] = cli[idx].__class__.__name__
        if option['cli_type'] in EXCLUDE_ACTIONS or \
                obj.dest in ignore_options:
            continue
        for key in dir(obj):
            if not key.startswith('_'):
                option[key] = getattr(obj, key)
        spec['fields'].append(option)

    # Field name & label
    for fld in spec['fields']:
        name: str = fld['metavar'] if fld['metavar'] else fld['dest']
        name = name.lower()
        fld['name']: str = name
        fld['label']: str = name.replace('_', ' ').capitalize()
        if label_overrides and fld['dest'] in label_overrides.keys():
            fld['label'] = label_overrides[fld['dest']]

    # Multiple inputs
    for fld in spec['fields']:
        fld['multiple_input']: bool = \
            True if fld['cli_type'] in MULTIPLE_INPUT_TYPES or fld['nargs'] \
            else False
        fld['multiple_input_has_limit'] = False
        fld['multiple_input_limit'] = None
        if fld['nargs'] and isinstance(fld['nargs'], int):
            fld['multiple_input_limit'] = fld['nargs']

    # Validation
    for fld in spec['fields']:
        fld['validation_type'] = fld['type']
        if fld['cli_type'] == '_CountAction':
            if fld['type'] and fld['type'] != int:
                msg = COUNT_TYPE_ERR_MSG.format(fld['dest'], fld['type'])
                raise TypeError(msg)
            fld['type']: str = 'int'

    # Convert CLI type to webform type
    for fld in spec['fields']:
        if fld['type'] == open or fld['name'] in upload_options:
            fld['type']: str = 'file'
        fld['type']: str = fld['type'] if fld['type'] \
            else TYPE_CONVERSIONS[fld['cli_type']]

    # Override the originally supplied CLI help text
    if help_overrides:
        for fld in spec['fields']:
            if fld['name'] not in help_overrides.keys():
                continue
            fld['help'] = help_overrides[fld['name']]

    # Separate advanced and non-advanced options
    non_advanced_options: List[Dict] = []
    for idx, fld in enumerate(spec['fields']):
        if fld['name'] in advanced_options:
            spec['advanced_fields'].append(spec['fields'][idx])
        else:
            non_advanced_options.append(spec['fields'][idx])
    spec['fields'] = non_advanced_options

    # Ordering
    if option_order:
        ordered_fields: List[Dict] = []
        for name in option_order:
            for fld in spec['fields']:
                if name == fld['dest']:
                    ordered_fields.append(fld)
        spec['fields'] = ordered_fields

    ordered_advanced_fields: List[Dict] = []
    for name in ordered_advanced_options:
        for fld in spec['advanced_fields']:
            if name == fld['dest']:
                ordered_advanced_fields.append(fld)
    spec['advanced_fields'] = ordered_advanced_fields

    # Delete keys not needed in webform spec
    for fld in spec['fields']:
        for key in DEL_ATTRS:
            del fld[key]

    for fld in spec['advanced_fields']:
        for key in DEL_ATTRS:
            del fld[key]

    return spec


webform: Dict = argeparse_to_webform(
    arg_parser=parser,
    title='XLSForm Borrow',
    subtitle='Generates translation summary files and merges translations '
             'between XLSForms.',
    upload_options=['xlsxfiles', 'merge'],
    ignore_options=['outfile', 'outdir', 'merge_all'],
    advanced_options=[
        'no_diverse', 'carry', 'correct', 'add', 'ignore', 'diverse'],
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
        'provided, then a translation file will be generated based on '
        'the contents of these forms. If "target files" are provided,'
        ' then new versions of those target files will be created, '
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
    },
    option_order=['xlsxfiles', 'merge'],)

fields: List[Dict] = webform['fields'] + webform['advanced_fields']
checkbox_options = [
    x['name'] for x in fields if x['type'] == 'checkbox']
# noinspection PyProtectedMember
cli_options: List[str] = [
    x.metavar if x.metavar else x.dest for x in parser._actions]
# TODO: Supply option for web app
print_all_errors: bool = True
# TODO for dependency: Supply 'outdir' as param in new 'argeparse_to_web_app'
send_files_option: str = 'outdir'
send_files_param: str = send_files_option if send_files_option \
    else 'outpath' if 'outpath' in cli_options \
    else 'outdir' if 'outdir' in cli_options \
    else 'outfile' if 'outfile' in cli_options \
    else ''
# # noinspection PyProtectedMember
# positional_arguments = [
#     x.metavar if x.metavar else x.dest
#     for x in parser._actions if not x.option_strings]


if not os.path.exists(TEMP_FILES_ROOT_DIR):
    os.mkdir(TEMP_FILES_ROOT_DIR)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Index"""
    if request.method == 'GET':
        return render_template(
            'index.html',
            webform=webform,)

    else:
        try:
            # Create temporary dirs
            # TODO (low priority): Delete previous request dirs if they've been
            #  there for more than threshold, 15 min?
            current_time: datetime = datetime.now()
            tempdir_name: str = str(current_time)[:19].replace(':', '.')
            this_requests_temp_dir: str = os.path.join(
                TEMP_FILES_ROOT_DIR, tempdir_name)
            this_request_input_dir: str = \
                os.path.join(this_requests_temp_dir, 'input')
            this_request_output_dir: str = \
                os.path.join(this_requests_temp_dir, 'output')
            os.mkdir(this_requests_temp_dir)
            os.mkdir(this_request_input_dir)
            os.mkdir(this_request_output_dir)

            upload_option_file_paths = {}
            for fld in fields:
                if fld['type'] == 'file':
                    option: str = fld['name']
                    upload_option_file_paths[option]: List[str] = []
                    files: List[FileStorage] = request.files.getlist(option)
                    for file in files:
                        # Side effect; uploads file
                        path: str = upload_file(
                            file=file,
                            upload_dir=this_request_input_dir)
                        upload_option_file_paths[option].append(path)

            # Build basic dictionary
            pre_kwargs = {
                **upload_option_file_paths,
                **{k: v for k, v in request.form.items()},
                send_files_param: this_request_output_dir
            }
            # Filter out empty options
            pre_kwargs = {
                k: v
                for k, v in pre_kwargs.items()
                if v
            }
            # Translate checkbox to _StoreTrueAction value
            pre_kwargs2 = {
                k: v
                if k not in checkbox_options
                else True if v == 'on' else False
                for k, v in pre_kwargs.items()
                if v
            }

            # Convert space-delimited string input to lists for multi-input
            kwargs = {}
            for k, v in pre_kwargs2.items():
                for fld in fields:
                    if k == fld['name']:
                        if fld['multiple_input'] and isinstance(v, str):
                            new_val: List[str] = v.split(' ')
                            kwargs[k] = new_val
                        else:
                            kwargs[k] = v
                        continue

            # args: List[str] = []
            # for arg in positional_arguments:
            #     args.append(kwargs.pop(arg))
            # borrow(*args, **kwargs)

            python_api(**kwargs)

            # TODO (low priority): capture output or return
            stderr, stdout = '', ''

            return render_template(
                'index.html',
                stderr=stderr,
                stdout=stdout,
                files_loc=this_requests_temp_dir,
                webform=webform,)

        except Exception as err:
            msg = 'An unexpected error occurred:\n\n'
            if print_all_errors:
                msg += str(err)
            return render_template(
                'index.html',
                stderr=msg,
                webform=webform,)


@app.route('/export', methods=['POST'])
def export():
    """Export"""
    files_dir: str = os.path.join(request.form['files_loc'], 'output')
    file_names: List[str] = os.listdir(files_dir)
    if file_names:
        if len(file_names) == 1:
            file_name: str = file_names[0]
            file_path: str = os.path.join(files_dir, file_name)
        else:
            file_name: str = 'results.zip'
            file_path: str = os.path.join(files_dir, file_name)
            with ZipFile(file_path, 'w') as zipfile:
                for file in file_names:
                    path: str = os.path.join(files_dir, file)
                    zipfile.write(
                        filename=path,
                        arcname=file,)
        return send_file(
            filename_or_fp=file_path,
            as_attachment=True,
            attachment_filename=file_name,)


if __name__ == '__main__':
    app.run(debug=True)
