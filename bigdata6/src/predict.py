import configparser
from pathlib import Path
from src.logger import Logger
import pyspark
from pyspark import SparkConf
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

root_dir = Path(__file__).parent.parent
CONFIG_PATH = str(root_dir / 'config.ini')


class Predictor:
    def __init__(self):
        self.logger = Logger(show=True).get_logger(__name__)
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(CONFIG_PATH)

        self.config = config
        spark_conf = SparkConf().setAll(config['SPARK'].items())
        self.spark = SparkSession.builder \
            .appName("KMeans") \
            .master("local[*]") \
            .config(conf=spark_conf) \
            .getOrCreate()

        self.data_path = str(root_dir / config['DATA']['processed'])
        self.model_path = str(root_dir / config['MODEL']['model_path'])

        self.pipeline = PipelineModel.load(self.model_path)
        self.logger.info("Model successfully loaded")

    def predict(self, df: pyspark.sql.DataFrame):
        """Return DataFrame with predicted cluster labels."""
        try:
            for c in df.columns:
                df = df.withColumn(c, col(c).cast("double"))
            df = df.na.fill(0)
            result_df = self.pipeline.transform(df)
            cols = df.columns + ["cluster"]
            return result_df.select(*cols)
        except Exception as e:
            self.logger.error(f"Error: {str(e)}", exc_info=True)
            raise

    def stop(self):
        self.spark.stop()
        self.logger.info("SparkSession stopped")


if __name__ == "__main__":
    pred = Predictor()
    df_new = pred.spark.read.option("header", True) \
                       .option("sep", "\t") \
                       .option("inferSchema", True) \
                       .csv(pred.data_path)

    labels = pred.predict(df_new).select('cluster')
    labels.show(10, truncate=False)
    pred.stop()
