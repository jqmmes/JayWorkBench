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
    queue_data = jobData.filter(jobData.OPERATION == 'JOB_QUEUED').filter(jobData.CLASS_METHOD_LINE == 'services.worker.WorkerService_queueJob$ODLib_Common_40')

    queue_data = queue_data.select(queue_data.TIMESTAMP, queue_data.ACTIONS.substr(15, 4).alias("QUEUE_SIZE"))

    start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.BrokerService_scheduleJob$ODLib_Common_78')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    end = jobData\
              .filter(jobData.OPERATION == 'COMPLETE')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCClient$executeJob$1_run_48')\
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


def processLogsCloud(data):
    jobData = data\
              .filter(data.JOB_ID.isNotNull())\
              .select('JOB_ID','TIMESTAMP','CLASS_METHOD_LINE','OPERATION', 'ACTIONS')

    queue_data = jobData.filter(jobData.OPERATION == 'JOB_QUEUED').filter(jobData.CLASS_METHOD_LINE == 'services.worker.grpc.WorkerGRPCServer$grpcImpl$1_execute_22')
    queue_data = queue_data.select(queue_data.TIMESTAMP, queue_data.ACTIONS.substr(15, 4).alias("QUEUE_SIZE"))

    start = jobData\
              .filter(jobData.OPERATION == 'INIT')\
              .filter(jobData.CLASS_METHOD_LINE == 'services.broker.grpc.BrokerGRPCServer$grpcImpl$1_executeJob_20')\
              .drop('OPERATION')\
              .drop('CLASS_METHOD_LINE')\
              .withColumnRenamed('TIMESTAMP', 'START_TIME')

    end = jobData\
              .filter(jobData.OPERATION == 'END')\
              .filter(jobData.CLASS_METHOD_LINE == 'java.util.concurrent.ThreadPoolExecutor_runWorker_1128')\
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
    print('EXPERIMENT,DEVICES,CLOUDS,PRODUCERS,RATE,MAX_QUEUE_SIZE,AVG_QUEUE_SIZE,TOTAL_JOBS,AVG_JOBS_DEVICE,MAX_JOBS_DEVICES,AVG_JOBS_CLOUD,MAX_JOBS_CLOUD,DEVICES_WITH_1+JOB,EXECUTION_TIME_AVG,EXECUTION_TIME_MAX,EXECUTION_TIME_MIN,EXECUTION_TIME_DEVICE_AVG,EXECUTION_TIME_DEVICE_MAX,EXECUTION_TIME_DEVICE_MIN,EXECUTION_TIME_CLOUD_AVG,EXECUTION_TIME_CLOUD_MAX,EXECUTION_TIME_CLOUD_MIN,AVG_EXPERIMENT_TIME,MAX_EXPERIMENT_TIME')
    for entry in os.listdir("logs"):
        if os.path.isdir("logs/{}".format(entry)):
            repetitions = os.listdir("logs/{}".format(entry))
            producers = 0
            rate = 0
            if (os.path.exists("logs/{}/conf.cfg".format(entry))):
                conf = open("logs/{}/conf.cfg".format(entry), "r").read().split("\n")
                for line in conf:
                    if line.find('Rate Time: '):
                        rate = int(line[11:-1])
                    if line.find('Producers: '):
                        producers = int(line[11:-1])
            if "lost_devices_mid_experience_CANCELED" not in repetitions:
                for repeat in repetitions:
                    if os.path.isdir("logs/{}/{}".format(entry, repeat)):
                        counter = 0

                        devices = 0
                        clouds = 0
                        max_queue = 0
                        avg_queue = 0
                        total_jobs = 0
                        avg_jobs_device = 0
                        max_jobs_device = 0
                        avg_jobs_cloud = 0
                        max_jobs_cloud = 0
                        jobs_with_1_plus_jobs = 0
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
                        for dir in os.listdir("logs/{}/{}".format(entry, repeat)):
                            counter += 1
                            if os.path.isdir("logs/{}/{}/{}".format(entry, repeat, dir)):
                                device_data = []
                                cloud_data = []
                                if not COMPRESSED_PRINT:
                                    print("{}/{}/{}".format(entry, repeat, dir), end=',')
                                    devices = 0
                                    clouds = 0
                                    max_queue = 0
                                    avg_queue = 0
                                    total_jobs = 0
                                    avg_jobs_device = 0
                                    max_jobs_device = 0
                                    avg_jobs_cloud = 0
                                    max_jobs_cloud = 0
                                    jobs_with_1_plus_jobs = 0
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
                                for device in os.listdir("logs/{}/{}/{}".format(entry, repeat, dir)):
                                    if device == "completion_timeout_exceded":
                                        continue
                                    #print("logs/{}/{}/{}/{}".format(entry, repeat, dir, device))
                                    data = readCSV("logs/{}/{}/{}/{}".format(entry, repeat, dir, device))
                                    if device == "hyrax_europe-west1-b.csv":
                                        cloud_data.append(processLogsCloud(data))
                                    else:
                                        device_data.append(processLogs(data))
                                device_jobs = []
                                device_execution_time_min = []
                                device_execution_time_max = []
                                device_execution_time_avg = []
                                device_queue = []
                                device_total_experiment_time = []
                                cloud_jobs = []
                                cloud_execution_time_min = []
                                cloud_execution_time_max = []
                                cloud_execution_time_avg = []
                                cloud_queue = []
                                cloud_total_experiment_time = []
                                for result in device_data:
                                    device_jobs.append(result[0].num)
                                    if (result[0].min):
                                        device_execution_time_min.append(result[0].min)
                                    if (result[0].max):
                                        device_execution_time_max.append(result[0].max)
                                    if (result[0].avg):
                                        device_execution_time_avg.append(result[0].avg)
                                    if result[1]:
                                        if (int(result[1])) > 0:
                                            device_queue.append(int(result[1]))
                                    else:
                                        device_queue.append(0)
                                    if (result[2].max and result[2].min):
                                        device_total_experiment_time.append(result[2].max-result[2].min)

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
                                    if len(cloud_queue) > 0 and len(cloud_execution_time_avg) > 0 and len(cloud_execution_time_max) > 0 and len(cloud_execution_time_min) > 0 and len(cloud_jobs) > 0 and len(cloud_total_experiment_time) > 0:
                                        devices += len(device_data)
                                        clouds += len(cloud_data)
                                        max_device_queue = max(device_queue) if len(device_queue) > 0 else 0
                                        max_cloud_queue = max(cloud_queue) if len(cloud_queue) > 0 else 0
                                        max_queue += max(max_device_queue, max_cloud_queue)
                                        avg_queue += (sum(device_queue)+sum(cloud_queue))/(len(device_queue)+len(cloud_queue))
                                        total_jobs += (sum(device_jobs)+sum(cloud_jobs))
                                        avg_jobs_device += (sum(device_jobs)/len(device_jobs))
                                        max_jobs_device += max(device_jobs)
                                        avg_jobs_cloud += min(cloud_jobs)
                                        max_jobs_cloud += max(cloud_jobs)
                                        jobs_with_1_plus_jobs += (len(device_jobs)+len(cloud_jobs))
                                        execution_time_avg += (sum(device_execution_time_avg)+sum(cloud_execution_time_avg)) / (len(device_execution_time_avg)+len(cloud_execution_time_avg))
                                        execution_time_max += max(max(device_execution_time_max), max(cloud_execution_time_max))
                                        execution_time_min += min(min(device_execution_time_min), min(cloud_execution_time_min))
                                        execution_time_device_avg += (sum(device_execution_time_avg) / len(device_execution_time_avg))
                                        execution_time_device_max += max(device_execution_time_max)
                                        execution_time_device_min += min(device_execution_time_min)
                                        execution_time_cloud_avg += sum(cloud_execution_time_avg) / len(cloud_execution_time_avg)
                                        execution_time_cloud_max += max(cloud_execution_time_max)
                                        execution_time_cloud_min += min(cloud_execution_time_min)
                                        avg_experiment_time += (sum(device_total_experiment_time)+sum(cloud_total_experiment_time))/(len(device_total_experiment_time)+len(cloud_total_experiment_time))
                                        max_experiment_time += max(max(device_total_experiment_time), max(cloud_total_experiment_time))
                                    else:
                                        devices += len(device_data)
                                        clouds += len(cloud_data)
                                        max_device_queue = max(device_queue) if len(device_queue) > 0 else 0
                                        max_queue += max_device_queue
                                        avg_queue +=(sum(device_queue))/(len(device_queue))
                                        total_jobs += sum(device_jobs)
                                        avg_jobs_device += sum(device_jobs)/len(device_jobs)
                                        max_jobs_device += max(device_jobs)
                                        jobs_with_1_plus_jobs += len(device_jobs)
                                        execution_time_avg += (sum(device_execution_time_avg)+sum(cloud_execution_time_avg)) / (len(device_execution_time_avg)+len(cloud_execution_time_avg))
                                        execution_time_max += max(device_execution_time_max)
                                        execution_time_min += min(device_execution_time_min)
                                        execution_time_device_avg += (sum(device_execution_time_avg) / len(device_execution_time_avg))
                                        execution_time_device_max += max(device_execution_time_max)
                                        execution_time_device_min += min(device_execution_time_min)
                                        avg_experiment_time += ((sum(device_total_experiment_time))/(len(device_total_experiment_time)))
                                        max_experiment_time += max(device_total_experiment_time)
                                except:
                                    print()
                                if not COMPRESSED_PRINT:
                                    print(devices, end=',')
                                    print(clouds, end=',')
                                    print(producers, end=',')
                                    print(rate, end=',')
                                    print(max_queue, end=',')
                                    print(avg_queue, end=',')
                                    print(total_jobs, end=',')
                                    print(avg_jobs_device, end=',')
                                    print(max_jobs_device, end=',')
                                    print(avg_jobs_cloud, end=',')
                                    print(max_jobs_cloud, end=',')
                                    print(jobs_with_1_plus_jobs, end=',')
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
                                    print(round(max_experiment_time))

                        if COMPRESSED_PRINT:
                            print("{}/{}".format(entry, repeat), end=',')
                            print(devices/counter, end=',')
                            print(clouds/counter, end=',')
                            print(producers, end=',')
                            print(rate, end=',')
                            print(max_queue/counter, end=',')
                            print(avg_queue/counter, end=',')
                            print(total_jobs/counter, end=',')
                            print(avg_jobs_device/counter, end=',')
                            print(max_jobs_device/counter, end=',')
                            print(avg_jobs_cloud/counter, end=',')
                            print(max_jobs_cloud/counter, end=',')
                            print(jobs_with_1_plus_jobs/counter, end=',')
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
                            print(round(max_experiment_time/counter))


    #data = readCSV(argv[1])
