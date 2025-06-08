import unittest
from unittest.mock import patch, mock_open
import os
import sys
import datetime # Import real datetime for use in tests
import json
import tempfile
import shutil

# Add project root to sys.path to allow importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from product_hunt_digest.src import utils

class TestUtils(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config_dir = os.path.join(self.temp_dir, 'config')
        self.temp_logs_dir = os.path.join(self.temp_dir, 'logs')
        os.makedirs(self.temp_config_dir, exist_ok=True)
        os.makedirs(self.temp_logs_dir, exist_ok=True)

        self.original_api_keys_file = utils.API_KEYS_FILE
        self.original_error_log_file = utils.ERROR_LOG_FILE
        self.original_config_dir = utils.CONFIG_DIR
        self.original_log_dir = utils.LOG_DIR

        utils.CONFIG_DIR = self.temp_config_dir
        utils.LOG_DIR = self.temp_logs_dir
        utils.API_KEYS_FILE = os.path.join(self.temp_config_dir, 'api_keys.json')
        utils.ERROR_LOG_FILE = os.path.join(self.temp_logs_dir, 'error.log')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        utils.API_KEYS_FILE = self.original_api_keys_file
        utils.ERROR_LOG_FILE = self.original_error_log_file
        utils.CONFIG_DIR = self.original_config_dir
        utils.LOG_DIR = self.original_log_dir

    @patch('product_hunt_digest.src.utils.datetime') # Patch the datetime module used in utils.py
    def test_get_previous_week_yyy_ww(self, mock_datetime_module):
        # Crucial: Make sure the mocked datetime module uses real timedelta
        mock_datetime_module.timedelta = datetime.timedelta

        # Case 1: Test with a date where previous week is in the same year
        mock_datetime_module.date.today.return_value = datetime.date(2023, 10, 27) # A Friday
        self.assertEqual(utils.get_previous_week_yyy_ww(), "2023/42")

        # Case 2: Test with a date where previous week is in the previous year
        mock_datetime_module.date.today.return_value = datetime.date(2024, 1, 3) # A Wednesday
        self.assertEqual(utils.get_previous_week_yyy_ww(), "2023/52")

        # Case 3: Test another case: Today is Monday, Jan 8th, 2024 (Week 2)
        mock_datetime_module.date.today.return_value = datetime.date(2024, 1, 8) # A Monday
        self.assertEqual(utils.get_previous_week_yyy_ww(), "2024/01")


    def test_get_api_key(self):
        # Case 1: Valid key
        mock_api_keys_content = {"gemini_api_key": "test_gemini_key", "grok_api_key": "test_grok_key"}
        with open(utils.API_KEYS_FILE, 'w') as f:
            json.dump(mock_api_keys_content, f)
        self.assertEqual(utils.get_api_key("gemini_api_key"), "test_gemini_key")
        self.assertEqual(utils.get_api_key("grok_api_key"), "test_grok_key")

        # Case 2: Non-existent key
        self.assertIsNone(utils.get_api_key("non_existent_key"))

        # Case 3: api_keys.json not found
        if os.path.exists(utils.API_KEYS_FILE):
            os.remove(utils.API_KEYS_FILE)
        self.assertIsNone(utils.get_api_key("gemini_api_key"))

        # Case 4: Malformed JSON
        with open(utils.API_KEYS_FILE, 'w') as f:
            f.write("this is not json")
        self.assertIsNone(utils.get_api_key("gemini_api_key"))

        # Case 5: Config directory not found
        original_temp_config_dir = utils.CONFIG_DIR
        non_existent_dir = os.path.join(self.temp_dir, "non_existent_config_unique_for_test")
        utils.CONFIG_DIR = non_existent_dir
        temp_api_keys_file_in_non_existent_dir = os.path.join(utils.CONFIG_DIR, 'api_keys.json')
        original_api_keys_file_path_for_test = utils.API_KEYS_FILE
        utils.API_KEYS_FILE = temp_api_keys_file_in_non_existent_dir

        self.assertIsNone(utils.get_api_key("gemini_api_key"))

        utils.CONFIG_DIR = original_temp_config_dir
        utils.API_KEYS_FILE = original_api_keys_file_path_for_test


    @patch('product_hunt_digest.src.utils.datetime') # Patch the datetime module
    def test_log_error(self, mock_datetime_module):
        # Crucial: Ensure real datetime object is returned by datetime.datetime.now()
        # The mock_datetime_module itself is a MagicMock.
        # mock_datetime_module.datetime is another MagicMock.
        # mock_datetime_module.datetime.now is what we want to control.
        mock_now_instance = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime_module.datetime.now.return_value = mock_now_instance

        test_message = "This is a unit test error message"
        utils.log_error(test_message)

        self.assertTrue(os.path.exists(utils.ERROR_LOG_FILE))
        with open(utils.ERROR_LOG_FILE, 'r') as f:
            content = f.read().strip()

        expected_log_entry = f"[{mock_now_instance.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {test_message}"
        self.assertEqual(content, expected_log_entry)

        current_error_log_path = utils.ERROR_LOG_FILE
        current_log_dir = utils.LOG_DIR

        new_temp_logs_dir = os.path.join(self.temp_dir, "newly_created_logs")
        if os.path.exists(new_temp_logs_dir):
            shutil.rmtree(new_temp_logs_dir)
        self.assertFalse(os.path.exists(new_temp_logs_dir))

        utils.LOG_DIR = new_temp_logs_dir
        utils.ERROR_LOG_FILE = os.path.join(new_temp_logs_dir, "error.log")

        utils.log_error("Another message for new dir creation")
        self.assertTrue(os.path.exists(new_temp_logs_dir))
        self.assertTrue(os.path.exists(utils.ERROR_LOG_FILE))

        with open(utils.ERROR_LOG_FILE, 'r') as f:
            content_new_dir = f.read().strip()
        expected_log_entry_new_dir = f"[{mock_now_instance.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Another message for new dir creation"
        self.assertEqual(content_new_dir, expected_log_entry_new_dir)

        utils.LOG_DIR = current_log_dir
        utils.ERROR_LOG_FILE = current_error_log_path

if __name__ == '__main__':
    unittest.main()
