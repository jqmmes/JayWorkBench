import lib.grpcControls as grpcControls
import lib.adb as adb
from time import sleep, time
import random
import threading
import os
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

def startWorker(experiment, repetition, seed_repeat, is_producer, device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
    global PENDING_JOBS, PENDING_WORKERS
    device_random = random.Random()
    device_random.seed(experiment.seed+device+str(repetition))
    if experiment.reboot:
        adb.rebootAndWait(device)
    adb.clearSystemLog(device)
    adb.stopAll(device)
    adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True)
    worker_ip = adb.getDeviceIp(device)
    ip_fetch_retries = 5
    while (worker_ip is None and ip_fetch_retries > 0):
        print("Failed to obtain ip for %s retries left %d" % (device, ip_fetch_retries))
        sleep(5)
        worker_ip = adb.getDeviceIp(device)
        ip_fetch_retries -= 1
    if (worker_ip is None):
        print("Failed to obtain ip for %s" % device)
        experiment.setFail()
        adb.rebootAndWait(device)
        boot_barrier.wait()
        start_barrier.wait()
        complete_barrier.wait()
        log_pull_barrier.wait()

    worker = grpcControls.remoteClient(worker_ip, device)
    worker.connectLauncherService()
    worker.setLogName(experiment.name)
    worker.startWorker()
    worker.startScheduler()
    worker.connectBrokerService()
    sleep(2)


    schedulers = worker.listSchedulers()
    models = worker.listModels()
    if (schedulers is None or models is None):
        experiment.setFail()
        boot_barrier.wait()
        start_barrier.wait()
        complete_barrier.wait()
        log_pull_barrier.wait()
        return


    if (experiment.isOK()):
        for scheduler in schedulers.scheduler:
            if scheduler.name == experiment.scheduler:
                if (worker.setScheduler(scheduler) is None):
                    print("Failed to setScheduler on %s" % device)
                    return
                break
        for model in models.models:
            if model.name == experiment.model:
                if (worker.setModel(model) is None):
                    print("Failed to setScheduler on %s" % device)
                    return
                break

        boot_barrier.wait()

        rate = float(experiment.request_rate)/float(experiment.request_time)


        start_barrier.wait()

        if (is_producer and experiment.isOK()):
            start_time=time()

            while ((time()-start_time) < experiment.duration and experiment.isOK()):
                next_event_in = device_random.expovariate(rate)
                if next_event_in > experiment.duration-(time()-start_time):
                    break
                sleep(next_event_in)
                threading.Thread(target = runJob, args = (worker,device_random)).start()

        complete_barrier.wait()

        log_pull_barrier.wait()

    adb.stopAll(worker.name)
    worker.destroy()

    if (experiment.isOK()):
        adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % experiment.name, destination='logs/%s/%d/%d/%s.csv' % (experiment.name, repetition, seed_repeat, worker.name), device=worker.name)

    system_log_path = "sys_logs/%s/%d/%d/" % (experiment.name, repetition, seed_repeat)
    os.makedirs(system_log_path, exist_ok=True)
    cleanLogs(system_log_path)
    adb.pullSystemLog(device, system_log_path)

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

    adb.DEBUG = False
    devices = adb.listDevices()
    if (len(devices) < experiment.devices):
        total_devices = len(adb.listDevices(0))
        if (total_devices < experiment.devices):
            print("Not Enought Devices")
            return
        print("Waiting for enough devices to charge (%d OK | %d NEEDED | %d TOTAL)" % (len(devices), experiment.devices, total_devices), end='')
        stdout.flush()
        while (len(devices) < experiment.devices):
            total_devices = len(adb.listDevices(0))
            if (total_devices < experiment.devices):
                print("Not Enought Devices")
                return
            else:
                sleep(60)
                print('.', end='')
                stdout.flush()
                new_devices = adb.listDevices()
                if (new_devices != devices):
                    for dev in new_devices:
                        if (dev not in devices):
                            print("\nDevice %s OK" % dev)
                    devices = new_devices
                    if (len(devices) < experiment.devices):
                        print("Waiting for enough devices to charge (%d OK | %d NEEDED | %d TOTAL)" % (len(devices), experiment.devices, total_devices), end='')
        print()
    adb.DEBUG = True

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
    conf.write("Cloudlets: %s\n" % str(experiment.cloudlets))
    conf.write("Seed: %s\n" % experiment.seed)
    conf.write("Repetitions: %s" % str(experiment.repetitions))
    conf.write("Producers: %s" % experiment.producers)
    conf.write("RepeatSeed: %s" % experiment.repeat_seed)
    conf.write("=============================\n")
    conf.close()

    stopClouds(experiment)
    for repetition in range(experiment.repetitions):
        print("Running Repetition %d" % repetition)

        complete_repetition = False
        while (not complete_repetition):
            os.makedirs("logs/%s/%d/" % (experiment.name, repetition), exist_ok=True)
            devices.sort()
            experiment_random.shuffle(devices)

            for seed_repeat in range(experiment.repeat_seed):
                os.makedirs("logs/%s/%d/%d/" % (experiment.name, repetition, seed_repeat), exist_ok=True)
                boot_barrier = threading.Barrier(experiment.devices + 1)
                start_barrier = threading.Barrier(experiment.devices + 1)
                complete_barrier = threading.Barrier(experiment.devices + 1)
                log_pull_barrier = threading.Barrier(experiment.devices + 1)
                finish_barrier = threading.Barrier(experiment.devices + len(experiment.cloudlets) + len(experiment.clouds) + 1)
                servers_finish_barrier = threading.Barrier(len(experiment.cloudlets) + len(experiment.clouds) + 1)

                startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)
                startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                producers = experiment.producers
                for device in devices[:experiment.devices]:
                    adb.screenOn(device)
                    threading.Thread(target = startWorker, args = (experiment, repetition, seed_repeat, (producers > 0), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)).start()
                    producers -= 1 # Os primeiros n devices é que produzem conteudo

                boot_barrier.wait()
                sleep(1)
                start_barrier.wait()

                complete_barrier.wait()
                while PENDING_JOBS > 0:
                    sleep(5)
                sleep(10)
                log_pull_barrier.wait()
                if (experiment.isOK()):
                    pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat)
                servers_finish_barrier.wait()
                finish_barrier.wait()

                for device in devices:
                    adb.screenOff(device)

                #stopClouds(experiment)

            if (experiment.isOK()):
                complete_repetition = True


        if (repetition != experiment.repetitions - 1):
            print("Waiting 5s for next repetition")
            sleep(5)


def startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloudlet_boot_barrier = threading.Barrier(len(experiment.cloudlets) + 1)
    for cloudlet in experiment.cloudlets:
        threading.Thread(target = startCloudletThread, args = (cloudlet, experiment, repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier)).start()
    cloudlet_boot_barrier.wait()

def startCloudletThread(cloudlet, experiment, repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier):
    print("Starting %s Cloudlet Instance" % cloudlet)
    cloudlet_instance = grpcControls.cloudClient(cloudlet, "%s_cloudlet" % cloudlet)

    cloudlet_instance.stop()

    cloudlet_instance.connectLauncherService()
    cloudlet_instance.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    cloudlet_instance.startWorker()
    sleep(2)
    cloudlet_instance.connectBrokerService()
    sleep(2)
    models = cloudlet_instance.listModels()
    if (models is None):
        experiment.setFail()
    else:
        for model in models.models:
            if model.name == experiment.model:
                if (cloudlet_instance.setModel(model) is None):
                    print("Failed to setScheduler on %s" % cloudlet)
                    experiment.setFail()
                break

    cloudlet_boot_barrier.wait() #inform startCloudlets that you have booted

    servers_finish_barrier.wait() #wait experiment completion to init shutdown
    cloudlet_instance.stop()
    finish_barrier.wait()

def pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat):
    log_name = "%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat)
    for cloud in experiment.clouds:
        os.system("scp joaquim@%s:~/logs/%s logs/%s/%s/%s/%s_%s.csv" % (cloud[2], log_name, experiment.name, repetition, seed_repeat, cloud[0], cloud[1]))
    for cloudlet in experiment.cloudlets:
        os.system("scp joaquim@%s:~/logs/%s logs/%s/%s/%s/cloudlet_%s.csv" % (cloudlet, log_name, experiment.name, repetition, seed_repeat, cloudlet))

def startCloudThread(cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier):
    print("Starting %s Cloud Instance" % cloud[0])
    stdout.flush()
    adb.cloudInstanceStart(cloud[0], cloud[1])
    while (not adb.cloudInstanceRunning(cloud[0])):
        sleep(5)
    print("\nWaiting %s Cloud DNS (%s) update" % (cloud[0], cloud[2]), end='')
    pingWait(cloud[2])
    cloud_instance = grpcControls.cloudClient(cloud[2], cloud[0])
    cloud_instance.connectLauncherService()
    cloud_instance.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    cloud_instance.startWorker()
    sleep(2)
    cloud_instance.connectBrokerService()
    sleep(2)
    models = cloud_instance.listModels()
    if (models is None):
        experiment.setFail()
    else:
        for model in models.models:
            if model.name == experiment.model:
                if (cloud_instance.setModel(model) is None):
                    print("Failed to setScheduler on %s" % cloud[0])
                    experiment.setFail()
                break
    cloud_boot_barrier.wait()
    servers_finish_barrier.wait()
    print("Stopping %s Cloud Instance" % cloud[0])
    stdout.flush()
    adb.cloudInstanceStop(cloud[0], cloud[1])
    finish_barrier.wait()


def startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloud_boot_barrier = threading.Barrier(len(experiment.clouds) + 1)
    for cloud in experiment.clouds:
        threading.Thread(target = startCloudThread, args = (cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier)).start()
    cloud_boot_barrier.wait()

def stopClouds(experiment):
    for cloud in experiment.clouds:
        print("Stopping %s Cloud Instance" % cloud[0])
        stdout.flush()
        adb.cloudInstanceStop(cloud[0], cloud[1])

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
    cloudlets = []
    seed = 0
    repetitions = 1
    producers = 0
    repeat_seed = 1

    _running_status = True

    def __init__(self, name):
        self.name = name

    def setFail(self):
        self._running_status = False

    def isOK(self):
        return self._running_status


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
                clouds = []
                for entry in config[section][option].split(','):
                    cloud_zone_address = entry.split("/")
                    clouds += [(cloud_zone_address[0], cloud_zone_address[1], cloud_zone_address[2])]
                    experiment.clouds = clouds
            elif option == "cloudlets":
                cloudlets = []
                for entry in config[section][option].split(','):
                    cloudlets += [entry]
                    experiment.cloudlets = cloudlets
            elif option == "seed":
                experiment.seed = config[section][option]
            elif option == "repetitions":
                experiment.repetitions = int(config[section][option])
            elif option == "producers":
                experiment.producers = int(config[section][option])
            elif option == "repeatseed":
                experiment.repeat_seed = int(config[section][option])
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
                    Seed                    = Seed to use [STR]
                    Clouds                  = Instance/Zone/IP, Instance/Zone/IP, ... [LIST]
                    Producers               = Number of producer devices [INT]
                    RepeatSeed              = Repeat experiment with same seed N times [INT]
                    Cloudlets               = IP, ... [LIST]

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
        print("Cloudlets: ", e.cloudlets)
        print("Seed: ", e.seed)
        print("Repetitions: ", e.repetitions)
        print("Producers: ", e.producers)
        print("RepeatSeed: ", e.repeat_seed)
        print("=============================")
        runExperiment(e)

if __name__ == '__main__':
    main()
