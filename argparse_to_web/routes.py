"""Generate simple single page form web applications from an argparse CLI."""
import os
from typing import List
from zipfile import ZipFile

from flask import render_template, request, send_file, current_app, \
    Blueprint


routes = Blueprint('routes', __name__)


@routes.route('/', methods=['GET', 'POST'])
def index():
    """Index"""
    app = current_app
    webform = app.webform
    handle_submission = app.handle_submission
    print_all_errors = app.print_all_errors

    if request.method == 'GET':
        return render_template(
            'index.html',
            webform=webform,)

    else:
        try:
            files_loc = handle_submission(request)

            # TODO (low priority): capture output or return
            stderr, stdout = '', ''  # get from handle_submission

            return render_template(
                'index.html',
                stderr=stderr,
                stdout=stdout,
                files_loc=files_loc,
                webform=webform,)

        except Exception as err:
            msg = 'An unexpected error occurred:\n\n'
            if print_all_errors:
                msg += str(err)
            return render_template(
                'index.html',
                stderr=msg,
                webform=webform,)


@routes.route('/export', methods=['POST'])
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
