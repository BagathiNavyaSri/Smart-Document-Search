from docx import Document


def parse_docx(file_path):
    """
    Extract text from DOCX files.
    """

    document = Document(file_path)

    extracted_text = []

    for paragraph in document.paragraphs:

        extracted_text.append(paragraph.text)

    return "\n".join(extracted_text)