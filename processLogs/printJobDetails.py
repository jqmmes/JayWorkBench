from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import DataFrame
from sys import argv
import os

# Initialize Spark
spark = SparkSession\
        .builder\
        .appName("LogProcessing")\
        .master("local[*]")\
        .getOrCreate()

sc = spark.sparkContext
sc.setLogLevel("OFF")

# Functions
def readCSV(file, debug=False):
    if debug:
      print('Reading ' + file)
    return spark.read.csv(file, inferSchema=True, header=True)

def writeCSV(df, path):
    df.write.csv(path, header=True, mode='overwrite')

def processDir(dir, avg, local=True, remote=True, cloud=True):
    jobData = None
    if not os.path.isdir(dir):
        return []
    for device in os.listdir(dir):
        if device == 'completion_timeout_exceded':
            continue
        data = readCSV("{}/{}".format(dir, device))
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
    #.filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_scheduleJob$ODLib_Common_95')\
    start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE.contains('services.broker.BrokerService_scheduleJob'))\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('ACTIONS')\
              .withColumnRenamed('NODE_NAME', 'ORIGIN_NODE')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    #.filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService$scheduleJob$1_invoke_98')\
    job_scheduled = jobData\
              .filter(jobData.OPERATION == 'SCHEDULED')\
              .filter(jobData.CLASS_METHOD_LINE.contains('services.broker.BrokerService$scheduleJob'))\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('ACTIONS')\
              .drop('NODE_NAME')\
              .withColumnRenamed('TIMESTAMP', 'SCHEDULED_TIME')

    #.filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCClient$executeJob$1$1_onCompleted_77')\
    end = jobData\
              .filter(jobData.OPERATION == 'COMPLETE')\
              .filter(jobData.CLASS_METHOD_LINE.contains('services.broker.grpc.BrokerGRPCClient$executeJob'))\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('NODE_NAME')\
              .drop('ACTIONS')\
              .withColumnRenamed('TIMESTAMP', 'END_TIME')

    #.filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCClient$executeJob$1$1_onCompleted_77')\
    data_reached_server = jobData\
              .filter(jobData.OPERATION == 'DATA_REACHED_SERVER')\
              .filter(jobData.CLASS_METHOD_LINE.contains('services.broker.grpc.BrokerGRPCClient$executeJob'))\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .drop('NODE_NAME')\
              .withColumnRenamed('TIMESTAMP', 'END_TIME')


    #.filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_executeJob$ODLib_Common_86')\
    if local or remote:
        # 'DESTINATION_NODE','JOB_ID', 'TIMESTAMP'
        queue_job = jobData\
                    .filter(jobData.OPERATION == 'INIT')\
                    .filter(jobData.CLASS_METHOD_LINE.contains('services.broker.BrokerService_executeJob'))\
                    .drop('OPERATION')\
                    .drop('CLASS_METHOD_LINE')\
                    .drop('ACTIONS')\
                    .withColumnRenamed('NODE_NAME', 'DESTINATION_NODE')\
                    .withColumnRenamed('TIMESTAMP', 'QUEUE_TIME')

        #.filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService$RunnableJobObjects_run_124')\
        execution_start = jobData\
                    .filter(jobData.OPERATION == 'INIT')\
                    .filter(jobData.CLASS_METHOD_LINE.contains('services.worker.WorkerService$RunnableJobObjects'))\
                    .drop('OPERATION')\
                    .drop('CLASS_METHOD_LINE')\
                    .drop('ACTIONS')\
                    .drop('NODE_NAME')\
                    .withColumnRenamed('TIMESTAMP', 'START_TIME')

        #.filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService$RunnableJobObjects_run_129')\
        image_read_end = jobData\
                    .filter(jobData.OPERATION == 'START')\
                    .filter(jobData.CLASS_METHOD_LINE.contains('services.worker.WorkerService$RunnableJobObjects'))\
                    .drop('OPERATION')\
                    .drop('CLASS_METHOD_LINE')\
                    .drop('ACTIONS')\
                    .drop('NODE_NAME')\
                    .withColumnRenamed('TIMESTAMP', 'END_TIME')

        #.filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService$RunnableJobObjects_run_129')\
        execution_end = jobData\
                    .filter(jobData.OPERATION == 'END')\
                    .filter(jobData.CLASS_METHOD_LINE.contains('services.worker.WorkerService$RunnableJobObjects'))\
                    .drop('OPERATION')\
                    .drop('CLASS_METHOD_LINE')\
                    .drop('ACTIONS')\
                    .drop('NODE_NAME')\
                    .withColumnRenamed('TIMESTAMP', 'EXECUTION_END_TIME')
    if cloud:
        #.filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCServer$grpcImpl$1_executeJob_22')\
        cloud_queue_job = jobData\
                  .filter(jobData.OPERATION == 'INIT')\
                  .filter(jobData.CLASS_METHOD_LINE.contains('services.broker.grpc.BrokerGRPCServer$grpcImpl$1_executeJob'))\
                  .drop('OPERATION')\
                  .drop('CLASS_METHOD_LINE')\
                  .drop('ACTIONS')\
                  .withColumnRenamed('NODE_NAME', 'DESTINATION_NODE')\
                  .withColumnRenamed('TIMESTAMP', 'QUEUE_TIME')

        #.filter(jobData.CLASS_METHOD_LINE == 'java.util.concurrent.ThreadPoolExecutor_runWorker_1128')\
        cloud_execution_start = jobData\
                  .filter(jobData.OPERATION == 'INIT')\
                  .filter(jobData.CLASS_METHOD_LINE.contains('java.util.concurrent.ThreadPoolExecutor_runWorker'))\
                  .drop('OPERATION')\
                  .drop('CLASS_METHOD_LINE')\
                  .drop('ACTIONS')\
                  .drop('NODE_NAME')\
                  .withColumnRenamed('TIMESTAMP', 'START_TIME')

        #.filter(jobData.CLASS_METHOD_LINE == 'java.util.concurrent.ThreadPoolExecutor_runWorker_1128')\
        cloud_image_read_end = jobData\
                  .filter(jobData.OPERATION == 'START')\
                  .filter(jobData.CLASS_METHOD_LINE.contains('java.util.concurrent.ThreadPoolExecutor_runWorker'))\
                  .drop('OPERATION')\
                  .drop('CLASS_METHOD_LINE')\
                  .drop('ACTIONS')\
                  .drop('NODE_NAME')\
                  .withColumnRenamed('TIMESTAMP', 'END_TIME')

        #.filter(jobData.CLASS_METHOD_LINE == 'java.util.concurrent.ThreadPoolExecutor_runWorker_1128')\
        cloud_execution_end = jobData\
                  .filter(jobData.OPERATION == 'END')\
                  .filter(jobData.CLASS_METHOD_LINE.contains('java.util.concurrent.ThreadPoolExecutor_runWorker'))\
                  .drop('OPERATION')\
                  .drop('CLASS_METHOD_LINE')\
                  .drop('ACTIONS')\
                  .drop('NODE_NAME')\
                  .withColumnRenamed('TIMESTAMP', 'EXECUTION_END_TIME')

    # Total Duration: end - start

    # Schedule Duration: job_scheduled - start
    # Job transfer Duration: data_reached_server - job_scheduled

    # Localhost execution Duration: end - queue_job
    # Execution Duration: execution_end - execution_start
    # Read Image Data: image_read_end - execution_start
    # Queue Duration: execution_start - queue_job

    # Cloud execution Duration: end - cloud_queue_job
    # Execution Duration: cloud_execution_end - cloud_execution_start
    # Read Image Data: cloud_image_read_end - cloud_execution_start
    # Queue Duration: cloud_execution_start - cloud_queue_job

    # Everything is times
    # TOTAL_DURATION, SCHEDULER_DECISION, DATA_TRANSFER, JOB_COMPLETION {QUEUE, EXECUTION_COMPLETION {IMAGE_LOAD, DETECTION}}

    # TOTAL_DURATION
    jobs = start.join(end, 'JOB_ID')\
                    .withColumn('TOTAL_DURATION', end.END_TIME - start.START_TIME).drop('END_TIME')

    # SCHEDULER_DECISION
    schedules = start.join(job_scheduled, 'JOB_ID').withColumn('SCHEDULER_DECISION', job_scheduled.SCHEDULED_TIME - start.START_TIME).drop('START_TIME').drop('SCHEDULED_TIME').drop('ACTIONS').drop('ORIGIN_NODE').drop('END_TIME')

    # DATA_TRANSFER
    data_transfer = job_scheduled.join(data_reached_server, 'JOB_ID').withColumn('DATA_TRANSFER', data_reached_server.END_TIME - job_scheduled.SCHEDULED_TIME).drop('START_TIME').drop('SCHEDULED_TIME')

    # QUEUE
    if local or remote:
        queue = queue_job.join(execution_start, 'JOB_ID').withColumn('QUEUE', execution_start.START_TIME - queue_job.QUEUE_TIME).drop('START_TIME').drop('QUEUE_TIME')
        if not (local and remote):
            cond = [start.JOB_ID == queue_job.JOB_ID, start.ORIGIN_NODE == queue_job.DESTINATION_NODE]
            origin_queue = queue_job.join(start, cond).drop(start.START_TIME).drop('ORIGIN_NODE').drop('QUEUE_TIME').drop('DESTINATION_NODE').drop(start.JOB_ID)
            local_queue = queue.join(origin_queue, 'JOB_ID')
        if local and not remote:
            queue = local_queue
        elif remote and not local:
            queue = queue.subtract(local_queue)

    if cloud:
        queue_cloud = cloud_queue_job.join(cloud_execution_start, 'JOB_ID').withColumn('QUEUE', cloud_execution_start.START_TIME - cloud_queue_job.QUEUE_TIME).drop('START_TIME').drop('QUEUE_TIME')
        if not local and not remote:
            queue = queue_cloud
        else:
            #queue_cloud = queue_cloud.drop('DESTINATION_NODE')
            queue = queue.union(queue_cloud)

    # IMAGE_LOAD
    if local or remote:
        image_load = execution_start.join(image_read_end, 'JOB_ID').withColumn('IMAGE_LOAD', image_read_end.END_TIME - execution_start.START_TIME).drop('START_TIME').drop('END_TIME')
    if cloud:
        image_load_cloud = cloud_execution_start.join(cloud_image_read_end, 'JOB_ID').withColumn('IMAGE_LOAD', cloud_image_read_end.END_TIME - cloud_execution_start.START_TIME).drop('START_TIME').drop('END_TIME')
        if not local and not remote:
            image_load = image_load_cloud
        else:
            image_load = image_load.union(image_load_cloud)

    # DETECTION
    if local or remote:
        detection = image_read_end.join(execution_end, 'JOB_ID').withColumn('DETECTION', execution_end.EXECUTION_END_TIME - image_read_end.END_TIME).drop('START_TIME').drop('EXECUTION_END_TIME')
    if cloud:
        detection_cloud = cloud_image_read_end.join(cloud_execution_end, 'JOB_ID').withColumn('DETECTION', cloud_execution_end.EXECUTION_END_TIME - cloud_image_read_end.END_TIME).drop('START_TIME').drop('EXECUTION_END_TIME')
        if not local and not remote:
            detection = detection_cloud
        else:
            detection = detection.union(detection_cloud)

    data = jobs.join(schedules, 'JOB_ID').join(data_transfer, 'JOB_ID').join(queue, 'JOB_ID').join(image_load, 'JOB_ID').join(detection, 'JOB_ID').drop('END_TIME').withColumn('RESULT_TRANSFER', jobs.TOTAL_DURATION - (data_transfer.DATA_TRANSFER + queue.QUEUE + image_load.IMAGE_LOAD + detection.DETECTION)).orderBy('START_TIME')

    if avg:
        return data.agg(F.avg('TOTAL_DURATION').alias('TOTAL_DURATION'),\
                         F.avg('SCHEDULER_DECISION').alias('SCHEDULER_DECISION'),\
                         F.avg('DATA_TRANSFER').alias('DATA_TRANSFER'),\
                         F.avg('QUEUE').alias('QUEUE'),\
                         F.avg('IMAGE_LOAD').alias('IMAGE_LOAD'),\
                         F.avg('DETECTION').alias('DETECTION'),\
                         F.avg('RESULT_TRANSFER').alias('RESULT_TRANSFER')).collect()
    return data.collect()


