from subprocess import PIPE, Popen
import shlex
import os
import platform
from werkzeug.utils import secure_filename

basedir = os.path.abspath(os.path.dirname(__file__))
path_char = '\\' if platform.system() == 'Windows' else '/'


def _run_background_process(command_line):
    """This method runs external program using command line interface.

    Returns:
         stdout,stdin: Of executed program.
    """

    args = shlex.split(command_line, posix=False)
    '''process = run(args, stdout=PIPE, stderr=PIPE, shell=True, check=True)
    stdout = process.stdout
    stderr = process.stderr'''

    process = Popen(args, stdout=PIPE, stderr=PIPE)
    process.wait()
    stdout = process.stdout.read().decode().strip()
    stderr = process.stderr.read().decode().strip()

    return stdout, stderr


def upload_file(file):
    filename = secure_filename(file.filename)
    upload_folder = basedir + path_char + 'temp_uploads'
    file_path = os.path.join(upload_folder, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    try:
        file.save(file_path)
    except FileNotFoundError:
        os.mkdir(upload_folder)
        file.save(file_path)

    return file_path
