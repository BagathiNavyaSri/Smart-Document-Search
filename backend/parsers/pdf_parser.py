import fitz
import pytesseract
import cv2
import numpy as np


def parse_pdf(file_path):
    """
    Extract text from PDF.
    Uses OCR fallback for scanned PDFs.
    """

    document = fitz.open(file_path)

    extracted_pages = []

    for page_number in range(len(document)):

        page = document.load_page(page_number)

        # =====================================
        # NORMAL PDF TEXT EXTRACTION
        # =====================================

        text = page.get_text().strip()

        # =====================================
        # OCR FALLBACK
        # =====================================

        if not text:

            pix = page.get_pixmap()

            image_bytes = pix.samples

            image = np.frombuffer(
                image_bytes,
                dtype=np.uint8
            ).reshape(
                pix.height,
                pix.width,
                pix.n
            )

            # convert RGB to BGR
            image = cv2.cvtColor(
                image,
                cv2.COLOR_RGB2BGR
            )

            # =====================================
            # IMAGE PREPROCESSING
            # =====================================

            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY
            )

            # noise removal
            gray = cv2.GaussianBlur(
                gray,
                (5, 5),
                0
            )

            # thresholding
            gray = cv2.threshold(
                gray,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )[1]

            # =====================================
            # OCR
            # =====================================

            text = pytesseract.image_to_string(
                gray
            )

        extracted_pages.append({

            "page_number": page_number + 1,

            "text": text
        })

    document.close()

    return extracted_pages