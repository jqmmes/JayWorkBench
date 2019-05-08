import grpcControls
from time import sleep, time
import random
import threading
import os
import adb
import configparser
from sys import argv, stdout

ASSETS=os.listdir("assets")
EXPERIMENTS = []
PENDING_JOBS = 0
PENDING_WORKERS = 0

def ping(hostname):
    response = os.system("ping -c 1 %s >/dev/null 2>&1" % hostname)
    #and then check the response...
    if response == 0:
        return True
    else:
        return False

def pingWait(hostname):
    while(not ping(hostname)):
        print(".", end='')
        stdout.flush()
        sleep(2)
    print("")

def runJob(worker, device_random):
    global PENDING_JOBS
    PENDING_JOBS += 1
    job = grpcControls.Job()
    asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]

    while (asset[-4:] not in ['.png', '.jpg']):
        asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]

    with open("assets/%s" % asset, "rb") as image:
        f = image.read()
        b = bytes(f)
        job.addBytes(b)
    print("%s\t%s" % (asset, job.id))
    print(worker.scheduleJob(job))
    PENDING_JOBS -= 1

def startWorker(experiment, repetition, is_producer, device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
    global PENDING_JOBS, PENDING_WORKERS
    device_random = random.Random()
    device_random.seed(experiment.seed+device)
    if experiment.reboot:
        adb.rebootAndWait(device)
    adb.stopAll(device)
    adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True)
    worker = grpcControls.remoteClient(adb.getDeviceIp(device), device)
    worker.connectLauncherService()
    worker.setLogName(experiment.name)
    worker.startWorker()
    worker.startScheduler()
    worker.connectBrokerService()
    sleep(2)
    for scheduler in worker.listSchedulers().scheduler:
        if scheduler.name == experiment.scheduler:
            if (worker.setScheduler(scheduler) is None):
                print("Failed to setScheduler on %s" % device)
                return
            break
    for model in worker.listModels().models:
        if model.name == experiment.model:
            if (worker.setModel(model) is None):
                print("Failed to setScheduler on %s" % device)
                return
            break

    boot_barrier.wait()

    rate = float(experiment.request_rate)/float(experiment.request_time)


    start_barrier.wait()

    if (is_producer):
        start_time=time()

        while (time()-start_time) < experiment.duration:
            next_event_in = device_random.expovariate(rate)
            if next_event_in > experiment.duration-(time()-start_time):
                break
            sleep(next_event_in)
            threading.Thread(target = runJob, args = (worker,device_random)).start()

    complete_barrier.wait()

    log_pull_barrier.wait()
    adb.stopAll(worker.name)
    worker.destroy()
    adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % experiment.name, destination='logs/%s/%d/%s.csv' % (experiment.name, repetition, worker.name), device=worker.name)

    finish_barrier.wait()


def cleanLogs(path):
    if os.path.isdir(path):
        for f in os.listdir(path):
            if os.path.isdir("%s%s" % (path, f)):
                cleanLogs("%s%s/" % (path, f))
                os.rmdir("%s%s" % (path, f))
            else:
                os.remove("%s%s" % (path, f))
    else:
        os.makedirs(path, exist_ok=True)


def runExperiment(experiment):
    global PENDING_JOBS
    experiment_random = random.Random()
    experiment_random.seed(experiment.seed)
    cleanLogs("logs/%s/" % experiment.name)

    devices = adb.listDevices()
    if (len(devices) < experiment.devices):
        print("Not Enought Devices")
        return
    conf = open("logs/%s/conf.cfg" % experiment.name, "w+")
    conf.write("Experiment: %s\n" % experiment.name)
    conf.write("========== CONFIG ==========\n")
    conf.write("Scheduler: %s\n" % experiment.scheduler)
    conf.write("TF Model: %s\n" % experiment.model)
    conf.write("Devices: %s\n" % str(experiment.devices))
    conf.write("Reboot: %s\n" % experiment.reboot)
    conf.write("Rate: %s\n" % str(experiment.request_rate))
    conf.write("Rate Time: %s\n" % str(experiment.request_time) + "s")
    conf.write("Duration: %s\n" % str(experiment.duration) + "s")
    conf.write("Clouds: %s\n" % str(experiment.clouds))
    conf.write("Seed: %s\n" % experiment.seed)
    conf.write("Repetitions: %s" % str(experiment.repetitions))
    conf.write("=============================\n")
    conf.close()
    for cloud in experiment.clouds:
        print("Stopping %s Cloud Instance" % cloud[0])
        stdout.flush()
        adb.cloudInstanceStop(cloud[0], cloud[1])
    for repetition in range(experiment.repetitions):
        print("Running Repetition %d" % repetition)
        for cloud in experiment.clouds:
            print("Starting %s Cloud Instance" % cloud[0])
            stdout.flush()
            adb.cloudInstanceStart(cloud[0], cloud[1])
            while (not adb.cloudInstanceRunning(cloud[0])):
                sleep(5)
            print("\nWaiting %s Cloud DNS (%s) update" % (cloud[0], cloud[2]), end='')
            pingWait(cloud[2])
        os.makedirs("logs/%s/%d/" % (experiment.name, repetition), exist_ok=True)
        devices.sort()
        experiment_random.shuffle(devices)
        boot_barrier = threading.Barrier(experiment.devices + 1)
        start_barrier = threading.Barrier(experiment.devices + 1)
        complete_barrier = threading.Barrier(experiment.devices + 1)
        log_pull_barrier = threading.Barrier(experiment.devices + 1)
        finish_barrier = threading.Barrier(experiment.devices + 1)
        producers = experiment.producers
        for device in devices[:experiment.devices]:
            threading.Thread(target = startWorker, args = (experiment, repetition, (producers > 0), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)).start()
            producers -= 1 # Os primeiros n devices é que produzem conteudo

        boot_barrier.wait()
        sleep(1)
        start_barrier.wait()

        complete_barrier.wait()
        while PENDING_JOBS > 0:
            sleep(5)
        sleep(10)
        log_pull_barrier.wait()
        finish_barrier.wait()
        for cloud in experiment.clouds:
            print("Stopping %s Cloud Instance" % cloud[0])
            stdout.flush()
            adb.cloudInstanceStop(cloud[0], cloud[1])
        if (repetition != experiment.repetitions - 1):
            print("Waiting 5s for next repetition")
            sleep(5)

