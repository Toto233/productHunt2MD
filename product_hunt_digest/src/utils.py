import datetime
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
API_KEYS_FILE = os.path.join(CONFIG_DIR, 'api_keys.json')
ERROR_LOG_FILE = os.path.join(LOG_DIR, 'error.log')

def get_previous_week_yyy_ww() -> str:
    """
    Determines the ISO year and week number for the Monday of the previous week.
    Returns a string formatted as "YYYY/WW".
    """
    today = datetime.date.today()
    start_of_current_week = today - datetime.timedelta(days=today.weekday())
    start_of_previous_week = start_of_current_week - datetime.timedelta(days=7)
    iso_year = start_of_previous_week.isocalendar()[0]
    iso_week = start_of_previous_week.isocalendar()[1]
    return f"{iso_year}/{iso_week:02d}"

def log_error(message: str):
    """
    Appends an error message with a timestamp to the error log file.
    Format: [YYYY-MM-DD HH:MM:SS] ERROR: message
    """
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] ERROR: {message}\n"
    try:
        with open(ERROR_LOG_FILE, 'a') as f:
            f.write(log_entry)
    except IOError as e:
        print(f"Failed to write to log file: {e}")


def get_api_key(service_name: str) -> str | None:
    """
    Retrieves an API key from the api_keys.json file.

    Args:
        service_name: The name of the service (e.g., "gemini_api_key").

    Returns:
        The API key string if found, otherwise None.
    """
    if not os.path.exists(CONFIG_DIR):
        log_error(f"Config directory not found: {CONFIG_DIR}")
        return None

    try:
        with open(API_KEYS_FILE, 'r') as f:
            keys = json.load(f)
        return keys.get(service_name)
    except FileNotFoundError:
        log_error(f"API keys file not found: {API_KEYS_FILE}")
        return None
    except json.JSONDecodeError:
        log_error(f"Error decoding JSON from API keys file: {API_KEYS_FILE}")
        return None
    except Exception as e:
        log_error(f"An unexpected error occurred while reading API keys: {e}")
        return None
