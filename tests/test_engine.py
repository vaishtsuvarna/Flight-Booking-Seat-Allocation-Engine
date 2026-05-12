import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.loader    import load_data, _load_csv
from src.validator import validate_data
from src.seat_alloc import allocate_seats
from src.reporter  import generate_reports


@pytest.fixture
def sample_flights():
    return pd.DataFrame({
        'flight_id':     ['F001', 'F002', 'F003'],
        'airline':       ['AirX', 'AirY', 'AirZ'],
        'source':        ['DEL', 'BOM', 'BLR'],
        'destination':   ['BOM', 'BLR', 'DEL'],
        'seat_capacity': [100,   50,    30],
    })


@pytest.fixture
def sample_bookings():
    return pd.DataFrame({
        'booking_id':   ['B001', 'B002', 'B003'],
        'flight_id':    ['F001', 'F002', 'F003'],
        'user_id':      ['U1',   'U2',   'U3'],
        'seats_booked': [10,     20,     5],
        'booking_date': ['2024-01-01', '2024-02-15', '2024-03-10'],
    })


class TestLoader:

    def test_load_valid_csvs(self, tmp_path, sample_flights, sample_bookings):
        """load_data() returns two DataFrames when both CSVs exist."""
        (tmp_path / 'data').mkdir()
        f_path = tmp_path / 'data' / 'flights.csv'
        b_path = tmp_path / 'data' / 'flight_bookings.csv'
        sample_flights.to_csv(f_path, index=False)
        sample_bookings.to_csv(b_path, index=False)

        flights_df, bookings_df = load_data(str(f_path), str(b_path))

        assert len(flights_df)  == 3
        assert len(bookings_df) == 3

    def test_missing_flights_file_raises(self, tmp_path, sample_bookings):
        """FileNotFoundError raised when flights CSV is missing."""
        (tmp_path / 'data').mkdir()
        b_path = tmp_path / 'data' / 'flight_bookings.csv'
        sample_bookings.to_csv(b_path, index=False)

        with pytest.raises(FileNotFoundError):
            load_data('nonexistent_flights.csv', str(b_path))

    def test_missing_bookings_file_raises(self, tmp_path, sample_flights):
        """FileNotFoundError raised when bookings CSV is missing."""
        (tmp_path / 'data').mkdir()
        f_path = tmp_path / 'data' / 'flights.csv'
        sample_flights.to_csv(f_path, index=False)

        with pytest.raises(FileNotFoundError):
            load_data(str(f_path), 'nonexistent_bookings.csv')

    def test_empty_csv_raises(self, tmp_path):
        """ValueError raised when a CSV file has no data rows."""
        empty_path = tmp_path / 'empty.csv'
        empty_path.write_text('flight_id,airline\n')

        with pytest.raises(ValueError, match="empty"):
            _load_csv(str(empty_path))

    def test_loaded_columns_intact(self, tmp_path, sample_flights, sample_bookings):
        """Loaded DataFrames retain all expected columns."""
        (tmp_path / 'data').mkdir()
        f_path = tmp_path / 'data' / 'flights.csv'
        b_path = tmp_path / 'data' / 'flight_bookings.csv'
        sample_flights.to_csv(f_path, index=False)
        sample_bookings.to_csv(b_path, index=False)

        flights_df, bookings_df = load_data(str(f_path), str(b_path))

        assert 'flight_id'     in flights_df.columns
        assert 'seat_capacity' in flights_df.columns
        assert 'booking_id'    in bookings_df.columns
        assert 'seats_booked'  in bookings_df.columns


