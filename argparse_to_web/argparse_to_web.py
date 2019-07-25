"""Generate simple single page form web applications from an argparse CLI."""
import os
from argparse import ArgumentParser
from datetime import datetime
from typing import List, Dict, Callable

from flask import Flask, request

# noinspection PyProtectedMember
from werkzeug.datastructures import FileStorage

from argparse_to_web.routes import routes
from argparse_to_web.utils import upload_file
from argparse_to_web.config import TEMP_FILES_ROOT_DIR, NO_TITLE_ERR_MSG, \
    EXCLUDE_ACTIONS, MULTIPLE_INPUT_TYPES, COUNT_TYPE_ERR_MSG, \
    TYPE_CONVERSIONS, DEL_ATTRS


class ArgparseToWeb:
    """Generate simple single page form web applications from argparse CLI.

    In the documentation, whenever you see reference to an option's "name",
    it is technically referring to what is known in Argeparse as the
    option's "dest".
    """

    def __init__(
        self,
        parser: ArgumentParser,
        python_api: Callable,
        debug: bool = False,
        title: str = None,
        subtitle: str = '',
        upload_options: List[str] = '',
        ignore_options: List[str] = '',
        advanced_options: List[str] = '',
        option_order: List[str] = None,
        advanced_option_order: List[str] = '',
        help_overrides: Dict[str, str] = '',
        label_overrides: Dict[str, str] = '',
        send_files_option: str = '',
    ):
        """Initialize

        Args:
            parser (ArgumentParser): Argeparse obj
            title (str): Name of the program/form. Displayed as header.
            subtitle (str): Description of program/form. Displayed below
                header.
            upload_options (list): List of names of options that are for
                uploading files.
            ignore_options (list): List of names of options to not render.
            send_files_option (str): Name of param which designates path to
                save files. This will then be used to send files to browser.
            advanced_options (list): List of names of options to marked as
                advanced for the purpose of rendering inside of an 'advanced
                options' expandable section.
            option_order (list): List of option names, in order of how they
                should be rendered in the web form from top to bottom.
            advanced_option_order (list): List of option names, in order of how
                they should be rendered in the web form from top to bottom.
            help_overrides (dict): Map of option names to the a string of help
                text to be substituted for whatever was supplied by the CLI
                originally.
            help_overrides (dict): Map of option names to the a string label
                to be substituted for what would otherwise be the CLI option
                name.
        """
        self.app = None
        self.debug = debug
        self.parser = parser
        self.python_api = python_api
        self.title = title
        self.subtitle = subtitle
        self.upload_options = upload_options
        self.ignore_options = ignore_options
        self.advanced_options = advanced_options
        self.option_order = option_order
        self.advanced_option_order = advanced_option_order
        self.help_overrides = help_overrides
        self.label_overrides = label_overrides
        self.send_files_option = send_files_option

        self.webform = self.create_webform_spec()
        self.fields: List[Dict] = \
            self.webform['fields'] + self.webform['advanced_fields']
        self.checkbox_options = [
            x['name'] for x in self.fields if x['type'] == 'checkbox']
        self.print_all_errors: bool = self.debug
        # noinspection PyProtectedMember,PyUnresolvedReferences
        cli_options: List[str] = [
            x.metavar if x.metavar else x.dest for x in parser._actions]
        self.send_files_param: str = send_files_option if send_files_option \
            else 'outpath' if 'outpath' in cli_options \
            else 'outdir' if 'outdir' in cli_options \
            else 'outfile' if 'outfile' in cli_options \
            else ''
        # # noinspection PyProtectedMember
        # positional_arguments = [
        #     x.metavar if x.metavar else x.dest
        #     for x in parser._actions if not x.option_strings]

    def serve(self):
        """Run a flask application"""
        self.app = self.create_app()
        self.app.run(debug=self.debug)

    def create_webform_spec(self) -> Dict:
        """Convert Argeparse CLI to a web form

        Return:
            dict: {'fields': [...], ...}
        """
        parser = self.parser
        title = self.title
        subtitle = self.subtitle
        upload_options = self.upload_options
        ignore_options = self.ignore_options
        advanced_options = self.advanced_options
        option_order = self.option_order
        advanced_option_order = self.advanced_option_order
        help_overrides = self.help_overrides
        label_overrides = self.label_overrides

        spec: Dict = {}
        spec['fields']: List[Dict] = []
        spec['advanced_fields']: List[Dict] = []
        ordered_advanced_options: List[str] = \
            advanced_option_order if advanced_option_order \
            else advanced_options if advanced_options \
            else []
        # noinspection PyProtectedMember,PyUnresolvedReferences
        cli: List = [x for x in parser._actions]

        # Get title
        spec['title']: str = title if title \
            else parser.prog \
            if hasattr(parser, 'prog') and parser.prog else ''
        if not spec['title']:
            raise ValueError(NO_TITLE_ERR_MSG)

        # Get subtitle
        spec['subtitle']: str = subtitle if subtitle \
            else parser.description \
            if hasattr(parser, 'description') and parser.description \
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
            fld['multiple_input']: bool = True \
                if fld['cli_type'] in MULTIPLE_INPUT_TYPES or fld['nargs'] \
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

    def handle_submission(self, request_obj: request) -> str:
        """Pass web form submission to CLI's python api

        Args:
            request_obj (request): Web request obj

        Returns:
            str: Directory of temp folders if output files were created
        """
        fields = self.fields
        send_files_param = self.send_files_param
        checkbox_options = self.checkbox_options
        python_api = self.python_api

        # Create temporary dirs
        # TODO (low priority): Delete previous request_obj dirs if they've been
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
            if fld['type'] != 'file':
                continue
            option: str = fld['name']
            upload_option_file_paths[option]: List[str] = []
            files: List[FileStorage] = request_obj.files.getlist(option)
            for file in files:
                # Not sure why, but 'application/octet-stream'  is being
                # submitted for fields that received no file from user; no
                # filename either
                if not file.filename:
                    continue
                # Side effect; uploads file
                path: str = upload_file(
                    file=file,
                    upload_dir=this_request_input_dir)
                upload_option_file_paths[option].append(path)

        # Build basic dictionary
        pre_kwargs = {
            **upload_option_file_paths,
            **{k: v for k, v in request_obj.form.items()}
        }
        # Filter out empty options
        pre_kwargs2 = {
            k: v
            for k, v in pre_kwargs.items()
            if v
        }
        # Translate checkbox to _StoreTrueAction value
        pre_kwargs3 = {
            k: v
            if k not in checkbox_options
            else True if v == 'on' else False
            for k, v in pre_kwargs2.items()
            if v
        }

        # Convert space-delimited string input to lists for multi-input
        pre_kwargs4 = {}
        for k, v in pre_kwargs3.items():
            for fld in fields:
                if k == fld['name']:
                    if fld['multiple_input'] and isinstance(v, str):
                        new_val: List[str] = v.split(' ')
                        pre_kwargs4[k] = new_val
                    else:
                        pre_kwargs4[k] = v
                    continue

        # Add outpath
        kwargs = {
            **pre_kwargs4,
            send_files_param: this_request_output_dir,
        }

        # args: List[str] = []
        # for arg in positional_arguments:
        #     args.append(kwargs.pop(arg))
        # borrow(*args, **kwargs)

        python_api(**kwargs)

        output_files: List[str] = os.listdir(this_request_output_dir)

        return this_requests_temp_dir if output_files else None

    def create_app(self) -> Flask:
        """Create a Flask application"""
        app = Flask(__name__)

        app.self = self
        app.webform = self.webform
        app.handle_submission = self.handle_submission
        app.print_all_errors = self.print_all_errors
        app.config['WEBFORM'] = self.webform

        app.register_blueprint(routes)

        if not os.path.exists(TEMP_FILES_ROOT_DIR):
            os.mkdir(TEMP_FILES_ROOT_DIR)

        return app
