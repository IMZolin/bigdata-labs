import logging
import os
import sys

FORMATTER = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
LOG_FILE = os.path.join(os.getcwd(), "logfile.log")


class Logger:
    """
    Class for logging behaviour of data exporting - object of ExportingTool class
    """

    def __init__(self, show: bool = True) -> None:
        """
        Re-defined __init__ method which sets show parameter

        Args:
            show (bool): if set, all logs will be shown in terminal
        """
        self.show = show

    def get_console_handler(self) -> logging.StreamHandler:
        """
        Create a console handler to show logs in the terminal
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        return console_handler

    def get_file_handler(self) -> logging.FileHandler:
        """
        Create a file handler to write logs to logfile.log
        """
        file_handler = logging.FileHandler(LOG_FILE, mode='w')
        file_handler.setFormatter(FORMATTER)
        return file_handler

    def get_logger(self, logger_name: str) -> logging.Logger:
        """
        Create logger with a given name

        Args:
            logger_name (str): name for logger

        Returns:
            logging.Logger: configured logger
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

        # Avoid duplicate handlers
        if not logger.handlers:
            if self.show:
                logger.addHandler(self.get_console_handler())
            logger.addHandler(self.get_file_handler())

        logger.propagate = False
        return logger
