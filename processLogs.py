from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from sys import argv
import os

#
#   TODO:   AVERAGE TIME PER JOB
#           NUMBER OF JOBS RECEIVED /  NUMBER OF JOBS COMPLETED / NUMBER OF JOBS OFFLOADED (TO CLOUD/TO REMOTE DEVICES)    BrokerService_scheduleJob$ODLib_Common_78   / BrokerGRPCClient$executeJob$1_run_48   /   EstimatedTimeScheduler_scheduleJob_52,SELECTED_WORKER,435fab6e-6f28-4f70-adf9-36c84d4ded0b,"WORKER_ID=406e649d-a53c-4d5a-a8d6-7f2535448732"
#           QUEUE SIZE EVOLUTION / MAX QUEUE SIZE         queueJob$ODLib_Common_40          JOBS_IN_QUEUE=%d
#           TOTAL RUN TIME
#

COMPRESSED_PRINT = True

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

def processLogs(data):
    jobData = data\
              .filter(data.JOB_ID.isNotNull())\
              .select('JOB_ID','TIMESTAMP','CLASS_METHOD_LINE','OPERATION', 'ACTIONS')
    queue_data = jobData.filter(jobData.OPERATION == 'JOB_QUEUED').filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService_queueJob$ODLib_Common_40').filter(jobData.JOB_ID != 'WORKER_CALIBRATION')

    queue_data = queue_data.select(queue_data.TIMESTAMP, queue_data.ACTIONS.substr(15, 4).alias("QUEUE_SIZE")).withColumn('QUEUE_SIZE', F.col('QUEUE_SIZE').cast('integer'))

    start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_scheduleJob$ODLib_Common_78')\
              .filter(jobData.JOB_ID != 'WORKER_CALIBRATION')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    # services.broker.BrokerService_executeJob$ODLib_Common_72, INIT
    localhost_execution_start = jobData\
                .filter(jobData.OPERATION == 'INIT')\
                .filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_executeJob$ODLib_Common_72')\
                .filter(jobData.JOB_ID != 'WORKER_CALIBRATION')\
                .drop('OPERATION')\
                .drop('CLASS_METHOD_LINE')\
                .drop('ACTIONS')\
                .withColumnRenamed('TIMESTAMP', 'START_TIME')

    # Local Execution: services.worker.WorkerService$RunnableJobObjects_run_132
    localhost_execution_end = jobData\
                .filter(jobData.OPERATION == 'COMPLETE')\
                .filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService$RunnableJobObjects_run_132')\
                .filter(jobData.JOB_ID != 'WORKER_CALIBRATION')\
                .drop('OPERATION')\
                .drop('CLASS_METHOD_LINE')\
                .drop('ACTIONS')\
                .withColumnRenamed('TIMESTAMP', 'END_TIME')


    end = jobData\
              .filter(jobData.OPERATION == 'COMPLETE')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCClient$executeJob$1_run_48')\
              .filter(jobData.JOB_ID != 'WORKER_CALIBRATION')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .withColumnRenamed('TIMESTAMP', 'END_TIME')

    device_jobs = start.join(end, 'JOB_ID')\
                    .withColumn('EXECUTION_TIME', end.END_TIME - start.START_TIME).drop('START_TIME').drop('END_TIME')
    localhost_jobs = start.join(localhost_execution_end, 'JOB_ID')\
                    .withColumn('EXECUTION_TIME', localhost_execution_end.END_TIME - start.START_TIME).drop('START_TIME').drop('END_TIME')
    execution_jobs = localhost_execution_start.join(localhost_execution_end, 'JOB_ID')\
                    .withColumn('EXECUTION_TIME', localhost_execution_end.END_TIME - localhost_execution_start.START_TIME).drop('START_TIME').drop('END_TIME')

    device_jobs_stats = device_jobs.agg(F.count('EXECUTION_TIME').alias('num'),\
                         F.avg('EXECUTION_TIME').alias('avg'),\
                         F.min('EXECUTION_TIME').alias('min'),\
                         F.max('EXECUTION_TIME').alias('max'),\
                         )

    # localhost jobs
    localhost_jobs_stats = localhost_jobs.agg(F.count('EXECUTION_TIME').alias('num'),\
                         F.avg('EXECUTION_TIME').alias('avg'),\
                         F.min('EXECUTION_TIME').alias('min'),\
                         F.max('EXECUTION_TIME').alias('max'),\
                         )
    #
    execution_jobs_stats = execution_jobs.agg(F.count('EXECUTION_TIME').alias('num'),\
                         F.avg('EXECUTION_TIME').alias('avg'),\
                         F.min('EXECUTION_TIME').alias('min'),\
                         F.max('EXECUTION_TIME').alias('max'),\
                         )

    queue_stats = queue_data.agg(F.max('QUEUE_SIZE').alias('MAX_QUEUE_SIZE'))
    global_stats = jobData.agg(F.min('TIMESTAMP').alias('min'), F.max('TIMESTAMP').alias('max'))
    device_jobs_result = device_jobs_stats.collect()[0]
    localhost_jobs_result = localhost_jobs_stats.collect()[0]
    execution_jobs_result = execution_jobs_stats.collect()[0]
    queue_result = queue_stats.collect()[0]
    global_result = global_stats.collect()[0]
    return (device_jobs_result, localhost_jobs_result, execution_jobs_result, queue_result[0], global_result)