if __name__ == '__main__':
    if len(argv) < 2:
        exit()
    if argv[1] == "avg" and len(argv) < 3:
        exit()
    if argv[1] == "no-header" and len(argv) < 3:
        exit()
    init = 2
    local = True
    remote = True
    cloud = True
    if (argv[1] not in  ["avg", "no-header", "cloud-only-no-header", "remote-only-no-header", "local-only-no-header", "local-remote-only-no-header", "local-cloud-only-no-header", "remote-cloud-only-no-header"]):
        init = 1
        print('ORIGIN,DESTINATION,', end='')
    if argv[1] not in ["no-header", "cloud-only-no-header", "remote-only-no-header", "local-only-no-header", "local-remote-only-no-header", "local-cloud-only-no-header", "remote-cloud-only-no-header"]:
        print('TOTAL_DURATION,SCHEDULER_DECISION,DATA_TRANSFER,QUEUE,IMAGE_LOAD,DETECTION')#,RESULT_TRANSFER')
    if argv[1] in ["local-only", "local-only-no-header"]:
        remote = False
        cloud = False
    elif argv[1] in ["remote-only", "remote-only-no-header"]:
        local = False
        cloud = False
    elif argv[1] in ["cloud-only", "cloud-only-no-header"]:
        local = False
        remote = False
    elif argv[1] in ["local-remote-only", "local-remote-only-no-header"]:
        cloud = False
    elif argv[1] in ["local-cloud-only", "local-cloud-only-no-header"]:
        remote = False
    elif argv[1] in ["remote-cloud-only", "remote-cloud-only-no-header"]:
        local = False
    for dir in argv[init:]:
        for row in processDir(dir, argv[1] == "avg", local, remote, cloud):
            if (argv[1] != "avg"):
                print('{},{},'.format(row.ORIGIN_NODE, row.DESTINATION_NODE), end=''),
            print('{},{},{},{},{},{}'.format(row.TOTAL_DURATION, row.SCHEDULER_DECISION, row.DATA_TRANSFER, row.QUEUE, row.IMAGE_LOAD, row.DETECTION))#, row.RESULT_TRANSFER))
