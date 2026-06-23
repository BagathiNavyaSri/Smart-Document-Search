import re


def preprocess_text(text):
    """
    Clean extracted text.
    """

    # lowercase
    text = text.lower()

    # remove extra spaces
    text = re.sub(r"\s+", " ", text)

    # remove special characters
    text = re.sub(r"[^\w\s]", "", text)

    # strip whitespace
    text = text.strip()

    return text