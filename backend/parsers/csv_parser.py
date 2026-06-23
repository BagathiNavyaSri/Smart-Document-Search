import pandas as pd


def parse_csv(file_path):
    """
    Extract text from CSV files.
    """

    dataframe = pd.read_csv(file_path)

    return dataframe.to_string(index=False) 