import cv2
import pytesseract


def _resize_image(image, max_dim=1600):
    """Resize large images proportionally to a maximum dimension for better OCR."""
    height, width = image.shape[:2]
    if max(height, width) <= max_dim:
        return image

    scale = max_dim / float(max(height, width))
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)


def _enhance_contrast(gray_image):
    """Improve contrast with CLAHE for uneven lighting and low-contrast text."""
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(gray_image)


def _reduce_noise(gray_image):
    """Apply noise reduction while preserving edges for tables and structured layouts."""
    return cv2.bilateralFilter(gray_image, d=9, sigmaColor=75, sigmaSpace=75)


def _adaptive_threshold(gray_image):
    """Use adaptive thresholding to improve OCR for documents with varying background illumination."""
    blurred = cv2.medianBlur(gray_image, 3)
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=10,
    )


def _otsu_threshold(gray_image):
    """Use Otsu thresholding as a second pass for clear high-contrast text regions."""
    _, otsu = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return otsu


def _merge_ocr_outputs(outputs):
    """Combine OCR outputs from multiple preprocessing passes while preserving unique lines."""
    merged_lines = []
    seen = set()
    for output in outputs:
        for line in output.splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            if normalized not in seen:
                seen.add(normalized)
                merged_lines.append(normalized)
    return "\n".join(merged_lines)


def parse_image(file_path):
    """
    Extract text from images using OCR.

    This function improves OCR accuracy for tables, charts, notes, and structured layouts
    by applying resizing, contrast enhancement, noise reduction, and multiple thresholding passes.
    """

    image = cv2.imread(file_path)
    if image is None:
        return ""

    image = _resize_image(image)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = _enhance_contrast(gray_image)
    denoised = _reduce_noise(enhanced)

    adaptive = _adaptive_threshold(denoised)
    otsu = _otsu_threshold(denoised)

    tesseract_config = "--oem 3 --psm 6"

    ocr_results = [
        pytesseract.image_to_string(denoised, config=tesseract_config),
        pytesseract.image_to_string(adaptive, config=tesseract_config),
        pytesseract.image_to_string(otsu, config=tesseract_config),
    ]

    return _merge_ocr_outputs(ocr_results)