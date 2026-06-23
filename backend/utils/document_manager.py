import os

from parsers.pdf_parser import parse_pdf
from parsers.docx_parser import parse_docx
from parsers.csv_parser import parse_csv
from parsers.excel_parser import parse_excel
from parsers.pptx_parser import parse_pptx
from parsers.text_parser import parse_text_file
from parsers.image_parser import parse_image


def process_document(file_path):
    """
    Detect file type and process document.
    """

    file_extension = os.path.splitext(file_path)[1].lower()

    # =====================================
    # PDF
    # =====================================

    if file_extension == ".pdf":

        return parse_pdf(file_path)

    # =====================================
    # DOCX
    # =====================================

    elif file_extension == ".docx":

        return parse_docx(file_path)

    # =====================================
    # CSV
    # =====================================

    elif file_extension == ".csv":

        return parse_csv(file_path)

    # =====================================
    # XLSX
    # =====================================

    elif file_extension == ".xlsx":

        return parse_excel(file_path)

    # =====================================
    # PPTX
    # =====================================

    elif file_extension == ".pptx":

        return parse_pptx(file_path)

    # =====================================
    # TXT
    # =====================================

    elif file_extension == ".txt":

        return parse_text_file(file_path)

    # =====================================
    # IMAGES
    # =====================================

    elif file_extension in [".png", ".jpg", ".jpeg"]:

        return parse_image(file_path)

    else:

        return "Unsupported file type"