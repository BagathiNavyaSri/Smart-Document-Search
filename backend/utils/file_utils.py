import os
import uuid
from config import UPLOAD_FOLDER


def create_upload_folder():
    """
    Create uploads folder if it does not exist.
    """

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)


def save_uploaded_file(upload_file):
    """
    Save uploaded file to uploads folder.
    """

    create_upload_folder()

    unique_filename = f"{uuid.uuid4()}_{upload_file.filename}"

    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(file_path, "wb") as file:
        file.write(upload_file.file.read())

    return file_path