import configparser
import os
import unittest
import numpy as np
import glob
from unittest import mock
import sys
import tempfile
import shutil
from src.logger import Logger
from src.train import Trainer

sys.path.insert(1, os.path.join(os.getcwd(), "src"))

SHOW_LOG = True


class TestTrainer(unittest.TestCase):
    def setUp(self):
        self.temp_config = "tmp_config.ini"
        shutil.copy("test_config.ini", self.temp_config)
        self.trainer = Trainer(config_path=self.temp_config)
        # self.trainer = Trainer(config_path="test_config.ini")

    def tearDown(self):
        if os.path.isdir(self.trainer.project_path):
            shutil.rmtree(self.trainer.project_path)
        if os.path.exists(self.temp_config):
            os.remove(self.temp_config)

    def test_init_data(self):
        self.assertIsNotNone(self.trainer.X_train, "X_train shouldn't be None after initialization")
        self.assertIsNotNone(self.trainer.y_train, "y_train shouldn't be None after initialization")
        self.assertIsNotNone(self.trainer.X_test, "X_test shouldn't be None after initialization")
        self.assertIsNotNone(self.trainer.y_test, "y_test shouldn't be None after initialization")

    def test_start_train(self):
        self.trainer.train_naive_bayes(predict=False)
        self.assertTrue(os.path.isfile(self.trainer.bayes_path), "Model file should be saved after training")

    def test_save(self):
        self.trainer.train_naive_bayes(predict=True)

        # Check that all relevant files are saved
        self.assertTrue(os.path.isfile(self.trainer.bayes_path), "Model file not saved")
        self.assertTrue(os.path.isfile(self.trainer.config_path), "Config file not saved")
        self.assertTrue(os.path.isfile(self.trainer.metrics_path), "Metrics file not saved")
        self.assertTrue(os.path.isfile(self.trainer.logs_path), "Logs file not saved")

        # Optionally: Check content of metrics/config
        with open(self.trainer.metrics_path, 'r') as f:
            metrics_content = f.read()
        self.assertIn("accuracy", metrics_content, "Accuracy metric should be present in saved metrics")
        with open(self.trainer.config_path, 'r') as f:
            config_content = f.read()
        self.assertIn("alpha", config_content, "Alpha parameter should be saved in config file")


if __name__ == "__main__":
    Logger(SHOW_LOG).get_logger(__name__).info("TEST TRAINING IS READY")
    unittest.main()