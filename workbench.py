import lib.grpcControls as grpcControls
import lib.adb as adb
from time import sleep, time
import random
import threading
import os
import configparser
from sys import argv, stdout
import sys
import subprocess


EXPERIMENTS = []
PENDING_JOBS = 0
PENDING_WORKERS = 0
LAST_REBOOT_TIME = 0
ALL_DEVICES = []


FNULL = open(os.devnull, "w")

def brokenBarrierExceptionHook(exception_type, exception, traceback):
    if (exception_type is threading.BrokenBarrierError):
        pass
    else:
        print("%s: %s" % (exception_type.__name__, exception))
        #raise exception

sys.excepthook = brokenBarrierExceptionHook

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

def runJob(worker, device_random, assets_dir="assets"):
    global PENDING_JOBS
    PENDING_JOBS += 1
    # Criar o job no python
    job = grpcControls.Job()
    asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]

    while (asset[-4:] not in ['.png', '.jpg']):
        asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]

    with open("%s/%s" % (assets_dir, asset), "rb") as image:
        f = image.read()
        b = bytes(f)
        job.addBytes(b)


    print("{}\t{}\tJOB_SUBMIT\t{}\t{}".format(time(), job.id, asset, worker.name))
    # Fazer schedule no python. Maneira antiga
    try:
        if not worker.scheduleJob(job):
            print("{}\t{}\tJOB_FAILED\tFAILED_SCHEDULE\t{}".format(time(), job.id, worker.name))
        else:
            print("{}\t{}\tJOB_COMPLETE\t{}".format(time(), job.id, worker.name))
    except Exception as job_exception:
        print("{}\t{}\tJOB_FAILED\t{}JOB_EXCEPTION\t{}".format(time(), job.id, worker.name))
    PENDING_JOBS -= 1

def createJob(worker, device_random, asset_id):
    global PENDING_JOBS
    PENDING_JOBS += 1
    print("{}\t{}\tJOB_SUBMIT\t{}".format(time(), asset_id, worker.name))
    try:
        if not worker.createJob(asset_id):
            print("{}\t{}\tJOB_FAILED\tFAILED_SCHEDULE\t{}".format(time(), asset_id, worker.name))
        else:
            print("{}\t{}\tJOB_COMPLETE\t{}".format(time(), asset_id, worker.name))
    except Exception as job_exception:
        print("{}\t{}\tJOB_FAILED\t{}JOB_EXCEPTION\t{}".format(time(), asset_id, worker.name))
    PENDING_JOBS -= 1

def calibrateWorker(worker, device_random, assets_dir="assets"):
    job = grpcControls.Job("WORKER_CALIBRATION")
    asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]

    while (asset[-4:] not in ['.png', '.jpg']):
        asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]

    with open("%s/%s" % (assets_dir, asset), "rb") as image:
        f = image.read()
        b = bytes(f)
        job.addBytes(b)
    print("{}\t{}\tJOB_SUBMIT\t{}\t{}".format(time(), job.id, asset, worker.name))
    try:
        if not worker.calibrateWorker(job):
            print("{}\t{}\tCALIBRATION_FAILED\tFAILED_CALIBRATION\t{}".format(time(), job.id, worker.name))
        else:
            print("{}\t{}\tCALIBRATION_COMPLETE\t{}".format(time(), job.id, worker.name))
    except Exception as job_exception:
        print("{}\t{}\tCALIBRATION_FAILED\t{}CALIBRATION_EXCEPTION\t{}".format(time(), job.id, worker.name))

def barrierWithTimeout(barrier, timeout, experiment=None, *skip_barriers):
    if experiment is not None:
        if not experiment.isOK():
            skipBarriers(experiment, *skip_barriers)
            return False
    try:
        barrier.wait(timeout=timeout)
    except Exception as barrier_exception:
        skipBarriers(experiment, *skip_barriers)
        return False
    if (barrier.broken):
        skipBarriers(experiment, *skip_barriers)
        return False
    return True