def processLogsCloud(data):
    jobData = data\
              .filter(data.JOB_ID.isNotNull())\
              .select('JOB_ID','TIMESTAMP','CLASS_METHOD_LINE','OPERATION', 'ACTIONS')
    queue_data = jobData.filter(jobData.OPERATION == 'JOB_QUEUED').filter(jobData.CLASS_METHOD_LINE == 'services.worker.grpc.WorkerGRPCServer$grpcImpl$1_execute_22').filter(jobData.JOB_ID != 'WORKER_CALIBRATION')
    queue_data = queue_data.select(queue_data.TIMESTAMP, queue_data.ACTIONS.substr(15, 4).alias("QUEUE_SIZE")).withColumn('QUEUE_SIZE', F.col('QUEUE_SIZE').cast('integer'))

    start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCServer$grpcImpl$1_executeJob_20')\
              .filter(jobData.JOB_ID != 'WORKER_CALIBRATION')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    end = jobData\
              .filter(jobData.OPERATION == 'END')\
              .filter(jobData.CLASS_METHOD_LINE == 'java.util.concurrent.ThreadPoolExecutor_runWorker_1128')\
              .filter(jobData.JOB_ID != 'WORKER_CALIBRATION')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .withColumnRenamed('TIMESTAMP', 'END_TIME')

    jobs = start.join(end, 'JOB_ID').withColumn('EXECUTION_TIME', end.END_TIME - start.START_TIME).drop('START_TIME').drop('END_TIME')

    job_info = start.join(end, 'JOB_ID')\
                    .withColumn('EXECUTION_TIME', end.END_TIME - start.START_TIME)

    stats = job_info.agg(F.count('EXECUTION_TIME').alias('num'),\
                         F.avg('EXECUTION_TIME').alias('avg'),\
                         F.min('EXECUTION_TIME').alias('min'),\
                         F.max('EXECUTION_TIME').alias('max'),\
                         )

    queue_stats = queue_data.agg(F.max('QUEUE_SIZE').alias('MAX_QUEUE_SIZE'))

    global_stats = jobData.agg(F.min('TIMESTAMP').alias('min'), F.max('TIMESTAMP').alias('max'))

    result = stats.collect()[0]
    queue_result = queue_stats.collect()[0]
    global_result = global_stats.collect()[0]
    return (result, queue_result[0], global_result)



