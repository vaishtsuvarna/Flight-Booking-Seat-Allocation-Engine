import pandas as pd
import logging

def allocate_seats(flights_df, bookings_df):
    merged_df = pd.merge(bookings_df, flights_df[['flight_id', 'seat_capacity']],
                         on='flight_id', how='left')

    merged_df['status'] = 'WAITLIST'
    merged_df['remaining_seats'] = 0

    # Track seats used per flight as we process bookings in order
    seats_used = {}

    for idx, row in merged_df.iterrows():
        fid = row['flight_id']
        capacity = row['seat_capacity']
        requested = row['seats_booked']

        used_so_far = seats_used.get(fid, 0)
        available = capacity - used_so_far

        if requested <= available:
            merged_df.at[idx, 'status'] = 'CONFIRMED'
            seats_used[fid] = used_so_far + requested
            merged_df.at[idx, 'remaining_seats'] = available - requested
            logging.info(
                f"Booking {row['booking_id']}: CONFIRMED "
                f"({requested} seats on flight {fid})."
            )
        else:
            merged_df.at[idx, 'remaining_seats'] = available
            logging.warning(
                f"Booking {row['booking_id']}: WAITLIST "
                f"(requested {requested}, only {available} left on flight {fid})."
            )

    return merged_df