import pandas as pd
import logging

def generate_reports(allocated_df):
    booking_report_cols = [
        'booking_id', 'flight_id', 'user_id',
        'seats_booked', 'booking_date', 'status'
    ]

    booking_report_cols = [c for c in booking_report_cols if c in allocated_df.columns]
    booking_status_df = allocated_df[booking_report_cols].copy()

    booking_status_path = 'booking_status_report.csv'
    booking_status_df.to_csv(booking_status_path, index=False)
    logging.info(f"Report saved: {booking_status_path} ({len(booking_status_df)} rows)")

    confirmed_df  = allocated_df[allocated_df['status'] == 'CONFIRMED']
    waitlisted_df = allocated_df[allocated_df['status'] == 'WAITLIST']

    # Total seats booked per flight 
    confirmed_seats_per_flight = (
        confirmed_df.groupby('flight_id')['seats_booked']
        .sum()
        .rename('confirmed_seats')
    )

    # Total seats on waitlist per flight
    waitlisted_seats_per_flight = (
        waitlisted_df.groupby('flight_id')['seats_booked']
        .sum()
        .rename('waitlisted_seats')
    )

    # Total bookings attempted per flight 
    total_booked_per_flight = (
        allocated_df.groupby('flight_id')['seats_booked']
        .sum()
        .rename('total_seats_booked')
    )

    # Capacity per flight 
    capacity_per_flight = (
        allocated_df.groupby('flight_id')['seat_capacity']
        .first()
        .rename('seat_capacity')
    )

    # Build summary by joining all series on flight_id
    flight_summary_df = (
        pd.DataFrame(capacity_per_flight)
        .join(total_booked_per_flight, how='left')
        .join(confirmed_seats_per_flight, how='left')
        .join(waitlisted_seats_per_flight, how='left')
        .fillna(0)
        .astype({
            'seat_capacity':      int,
            'total_seats_booked': int,
            'confirmed_seats':    int,
            'waitlisted_seats':   int,
        })
        .reset_index()
    )

    # Remaining = capacity minus only confirmed seats 
    flight_summary_df['remaining_seats'] = (
        flight_summary_df['seat_capacity'] - flight_summary_df['confirmed_seats']
    )

    flight_summary_path = 'flight_seat_summary.csv'
    flight_summary_df.to_csv(flight_summary_path, index=False)
    logging.info(f"Report saved: {flight_summary_path} ({len(flight_summary_df)} rows)")

    return booking_status_df, flight_summary_df