if __name__ == '__main__':
    print('EXPERIMENT,DEVICES,CLOUDS,CLOUDLETS,PRODUCERS,RATE,MAX_QUEUE_SIZE_DEVICE,AVG_QUEUE_SIZE_DEVICE,MAX_QUEUE_SIZE_CLOUD,AVG_QUEUE_SIZE_CLOUD,TOTAL_JOBS,JOBS_OFFLOADED,AVG_JOBS_DEVICE,MAX_JOBS_DEVICES,AVG_JOBS_CLOUD,MAX_JOBS_CLOUD,DEVICES_WITH_1+JOB,EXECUTION_TIME_AVG,EXECUTION_TIME_MAX,EXECUTION_TIME_MIN,EXECUTION_TIME_DEVICE_AVG,EXECUTION_TIME_DEVICE_MAX,EXECUTION_TIME_DEVICE_MIN,EXECUTION_TIME_CLOUD_AVG,EXECUTION_TIME_CLOUD_MAX,EXECUTION_TIME_CLOUD_MIN,AVG_EXPERIMENT_TIME,MAX_EXPERIMENT_TIME,NUM_TIMEOUTS,LOCALHOST_EXECUTIONS,LOCALHOST_EXECUTIONS_MAX,LOCALHOST_EXECUTIONS_AVG,LOCALHOST_EXECUTIONS_MIN,DEVICE_RECEIVED_EXECUTIONS,DEVICE_RECEIVED_EXECUTIONS_MAX,DEVICE_RECEIVED_EXECUTIONS_AVG,DEVICE_RECEIVED_EXECUTIONS_MIN,LOCALHOST_EXECUTION_TIME_AVG,LOCALHOST_EXECUTION_TIME_MIN,LOCALHOST_EXECUTION_TIME_MAX,DEVICE_RECEIVED_EXECUTION_TIME_AVG,DEVICE_RECEIVED_EXECUTION_TIME_MIN,DEVICE_RECEIVED_EXECUTION_TIME_MAX')
    for entry in os.listdir("logs"):
        if os.path.isdir("logs/{}".format(entry)):
            repetitions = os.listdir("logs/{}".format(entry))
            producers = 0
            rate = 0
            if (os.path.exists("logs/{}/conf.cfg".format(entry))):
                conf = open("logs/{}/conf.cfg".format(entry), "r").read().split("\n")
                for line in conf:
                    if line.find('Rate Time: ') == 0:
                        rate = int(line[11:-1])
                    if line.find('Producers: ') == 0:
                        producers = int(line[11:])
            if "lost_devices_mid_experience_CANCELED" not in repetitions:
                counter = 0
                devices = 0
                clouds = 0
                cloudlets = 0
                max_device_queue = 0
                avg_queue_device = 0
                max_cloud_queue = 0
                avg_queue_cloud = 0
                total_jobs = 0
                avg_jobs_device = 0
                max_jobs_device = 0
                avg_jobs_cloud = 0
                max_jobs_cloud = 0
                devs_with_1_plus_jobs = 0
                execution_time_avg = 0
                execution_time_max = 0
                execution_time_min = 0
                execution_time_device_avg = 0
                execution_time_device_max = 0
                execution_time_device_min = 0
                execution_time_cloud_avg = 0
                execution_time_cloud_max = 0
                execution_time_cloud_min = 0
                avg_experiment_time = 0
                max_experiment_time = 0
                completion_timeout = 0

                total_localhost_jobs = 0
                max_localhost_jobs = 0
                avg_localhost_jobs = 0
                min_localhost_jobs = 0

                total_device_reveived_jobs = 0
                max_device_reveived_jobs = 0
                avg_device_reveived_jobs = 0
                min_device_reveived_jobs = 0

                execution_time_device_reveived_avg = 0
                execution_time_device_reveived_min = 0
                execution_time_device_reveived_max = 0

                execution_time_localhost_avg = 0
                execution_time_localhost_min = 0
                execution_time_localhost_max = 0

                for repeat in repetitions:
                    if os.path.isdir("logs/{}/{}".format(entry, repeat)):
                        for dir in os.listdir("logs/{}/{}".format(entry, repeat)):
                            counter += 1
                            if os.path.isdir("logs/{}/{}/{}".format(entry, repeat, dir)):
                                device_data = []
                                cloud_data = []
                                cloudlet_data = []
                                if not COMPRESSED_PRINT:
                                    print("{}/{}/{}".format(entry, repeat, dir), end=',')
                                    devices = 0
                                    clouds = 0
                                    cloudlets = 0
                                    max_device_queue = 0
                                    avg_queue_device = 0
                                    max_cloud_queue = 0
                                    avg_queue_cloud = 0
                                    total_jobs = 0
                                    avg_jobs_device = 0
                                    max_jobs_device = 0
                                    avg_jobs_cloud = 0
                                    max_jobs_cloud = 0
                                    devs_with_1_plus_jobs = 0
                                    execution_time_avg = 0
                                    execution_time_max = 0
                                    execution_time_min = 0
                                    execution_time_device_avg = 0
                                    execution_time_device_max = 0
                                    execution_time_device_min = 0
                                    execution_time_cloud_avg = 0
                                    execution_time_cloud_max = 0
                                    execution_time_cloud_min = 0
                                    avg_experiment_time = 0
                                    max_experiment_time = 0
                                    completion_timeout = 0

                                    total_localhost_jobs = 0
                                    max_localhost_jobs = 0
                                    avg_localhost_jobs = 0
                                    min_localhost_jobs = 0

                                    total_device_reveived_jobs = 0
                                    max_device_reveived_jobs = 0
                                    avg_device_reveived_jobs = 0
                                    min_device_reveived_jobs = 0

                                    execution_time_device_reveived_avg = 0
                                    execution_time_device_reveived_min = 0
                                    execution_time_device_reveived_max = 0

                                    execution_time_localhost_avg = 0
                                    execution_time_localhost_min = 0
                                    execution_time_localhost_max = 0
                                for device in os.listdir("logs/{}/{}/{}".format(entry, repeat, dir)):
                                    if device == "completion_timeout_exceded":
                                        completion_timeout += 1
                                    data = readCSV("logs/{}/{}/{}/{}".format(entry, repeat, dir, device))
                                    if device == "hyrax_europe-west1-b.csv":
                                        cloud_data.append(processLogsCloud(data))
                                    elif device[:9] == "cloudlet_":
                                        cloudlet_data.append(processLogsCloud(data))
                                    elif device == 'completion_timeout_exceded':
                                        continue
                                    else:
                                        device_data.append(processLogs(data))
                                device_jobs = []
                                device_execution_time_min = []
                                device_execution_time_max = []
                                device_execution_time_avg = []

                                localhost_jobs = []
                                localhost_execution_time_min = []
                                localhost_execution_time_max = []
                                localhost_execution_time_avg = []

                                device_reveived_jobs = []
                                device_reveived_execution_time_min = []
                                device_reveived_execution_time_max = []
                                device_reveived_execution_time_avg = []

                                device_queue = []
                                device_total_experiment_time = []
                                cloud_jobs = []
                                cloud_execution_time_min = []
                                cloud_execution_time_max = []
                                cloud_execution_time_avg = []
                                cloud_queue = []
                                cloud_total_experiment_time = []

                                # TODO: LOCALHOST JOBS, OFFLOADED JOBS, RECEIVED JOBS

                                for result in device_data:
                                    device_jobs.append(result[0].num)
                                    if (result[0].min):
                                        device_execution_time_min.append(result[0].min)
                                    if (result[0].max):
                                        device_execution_time_max.append(result[0].max)
                                    if (result[0].avg):
                                        device_execution_time_avg.append(result[0].avg)

                                    localhost_jobs.append(result[1].num)
                                    if (result[1].min):
                                        localhost_execution_time_min.append(result[1].min)
                                    if (result[1].max):
                                        localhost_execution_time_max.append(result[1].max)
                                    if (result[1].avg):
                                        localhost_execution_time_avg.append(result[1].avg)

                                    device_reveived_jobs.append(result[2].num)
                                    if (result[2].min):
                                        device_reveived_execution_time_min.append(result[2].min)
                                    if (result[2].max):
                                        device_reveived_execution_time_max.append(result[2].max)
                                    if (result[2].avg):
                                        device_reveived_execution_time_avg.append(result[2].avg)

                                    if result[3]:
                                        if (int(result[3])) > 0:
                                            device_queue.append(int(result[3]))
                                    else:
                                        device_queue.append(0)
                                    if (result[4].max and result[4].min):
                                        device_total_experiment_time.append(result[4].max-result[4].min)


                                cloud_data += cloudlet_data
                                for result in cloud_data:
                                    cloud_jobs.append(result[0].num)
                                    if (result[0].min):
                                        cloud_execution_time_min.append(result[0].min)
                                    if (result[0].max):
                                        cloud_execution_time_max.append(result[0].max)
                                    if (result[0].avg):
                                        cloud_execution_time_avg.append(result[0].avg)
                                    if result[1]:
                                        cloud_queue.append(int(result[1]))
                                    else:
                                        cloud_queue.append(0)
                                    if (result[2].max and result[2].min):
                                        cloud_total_experiment_time.append(result[2].max-result[2].min)

                                try:
                                    #if True:
                                    if len(cloud_queue) > 0 and len(cloud_execution_time_avg) > 0 and len(cloud_execution_time_max) > 0 and len(cloud_execution_time_min) > 0 and len(cloud_jobs) > 0 and len(cloud_total_experiment_time) > 0:
                                        devices += len(device_data)
                                        clouds += len(cloud_data)-len(cloudlet_data)
                                        cloudlets += len(cloudlet_data)

                                        max_device_queue = max(max_device_queue, max(device_queue) if len(device_queue) > 0 else 0)
                                        avg_queue_device += (sum(device_queue)/len(device_queue)) if len(device_queue) > 0 else 0
                                        max_cloud_queue = max(max_cloud_queue, max(cloud_queue) if len(cloud_queue) > 0 else 0)
                                        avg_queue_cloud += (sum(cloud_queue)/len(cloud_queue)) if len(cloud_queue) > 0 else 0

                                        total_jobs += sum(device_jobs)
                                        avg_jobs_device += (sum(device_jobs)/producers)
                                        max_jobs_device += max(device_jobs)
                                        avg_jobs_cloud += min(cloud_jobs)
                                        max_jobs_cloud += max(cloud_jobs)
                                        devs_with_1_plus_jobs += (len(device_jobs)+len(cloud_jobs))
                                        execution_time_avg += ((sum(device_execution_time_avg)+sum(cloud_execution_time_avg)) / (len(device_execution_time_avg)+len(cloud_execution_time_avg))) if ((len(device_execution_time_avg)+len(cloud_execution_time_avg))) > 0 else 0
                                        execution_time_max += max(max(device_execution_time_max), max(cloud_execution_time_max))
                                        execution_time_min += min(min(device_execution_time_min), min(cloud_execution_time_min))
                                        execution_time_device_avg += (sum(device_execution_time_avg) / len(device_execution_time_avg))
                                        execution_time_device_max += max(device_execution_time_max) if len(device_execution_time_max) else 0
                                        execution_time_device_min += min(device_execution_time_min) if len(device_execution_time_min) else 0
                                        execution_time_cloud_avg += (sum(cloud_execution_time_avg) / len(cloud_execution_time_avg)) if len(cloud_execution_time_avg) > 0 else 0
                                        execution_time_cloud_max += max(cloud_execution_time_max) if len(cloud_execution_time_max) > 0 else 0
                                        execution_time_cloud_min += min(cloud_execution_time_min) if len(cloud_execution_time_min) > 0 else 0
                                        avg_experiment_time += ((sum(device_total_experiment_time)+sum(cloud_total_experiment_time))/(len(device_total_experiment_time)+len(cloud_total_experiment_time))) if ((len(device_total_experiment_time)+len(cloud_total_experiment_time))) > 0 else 0
                                        max_experiment_time += max(max(device_total_experiment_time) if len(device_total_experiment_time) > 0 else 0, max(cloud_total_experiment_time) if len(cloud_total_experiment_time) > 0 else 0)

                                        total_localhost_jobs += sum(localhost_jobs) if len(localhost_jobs) > 0 else 0
                                        max_localhost_jobs += max(localhost_jobs) if len(localhost_jobs) > 0 else 0
                                        avg_localhost_jobs += (sum(localhost_jobs)/len(localhost_jobs))  if len(localhost_jobs) > 0 else 0
                                        min_localhost_jobs += min(localhost_jobs) if len(localhost_jobs) > 0 else 0

                                        total_device_reveived_jobs += sum(device_reveived_jobs) if len(device_reveived_jobs) > 0 else 0
                                        max_device_reveived_jobs += max(device_reveived_jobs) if len(device_reveived_jobs) > 0 else 0
                                        avg_device_reveived_jobs += (sum(device_reveived_jobs)/len(device_reveived_jobs)) if len(device_reveived_jobs) > 0 else 0
                                        min_device_reveived_jobs += min(device_reveived_jobs) if len(device_reveived_jobs) > 0 else 0

                                        execution_time_localhost_avg += (sum(localhost_execution_time_avg) / len(localhost_execution_time_avg)) if len(localhost_execution_time_avg) > 0 else 0
                                        execution_time_localhost_max += max(localhost_execution_time_max) if len(localhost_execution_time_max) > 0 else 0
                                        execution_time_localhost_min += min(localhost_execution_time_min) if len(localhost_execution_time_min) > 0 else 0

                                        execution_time_device_reveived_avg += (sum(device_reveived_execution_time_avg) / len(device_reveived_execution_time_avg)) if len(device_reveived_execution_time_avg) > 0 else 0
                                        execution_time_device_reveived_max += max(device_reveived_execution_time_max) if len(device_reveived_execution_time_max) > 0 else 0
                                        execution_time_device_reveived_min += min(device_reveived_execution_time_min) if len(device_reveived_execution_time_min) > 0 else 0
                                    else:
                                        devices += len(device_data)
                                        clouds += len(cloud_data)
                                        cloudlets = len(cloudlet_data)

                                        max_device_queue = max(max_device_queue, max(device_queue) if len(device_queue) > 0 else 0)
                                        avg_queue_device += (sum(device_queue)/len(device_queue)) if len(device_queue) > 0 else 0
                                        max_cloud_queue = max(max_cloud_queue, max(cloud_queue) if len(cloud_queue) > 0 else 0)
                                        avg_queue_cloud += (sum(device_queue)/len(cloud_queue)) if len(cloud_queue) > 0 else 0


                                        total_jobs += sum(device_jobs) if len(device_jobs) else 0
                                        avg_jobs_device += sum(device_jobs)/producers if producers > 0 else 0
                                        max_jobs_device += max(device_jobs) if len(device_jobs) > 0 else 0
                                        devs_with_1_plus_jobs += len(device_jobs)
                                        execution_time_avg += ((sum(device_execution_time_avg)+sum(cloud_execution_time_avg)) / (len(device_execution_time_avg)+len(cloud_execution_time_avg))) if ((len(device_execution_time_avg)+len(cloud_execution_time_avg))) > 0 else 0
                                        execution_time_max += max(device_execution_time_max) if len(device_execution_time_max) > 0 else 0
                                        execution_time_min += min(device_execution_time_min) if len(device_execution_time_min) > 0 else 0
                                        execution_time_device_avg += (sum(device_execution_time_avg) / len(device_execution_time_avg)) if len(device_execution_time_avg) > 0 else 0
                                        execution_time_device_max += max(device_execution_time_max) if len(device_execution_time_max) else 0
                                        execution_time_device_min += min(device_execution_time_min) if len(device_execution_time_min) else 0
                                        avg_experiment_time += ((sum(device_total_experiment_time))/(len(device_total_experiment_time))) if len(device_total_experiment_time) > 0 else 0
                                        max_experiment_time += max(device_total_experiment_time) if len(device_total_experiment_time) > 0 else 0

                                        total_localhost_jobs += sum(localhost_jobs) if len(localhost_jobs) > 0 else 0
                                        max_localhost_jobs += max(localhost_jobs) if len(localhost_jobs) > 0 else 0
                                        avg_localhost_jobs += (sum(localhost_jobs)/len(localhost_jobs))  if len(localhost_jobs) > 0 else 0
                                        min_localhost_jobs += min(localhost_jobs) if len(localhost_jobs) > 0 else 0

                                        total_device_reveived_jobs += sum(device_reveived_jobs) if len(device_reveived_jobs) > 0 else 0
                                        max_device_reveived_jobs += max(device_reveived_jobs) if len(device_reveived_jobs) > 0 else 0
                                        avg_device_reveived_jobs += (sum(device_reveived_jobs)/len(device_reveived_jobs)) if len(device_reveived_jobs) > 0 else 0
                                        min_device_reveived_jobs += min(device_reveived_jobs) if len(device_reveived_jobs) > 0 else 0

                                        execution_time_localhost_avg += (sum(localhost_execution_time_avg) / len(localhost_execution_time_avg)) if len(localhost_execution_time_avg) > 0 else 0
                                        execution_time_localhost_max += max(localhost_execution_time_max) if len(localhost_execution_time_max) > 0 else 0
                                        execution_time_localhost_min += min(localhost_execution_time_min) if len(localhost_execution_time_min) > 0 else 0

                                        execution_time_device_reveived_avg += (sum(device_reveived_execution_time_avg) / len(device_reveived_execution_time_avg)) if len(device_reveived_execution_time_avg) > 0 else 0
                                        execution_time_device_reveived_max += max(device_reveived_execution_time_max) if len(device_reveived_execution_time_max) > 0 else 0
                                        execution_time_device_reveived_min += min(device_reveived_execution_time_min) if len(device_reveived_execution_time_min) > 0 else 0
                                except:
                                    print()
                                if not COMPRESSED_PRINT:
                                    print(devices, end=',')
                                    print(clouds, end=',')
                                    print(cloudlets, end=',')
                                    print(producers, end=',')
                                    print(rate, end=',')

                                    print("%d" % max_device_queue, end=',')
                                    print("%.2f" % avg_queue_device, end=',')
                                    print("%d" % max_cloud_queue, end=',')
                                    print("%.2f" % avg_queue_cloud, end=',')

                                    print(total_jobs, end=',')
                                    #OFFLOADED
                                    print(total_jobs-total_localhost_jobs, end=',')
                                    print("%.2f" % avg_jobs_device, end=',')
                                    print(max_jobs_device, end=',')
                                    print("%.2f" % avg_jobs_cloud, end=',')
                                    print(max_jobs_cloud, end=',')
                                    print(devs_with_1_plus_jobs, end=',')


                                    print(round(execution_time_avg), end=',')
                                    print(round(execution_time_max), end=',')
                                    print(round(execution_time_min), end=',')
                                    print(round(execution_time_device_avg), end=',')
                                    print(round(execution_time_device_max), end=',')
                                    print(round(execution_time_device_min), end=',')
                                    print(round(execution_time_cloud_avg), end=',')
                                    print(round(execution_time_cloud_max), end=',')
                                    print(round(execution_time_cloud_min), end=',')
                                    print(round(avg_experiment_time), end=',')
                                    print(round(max_experiment_time), end=',')
                                    print(completion_timeout, end=',')
                                    #,'LOCALHOST_EXECUTIONS','LOCALHOST_EXECUTIONS_MAX','LOCALHOST_EXECUTIONS_AVG','LOCALHOST_EXECUTIONS_MIN','DEVICE_RECEIVED_EXECUTIONS','DEVICE_RECEIVED_EXECUTIONS_MAX','DEVICE_RECEIVED_EXECUTIONS_AVG','DEVICE_RECEIVED_EXECUTIONS_MIN'
                                    print(total_localhost_jobs, end=',')
                                    print(max_localhost_jobs, end=',')
                                    print(avg_localhost_jobs, end=',')
                                    print(min_localhost_jobs, end=',')

                                    print(total_device_reveived_jobs, end=',')
                                    print(max_device_reveived_jobs, end=',')
                                    print(avg_device_reveived_jobs, end=',')
                                    print(min_device_reveived_jobs)

                                    #LOCALHOST_EXECUTION_TIME_AVG,LOCALHOST_EXECUTION_TIME_MIN,LOCALHOST_EXECUTION_TIME_MAX,DEVICE_RECEIVED_EXECUTION_TIME_AVG,DEVICE_RECEIVED_EXECUTION_TIME_MIN,DEVICE_RECEIVED_EXECUTION_TIME_MAX,
                                    print(execution_time_localhost_avg, end=',')
                                    print(execution_time_localhost_min, end=',')
                                    print(execution_time_localhost_max, end=',')

                                    print(execution_time_device_reveived_avg, end=',')
                                    print(execution_time_device_reveived_min, end=',')
                                    print(execution_time_device_reveived_max)

                if COMPRESSED_PRINT:
                    if counter == 0:
                        continue
                    print("{}".format(entry), end=',')
                    print(int(devices/counter), end=',')
                    print(int(clouds/counter), end=',')
                    print(int(cloudlets/counter), end=',')
                    print(producers, end=',')
                    print(rate, end=',')

                    print("%d" %  max_device_queue, end=',')
                    print("%.2f" % (avg_queue_device/counter), end=',')
                    print("%d" %  max_cloud_queue, end=',')
                    print("%.2f" % (avg_queue_cloud/counter), end=',')

                    print("%.2f" % (total_jobs/counter), end=',')
                    #OFFLOADED
                    print("%.2f" % ((total_jobs-total_localhost_jobs)/counter), end=',')

                    print("%.2f" % (avg_jobs_device/counter), end=',')
                    print("%.2f" % (max_jobs_device/counter), end=',')
                    print("%.2f" % (avg_jobs_cloud/counter), end=',')
                    print("%.2f" % (max_jobs_cloud/counter), end=',')
                    print("%.2f" % (devs_with_1_plus_jobs/counter), end=',')
                    print(round(execution_time_avg/counter), end=',')
                    print(round(execution_time_max/counter), end=',')
                    print(round(execution_time_min/counter), end=',')
                    print(round(execution_time_device_avg/counter), end=',')
                    print(round(execution_time_device_max/counter), end=',')
                    print(round(execution_time_device_min/counter), end=',')
                    print(round(execution_time_cloud_avg/counter), end=',')
                    print(round(execution_time_cloud_max/counter), end=',')
                    print(round(execution_time_cloud_min/counter), end=',')
                    print(round(avg_experiment_time/counter), end=',')
                    print(round(max_experiment_time/counter), end=',')
                    print(completion_timeout, end=',')
                    #,'LOCALHOST_EXECUTIONS','LOCALHOST_EXECUTIONS_MAX','LOCALHOST_EXECUTIONS_AVG','LOCALHOST_EXECUTIONS_MIN','DEVICE_RECEIVED_EXECUTIONS','DEVICE_RECEIVED_EXECUTIONS_MAX','DEVICE_RECEIVED_EXECUTIONS_AVG','DEVICE_RECEIVED_EXECUTIONS_MIN'
                    print("%.2f" % (total_localhost_jobs/counter), end=',')
                    print("%.2f" % (max_localhost_jobs/counter), end=',')
                    print("%.2f" % (avg_localhost_jobs/counter), end=',')
                    print("%.2f" % (min_localhost_jobs/counter), end=',')

                    print("%.2f" % (total_device_reveived_jobs/counter), end=',')
                    print("%.2f" % (max_device_reveived_jobs/counter), end=',')
                    print("%.2f" % (avg_device_reveived_jobs/counter), end=',')
                    print("%.2f" % (min_device_reveived_jobs/counter), end=',')

                    #LOCALHOST_EXECUTION_TIME_AVG,LOCALHOST_EXECUTION_TIME_MIN,LOCALHOST_EXECUTION_TIME_MAX,DEVICE_RECEIVED_EXECUTION_TIME_AVG,DEVICE_RECEIVED_EXECUTION_TIME_MIN,DEVICE_RECEIVED_EXECUTION_TIME_MAX,
                    print("%.2f" % (execution_time_localhost_avg/counter), end=',')
                    print("%.2f" % (execution_time_localhost_min/counter), end=',')
                    print("%.2f" % (execution_time_localhost_max/counter), end=',')

                    print("%.2f" % (execution_time_device_reveived_avg/counter), end=',')
                    print("%.2f" % (execution_time_device_reveived_min/counter), end=',')
                    print("%.2f" % (execution_time_device_reveived_max/counter))
