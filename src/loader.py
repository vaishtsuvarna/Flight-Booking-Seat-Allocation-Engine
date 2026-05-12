import pandas as pd
import os
import logging

def _load_csv(file_path):

    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist.")
        raise FileNotFoundError(f"File {file_path} does not exist.")

    df = pd.read_csv(file_path)

    if df.empty:
        logging.warning(f"File {file_path} is empty.")
        raise ValueError(f"File {file_path} is empty.")

    logging.info(f"Loaded '{file_path}' — {len(df)} row(s).")
    return df


def load_data(flights_path, bookings_path):

    flights_df  = _load_csv(flights_path)
    bookings_df = _load_csv(bookings_path)
    return flights_df, bookings_df