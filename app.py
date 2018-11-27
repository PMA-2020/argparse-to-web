"""App"""
import platform
import os

from flask import Flask, render_template, request, send_file
from pmix.borrow import borrow

# noinspection PyProtectedMember
from static_methods import upload_file

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
path_char = '\\' if platform.system() == 'Windows' else '/'


@app.route('/', methods=['GET', 'POST'])
def index():
    """Index"""
    if request.method == 'GET':
        return render_template('index.html')
    else:
        try:
            source_files = request.files.getlist("sources[]")
            source_file_names = []
            for file in source_files:
                filename = upload_file(file)
                source_file_names.append(filename)  # TODO: make sure is list
            target_origin = request.files['target']
            target_file = upload_file(target_origin)
            # options_list = request.form.getlist('options[]')
            # options = " ".join(options_list)

            # command = _build_cli_command(target_file=target_file,
            #                              outpath=basedir + path_char +
            #                              'temp_uploads',
            #                              source_file_names=source_file_names)
            # stdout, stderr = _run_background_process(command)
            output_filename = 'result.xlsx'
            outpath = basedir + path_char + 'temp_uploads' + path_char + \
                      output_filename
            kwargs = {
                'merge': target_file,
                'merge_all': None,
                'correct': None,
                'no_diverse': None,
                'diverse': None,
                'add': None,
                'ignore': None,
                'carry': None,
                'outpath': outpath,
                'xlsxfiles': source_file_names
            }

            # TODO: capture stderr and stdout from here
            borrow(**kwargs)
            stderr = ''
            stdout = ''

            return render_template('index.html',
                                   stderr=stderr,
                                   stdout=stdout,
                                   output_file_path=outpath,
                                   output_file_name=output_filename)

        except Exception as err:
            msg = 'An unexpected error occurred:\n\n' + str(err)
            return render_template('index.html', stderr=msg)


@app.route('/export', methods=['POST'])
def export():
    """Export"""
    output_file_path = request.form['output_file_path']
    output_file_name = request.form['output_file_name']
    return send_file(output_file_path, None, True, output_file_name)


if __name__ == '__main__':
    app.run(debug=True)
