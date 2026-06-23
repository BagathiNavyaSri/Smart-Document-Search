import pandas as pd


def parse_excel(file_path):
    """
    Extract text from all sheets in Excel file.
    """

    excel_data = pd.read_excel(file_path, sheet_name=None)

    extracted_text = []

    for sheet_name, dataframe in excel_data.items():

        extracted_text.append(f"\nSheet Name: {sheet_name}\n")

        extracted_text.append(dataframe.to_string(index=False))

    return "\n".join(extracted_text)