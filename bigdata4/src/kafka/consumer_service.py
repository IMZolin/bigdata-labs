import os
import signal
import time
from src.logger import Logger
from src.kafka.consumer import Consumer

SHOW_LOG = True

logger = Logger(show=SHOW_LOG).get_logger(__name__)


def main():
    consumer = Consumer()

    def _signal_handler(sig, frame):
        logger.info("Received signal %s, stopping consumer...", sig)
        consumer.stop()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        consumer.run()
    except Exception as e:
        logger.error("Consumer crashed: %s", e, exc_info=True)
    finally:
        logger.info("Consumer service exiting.")

if __name__ == "__main__":
    main()