def skipBarriers(experiment, *skip_barriers):
    print("ERROR\tSKIP_BARRIERS")
    if experiment:
        experiment.setFail()
    for barrier in skip_barriers:
        barrier.wait()

def getDeviceIp(device):
    for n in range(5):
        worker_ip = adb.getDeviceIp(device)
        return worker_ip if worker_ip is not None else sleep(5)
    return None

def rebootDevice(device, device_random, max_sleep_random=10, retries=3):
    global LAST_REBOOT_TIME
    while True:
        sleep_duration = device_random.randint(0,10*max_sleep_random)
        sleep(sleep_duration)
        if (time()-LAST_REBOOT_TIME > 30):
            LAST_REBOOT_TIME = time()
            print("REBOOT_WORKER\t%s" % device.name)
            pre_reboot_worker_ip = getDeviceIp(device)
            if adb.rebootAndWait(device, timeout=180):
                print("REBOOT_WORKER_COMPLETE\t%s" % device.name)
                return True
            else:
                if (retries > 0):
                    print("REBOOT_WORKER_RETRY\t%s" % device.name)
                    return rebootDevice(device, device_random, 10, retries - 1)
                else:
                    print("REBOOT_WORKER_FAIL\t%s" % device.name)
                    return False


def startWorker(experiment, repetition, seed_repeat, is_producer, device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
    global PENDING_JOBS, PENDING_WORKERS
    if (adb.freeSpace(device=device) < 1.0):
        print('LOW_SDCARD_SPACE\t%s' % device.name)
        adb.uninstallPackage(device)
        print('PACKAGE_UNINSTALLED\t%s' % device.name)
        adb.pushFile('apps', 'ODLauncher-release.apk', path='', device=device)
        print('PACKAGE_PUSHED\t%s' % device.name)
        adb.pmInstallPackage('apps', 'ODLauncher-release.apk', device)
        print('PACKAGE_INSTALLED\t%s' % device.name)
    adb.connectWifiADB(device)
    print("START_WORKER\t%s" % device.name)
    device_random = random.Random()
    device_random.seed(experiment.seed+device.name+str(repetition))
    rate = float(experiment.request_rate)/float(experiment.request_time)
    print('GENERATING_JOBS\tRATE: {}\t{}'.format(rate, device.name))
    job_intervals = []
    asset_list = []
    while(sum(job_intervals) < experiment.duration):
        job_intervals.append(device_random.expovariate(rate))
        asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]
        while (asset[-4:] not in ['.png', '.jpg']):
            asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]
        print('SELECTED_ASSET\t{}\t{}'.format(asset, device.name))
        asset_list.append(asset)
    if experiment.reboot:
        if not rebootDevice(device, device_random, experiment.devices):
            sleep(10)
            retries = 0
            while True:
                wifi_adb = adb.connectWifiADB(device)
                if wifi_adb[1]:
                    device = wifi_adb[0]
                    break
                if retries > 3:
                    print("FAILED_SWITCHING_TO_WIFI_ADB\t%s\t%s" % (device.name, device.ip))
                    skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                    return
                adb.enableWifiADB(device)
                sleep(1)
                retries += 1
        adb.connectWifiADB(device)
    sleep(2)
    print('PUSHING_ASSETS\t%s' % device.name)
    for asset in asset_list:
        print('PUSHING_ASSET\t%s\t%s' % (asset, device.name))
        adb.pushFile(experiment.assets, asset, device=device)
    adb.screenOn(device)
    adb.setBrightness(device, 0)
    adb.clearSystemLog(device)
    print("STOP_ALL_SERVICE\t%s" % device.name)
    adb.stopAll(device)
    sleep(2)
    print("STARTING_LAUNCH_SERVICE\t%s" % device.name)
    if not adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True):
        print("FAILED_LAUNCH_SERVICE\t%s" % device.name)
        skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        return

    try:
        worker_ip = getDeviceIp(device)
        if (worker_ip is None):
            print("FAILED_OBTAIN_IP\t%s" % device.name)
            skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
            adb.rebootAndWait(device)
            return
        print("STARTING_SERVICES\t%s" % device.name)
        worker = grpcControls.remoteClient(worker_ip, device.name)
        worker.connectLauncherService()
        worker.setLogName(experiment.name)
        if experiment.start_worker:
            worker.startWorker()
        worker.startScheduler()
        worker.connectBrokerService()
        sleep(2)
    except Exception:
        print(Exception)
        print("Error Starting Worker %s" % device.name)
        skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        return



    schedulers = worker.listSchedulers()
    if experiment.start_worker:
        models = worker.listModels()
    if (schedulers is None):# or models is None):
        print("ERROR_GETTING_MODELS_OR_SCHEDULERS\t%s" % device.name)
        skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        return

    for scheduler in schedulers.scheduler:
        if scheduler.name == experiment.scheduler and experiment.isOK():
            if (worker.setScheduler(scheduler) is None):
                print("Failed to setScheduler on %s" % device.name)
                skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                return
            break
    if experiment.start_worker:
        for model in models.models:
            if model.name == experiment.model and experiment.isOK():
                if (worker.setModel(model) is None):
                    print("Failed to setModel on %s" % device.name)
                    skipBarriers(experiment, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                    return
                break

    print("WAIT_ON_BARRIER\tBOOT_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(boot_barrier, 200*experiment.devices, experiment, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
        print("BROKEN_BARRIER\tBOOT_BARRIER\t%s" % device.name)
        return

    if experiment.start_worker:
        print("CALIBRATION\t{}".format(device.name))
        #calibrateWorker(worker, device_random, experiment.assets)
        #sleep(15)


    print("WAIT_ON_BARRIER\tSTART_BARRIER\t%s" % device.name)
    start_barrier.wait()

    i = 0
    while (i < (len(job_intervals) - 1)  and experiment.isOK() and is_producer):
        print("NEXT_EVENT_IN\t{}".format(job_intervals[i]))
        sleep(job_intervals[i])
        #threading.Thread(target = runJob, args = (worker,device_random,experiment.assets)).start()
        threading.Thread(target = createJob, args = (worker,device_random,asset_list[i])).start()
        i = i+1

    print("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(complete_barrier, experiment.duration+experiment.timeout+240 + (0 if is_producer else experiment.duration), experiment, log_pull_barrier, finish_barrier):
        print("BROKEN_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
        return
    adb.screenOff(device)
    print("WAIT_ON_BARRIER\tLOG_PULL_BARRIER\t%s" % device.name)
    log_pull_barrier.wait()

    try:
        adb.stopAll(device)
        worker.destroy()
    except:
        print("Error Stopping Worker")



    try:
        if (experiment.isOK()):
            adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % experiment.name, destination='logs/%s/%d/%d/%s.csv' % (experiment.name, repetition, seed_repeat, device.name), device=device)
    except:
        experiment.setFail()

    try:
        system_log_path = "sys_logs/%s/%d/%d/" % (experiment.name, repetition, seed_repeat)
        os.makedirs(system_log_path, exist_ok=True)
        adb.pullSystemLog(device, system_log_path)
    except:
        None
    print("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % device.name)

    log_available = False
    for entry in os.listdir('logs/%s/%d/%d/' % (experiment.name, repetition, seed_repeat)):
        if entry == '%s.csv' % device.name:
            log_available = True
            break

    if not log_available:
        experiment.setFail()



    finish_barrier.wait()
    adb.screenOff(device)


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
    global PENDING_JOBS, ALL_DEVICES, ASSETS
    printExperiment(stdout, experiment)
    experiment_random = random.Random()
    experiment_random.seed(experiment.seed)
    cleanLogs("logs/%s/" % experiment.name)
    cleanLogs("sys_logs/%s/" % experiment.name)
    ASSETS=os.listdir(experiment.assets)

    devices = ALL_DEVICES #adb.listDevices(0)
    if (len(devices) < experiment.devices):
        os.system("touch logs/%s/not_enough_devices_CANCELED"  % experiment.name)
        return

    conf = open("logs/%s/conf.cfg" % experiment.name, "w+")
    printExperiment(conf, experiment)
    conf.close()

    stopClouds(experiment)
    for repetition in range(experiment.repetitions):
        print("=========================\tREPETITION {}\t========================".format(repetition))

        os.makedirs("logs/%s/%d/" % (experiment.name, repetition), exist_ok=True)
        devices.sort(key=lambda e: e.name, reverse=False)
        experiment_random.shuffle(devices)

        for seed_repeat in range(experiment.repeat_seed):
            print("=========================\tSEED_REPEAT {}\t========================".format(seed_repeat))
            while (True):
                timeout = False
                experiment.setOK()

                # Verifica as baterias e garante que os dispositivos continuam sempre disponiveis. retorna falso se algum device se perdeu
                if not neededDevicesAvailable(experiment, devices):
                    return

                os.makedirs("logs/%s/%d/%d/" % (experiment.name, repetition, seed_repeat), exist_ok=True)
                boot_barrier = threading.Barrier(experiment.devices + 1)
                start_barrier = threading.Barrier(experiment.devices + 1)
                complete_barrier = threading.Barrier(experiment.devices + 1)
                log_pull_barrier = threading.Barrier(experiment.devices + 1)
                finish_barrier = threading.Barrier(experiment.devices + len(experiment.cloudlets) + len(experiment.clouds) + 1)
                servers_finish_barrier = threading.Barrier(len(experiment.cloudlets) + len(experiment.clouds) + 1)

                startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)
                startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                if (len(experiment.clouds) == 0):
                    stopClouds(experiment)

                producers = experiment.producers
                for device in devices[:experiment.devices]:
                    threading.Thread(target = startWorker, args = (experiment, repetition, seed_repeat, (producers > 0), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)).start()
                    producers -= 1 # Os primeiros n devices é que produzem conteudo
                print("WAIT_ON_BARRIER\tBOOT_BARRIER\tMAIN_LOOP")
                if not barrierWithTimeout(boot_barrier, 200*experiment.devices, experiment): # 15m
                    print("BROKEN_BARRIER\tBOOT_BARRIER\tMAIN")
                sleep(1)
                print("WAIT_ON_BARRIER\tSTART_BARRIER\tMAIN_LOOP")
                if not barrierWithTimeout(start_barrier, 60, experiment):
                    print("BROKEN_BARRIER\tSTART_BARRIER\tMAIN")

                completetion_timeout_start = time()
                while (PENDING_JOBS > 0 and experiment.isOK()) or experiment.duration > time()-completetion_timeout_start:
                    sleep(2)
                    if (time()-completetion_timeout_start > experiment.duration+experiment.timeout):
                        print("COMPLETION_TIMEOUT_EXCEDED")
                        os.system("touch logs/%s/%d/%d/completion_timeout_exceded"  % (experiment.name, repetition, seed_repeat))
                        break
                sleep(2)
                print("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\tMAIN_LOOP")
                if not barrierWithTimeout(complete_barrier, 240, experiment):
                    print("BROKEN_BARRIER\tCOMPLETE_BARRIER\tMAIN")
                sleep(1)
                print("WAIT_ON_BARRIER\tLOG_PULL_BARRIER\tMAIN_LOOP")
                barrierWithTimeout(log_pull_barrier, 60, experiment)
                if (experiment.isOK()):
                    pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat)

                print("WAIT_ON_BARRIER\tSERVER_FINISH_BARRIER\tMAIN_LOOP")
                barrierWithTimeout(servers_finish_barrier, 60, experiment)
                print("WAIT_ON_BARRIER\tFINISH_BARRIER\tMAIN_LOOP")
                barrierWithTimeout(finish_barrier, 240, experiment)

                if (experiment.isOK()):
                    break


        if (repetition != experiment.repetitions - 1):
            print("Waiting 5s for next repetition")
            sleep(5)

def neededDevicesAvailable(experiment, devices, retries=5):
    if retries < 0:
        experiment.setFail()
        os.system("touch logs/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
        return False
    if not checkBattery(25, *devices[:experiment.devices]):
        sleep(5)
        return neededDevicesAvailable(experiment, devices, retries-1)
    else:
        return True

def checkBattery(min_battery, *devices):
    battery_barrier = threading.Barrier(len(devices) + 1)
    for device in devices:
        threading.Thread(target = checkBatteryDevice, args = (min_battery, device, battery_barrier)).start()
    if not barrierWithTimeout(battery_barrier, 3600):
        all_devices = adb.listDevices(0)
        for device in all_devices:
            if device not in devices:
                return False
    return True

def checkBatteryDevice(min_battery, device, battery_barrier):
    adb.screenOff(device)
    battery_level = adb.getBatteryLevel(device)
    if (battery_level < 0):
        print("INVALID_BATTERY_CONTINUING ON {}".format(device.name))
        barrierWithTimeout(battery_barrier, 3600)
        return
    if (battery_level < min_battery):
        counter = 0
        while (not battery_barrier.broken and (battery_level < max(0, min(100, min_battery + 10)))):
            if (counter % 5 == 0):
                print("NOT_ENOUGH_BATTERY ON {} ({}%)".format(device.name, battery_level))
            sleep(120)
            battery_level = adb.getBatteryLevel(device)
            counter += 1
    barrierWithTimeout(battery_barrier, 3600)

def startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloudlet_boot_barrier = threading.Barrier(len(experiment.cloudlets) + 1)
    for cloudlet in experiment.cloudlets:
        threading.Thread(target = startCloudletThread, args = (cloudlet, experiment, repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier)).start()
    cloudlet_boot_barrier.wait()

def killLocalCloudlet():
    pid = os.popen("jps -lV | grep ODCloud.jar | cut -d' ' -f1").read()[:-1]
    if pid != '':
        subprocess.run(['kill', '-9', pid])


def startCloudletThread(cloudlet, experiment, repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier):
    print("Starting %s Cloudlet Instance" % cloudlet)
    device_random = random.Random()
    device_random.seed(experiment.seed+cloudlet+str(repetition))

    cloudlet_control = grpcControls.cloudletControl(cloudlet, "%s_cloudlet" % cloudlet)
    cloudlet_control.connect()
    cloudlet_control.stop()
    cloudlet_control.start()
    sleep(1)


    cloudlet_instance = grpcControls.cloudClient(cloudlet, "%s_cloudlet" % cloudlet)

    #cloudlet_instance.stop()

    cloudlet_instance.connectLauncherService()
    cloudlet_instance.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    cloudlet_instance.startWorker()
    sleep(1)
    cloudlet_instance.connectBrokerService()
    sleep(1)
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

    print("CALIBRATION\t{}".format(cloudlet))
    #calibrateWorker(cloudlet_instance, device_random, experiment.assets)

    servers_finish_barrier.wait() #wait experiment completion to init shutdown
    cloudlet_instance.stop()
    cloudlet_control.stop()
    finish_barrier.wait()

def pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat):
    log_name = "%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat)
    for cloud in experiment.clouds:
        os.system("scp joaquim@%s:~/logs/%s logs/%s/%s/%s/%s_%s.csv" % (cloud[2], log_name, experiment.name, repetition, seed_repeat, cloud[0], cloud[1]))
    for cloudlet in experiment.cloudlets:
        if (cloudlet == '127.0.0.1'):
            os.system("cp /home/joaquim/ODCloud/logs/%s logs/%s/%s/%s/cloudlet_%s.csv" % (log_name, experiment.name, repetition, seed_repeat, cloudlet))
        else:
            os.system("scp joaquim@%s:~/ODCloud/logs/%s logs/%s/%s/%s/cloudlet_%s.csv" % (cloudlet, log_name, experiment.name, repetition, seed_repeat, cloudlet))

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
    print("WAIT_ON_BARRIER\tCLOUD_BOOT_BARRIER\t%s" % cloud[0])
    cloud_boot_barrier.wait()
    print("WAIT_ON_BARRIER\tSERVER_FINISH_BARRIER\t%s" % cloud[0])
    servers_finish_barrier.wait()
    print("Stopping %s Cloud Instance" % cloud[0])
    stdout.flush()
    adb.cloudInstanceStop(cloud[0], cloud[1])
    print("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % cloud[0])
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
    timeout = 1500 # 25 Mins
    start_worker = True
    assets = "assets"

    _running_status = True

    def __init__(self, name):
        self.name = name

    def setFail(self):
        self._running_status = False

    def setOK(self):
        self._running_status = True

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
            elif option == "timeout":
                experiment.timeout = int(config[section][option])
            elif option == "startworkers":
                experiment.start_worker = config[section][option] == "True"
            elif option == "assets":
                experiment.assets = config[section][option]
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
                    Timeout                 = Max time after experiment duration to cancel execution
                    StartWorkers            = Start Device Workers [BOOL] (Default True)
                    Assets                  = Assets directory [assets] (Default Value)

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

def printExperiment(conf, experiment):
    conf.write("Experiment: %s\n" % experiment.name)
    conf.write("==============\tCONFIG\t==============\n")
    conf.write("Scheduler: %s\n" % experiment.scheduler)
    conf.write("TF Model: %s\n" % experiment.model)
    conf.write("Devices: %s\n" % str(experiment.devices))
    conf.write("Reboot: %s\n" % experiment.reboot)
    conf.write("Rate: %s\n" % str(experiment.request_rate))
    conf.write("Rate Time: %s" % str(experiment.request_time) + "s\n")
    conf.write("Duration: %s" % str(experiment.duration) + "s\n")
    conf.write("Clouds: %s\n" % str(experiment.clouds))
    conf.write("Cloudlets: %s\n" % str(experiment.cloudlets))
    conf.write("Seed: %s\n" % experiment.seed)
    conf.write("Repetitions: %s\n" % str(experiment.repetitions))
    conf.write("Producers: %s\n" % experiment.producers)
    conf.write("RepeatSeed: %s\n" % experiment.repeat_seed)
    conf.write("Timeout: %s\n" % experiment.timeout)

def main():
    global ALL_DEVICES
    if (len(argv) < 2):
        print("\tPlease provide config file!")
        help()
        return
    if argv[1].lower() == "help":
        help()
    elif argv[1].lower() == "install":
        for device in adb.listDevices(0):
            adb.removePackage(device)
            adb.installPackage('apps/ODLauncher-release.apk', device)
    else:
        if "DEBUG_GRPC" in os.environ and int(os.environ["DEBUG_GRPC"]) == 1:
            grpcControls.DEBUG = True
        if "DEBUG_ADB" in os.environ and int(os.environ["DEBUG_ADB"]) == 1:
            adb.DEBUG = True
        ALL_DEVICES = adb.listDevices(0)
        print("==============\tDEVICES\t==============")
        for device in ALL_DEVICES:
            print("{} ({})".format(device.name, device.ip))
            adb.screenOff(device)
            #adb.rebootAndWait(device)
        print("===================================")
        for i in range(1, len(argv)):
            readConfig(argv[i])
        EXPERIMENTS.sort(key=lambda e: e.devices+e.producers-e.request_time, reverse=False)
        for e in EXPERIMENTS:
            runExperiment(e)

if __name__ == '__main__':
    main()
