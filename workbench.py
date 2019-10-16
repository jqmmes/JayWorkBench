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
from datetime import datetime


EXPERIMENTS = []
PENDING_JOBS = 0
PENDING_WORKERS = 0
LAST_REBOOT_TIME = 0
ALL_DEVICES = []
FNULL = open(os.devnull, "w")
LOG_FILE = stdout

def log(str, end="\n"):
    global LOG_FILE
    LOG_FILE.write(str+end)
    LOG_FILE.flush()

def brokenBarrierExceptionHook(exception_type, exception, traceback):
    if (exception_type is threading.BrokenBarrierError):
        pass
    else:
        log("%s: %s" % (exception_type.__name__, exception))
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
        #log(".", end='')
        #stdout.flush()
        sleep(2)
    #log("")

'''def runJob(worker, device_random, assets_dir="assets"):
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


    log("{}\t{}\tJOB_SUBMIT\t{}\t{}".format(time(), job.id, asset, worker.name))
    # Fazer schedule no python. Maneira antiga
    try:
        if not worker.scheduleJob(job):
            log("{}\t{}\tJOB_FAILED\tFAILED_SCHEDULE\t{}".format(time(), job.id, worker.name))
        else:
            log("{}\t{}\tJOB_COMPLETE\t{}".format(time(), job.id, worker.name))
    except Exception as job_exception:
        log("{}\t{}\tJOB_FAILED\t{}JOB_EXCEPTION\t{}".format(time(), job.id, worker.name))
    PENDING_JOBS -= 1'''

def createJob(worker, asset_id):
    global PENDING_JOBS
    PENDING_JOBS += 1
    log("{}\t{}\tJOB_SUBMIT\t{}".format(time(), asset_id, worker.name))
    try:
        if not worker.createJob(asset_id):
            log("{}\t{}\tJOB_FAILED\tFAILED_SCHEDULE\t{}".format(time(), asset_id, worker.name))
        else:
            log("{}\t{}\tJOB_COMPLETE\t{}".format(time(), asset_id, worker.name))
    except Exception as job_exception:
        log("{}\t{}\tJOB_FAILED\t{}JOB_EXCEPTION\t{}".format(time(), asset_id, worker.name))
    PENDING_JOBS -= 1

def calibrateWorkerThread(worker, worker_seed, device=None, asset_id=""):
    log("CALIBRATION\t{}".format(worker.name))
    asset = asset_id
    if (asset == ""):
        device_random = random.Random()
        device_random.seed(worker_seed)
        files_on_device = adb.listFiles(device=device)

        asset = files_on_device[device_random.randint(0,len(files_on_device)-1)]
        while (asset[-4:] not in ['.png', '.jpg']):
            asset = files_on_device[device_random.randint(0,len(files_on_device)-1)]

    log("{}\t{}\tJOB_SUBMIT\t{}\t{}".format(time(), "CALIBRATION_JOB", asset, worker.name))
    try:
        if not worker.calibrateWorker(asset):
            log("{}\t{}\tCALIBRATION_FAILED\tFAILED_CALIBRATION\t{}".format(time(), "CALIBRATION_JOB", worker.name))
        else:
            log("{}\t{}\tCALIBRATION_COMPLETE\t{}".format(time(), "CALIBRATION_JOB", worker.name))
    except Exception as job_exception:
        log("{}\t{}\tCALIBRATION_FAILED\t{}CALIBRATION_EXCEPTION\t{}".format(time(), "CALIBRATION_JOB", worker.name))

def barrierWithTimeout(barrier, timeout, experiment=None, show_error=True, device=None, *skip_barriers):
    if experiment is not None:
        if not experiment.isOK():
            skipBarriers(experiment, show_error, device, *skip_barriers)
            return False
    try:
        barrier.wait(timeout=timeout)
    except Exception as barrier_exception:
        skipBarriers(experiment, show_error, device, *skip_barriers)
        return False
    if (barrier.broken):
        skipBarriers(experiment, show_error, device, *skip_barriers)
        return False
    return True

