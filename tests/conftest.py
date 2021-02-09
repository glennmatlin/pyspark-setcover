from pyspark.conf import SparkConf
from pyspark.sql.session import SparkSession
import pytest

conf = SparkConf()
conf.set("spark.logConf", "true")


@pytest.fixture(scope="session")
def spark_fixture():
    spark = (
        SparkSession.builder.config(conf=conf)
        .master("local")
        .appName("pyspark-setcover")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("OFF")
    yield spark