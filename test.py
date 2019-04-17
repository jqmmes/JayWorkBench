import grpcControls
from time import sleep, time
import random
import threading
import os
import adb
import configparser
from sys import argv
from dataclasses import dataclass

#LOG_NAME='Log_03'
#RATE = 1/5 # Events/Seconds --> Events per seconds

ASSETS=os.listdir("assets")
EXPERIMENTS = []
RUNNING_WORKERS = 0
PENDING_JOBS = 0
'''
def run():
    devices = adb.listDevices()
    for device in devices:
        adb.rebootAndWait(device)
        adb.stopAll()
        adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True)
    worker = grpcControls.remoteClient(adb.getDeviceIp(devices[0]), devices[0])
    worker.connectLauncherService()
    worker.setLogName(LOG_NAME)
    worker.startWorker()
    worker.startScheduler()
    worker.connectBrokerService()
    sleep(1)
    print(worker.listSchedulers())
    worker.setScheduler(worker.listSchedulers().scheduler[0])
    worker.setModel(worker.listModels().models[0])
    while True:
        sleep(random.expovariate(RATE))
        threading.Thread(target = runJob, args = (worker,)).start()
    adb.stopAll()
    adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % LOG_NAME, destination='logs/%s_%s.csv' % (devices[0], LOG_NAME))
'''

def runJob(worker):
    global PENDING_JOBS
    PENDING_JOBS += 1
    job = grpcControls.Job()
    asset = ASSETS[random.randint(0,len(ASSETS)-1)]

    while (asset[-4:] not in ['.png', '.jpg']):
        asset = ASSETS[random.randint(0,len(ASSETS)-1)]

    with open("assets/%s" % asset, "rb") as image:
        f = image.read()
        b = bytes(f)
        job.addBytes(b)
    print("%s\t%s" % (asset, job.id))
    print(worker.scheduleJob(job))
    PENDING_JOBS -= 1

START_TIME=time()

def runExperiment(experiment):
    global START_TIME, RUNNING_WORKERS, PENDING_JOBS
    random.seed(experiment.seed)
    devices = random.shuffle(adb.listDevices())[:experiment.devices]
    workers = []
    for device in devices:
        if experiment.reboot:
            adb.rebootAndWait(device)
        adb.stopAll(device)
        adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True)
        worker = grpcControls.remoteClient(adb.getDeviceIp(devices), devices)
        worker.connectLauncherService()
        worker.setLogName(experiment.name)
        worker.startWorker()
        worker.startScheduler()
        worker.connectBrokerService()
        sleep(2)
        for scheduler in worker.listSchedulers():
            if scheduler.name == experiment.scheduler:
                worker.setScheduler(scheduler)
                break
        for model in worker.listModels():
            if model.name == experiment.model:
                worker.setModel(model)
                break
        workers.append(worker)
    START_TIME=time()
    for worker in workers:
        threading.Thread(target = generateJobs, args = (experiment.duration, (float(experiment.request_rate)/float(experiment.request_time)), worker)).start()
    sleep(experiment.duration - (Time()-START_TIME))
    while RUNNING_WORKERS > 0 and PENDING_JOBS > 0:
        sleep(5)
    for worker in workers:
        adb.stopAll(worker.name)
        adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % LOG_NAME, destination='logs/%s/%s_%s.csv' % (experiment.name, worker.name, experiment.name))

def generateJobs(time_limit, rate, worker):
    global RUNNING_WORKERS
    RUNNING_WORKERS += 1
    while (time()-START_TIME) < time_limit:
        sleep(random.expovariate(rate))
        threading.Thread(target = runJob, args = (worker,)).start()
    RUNNING_WORKERS -= 1

@dataclass
class Experiment:
    name = ""
    scheduler = "SingleDevice [LOCAL]"
    model = "ssd_mobilenet_v1_fpn_coco"
    devices = 0
    reboot = False
    request_rate = 0
    request_time = 1
    duration = 0
    cloud = False
    seed=0

    def __init__(self, name):
        self.name = name


def readConfig(confName):
    config = configparser.ConfigParser()
    config.read(confName)
    for section in config.sections():
        experiment = Experiment(section)
        for option in config.options(section):
            if option == "strategy":
                experiment.scheduler = config[section][option]
            elif option == "model":
                experiment.model = config[section][option]
            elif option == "devices":
                experiment.devices = int(config[section][option])
            elif option == "rebootdevices":
                experiment.reboot = config[section][option] == "True"
            elif option == "generationraterequests":
                experiment.request_rate = int(config[section][option])
            elif option == "generationrateseconds":
                experiment.request_time = int(config[section][option])
                if (experiment.request_time == 0) experiment.request_time = 1
            elif option == "duration":
                experiment.duration = int(config[section][option])
            elif option == "turnoncloud":
                experiment.cloud = config[section][option] == "True"
            elif option = "seed":
                experiment.seed = config[section][option]
        EXPERIMENTS.append(experiment)

def main():
    if (len(argv) < 2):
        print("Please provide config file")
        return
    readConfig(argv[1])
    for e in EXPERIMENTS:
        print(e.name)
        print(e.scheduler)
        print(e.model)
        print(e.devices)
        print(e.reboot)
        print(e.request_rate)
        print(e.request_time)
        print(e.duration)
        print(e.cloud)
        print(e.seed)

if __name__ == '__main__':
    main()
