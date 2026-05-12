import pandas as pd
import logging

def validate_data(flights_df, bookings_df):

    invalid_mask = pd.Series([False] * len(bookings_df), index=bookings_df.index)

    #Flight must exist
    valid_flight_ids = set(flights_df['flight_id'])
    invalid_flight_mask = ~bookings_df['flight_id'].isin(valid_flight_ids)
    if invalid_flight_mask.any():
        for fid in bookings_df.loc[invalid_flight_mask, 'flight_id'].unique():
            logging.error(f"Flight {fid} does not exist — bookings rejected.")
    invalid_mask |= invalid_flight_mask

    #seats_booked must be > 0
    invalid_seats_mask = bookings_df['seats_booked'] <= 0
    if invalid_seats_mask.any():
        logging.error(
            f"{invalid_seats_mask.sum()} booking(s) rejected: seats_booked must be > 0."
        )
    invalid_mask |= invalid_seats_mask

    #booking_date must be a valid date
    parsed_dates = pd.to_datetime(bookings_df['booking_date'], errors='coerce')
    invalid_date_mask = parsed_dates.isnull()
    if invalid_date_mask.any():
        logging.error(
            f"{invalid_date_mask.sum()} booking(s) rejected: invalid booking_date."
        )
    invalid_mask |= invalid_date_mask

    valid_bookings_df = bookings_df[~invalid_mask].copy()
    logging.info(
        f"Validation complete: {len(valid_bookings_df)} valid, "
        f"{invalid_mask.sum()} invalid booking(s)."
    )
    return valid_bookings_df