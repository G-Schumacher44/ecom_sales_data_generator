# src/utils/date_utils.py
from datetime import datetime, timedelta
import random

def random_date_in_last_n_days(n=30, faker_instance=None):
    """
    Generates a random date within the last n days from today.
    If faker_instance is provided, it uses faker's date_between.
    """
    if faker_instance:
        return faker_instance.date_between(start_date=f'-{n}d', end_date='today')
    else:
        today = datetime.now().date()
        random_days = random.randint(0, n)
        return today - timedelta(days=random_days)

def safe_date_between(start_date, end_date):
    """
    Generates a random date between start_date and end_date (inclusive).
    Handles string dates by converting them to datetime.date objects.
    Ensures start_date <= end_date.
    """
    # Convert string dates to datetime.date objects if necessary
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date > end_date:
        # Swap if start_date is after end_date to ensure a valid range
        start_date, end_date = end_date, start_date

    time_between_dates = end_date - start_date
    random_days = random.randint(0, time_between_dates.days)
    return start_date + timedelta(days=random_days)