def skipBarriers(experiment, show_error=True, device=None, *skip_barriers):
    if show_error:
        log("ERROR\tSKIP_BARRIERS\t{}".format(device))
    if experiment:
        experiment.setFail()
    for barrier in skip_barriers:
        barrier.wait()

def getDeviceIp(device):
    for n in range(5):
        worker_ip = adb.getDeviceIp(device)
        return worker_ip if worker_ip is not None else sleep(5)
    return None

def experimentRebootDevice(device, device_random, max_sleep_random=10, retries=3):
    global LAST_REBOOT_TIME
    while True:
        sleep_duration = device_random.randint(0,10*max_sleep_random)
        sleep(sleep_duration)
        if (time()-LAST_REBOOT_TIME > 30):
            LAST_REBOOT_TIME = time()
            log("REBOOT_WORKER\t%s" % device.name)
            pre_reboot_worker_ip = getDeviceIp(device)
            if adb.rebootAndWait(device, timeout=180):
                log("REBOOT_WORKER_COMPLETE\t%s" % device.name)
                return True
            else:
                if (retries > 0):
                    log("REBOOT_WORKER_RETRY\t%s" % device.name)
                    return experimentRebootDevice(device, device_random, 10, retries - 1)
                else:
                    log("REBOOT_WORKER_FAIL\t%s" % device.name)
                    return False

