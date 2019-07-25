"""Utility functions"""
import os
from werkzeug.utils import secure_filename


def upload_file(file, upload_dir: str):
    """Upload a file"""
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    try:
        file.save(file_path)
    except FileNotFoundError:
        os.mkdir(upload_dir)
        file.save(file_path)

    return file_path
