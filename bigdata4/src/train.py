
import configparser
import os
import numpy as np
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
import pickle
import sys
import traceback
from datetime import datetime
from src.logger import Logger
import yaml

SHOW_LOG = True

class Trainer:
    def __init__(self, config_path="config.ini"):
        self.config = configparser.ConfigParser()
        self.logger = Logger(show=SHOW_LOG).get_logger(__name__)
        self.config_path = config_path
        self.config.read(config_path)
        self.base_dir = os.path.dirname(os.path.abspath(config_path))
        self.X_train = np.load(self.config["SPLIT_DATA"]["X_train"])
        self.y_train = np.load(self.config["SPLIT_DATA"]["y_train"])
        self.X_test = np.load(self.config["SPLIT_DATA"]["X_test"])
        self.y_test = np.load(self.config["SPLIT_DATA"]["y_test"])
        folder_name = f"{'NAIVE_BAYES'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.project_path = os.path.join(os.getcwd(), "experiments", folder_name)
        self.bayes_path = os.path.join(self.project_path, "naive_bayes.pkl")

        self.model_config = os.path.join(self.project_path, "config.yml")
        self.metrics_path = os.path.join(self.project_path, "metrics.yml")
        self.logs_path = os.path.join(self.project_path, "logs.txt")
        self.logger.info("Trainer is ready")

    def train_naive_bayes(self, predict=False, alpha=1.0, fit_prior=True):
        classifier = MultinomialNB(alpha=alpha, fit_prior=fit_prior)
        try:
            classifier.fit(self.X_train, self.y_train)
        except Exception:
            self.logger.error(traceback.format_exc())
            sys.exit(1)    

        metrics = {}
        if predict:
            y_pred = classifier.predict(self.X_test)
            accuracy = accuracy_score(self.y_test, y_pred)
            report = classification_report(self.y_test, y_pred)
            metrics['accuracy'] = accuracy
            metrics['classification_report'] = report
            self.logger.info(f"Naive Bayes Accuracy: {accuracy:.4f}")
            self.logger.info("Classification Report (Naive Bayes):\n" + report)

        params = {'path': self.bayes_path, 'alpha': alpha, 'fit_prior': fit_prior}
        self.save_model(classifier, path=self.bayes_path, name="NAIVE_BAYES", params=params, metrics=metrics)

    def save_model(self, classifier, path: str, name: str, params: dict, metrics: dict) -> bool:
        os.makedirs(self.project_path, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(classifier, f)
        self.logger.info(f'{path} is saved')

        params['path'] = os.path.relpath(path, start=os.getcwd())
        if name not in self.config.sections():
            self.config.add_section(name)
        for k, v in params.items():
            self.config.set(name, k, str(v))

        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        self.logger.info(f"Config updated at {self.config_path}")

        # Save params separately
        with open(self.model_config, 'w') as f:
            yaml.dump(params, f)
        self.logger.info(f"Model params saved at {self.model_config}")

        # Save metrics
        with open(self.metrics_path, 'w') as metricsfile:
            yaml.dump(metrics, metricsfile)
        self.logger.info(f"Metrics saved at {self.metrics_path}")
        with open(self.logs_path, 'w') as logfile:
            logfile.write(f"Naive Bayes Training\n")
            logfile.write(f"Parameters: {params}\n")
            logfile.write(f"Metrics: {metrics}\n")
        self.logger.info(f"Logs saved at {self.logs_path}")
        return os.path.isfile(path)


if __name__ == "__main__":
    trainer = Trainer()
    trainer.train_naive_bayes(predict=True, alpha=1.0, fit_prior=True)
