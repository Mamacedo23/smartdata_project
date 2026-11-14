# Databricks notebook source
version = open("../VERSION").read().strip()
print(f"Ejecutando pipeline version {version}")

# COMMAND ----------
from pyspark.sql import functions as F

bronze = spark.createDataFrame(
    [(1, "lima", 120.0), (2, "cusco", 80.5), (3, "arequipa", None)],
    ["id", "ciudad", "monto"],
)

silver = (
    bronze.filter(F.col("importe").isNotNull())
    .withColumn("ciudad", F.upper("ciudad"))
    .withColumn("pipeline_version", F.lit(version))
)

silver.write.mode("overwrite").saveAsTable("workspace.default.demo_silver")
display(silver)
