import configparser
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import sys

from src.logger import Logger

sys.path.insert(1, os.path.join(os.getcwd(), "src"))

from preprocess import DataMaker

config = configparser.ConfigParser()
config.read("config.ini")
SHOW_LOG = True


class TestDataMaker(unittest.TestCase):

    def setUp(self) -> None:
        logger = Logger(SHOW_LOG)
        self.log = logger.get_logger(__name__)
        self.data_maker = DataMaker()

    @patch.object(DataMaker, 'save_splitted_data')
    def test_split_data(self, mock_save_splitted_data):
        mock_save_splitted_data.return_value = True
        result = self.data_maker.split_data()
        self.assertEqual(result, True)
        self.assertEqual(mock_save_splitted_data.call_count, 4)

    @patch("src.preprocess.np.save")  
    def test_save_splitted_data(self, mock_save):
        mock_save.return_value = None  
        self.data_maker.save_splitted_data(np.array([1, 2, 3]), "test.npy")
        mock_save.assert_called()
        args, kwargs = mock_save.call_args
        self.assertTrue(np.array_equal(args[1], np.array([1, 2, 3])))

    @patch('src.preprocess.os.path.isfile')
    def test_save_splitted_data_file_exists(self, mock_isfile):
        mock_isfile.return_value = True
        result = self.data_maker.save_splitted_data(np.array([1, 2, 3]), "test.npy")
        self.assertTrue(result)

    @patch('src.preprocess.os.path.isfile')
    def test_save_splitted_data_file_not_exists(self, mock_isfile):
        mock_isfile.return_value = False
        result = self.data_maker.save_splitted_data(np.array([1, 2, 3]), "test.npy")
        self.assertFalse(result)

    @patch('src.preprocess.os.path.isfile')
    def test_data_path_not_exists(self, mock_isfile):
        mock_isfile.return_value = False
        result = self.data_maker.split_data(test_size=0.2)
        self.assertFalse(result)

    @patch('src.preprocess.os.path.isfile')
    @patch('src.preprocess.pd.read_csv')
    def test_data_path_exists(self, mock_read_csv, mock_isfile):
        mock_isfile.return_value = True
        mock_read_csv.return_value = pd.DataFrame({
            'SentimentText': ['So bad!', 'Great!'],
            'Sentiment': [0, 1]
        })
        result = self.data_maker.split_data(test_size=0.2)
        self.assertTrue(result)


if __name__ == "__main__":
    Logger(SHOW_LOG).get_logger(__name__).info("TEST PREPROCESSING IS READY")
    unittest.main()
