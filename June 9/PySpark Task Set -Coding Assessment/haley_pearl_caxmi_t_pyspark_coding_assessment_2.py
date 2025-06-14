# -*- coding: utf-8 -*-
"""Haley Pearl Caxmi T-PySpark Coding Assessment 2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1K9bjX8k-wyWMgKoDVV1wtkfq_A7H12hk
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *


spark = SparkSession.builder.appName("PySparkTaskSet").getOrCreate()
spark

# Mount Drive
from google.colab import drive
drive.mount('/content/drive')
# Set data paths
base_path = "/content/drive/MyDrive"
emp_path = f"{base_path}/employees.csv"
att_path = f"{base_path}/attendance.csv"
bonus_path = f"{base_path}/bonuses.json"

#1. Ingestion & Exploration
#Read all 3 files (CSV + JSON) using PySpark
employees = spark.read.option("header", True).csv(emp_path, inferSchema=True)
attendance = spark.read.option("header", True).csv(att_path, inferSchema=True)
bonuses = spark.read.option("multiline", True).json(bonus_path)

#Show schemas and sample records
employees.printSchema()
attendance.printSchema()
bonuses.printSchema()

employees.show(truncate=False)
attendance.show(truncate=False)
bonuses.show(truncate=False)

#Count distinct departments
employees.select("Department").distinct().show()

#2. DataFrame Operations
#Add a column TenureYears using datediff() and round()
from pyspark.sql.functions import datediff, current_date, round, col

emp_with_tenure = employees.withColumn("TenureYears", round(datediff(current_date(), col("JoinDate"))/365, 2))
emp_with_tenure.show()

#Calculate TotalCompensation = Salary + Bonus
emp_bonus = emp_with_tenure.join(bonuses, "EmpID", "left")
emp_comp = emp_bonus.withColumn("TotalCompensation", col("Salary") + col("Bonus"))
emp_comp.select("EmpID", "Name", "Salary", "Bonus", "TotalCompensation").show()

#Filter employees with more than 2 years
emp_comp.filter(col("TenureYears") > 2).show()

#Employees who report to a manager
employees.filter(col("ManagerID").isNotNull()).show()

#3. Aggregation
#Average salary per department
employees.groupBy("Department").agg(avg("Salary").alias("AvgSalary")).show()

#Number of employees under each manager
employees.groupBy("ManagerID").count().withColumnRenamed("count", "EmployeesUnder").show()

#Count of absences per employee
attendance.filter(col("Status") == "Absent").groupBy("EmpID").count().withColumnRenamed("count", "Absences").show()

#4. Joins
#Join employees + attendance → Attendance %
total_days = attendance.groupBy("EmpID").count().withColumnRenamed("count", "TotalDays")
present_days = attendance.filter(col("Status") == "Present").groupBy("EmpID").count().withColumnRenamed("count", "PresentDays")
attendance_pct = total_days.join(present_days, "EmpID").withColumn("AttendancePct", round(col("PresentDays") / col("TotalDays") * 100, 2))
attendance_pct.show()

#Join employees + bonuses → Top 3 by TotalCompensation
top3 = emp_comp.orderBy(col("TotalCompensation").desc()).limit(3)
top3.select("EmpID", "Name", "TotalCompensation").show()

#Multi-level join: employees + bonuses + attendance
multi_join = employees.join(bonuses, "EmpID", "left").join(attendance, "EmpID", "left")
multi_join.show()

#5. String & Date Functions
#Extract year and month from JoinDate
employees.withColumn("JoinYear", year("JoinDate")).withColumn("JoinMonth", month("JoinDate")).select("EmpID", "Name", "JoinYear", "JoinMonth").show()

#Mask names using regex_replace
employees.withColumn("MaskedName", regexp_replace("Name", r'[a-zA-Z]', '*')).show()

#Create EmpCode like EMP001
employees.withColumn("EmpCode", format_string("EMP%03d", col("EmpID"))).show()

#6. Conditional & Null Handling
#Label performance
emp_perf = emp_bonus.withColumn(
    "Performance",
    when(col("Bonus") > 6000, "High")
    .when((col("Bonus") >= 4000) & (col("Bonus") <= 6000), "Medium")
    .otherwise("Low")
)
emp_perf.select("EmpID", "Name", "Bonus", "Performance").show()

#Handle missing ManagerID using fillna("No Manager")
employees.withColumn("ManagerID_str", col("ManagerID").cast("string")).fillna("No Manager", subset=["ManagerID_str"]).show()

#7. Spark SQL
#Create database
spark.sql("CREATE DATABASE IF NOT EXISTS hr")
spark.sql("USE hr")

#Save as temp views (or as permanent tables in warehouse path if needed)
employees.createOrReplaceTempView("employees")
attendance.createOrReplaceTempView("attendance")
bonuses.createOrReplaceTempView("bonuses")

#Top paid employee in each department
spark.sql("""
SELECT Department, Name, Salary
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY Department ORDER BY Salary DESC) as rnk
    FROM employees
) WHERE rnk = 1
""").show()

#Attendance rate by department
spark.sql("""
SELECT e.Department, ROUND(SUM(CASE WHEN a.Status='Present' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) AS AttendanceRate
FROM employees e
JOIN attendance a ON e.EmpID = a.EmpID
GROUP BY e.Department
""").show()

#Employees joined after 2021 with salary > 70000
spark.sql("""
SELECT * FROM employees
WHERE year(JoinDate) > 2021 AND Salary > 70000
""").show()

#8. Advanced
# UDF to classify departments
from pyspark.sql.types import StringType

def dept_type(dept):
    return "Tech" if dept in ["Engineering", "IT"] else "Non-Tech"

spark.udf.register("dept_type_udf", dept_type, StringType())

employees.withColumn("DeptType", expr("dept_type_udf(Department)")).show()

#Create a view emp_attendance_summary
emp_attendance_summary = employees.join(attendance_pct, "EmpID", "left")
emp_attendance_summary.createOrReplaceTempView("emp_attendance_summary")

#Save as Parquet partitioned by Department
emp_attendance_summary.write.mode("overwrite").partitionBy("Department").parquet("/content/drive/MyDrive/emp_attendance_summary_parquet")