class TestValidator:

    def test_invalid_flight_rejected(self, sample_flights):
        """Bookings referencing a non-existent flight_id are dropped."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F001', 'F999'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [10,     5],
            'booking_date': ['2024-01-01', '2024-01-02'],
        })
        valid = validate_data(sample_flights, bookings)
        assert len(valid) == 1
        assert 'F999' not in valid['flight_id'].values

    def test_all_invalid_flights_rejected(self, sample_flights):
        """All bookings dropped when none reference a valid flight."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001'],
            'flight_id':    ['FXXX'],
            'user_id':      ['U1'],
            'seats_booked': [10],
            'booking_date': ['2024-01-01'],
        })
        valid = validate_data(sample_flights, bookings)
        assert valid.empty

    def test_negative_seats_rejected(self, sample_flights):
        """Bookings with seats_booked < 0 are dropped."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F001', 'F001'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [10,     -5],
            'booking_date': ['2024-01-01', '2024-01-02'],
        })
        valid = validate_data(sample_flights, bookings)
        assert len(valid) == 1
        assert (valid['seats_booked'] > 0).all()

    def test_zero_seats_rejected(self, sample_flights):
        """Bookings with seats_booked == 0 are dropped."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001'],
            'flight_id':    ['F001'],
            'user_id':      ['U1'],
            'seats_booked': [0],
            'booking_date': ['2024-01-01'],
        })
        valid = validate_data(sample_flights, bookings)
        assert valid.empty

    def test_invalid_date_rejected(self, sample_flights):
        """Bookings with unparseable booking_date are dropped."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F001', 'F001'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [10,     5],
            'booking_date': ['2024-01-01', 'not-a-date'],
        })
        valid = validate_data(sample_flights, bookings)
        assert len(valid) == 1
        assert 'not-a-date' not in valid['booking_date'].values

    def test_multiple_violations_all_rejected(self, sample_flights):
        """A row with multiple violations is dropped once."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F001', 'FBAD'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [10,     -1],
            'booking_date': ['2024-01-01', 'bad-date'],
        })
        valid = validate_data(sample_flights, bookings)
        assert len(valid) == 1

    def test_all_valid_bookings_pass(self, sample_flights, sample_bookings):
        """All valid bookings survive validation unchanged."""
        valid = validate_data(sample_flights, sample_bookings)
        assert len(valid) == len(sample_bookings)

class TestSeatAllocation:

    def test_seat_allocation_confirmed(self, sample_flights):
        """Booking within seat capacity is CONFIRMED."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001'],
            'flight_id':    ['F001'],
            'user_id':      ['U1'],
            'seats_booked': [50],
            'booking_date': ['2024-01-01'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'status'].values[0] == 'CONFIRMED'

    def test_seat_allocation_exact_capacity_confirmed(self, sample_flights):
        """Booking exactly equal to seat capacity is CONFIRMED."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001'],
            'flight_id':    ['F003'],
            'user_id':      ['U1'],
            'seats_booked': [30],
            'booking_date': ['2024-01-01'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'status'].values[0] == 'CONFIRMED'

    def test_waitlist_logic(self, sample_flights):
        """Booking exceeding seat capacity is WAITLISTED."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001'],
            'flight_id':    ['F003'],
            'user_id':      ['U1'],
            'seats_booked': [31],
            'booking_date': ['2024-01-01'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'status'].values[0] == 'WAITLIST'

    def test_waitlist_after_seats_exhausted(self, sample_flights):
        """Second booking is WAITLISTED when first booking consumes all seats."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F003', 'F003'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [25,     10],
            'booking_date': ['2024-01-01', '2024-01-02'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'status'].values[0] == 'CONFIRMED'
        assert result.loc[result['booking_id'] == 'B002', 'status'].values[0] == 'WAITLIST'

    def test_multiple_flights_independent(self, sample_flights):
        """Seat tracking is independent per flight."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F003', 'F001'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [30,     50],
            'booking_date': ['2024-01-01', '2024-01-02'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert (result['status'] == 'CONFIRMED').all()

    def test_remaining_seats_calculation(self, sample_flights):
        """remaining_seats = seat_capacity - seats_booked after one booking."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001'],
            'flight_id':    ['F001'],
            'user_id':      ['U1'],
            'seats_booked': [40],
            'booking_date': ['2024-01-01'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'remaining_seats'].values[0] == 60

    def test_remaining_seats_cumulative(self, sample_flights):
        """remaining_seats decrements correctly across sequential bookings."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F001', 'F001'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [40,     30],
            'booking_date': ['2024-01-01', '2024-01-02'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'remaining_seats'].values[0] == 60
        assert result.loc[result['booking_id'] == 'B002', 'remaining_seats'].values[0] == 30

    def test_remaining_seats_waitlisted_not_deducted(self, sample_flights):
        """Waitlisted bookings do NOT reduce remaining_seats."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002'],
            'flight_id':    ['F003', 'F003'],
            'user_id':      ['U1',   'U2'],
            'seats_booked': [30,     10],
            'booking_date': ['2024-01-01', '2024-01-02'],
        })
        result = allocate_seats(sample_flights, bookings)
        assert result.loc[result['booking_id'] == 'B001', 'remaining_seats'].values[0] == 0
        assert result.loc[result['booking_id'] == 'B002', 'remaining_seats'].values[0] == 0


