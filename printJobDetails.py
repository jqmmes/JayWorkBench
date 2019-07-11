from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from sys import argv
import os

# Initialize Spark
spark = SparkSession\
        .builder\
        .appName("LogProcessing")\
        .master("local[*]")\
        .getOrCreate()
sc = spark.sparkContext
sc.setLogLevel("WARN")

# Functions
def readCSV(file, debug=False):
    if debug:
      print('Reading ' + file)
    return spark.read.csv(file, inferSchema=True, header=True)

def writeCSV(df, path):
    df.write.csv(path, header=True, mode='overwrite')

if __name__ == '__main__':
    print('TIMESTAMP,ORIGIN,DESTINATION,DURATION,TOTAL_DURATION,JOB_ID')
    jobData = None
    for device in os.listdir(argv[1]):
        if device == 'completion_timeout_exceded':
            continue
        data = readCSV("{}/{}".format(argv[1], device))
        if jobData is None:
            jobData = data\
                      .filter(data.JOB_ID.isNotNull())\
                      .filter(data.JOB_ID != 'WORKER_CALIBRATION')\
                      .select('NODE_NAME','JOB_ID','TIMESTAMP','CLASS_METHOD_LINE','OPERATION', 'ACTIONS')
        else:
            jobData = jobData.union(data\
                      .filter(data.JOB_ID.isNotNull())\
                      .filter(data.JOB_ID != 'WORKER_CALIBRATION')\
                      .select('NODE_NAME','JOB_ID','TIMESTAMP','CLASS_METHOD_LINE','OPERATION', 'ACTIONS'))
    start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_scheduleJob$ODLib_Common_78')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('ACTIONS')\
              .withColumnRenamed('NODE_NAME', 'ORIGIN_NODE')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    end = jobData\
              .filter(jobData.OPERATION == 'COMPLETE')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCClient$executeJob$1_run_48')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('NODE_NAME')\
              .drop('ACTIONS')\
              .withColumnRenamed('TIMESTAMP', 'END_TIME')

    # services.broker.BrokerService_executeJob$ODLib_Common_72, INIT
    # 'DESTINATION_NODE','JOB_ID', 'TIMESTAMP'
    localhost_execution_start = jobData\
                .filter(jobData.OPERATION == 'INIT')\
                .filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_executeJob$ODLib_Common_72')\
                .drop('OPERATION')\
                .drop('CLASS_METHOD_LINE')\
                .drop('ACTIONS')\
                .withColumnRenamed('NODE_NAME', 'DESTINATION_NODE')\
                .withColumnRenamed('TIMESTAMP', 'START_TIME')

    #'JOB_ID', 'TIMESTAMP'
    localhost_execution_end = jobData\
                .filter(jobData.OPERATION == 'COMPLETE')\
                .filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService$RunnableJobObjects_run_132')\
                .drop('OPERATION')\
                .drop('CLASS_METHOD_LINE')\
                .drop('ACTIONS')\
                .drop('NODE_NAME')\
                .withColumnRenamed('TIMESTAMP', 'END_TIME')

    cloud_start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCServer$grpcImpl$1_executeJob_20')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('ACTIONS')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    cloud_end = jobData\
              .filter(jobData.OPERATION == 'END')\
              .filter(jobData.CLASS_METHOD_LINE == 'java.util.concurrent.ThreadPoolExecutor_runWorker_1128')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('ACTIONS')\
              .drop('NODE_NAME')\
              .withColumnRenamed('TIMESTAMP', 'END_TIME')


    device_jobs = start.join(end, 'JOB_ID')\
                    .withColumn('TOTAL_DURATION', end.END_TIME - start.START_TIME).drop('END_TIME')

    execution_jobs = localhost_execution_start.join(localhost_execution_end, 'JOB_ID')\
                    .withColumn('DURATION', localhost_execution_end.END_TIME - localhost_execution_start.START_TIME).drop('START_TIME').drop('END_TIME').withColumnRenamed('ORIGIN_NODE', 'DESTINATION_NODE').withColumnRenamed('JOB_ID', 'JOB_ID_1')

    cloud_jobs = cloud_start.join(cloud_end, 'JOB_ID')\
                .withColumn('DURATION', cloud_end.END_TIME - cloud_start.START_TIME).drop('START_TIME').drop('END_TIME').withColumnRenamed('ORIGIN_NODE', 'DESTINATION_NODE').withColumnRenamed('JOB_ID', 'JOB_ID_1')

    execution_jobs = execution_jobs.union(cloud_jobs)

    for row in device_jobs.join(execution_jobs, device_jobs.JOB_ID == execution_jobs.JOB_ID_1, how='left').drop('JOB_ID_1').sort('START_TIME').collect():
        print('{},{},{},{},{},{}'.format(row.START_TIME, row.ORIGIN_NODE, row.DESTINATION_NODE, row.DURATION, row.TOTAL_DURATION, row.JOB_ID))