def startWorkerThread(experiment, worker_seed, repetition, seed_repeat, is_producer, is_worker, device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
    global PENDING_JOBS, PENDING_WORKERS
    if (adb.freeSpace(device=device) < 1.0):
        log('LOW_SDCARD_SPACE\t%s' % device.name)
        adb.uninstallPackage(device)
        log('PACKAGE_UNINSTALLED\t%s' % device.name)
        adb.pushFile('apps', 'ODLauncher-release.apk', path='', device=device)
        log('PACKAGE_PUSHED\t%s' % device.name)
        adb.pmInstallPackage('apps', 'ODLauncher-release.apk', device)
        log('PACKAGE_INSTALLED\t%s' % device.name)
    adb.connectWifiADB(device)
    log("START_DEVICE\t%s" % device.name)
    device_random = random.Random()
    device_random.seed(experiment.seed+worker_seed+str(repetition))
    rate = float(experiment.request_rate)/float(experiment.request_time)
    log('GENERATING_JOBS\tRATE: {}\t{}'.format(rate, device.name))
    job_intervals = []
    asset_list = []
    while(sum(job_intervals) < experiment.duration):
        job_intervals.append(device_random.expovariate(rate))
        asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]
        while ((asset[-4:] not in ['.png', '.jpg'] and experiment.asset_type == 'image') or (asset[-4:] not in ['.mp4'] and experiment.asset_type == 'video')):
            asset = ASSETS[device_random.randint(0,len(ASSETS)-1)]
        asset_list.append(asset)
    log('SELECTED_ASSET\t{} ASSETS\t{}'.format(len(asset_list), device.name))
    if experiment.reboot:
        if not experimentRebootDevice(device, device_random, experiment.devices):
            sleep(10)
            retries = 0
            while True:
                wifi_adb = adb.connectWifiADB(device)
                if wifi_adb[1]:
                    device = wifi_adb[0]
                    break
                if retries > 3:
                    log("FAILED_SWITCHING_TO_WIFI_ADB\t%s\t%s" % (device.name, device.ip))
                    skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                    experiment.deviceFail(device.name)
                    return
                adb.enableWifiADB(device)
                sleep(1)
                retries += 1
        adb.connectWifiADB(device)
    sleep(2)
    log("LISTING_FILES_ON_DEVICE\t%s" % device.name)
    files_on_device = adb.listFiles(device=device)
    log('PUSHING_ASSETS\t%s' % device.name)
    for asset in asset_list:
        if (asset not in files_on_device):
            adb.pushFile(experiment.assets, asset, device=device)
            files_on_device.append(asset)
    adb.screenOn(device)
    adb.setBrightness(device, 0)
    adb.clearSystemLog(device)
    log("STOP_ALL_SERVICE\t%s" % device.name)
    adb.stopAll(device)
    sleep(2)
    log("STARTING_LAUNCH_SERVICE\t%s" % device.name)
    if not adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True):
        log("FAILED_LAUNCH_SERVICE\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        return
    try:
        worker_ip = getDeviceIp(device)
        if (worker_ip is None and retries < 5):
            log("FAILED_OBTAIN_IP\t%s" % device.name)
            skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
            experiment.deviceFail(device.name)
            adb.rebootAndWait(device)
            return
        log("STARTING_SERVICES\t%s" % device.name)
        worker = grpcControls.remoteClient(worker_ip, device.name, LOG_FILE)
        worker.connectLauncherService()
        worker.setLogName(experiment.name)
        if is_worker:
            worker.startWorker()
        worker.startScheduler()
        worker.connectBrokerService()
        sleep(2)
    except Exception:
        log("Error Starting Worker %s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        return
    if experiment.settings:
        worker.setSettings(experiment.settings)
    schedulers = worker.listSchedulers()
    if is_worker:
        models = worker.listModels()
    if (schedulers is None):# or models is None):
        log("ERROR_GETTING_MODELS_OR_SCHEDULERS\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        return
    for scheduler in schedulers.scheduler:
        if scheduler.name == experiment.scheduler and experiment.isOK():
            if (worker.setScheduler(scheduler) is None):
                log("Failed to setScheduler on %s" % device.name)
                skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                experiment.deviceFail(device.name)
                return
            break
    if is_worker:
        for model in models.models:
            if model.name == experiment.model and experiment.isOK():
                if (worker.setModel(model) is None):
                    log("Failed to setModel on %s" % device.name)
                    skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                    experiment.deviceFail(device.name)
                    return
                break
    log("WAIT_ON_BARRIER\tBOOT_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(boot_barrier, 200*experiment.devices, experiment, True, device.name, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
        log("BROKEN_BARRIER\tBOOT_BARRIER\t%s" % device.name)
        return
    if is_worker and experiment.calibration:
        calibrateWorkerThread(worker, worker_seed, device)
    log("WAIT_ON_BARRIER\tSTART_BARRIER\t%s" % device.name)
    start_barrier.wait()
    i = 0
    while (i < (len(job_intervals) - 1)  and experiment.isOK() and is_producer):
        log("NEXT_EVENT_IN\t{}".format(job_intervals[i]))
        sleep(job_intervals[i])
        threading.Thread(target = createJob, args = (worker,asset_list[i])).start()
        i = i+1
    log("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(complete_barrier, experiment.duration+experiment.timeout+240 + (0 if is_producer else experiment.duration), experiment, True, device.name, log_pull_barrier, finish_barrier):
        log("BROKEN_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
        return
    adb.screenOff(device)
    log("WAIT_ON_BARRIER\tLOG_PULL_BARRIER\t%s" % device.name)
    log_pull_barrier.wait()
    try:
        log("STOP_WORKER\tSTART\t%s" % device.name)
        worker.destroy()
        adb.stopAll(device)
        log("STOP_WORKER\tCOMPLETE\t%s" % device.name)
    except:
        log("STOP_WORKER\tERROR\t%s" % device.name)
    try:
        if (experiment.isOK()):
            log("PULLING_LOG\t%s\tLOG" % device.name)
            adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % experiment.name, destination='logs/%s/%d/%d/%s.csv' % (experiment.name, repetition, seed_repeat, device.name), device=device)
            log("PULLING_LOG\t%s\tLOG\tOK" % device.name)
    except:
        log("PULLING_LOG\t%s\tLOG\tERROR" % device.name)
        experiment.setFail()
        experiment.deviceFail(device.name)
    try:
        log("PULLING_LOG\t%s\tSYS_LOG" % device.name)
        system_log_path = "sys_logs/%s/%d/%d/" % (experiment.name, repetition, seed_repeat)
        os.makedirs(system_log_path, exist_ok=True)
        adb.pullSystemLog(device, system_log_path)
        log("PULLING_LOG\t%s\tSYS_LOG\tOK" % device.name)
    except:
        log("PULLING_LOG\t%s\tSYS_LOG\tERROR" % device.name)
        experiment.deviceFail(device.name)
    log("CHECKING_LOG\t%s" % device.name)
    log_available = False
    for entry in os.listdir('logs/%s/%d/%d/' % (experiment.name, repetition, seed_repeat)):
        if entry == '%s.csv' % device.name:
            log("CHECKING_LOG\t%s\tOK" % device.name)
            log_available = True
            break
    if not log_available:
        log("CHECKING_LOG\t%s\tFAILED" % device.name)
        experiment.setFail()
        experiment.deviceFail(device.name)
    log("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % device.name)
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
    logExperiment(LOG_FILE, experiment)
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
    logExperiment(conf, experiment)
    conf.close()

    killLocalCloudlet()
    #stopClouds(experiment)

    #for device in devices:
    #    rebootDevice(device)
    #    sleep(2)

    for repetition in range(experiment.repetitions):
        log("=========================\tREPETITION {}\t========================".format(repetition))

        os.makedirs("logs/%s/%d/" % (experiment.name, repetition), exist_ok=True)
        devices.sort(key=lambda e: e.name, reverse=False)
        experiment_random.shuffle(devices)

        for seed_repeat in range(experiment.repeat_seed):
            repeat_tries = 0
            while (True):
                if repeat_tries > 10:
                    os.system("touch logs/%s/too_many_repeat_retries_CANCELED"  % experiment.name)
                    return
                log("=========================\tSEED_REPEAT {} | ATTEMPT {}\t========================".format(seed_repeat, repeat_tries))
                timeout = False
                experiment.setOK()

                # Verifica as baterias e garante que os dispositivos continuam sempre disponiveis. retorna falso se algum device se perdeu
                #if not neededDevicesAvailable(experiment, devices):
                #    return
                experiment_devices = getNeededDevicesAvailable(experiment, devices)
                if experiment_devices == []:
                    os.system("touch logs/%s/not_enough_devices_CANCELED"  % experiment.name)
                    log("=========================\tEXPERIMET_FAILED_NOT_ENOUGHT_DEVICES\t{}\t========================".format(experiment.name))
                    return

                # Descartar os dispositivos que mais falharam durante esta experiencia, sempre que possivel.
                failed_devices = []
                failed_devices_map = experiment.getFailedDevices()
                for key in failed_devices_map:
                    failed_devices.append(key)
                failed_devices.sort(key=lambda e: failed_devices_map[e], reverse=True)
                for failed_device in failed_devices[:max(len(experiment_devices)-experiment.devices, 0)]:
                    experiment_devices.remove(failed_device)

                os.makedirs("logs/%s/%d/%d/" % (experiment.name, repetition, seed_repeat), exist_ok=True)
                boot_barrier = threading.Barrier(experiment.devices + 1)
                start_barrier = threading.Barrier(experiment.devices + 1)
                complete_barrier = threading.Barrier(experiment.devices + 1)
                log_pull_barrier = threading.Barrier(experiment.devices + 1)
                finish_barrier = threading.Barrier(experiment.devices + len(experiment.cloudlets) + len(experiment.clouds) + 1)
                servers_finish_barrier = threading.Barrier(len(experiment.cloudlets) + len(experiment.clouds) + 1)

                startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                if (len(experiment.clouds) == 0):
                    stopClouds(experiment)

                producers = experiment.producers
                workers = experiment.workers
                i = 0
                for device in experiment_devices[:experiment.devices]:
                    threading.Thread(target = startWorkerThread, args = (experiment, "seed_{}".format(i),repetition, seed_repeat, (producers > 0), (experiment.start_worker and (workers > 0)), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)).start()
                    producers -= 1 # Os primeiros n devices é que produzem conteudo
                    workers -= 1 # Os primeiros n devices é que são workers
                    i += 1
                # TODO: Validar que os devices encontram bem as clouds por elas arrancarem depois dos devices
                startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                log("WAIT_ON_BARRIER\tBOOT_BARRIER\tMAIN_LOOP")
                if not barrierWithTimeout(boot_barrier, 200*experiment.devices, experiment, True, "MAIN"): # 15m
                    log("BROKEN_BARRIER\tBOOT_BARRIER\tMAIN")
                sleep(1)
                log("WAIT_ON_BARRIER\tSTART_BARRIER\tMAIN_LOOP")
                if not barrierWithTimeout(start_barrier, 60, experiment, True, "MAIN"):
                    log("BROKEN_BARRIER\tSTART_BARRIER\tMAIN")

                completetion_timeout_start = time()
                while (PENDING_JOBS > 0 and experiment.isOK()) or experiment.duration > time()-completetion_timeout_start:
                    sleep(2)
                    if (time()-completetion_timeout_start > experiment.duration+experiment.timeout):
                        log("COMPLETION_TIMEOUT_EXCEDED")
                        os.system("touch logs/%s/%d/%d/completion_timeout_exceded"  % (experiment.name, repetition, seed_repeat))
                        break
                sleep(2)
                log("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\tMAIN_LOOP")
                if not barrierWithTimeout(complete_barrier, 240, experiment, True, "MAIN"):
                    log("BROKEN_BARRIER\tCOMPLETE_BARRIER\tMAIN")
                sleep(1)
                log("WAIT_ON_BARRIER\tLOG_PULL_BARRIER\tMAIN_LOOP")
                barrierWithTimeout(log_pull_barrier, 60, experiment, True, "MAIN")
                if (experiment.isOK()):
                    pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat)

                log("WAIT_ON_BARRIER\tSERVER_FINISH_BARRIER\tMAIN_LOOP")
                barrierWithTimeout(servers_finish_barrier, 60, experiment, True, "MAIN", servers_finish_barrier, finish_barrier)
                log("WAIT_ON_BARRIER\tFINISH_BARRIER\tMAIN_LOOP")
                barrierWithTimeout(finish_barrier, 240, experiment, True, "MAIN", finish_barrier)

                if (experiment.isOK()):
                    break
                repeat_tries += 1


        if (repetition != experiment.repetitions - 1):
            log("Waiting 5s for next repetition")
            sleep(5)

'''def neededDevicesAvailable(experiment, devices, retries=5):
    if retries < 0:
        experiment.setFail()
        os.system("touch logs/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
        return False
    if not checkBattery(20, *devices[:experiment.devices]):
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
        log("INVALID_BATTERY_CONTINUING ON {}".format(device.name))
        barrierWithTimeout(battery_barrier, 3600)
        return
    if (battery_level < min_battery):
        counter = 0
        while (not battery_barrier.broken and (battery_level < max(0, min(100, min_battery + 10)))):
            if (counter % 5 == 0):
                log("NOT_ENOUGH_BATTERY ON {} ({}%)".format(device.name, battery_level))
            sleep(120)
            battery_level = adb.getBatteryLevel(device)
            counter += 1
    barrierWithTimeout(battery_barrier, 3600)'''

def getNeededDevicesAvailable(experiment, devices, retries=5):
    if retries < 0:
        experiment.setFail()
        os.system("touch logs/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
        return []
    to_charge = []
    good_to_use = []
    for device in devices:
        if getBatteryLevel(device) >= experiment.min_battery:
            good_to_use.append(device)
        else:
            to_charge.append(device)
    if len(good_to_use) >= experiment.devices:
        return good_to_use
    else:
        discoverable_devices = adb.listDevices(0)
        good_to_charge = []
        for device in to_charge:
            if device in discoverable_devices:
                good_to_charge.append(device)
        if len(good_to_use) + len(good_to_charge) < experiment.devices:
            experiment.setFail()
            os.system("touch logs/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
            return []
        battery_barrier = threading.Barrier(experiment.devices - len(good_to_use) + 1)
        for device in good_to_charge:
            threading.Thread(target = chargeDevice, args = (min_battery, device, battery_barrier)).start()
        barrierWithTimeout(battery_barrier, 3600, show_error=False)
        return getNeededDevicesAvailable(experiment, devices, retries-1)

def rebootDevice(device, retries=3):
    if retries < 0:
        log("REBOOT_DEVICE_FAIL\t%s" % device.name)
        return False
    log("REBOOT_DEVICE\t%s" % device.name)
    pre_reboot_worker_ip = getDeviceIp(device)
    if adb.rebootAndWait(device, timeout=180):
        log("REBOOT_DEVICE_COMPLETE\t%s" % device.name)
        return True
    else:
        log("REBOOT_DEVICE_RETRY\t%s" % device.name)
        return rebootDevice(device, retries - 1)

def getBatteryLevel(device, retries=5):
    if retries < 0:
        return -1
    battery_level = adb.getBatteryLevel(device)
    if (battery_level < 0):
        log("INVALID_BATTERY ON {}".format(device.name))
        if rebootDevice(device):
            return getBatteryLevel(device, retries-1)
        else:
            return -1
    return battery_level

def chargeDevice(min_battery, device, battery_barrier):
    counter = 0
    while (not battery_barrier.broken and (getBatteryLevel(device) < max(0, min(100, min_battery)))):
        if (counter % 5 == 0):
            log("CHARGING_DEVICE {} ({}%)".format(device.name, battery_level))
        sleep(120)
        counter += 1
    barrierWithTimeout(battery_barrier, 3600, show_error=False)

def startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloudlet_boot_barrier = threading.Barrier(len(experiment.cloudlets) + 1)
    i = 0
    for cloudlet in experiment.cloudlets:
        threading.Thread(target = startCloudletThread, args = (cloudlet, experiment, "cloudlet_seed_{}".format(i), repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier)).start()
        i += 1
    cloudlet_boot_barrier.wait()

def killLocalCloudlet():
    pid = os.popen("jps -lV | grep ODCloud.jar | cut -d' ' -f1").read()[:-1]
    if pid != '':
        subprocess.run(['kill', '-9', pid])

def startCloudletThread(cloudlet, experiment, cloudlet_seed, repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier):
    log("Starting %s Cloudlet Instance" % cloudlet)
    device_random = random.Random()
    device_random.seed(experiment.seed+cloudlet_seed+str(repetition))
    cloudlet_control = grpcControls.cloudControl(cloudlet, "%s_cloudlet" % cloudlet, LOG_FILE)
    cloudlet_control.connect()
    cloudlet_control.stop()
    cloudlet_control.start()
    sleep(1)
    cloudlet_instance = grpcControls.cloudClient(cloudlet, "%s_cloudlet" % cloudlet, LOG_FILE)
    #cloudlet_instance.stop()
    cloudlet_instance.connectLauncherService()
    cloudlet_instance.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    if experiment.settings or experiment.mcast_interface:
        cloudlet_instance.setSettings(experiment.settings, experiment.mcast_interface)
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
                    log("Failed to setScheduler on %s" % cloudlet)
                    experiment.setFail()
                break
    cloudlet_boot_barrier.wait() #inform startCloudlets that you have booted
    if (experiment.calibration):
        calibrateWorkerThread(cloudlet_instance, cloudlet_seed, asset_id="%s.jpg" % experiment.asset_quality)
    servers_finish_barrier.wait() #wait experiment completion to init shutdown
    cloudlet_instance.stop()
    cloudlet_control.stop()
    finish_barrier.wait()

def pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat):
    log_name = "%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat)
    for cloud in experiment.clouds:
        os.system("scp joaquim@%s:~/ODCloud/logs/%s logs/%s/%s/%s/%s_%s.csv" % (cloud.address, log_name, experiment.name, repetition, seed_repeat, cloud.instance, cloud.zone))
    for cloudlet in experiment.cloudlets:
        if (cloudlet == '127.0.0.1'):
            os.system("cp /home/joaquim/ODCloud/logs/%s logs/%s/%s/%s/cloudlet_%s.csv" % (log_name, experiment.name, repetition, seed_repeat, cloudlet))
        else:
            os.system("scp joaquim@%s:~/ODCloud/logs/%s logs/%s/%s/%s/cloudlet_%s.csv" % (cloudlet, log_name, experiment.name, repetition, seed_repeat, cloudlet))

def startCloudThread(cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier):
    log("START_CLOUD_INSTANCE\t{}\t({})".format(cloud.instance, cloud.address))
    stdout.flush()
    adb.cloudInstanceStart(cloud.instance, cloud.zone)
    while (not adb.cloudInstanceRunning(cloud.instance)):
        sleep(5)
    log("WAITING_FOR_CLOUD_DNS_UPDATE\t%s\t(%s)" % (cloud.instance, cloud.address))
    pingWait(cloud.address)

    cloud_control = grpcControls.cloudControl(cloud.address, "{}_{}_cloud".format(cloud.instance, cloud.zone), LOG_FILE)
    cloud_control.connect()
    cloud_control.stop()
    cloud_control.start()
    sleep(1)

    cloud_instance = grpcControls.cloudClient(cloud.address, cloud.instance, LOG_FILE)
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
                    log("Failed to setScheduler on %s" % cloud.instance)
                    experiment.setFail()
                break
    log("WAIT_ON_BARRIER\tCLOUD_BOOT_BARRIER\t%s" % cloud.instance)
    cloud_boot_barrier.wait()
    log("WAIT_ON_BARRIER\tSERVER_FINISH_BARRIER\t%s" % cloud.instance)
    servers_finish_barrier.wait()
    log("Stopping %s Cloud Instance" % cloud.instance)
    cloud_instance.stop()
    cloud_control.stop()
    log("STOPPING_CLOUD_INSTANCE\t{}\t({})".format(cloud.instance, cloud.address))
    adb.cloudInstanceStop(cloud.instance, cloud.zone)
    log("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % cloud.instance)
    finish_barrier.wait()


def startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloud_boot_barrier = threading.Barrier(len(experiment.clouds) + 1)
    for cloud in experiment.clouds:
        threading.Thread(target = startCloudThread, args = (cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier)).start()
    cloud_boot_barrier.wait()
    log("CLOUDS_BOOTED\tWAIT_5S_FOR_DEVICE_TO_FIND_THEM_ACTIVE")
    sleep(5)

def stopClouds(experiment):
    for cloud in experiment.clouds:
        log("Stopping %s Cloud Instance" % cloud.instance)
        stdout.flush()
        adb.cloudInstanceStop(cloud.instance, cloud.zone)

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
    workers = -1
    assets = "assets"
    asset_type = "image"
    calibration = False
    asset_quality = "SD"
    settings = {}
    mcast_interface = None
    min_battery = 20

    _failed_devices = {}
    _running_status = True

    def __init__(self, name):
        self.name = name

    def setFail(self):
        self._running_status = False

    def setOK(self):
        self._running_status = True

    def isOK(self):
        return self._running_status

    def deviceFail(self, device):
        if device in failed_devices:
            self._failed_devices[device] += 1
        else:
            self._failed_devices[device] = 0

    def getFailedDevices(self):
        return self._failed_devices


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
                    clouds.append(grpcControls.Cloud(cloud_zone_address[0], cloud_zone_address[1], cloud_zone_address[2]))
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
            elif option == "workers":
                experiment.workers = int(config[section][option])
            elif option == "assets":
                experiment.assets = config[section][option]
            elif option == "assettype":
                experiment.asset_type = config[section][option]
            elif option == "calibration":
                experiment.calibration = config[section][option] == "True"
            elif option == "Assetquality":
                if (config[section][option] in ["SD", "HD", "UHD"]):
                    experiment.asset_quality = config[section][option]
            elif option == "settings":
                for entry in config[section][option].split(';'):
                    setting = entry.split(':')
                    experiment.settings[setting[0].strip()] = setting[1].strip()
            elif option == "multicastinterface":
                experiment.mcast_interface = config[section][option]
            elif option == "minbattery":
                experiment.min_battery = int(config[section][option])
        if (experiment.producers == 0 or experiment.producers > experiment.devices):
            experiment.producers = experiment.devices
        if (experiment.workers == -1 or experiment.workers > experiment.devices):
            experiment.workers = experiment.devices
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
                    StartWorkers            = Start Device Worker devices [INT]
                    Workers                 = Number of Workers [BOOL] (Default True)
                    Assets                  = Assets directory [assets] (Default Value)
                    AssetType               = Asset Type (image/video) [image] (Default Value)
                    Calibration             = Run ODLib calibration before begin [BOOL] (Default False)
                    Settings                = Set ODLib settings (setting: value;...) [LIST]
                    AssetQuality            = Inform about asset quality (SD/HD/UHD) [STR] (Default SD)
                    MultiCastInterface      = MCAST_INTERFACE: interface to use in cloudlet [STR]
                    MinBattery              = Minimum battery to run experiment [INT] (Default 20)

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

                    ComputationEstimateScheduler            (Same as estimate but witout Bandwidth Estimate)

            Settings:
                    CLOUD_IP
                    GRPC_MAX_MESSAGE_SIZE
                    RTTHistorySize
                    pingTimeout
                    RTTDelayMillis
                    PING_PAYLOAD_SIZE
                    averageComputationTimesToStore
                    workingThreads
                    workerStatusUpdateInterval
                    AUTO_STATUS_UPDATE_INTERVAL_MS
                    RTTDelayMillisFailRetry
                    RTTDelayMillisFailAttempts
                    DEVICE_ID
                    BANDWIDTH_ESTIMATE_TYPE: [ACTIVE/PASSIVE/ALL]
        ================================================ HELP ================================================''')

def logExperiment(conf, experiment):
    conf.write("Experiment: %s\n" % experiment.name)
    conf.write("==============\tCONFIG\t==============\n")
    conf.write("Scheduler: %s\n" % experiment.scheduler)
    conf.write("TF Model: %s\n" % experiment.model)
    conf.write("Devices: %s\n" % str(experiment.devices))
    conf.write("Reboot: %s\n" % experiment.reboot)
    conf.write("Rate: %s\n" % str(experiment.request_rate))
    conf.write("Rate Time: %s" % str(experiment.request_time) + "s\n")
    conf.write("Duration: %s" % str(experiment.duration) + "s\n")
    conf.write("Clouds: [")
    for cloud in experiment.clouds:
        conf.write("({}, {}, {})".format(cloud.instance, cloud.zone, cloud.address))
    conf.write("]\n")
    conf.write("Cloudlets: %s\n" % str(experiment.cloudlets))
    conf.write("Seed: %s\n" % experiment.seed)
    conf.write("Repetitions: %s\n" % str(experiment.repetitions))
    conf.write("Producers: %s\n" % experiment.producers)
    conf.write("RepeatSeed: %s\n" % experiment.repeat_seed)
    conf.write("Timeout: %s\n" % experiment.timeout)
    conf.write("======================================\n")

def main():
    global ALL_DEVICES, LOG_FILE
    now = datetime.now()
    LOG_FILE = open("workbench_logs/log_{}_{}_{}_{}_{}_{}.log".format(now.year, now.month, now.day, now.hour, now.minute, now.second), "w")
    if (len(argv) < 2):
        log("\tPlease provide config file!")
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
        log("==============\tDEVICES\t==============")
        ALL_DEVICES = adb.listDevices(0)
        for device in ALL_DEVICES:
            log("{} ({})".format(device.name, device.ip))
            adb.screenOff(device)
            #adb.rebootAndWait(device)
        log("===================================")
        for i in range(1, len(argv)):
            readConfig(argv[i])
        EXPERIMENTS.sort(key=lambda e: e.devices+e.producers-e.request_time+len(e.cloudlets), reverse=False)
        for e in EXPERIMENTS:
            runExperiment(e)
            # TODO: Ler um ficheiro com as novas experiencias caso seja necessario. OU uma folder de configs novas que são consumidas.
            # TODO: Mover o ficheiro de configurações executados para uma pasta
            # TODO: Escrever num log especial as experiencias completas
            # TODO: Escrever num log a experiencia currente
            # TODO: Organizar melhor os logs. Só ter um directorio de logs, e dentro o sys, o workbench etc...


if __name__ == '__main__':
    main()