class TestReporter:

    @pytest.fixture
    def allocated_df(self, sample_flights):
        """Pre-allocated DataFrame to use as reporter input."""
        bookings = pd.DataFrame({
            'booking_id':   ['B001', 'B002', 'B003'],
            'flight_id':    ['F001', 'F001', 'F002'],
            'user_id':      ['U1',   'U2',   'U3'],
            'seats_booked': [40,     70,     20],
            'booking_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
        })
        return allocate_seats(sample_flights, bookings)

    def test_booking_status_report_columns(self, allocated_df, tmp_path, monkeypatch):
        """booking_status_report.csv contains all required columns."""
        monkeypatch.chdir(tmp_path)
        booking_report, _ = generate_reports(allocated_df)
        required = {'booking_id', 'flight_id', 'user_id', 'seats_booked', 'booking_date', 'status'}
        assert required.issubset(set(booking_report.columns))

    def test_booking_status_report_row_count(self, allocated_df, tmp_path, monkeypatch):
        """booking_status_report.csv has one row per booking."""
        monkeypatch.chdir(tmp_path)
        booking_report, _ = generate_reports(allocated_df)
        assert len(booking_report) == len(allocated_df)

    def test_booking_status_values_valid(self, allocated_df, tmp_path, monkeypatch):
        """Status column contains only CONFIRMED or WAITLIST."""
        monkeypatch.chdir(tmp_path)
        booking_report, _ = generate_reports(allocated_df)
        assert booking_report['status'].isin(['CONFIRMED', 'WAITLIST']).all()

    def test_flight_summary_columns(self, allocated_df, tmp_path, monkeypatch):
        """flight_seat_summary.csv contains all required columns."""
        monkeypatch.chdir(tmp_path)
        _, flight_summary = generate_reports(allocated_df)
        required = {
            'flight_id', 'seat_capacity', 'total_seats_booked',
            'confirmed_seats', 'waitlisted_seats', 'remaining_seats'
        }
        assert required.issubset(set(flight_summary.columns))

    def test_flight_summary_remaining_seats_correct(self, allocated_df, tmp_path, monkeypatch):
        """remaining_seats = seat_capacity - confirmed_seats."""
        monkeypatch.chdir(tmp_path)
        _, flight_summary = generate_reports(allocated_df)
        for _, row in flight_summary.iterrows():
            assert row['remaining_seats'] == row['seat_capacity'] - row['confirmed_seats']

    def test_flight_summary_confirmed_plus_waitlisted(self, allocated_df, tmp_path, monkeypatch):
        """confirmed_seats + waitlisted_seats == total_seats_booked per flight."""
        monkeypatch.chdir(tmp_path)
        _, flight_summary = generate_reports(allocated_df)
        for _, row in flight_summary.iterrows():
            assert row['confirmed_seats'] + row['waitlisted_seats'] == row['total_seats_booked']

    def test_csv_files_created(self, allocated_df, tmp_path, monkeypatch):
        """Both CSV output files are physically created on disk."""
        monkeypatch.chdir(tmp_path)
        generate_reports(allocated_df)
        assert (tmp_path / 'booking_status_report.csv').exists()
        assert (tmp_path / 'flight_seat_summary.csv').exists()

    def test_csv_content_matches_dataframe(self, allocated_df, tmp_path, monkeypatch):
        """CSV on disk matches the returned DataFrame exactly."""
        monkeypatch.chdir(tmp_path)
        booking_report, _ = generate_reports(allocated_df)
        on_disk = pd.read_csv(tmp_path / 'booking_status_report.csv')
        assert list(on_disk.columns) == list(booking_report.columns)
        assert len(on_disk) == len(booking_report)