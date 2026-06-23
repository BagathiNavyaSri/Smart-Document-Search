def parse_text_file(file_path):
    """
    Extract text from TXT files.
    """

    with open(file_path, "r", encoding="utf-8") as file:

        text = file.read()

    return text