class Experiment:
    name = ""
    scheduler = "SingleDevice [LOCAL]"
    model = "ssd_mobilenet_v1_fpn_coco"
    devices = 0
    reboot = False
    request_rate = 0
    request_time = 1
    duration = 0
    clouds = []
    seed = 0
    repetitions = 1
    producers = 0

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
                if (experiment.request_time == 0): experiment.request_time = 1
            elif option == "duration":
                experiment.duration = int(config[section][option])
            elif option == "clouds":
                for entry in config[section][option].split(','):
                    cloud_zone_address = entry.split("/")
                    experiment.clouds += [(cloud_zone_address[0], cloud_zone_address[1], cloud_zone_address[2])]
            elif option == "seed":
                experiment.seed = config[section][option]
            elif option == "repetitions":
                experiment.repetitions = int(config[section][option])
            elif option == "producers":
                experiment.producers = int(config[section][option])
        if (experiment.producers == 0 or experiment.producers > experiment.devices):
            experiment.producers = experiment.devices
        EXPERIMENTS.append(experiment)

def help():
    print('''        ================================================ HELP ================================================
        Run:        python3 test.py conf.cfg

        Config Parameters:
                    # Comment. Use python configparser syntax
                    [Experiment Name]
                    # Config Options
                    Strategy                = Scheduler to use [STR]
                    Model                   = Tensorflow model to use [STR]
                    Devices                 = Number of Devices [INT]
                    RebootDevices           = True|False [BOOL]
                    GenerationRateRequests  = Number of requests (Poisson Distribution) [INT]
                    GenerationRateSeconds   = Per ammount of time (Poisson Distribution) [INT]
                    Duration                = experiment duration [INT]
                    TurnOnCloud             = True|False [BOOL]
                    Seed                    = Seed to use [STR]

        Models:
                    ssd_mobilenet_v1_fpn_coco
                    ssd_mobilenet_v1_coco
                    ssd_mobilenet_v2_coco
                    ssdlite_mobilenet_v2_coco
                    ssd_resnet_50_fpn_coco

        Strategies:
                    SingleDeviceScheduler [LOCAL]
                    SingleDeviceScheduler [REMOTE]
                    SingleDeviceScheduler [CLOUD]

                    MultiDeviceScheduler [RoundRobin] [REMOTE]
                    MultiDeviceScheduler [RoundRobin] [CLOUD]
                    MultiDeviceScheduler [RoundRobin] [LOCAL, CLOUD]
                    MultiDeviceScheduler [RoundRobin] [LOCAL, REMOTE]
                    MultiDeviceScheduler [RoundRobin] [CLOUD, REMOTE]
                    MultiDeviceScheduler [RoundRobin] [LOCAL, CLOUD, REMOTE]

                    MultiDeviceScheduler [Random] [REMOTE]
                    MultiDeviceScheduler [Random] [CLOUD]
                    MultiDeviceScheduler [Random] [LOCAL, CLOUD]
                    MultiDeviceScheduler [Random] [LOCAL, REMOTE]
                    MultiDeviceScheduler [Random] [CLOUD, REMOTE]
                    MultiDeviceScheduler [Random] [LOCAL, CLOUD, REMOTE]

                    SmartScheduler

                    EstimatedTimeScheduler
        ================================================ HELP ================================================''')

def main():
    if (len(argv) < 2):
        print("\tPlease provide config file!")
        help()
        return
    if argv[1].lower() == "help":
        help()
    readConfig(argv[1])
    for e in EXPERIMENTS:
        print("Experiment: " + e.name)
        print("========== CONFIG ==========")
        print("Scheduler: ", e.scheduler)
        print("TF Model: ", e.model)
        print("Devices: ", str(e.devices))
        print("Reboot: ", e.reboot)
        print("Rate: ", str(e.request_rate))
        print("Rate Time: ", str(e.request_time) + "s")
        print("Duration: ", str(e.duration) + "s")
        print("Clouds: ", e.clouds)
        print("Seed: ", e.seed)
        print("Repetitions: ", e.repetitions)
        print("=============================")
        runExperiment(e)

if __name__ == '__main__':
    main()
