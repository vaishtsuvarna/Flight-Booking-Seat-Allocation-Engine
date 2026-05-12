import logging
import sys
import pandas as pd
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from loader import load_data
from validator import validate_data
from seat_alloc import allocate_seats
from reporter import generate_reports

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs.log', mode='w'),
    ]
)

FLIGHTS_PATH  = 'data/flights.csv'
BOOKINGS_PATH = 'data/flight_bookings.csv'


def main():
    logging.info("  Flight Booking & Seat Allocation Engine — START")
    logging.info("=" * 60)
    print(" Flight Booking & Seat Allocation Engine")

   #load
    logging.info("Loading data...")
    try:
        flights_df, bookings_df = load_data(FLIGHTS_PATH, BOOKINGS_PATH)
        logging.info(f"  Loaded {len(flights_df)} flight(s), {len(bookings_df)} booking(s).")
        print("Data loading successful.")
    except FileNotFoundError as e:
        logging.critical(f"Input file not found: {e}")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Failed to load data: {e}")
        sys.exit(1)

    #validate
    logging.info("Validating bookings...")
    try:
        valid_bookings_df = validate_data(flights_df, bookings_df)
        if valid_bookings_df.empty:
            logging.error("No valid bookings remain after validation. Exiting.")
            sys.exit(1)
        logging.info(f"  {len(valid_bookings_df)} valid booking(s) passed validation.")
        print("Data validation successful.")
    except Exception as e:
        logging.critical(f"Validation crashed unexpectedly: {e}")
        sys.exit(1)

    logging.info("Allocating seats...")
    try:
        allocated_df = allocate_seats(flights_df, valid_bookings_df)

        confirmed  = (allocated_df['status'] == 'CONFIRMED').sum()
        waitlisted = (allocated_df['status'] == 'WAITLIST').sum()
        logging.info(f"  Allocation complete — CONFIRMED: {confirmed}, WAITLIST: {waitlisted}.")
        print("Seat allocation successful.")
    except Exception as e:
        logging.critical(f"Seat allocation failed: {e}")
        sys.exit(1)

    logging.info("Generating reports...")
    try:
        booking_report, flight_summary = generate_reports(allocated_df)
        logging.info("booking_status_report.csv")
        logging.info("flight_seat_summary.csv")
        print("Report generation successful.")
    except Exception as e:
        logging.critical(f"Report generation failed: {e}")
        sys.exit(1)
    logging.info("  Engine completed successfully.")



if __name__ == '__main__':
    main()