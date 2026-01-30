import configparser
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
import sys

from src.logger import Logger

sys.path.insert(1, os.path.join(os.getcwd(), "src"))
from preprocess import DataMaker

SHOW_LOG = True

class TestDataMaker(unittest.TestCase):

    def setUp(self) -> None:
        logger = Logger(SHOW_LOG)
        self.log = logger.get_logger(__name__)
        self.temp_dir = tempfile.mkdtemp()
        self.temp_config = os.path.join(self.temp_dir, "tmp_config.ini")
        shutil.copy("test_config.ini", self.temp_config)
        self.data_maker = DataMaker(config_path=self.temp_config, project_path=self.temp_dir)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.temp_config):
            os.remove(self.temp_config)

    @patch.object(DataMaker, 'save_splitted_data', return_value=True)
    @patch('src.preprocess.pd.read_csv')
    @patch('src.preprocess.os.path.isfile')
    def test_split_data(self, mock_isfile, mock_read_csv, mock_save_splitted_data):
        # Treat all files as existing
        def isfile_side_effect(path):
            if path == self.data_maker.data_path:
                return True
            elif path in self.data_maker.train_path + self.data_maker.test_path:
                return True
            return False
        mock_isfile.side_effect = isfile_side_effect

        mock_read_csv.return_value = pd.DataFrame({
            'SentimentText': ['Bad movie', 'Great film'],
            'Sentiment': [0, 1]
        })

        result = self.data_maker.split_data()
        self.assertTrue(result)
        self.assertEqual(mock_save_splitted_data.call_count, 4)

    @patch("src.preprocess.np.save", return_value=None)
    @patch("src.preprocess.os.path.isfile", return_value=True)
    def test_save_splitted_data(self, mock_isfile, mock_save):
        data = np.array([1, 2, 3])
        result = self.data_maker.save_splitted_data(data, "test.npy")
        self.assertTrue(result)
        mock_save.assert_called_once()
        args, _ = mock_save.call_args
        self.assertTrue(np.array_equal(args[1], data))

    @patch("src.preprocess.os.path.isfile", return_value=False)
    def test_save_splitted_data_file_not_exists(self, mock_isfile):
        result = self.data_maker.save_splitted_data(np.array([1, 2, 3]), "test.npy")
        self.assertFalse(result)

    @patch("src.preprocess.os.path.isfile", return_value=False)
    def test_data_path_not_exists(self, mock_isfile):
        result = self.data_maker.split_data(test_size=0.2)
        self.assertFalse(result)

    @patch('src.preprocess.os.path.isfile')
    @patch('src.preprocess.pd.read_csv')
    @patch.object(DataMaker, 'save_splitted_data', return_value=True)
    def test_data_path_exists(self, mock_save, mock_read_csv, mock_isfile):
        def isfile_side_effect(path):
            if path == self.data_maker.data_path:
                return True
            elif path in self.data_maker.train_path + self.data_maker.test_path:
                return True
            return False

        mock_isfile.side_effect = isfile_side_effect

        mock_read_csv.return_value = pd.DataFrame({
            'SentimentText': ['So bad!', 'Great!'],
            'Sentiment': [0, 1]
        })

        result = self.data_maker.split_data(test_size=0.2)
        self.assertTrue(result)
        self.assertEqual(mock_save.call_count, 4)


if __name__ == "__main__":
    Logger(SHOW_LOG).get_logger(__name__).info("TEST PREPROCESSING IS READY")
    unittest.main()
