import argparse
import configparser
from pathlib import Path
from src.logger import Logger
from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.errors import AnalysisException
import py4j

root_dir = Path(__file__).parent.parent
CONFIG_PATH = str(root_dir / 'config.ini')

class WordCounter:
    def __init__(self):
        self.logger = Logger(show=True).get_logger(__name__)
        config = configparser.ConfigParser()
        config.optionxform = str  
        config.read(CONFIG_PATH)
        
        try:
            config.read(CONFIG_PATH)
            if 'SPARK' not in config:
                raise KeyError("Missing 'SPARK' section in config.ini")
        except (configparser.Error, KeyError) as e:
            self.logger.error(f"Configuration error: {e}", exc_info=True)
            raise
        self.config = config
        spark_conf = SparkConf().setAll(config['SPARK'].items())
        self.spark = SparkSession.builder \
            .appName("WordCount") \
            .master("local[*]") \
            .config(conf=spark_conf) \
            .getOrCreate()
        self.word_counts = None

    def process(self, input_path, output_path=None):
        try:
            df = self.spark.read.text(input_path)
            # Split lines into words
            words = df.selectExpr("explode(split(value, ' ')) as word")
            # Count word occurrences
            self.word_counts = (
                words.groupBy("word").count().orderBy("count", ascending=False)
            )
            self.logger.info("Word count results:")
            self.word_counts.show()
            # Save results if output path provided
            if output_path:
                self.word_counts.write.mode("overwrite").csv(output_path, header=True)
                self.logger.info(f"Results saved to: {output_path}")
        except FileNotFoundError as e:
            self.logger.error(f"Input path not found: {input_path}", exc_info=True)
            raise
        except AnalysisException as e:
            self.logger.error(f"Spark analysis error: {e}", exc_info=True)
            raise
        except py4j.protocol.Py4JJavaError as e:
            self.logger.error(f"Py4J Java error: {e}", exc_info=True)
            raise
        except Exception as e:  # Fallback for truly unexpected cases
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            raise
        finally:
            self.spark.stop()
            self.logger.info("Spark session stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    wc = WordCounter()
    wc.process(args.input, args.output)
