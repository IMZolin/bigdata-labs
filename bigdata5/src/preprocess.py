import os
import shutil
import configparser
from pathlib import Path
from src.logger import Logger
from functools import reduce
from pyspark import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr, when
from pyspark.sql.utils import AnalysisException

root_dir = Path(__file__).parent.parent
CONFIG_PATH = str(root_dir / 'config.ini')


class DataMaker:
    def __init__(self):
        self.spark = None
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

        self.source_path = str(root_dir / config['DATA']['source'])
        self.output_path = str(root_dir / config['DATA']['processed'])

    def prepare_data(self):
        try:
            self.logger.info("Starting preprocessing...")

            # Reading data
            try:
                df = self.spark.read.option("header", True) \
                    .option("sep", "\t") \
                    .option("inferSchema", True) \
                    .csv(self.source_path)
            except AnalysisException as e:
                self.logger.error(f"Spark read error: {e}")
                raise
            except FileNotFoundError as e:
                self.logger.error(f"Source file not found: {e}")
                raise

            nutrient_columns = df.columns[88:]
            df_nutrients = df.select(nutrient_columns)

            # Clean missing values
            df_cleaned = df_nutrients.filter(
                ~reduce(lambda a, b: a & b, [col(c).isNull() for c in df_nutrients.columns])
            )
            df_filled = df_cleaned.fillna(0.0)

            lower_bound, upper_bound = 0.0, 1000.0
            median_exprs = [expr(f"percentile_approx(`{c}`, 0.5)").alias(c) for c in df_filled.columns]

            medians = df_filled.agg(*median_exprs).collect()[0].asDict()
            df_cleansed = df_filled

            for c in df_filled.columns:
                if c in medians and medians[c] is not None:
                    median = medians[c]
                    df_cleansed = df_cleansed.withColumn(
                        c,
                        when((col(c) < lower_bound) | (col(c) > upper_bound), median).otherwise(col(c))
                    )

            temp_output_path = self.output_path[:-4]

            try:
                df_cleansed.coalesce(1).write \
                    .mode("overwrite") \
                    .option("header", True) \
                    .option("sep", "\t") \
                    .csv(temp_output_path)
            except PermissionError as e:
                self.logger.error(f"Permission error while writing: {e}")
                raise

            for file in os.listdir(temp_output_path):
                if file.startswith("part-00000"):
                    shutil.move(os.path.join(temp_output_path, file), self.output_path)
                    break
            shutil.rmtree(temp_output_path)

            self.logger.info("Data successfully processed and saved!")

        except (AnalysisException, FileNotFoundError, PermissionError) as e:
            # Known issues: log as error and re-raise
            self.logger.error(f"Known error: {e}", exc_info=True)
            raise
        except Exception as e:
            # Unexpected issues: log as critical
            self.logger.critical(f"Unexpected error: {e}", exc_info=True)
            raise
        finally:
            if self.spark:
                self.spark.stop()
                self.logger.info("Spark session stopped")


if __name__ == "__main__":
    data_maker = DataMaker()
    data_maker.prepare_data()
