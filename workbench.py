import lib.grpcControls as grpcControls
import lib.adb as adb
from lib.curse import draw_curses
from time import sleep, time, gmtime, ctime
import random
from threading import Barrier, Lock, Thread, BrokenBarrierError
import os
import shutil
import configparser
from sys import argv, stdout
import sys
import subprocess
from datetime import datetime
import argparse
from collections import deque
from func_timeout import func_timeout, FunctionTimedOut

EXPERIMENTS = []
SCHEDULED_EXPERIMENTS = {}
PENDING_JOBS = 0
PENDING_WORKERS = 0
LAST_REBOOT_TIME = 0
ALL_DEVICES = []
FNULL = open(os.devnull, "w")
LOG_FILE = stdout
CURSES = None
CURSES_LOGS = None
CURSES_LOGS_LOCK = Lock()
LOGS_LOCK = Lock()

def log(str, end="\n"):
    global LOG_FILE, CURSES_LOGS, LOGS_LOCK
    if LOGS_LOCK.acquire(timeout=2):
        LOG_FILE.write(ctime()+"\t"+str+end)
        LOG_FILE.flush()
        LOGS_LOCK.release()
    if CURSES:
        CURSES_LOGS.append(str)
        write_curses_logs()
    elif LOG_FILE.name != "<stdout>":
        print(ctime()+"\t"+str, end=end)

def write_curses_logs():
    global CURSES_LOGS, CURSES_LOGS_LOCK
    if not CURSES_LOGS:
        return
    if CURSES_LOGS_LOCK.acquire(timeout=2):
        for i in range(min(len(CURSES_LOGS), CURSES.maxHeight()-5)):
            CURSES.add_text(1,CURSES.maxWidth(),6+i,text="#\t{}".format(CURSES_LOGS[i]))
        CURSES_LOGS_LOCK.release()


def brokenBarrierExceptionHook(exception_type, exception, traceback):
    if (exception_type is BrokenBarrierError):
        pass
    else:
        log("%s: %s" % (exception_type.__name__, exception))

sys.excepthook = brokenBarrierExceptionHook

def ping(hostname):
    response = os.system("ping -c 1 %s >/dev/null 2>&1" % hostname)
    if response == 0:
        return True
    else:
        return False

def pingWait(hostname):
    while(not ping(hostname)):
        sleep(2)

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

def barrierWithTimeout(barrier, timeout=None, experiment=None, show_error=True, device=None, *skip_barriers):
    if experiment is not None:
        if not experiment.isOK():
            skipBarriers(experiment, show_error, device, *skip_barriers)
            return False
    if (barrier.broken):
        skipBarriers(experiment, show_error, device, *skip_barriers)
        return False
    try:
        if timeout is not None:
            barrier.wait(timeout=timeout)
        else:
            barrier.wait(timeout=2400) # 40mins max timeout overall
    except Exception as barrier_exception:
        skipBarriers(experiment, show_error, device, *skip_barriers)
        return False
    return True

def skipBarriers(experiment, show_error=True, device=None, *skip_barriers):
    if experiment:
        experiment.setFail()
    for barrier in skip_barriers:
        try:
            barrier.abort()
        except:
            None
        if show_error:
            log("INFO\tSKIP_BARRIER\t{}".format(device))

def getDeviceIp(device):
    for n in range(5):
        worker_ip = adb.getDeviceIp(device)
        return worker_ip if worker_ip is not None else sleep(5)
    return None

def experimentRebootDevice(device, device_random, max_sleep_random=10, retries=3):
    global LAST_REBOOT_TIME
    while True:
        sleep_duration = device_random.randint(0,max_sleep_random)
        sleep(sleep_duration)
        if (time()-LAST_REBOOT_TIME > 2):
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

# TODO: tentar matar pelo system:
# lsof -i tcp:50000 | grep "->device.host_name:50000"
# tcpkill
def destroyWorker(worker, device):
    try:
        log("STOP_WORKER\tSTART\t%s" % device.name)
        worker.destroy()
        adb.stopAll(device)
        log("STOP_WORKER\tCOMPLETE\t%s" % device.name)
    except:
        log("STOP_WORKER\tERROR\t%s" % device.name)

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
    if experiment.reboot and not device.already_rebooted:
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
    device.already_rebooted = False
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
    worker = None
    error = False
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
    except FunctionTimedOut:
        log("Error Starting Worker %s\t[FUNCTION_TIMED_OUT]" % device.name)
        error = True
    except Exception:
        log("Error Starting Worker %s" % device.name)
        error = True
    if error:
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        if worker is not None:
            destroyWorker(worker, device)
        return
    if experiment.settings:
        worker.setSettings(experiment.settings)
    try:
        schedulers = worker.listSchedulers()
        if is_worker:
            models = worker.listModels()
    except FunctionTimedOut:
        log("ERROR_GETTING_MODELS_OR_SCHEDULERS\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        destroyWorker(worker, device)
        return
    if (schedulers is None):# or models is None):
        log("ERROR_GETTING_MODELS_OR_SCHEDULERS\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        destroyWorker(worker, device)
        return
    for scheduler in schedulers.scheduler:
        if scheduler.name == experiment.scheduler and experiment.isOK():
            if (worker.setScheduler(scheduler) is None):
                log("Failed to setScheduler on %s" % device.name)
                skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                experiment.deviceFail(device.name)
                destroyWorker(worker, device)
                return
            break
    if is_worker:
        for model in models.models:
            if model.name == experiment.model and experiment.isOK():
                if (worker.setModel(model) is None):
                    log("Failed to setModel on %s" % device.name)
                    skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                    experiment.deviceFail(device.name)
                    destroyWorker(worker, device)
                    return
                break
    log("WAIT_ON_BARRIER\tBOOT_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(boot_barrier, 200*experiment.devices, experiment, True, device.name, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
        log("BROKEN_BARRIER\tBOOT_BARRIER\t%s" % device.name)
        destroyWorker(worker, device)
        return
    if is_worker and experiment.calibration:
        calibrateWorkerThread(worker, worker_seed, device)
    log("WAIT_ON_BARRIER\tSTART_BARRIER\t%s" % device.name)
    barrierWithTimeout(start_barrier)
    i = 0
    while (i < (len(job_intervals) - 1)  and experiment.isOK() and is_producer):
        log("NEXT_EVENT_IN\t{}".format(job_intervals[i]))
        sleep(job_intervals[i])
        Thread(target = createJob, args = (worker,asset_list[i])).start()
        i = i+1
    log("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(complete_barrier, experiment.duration+experiment.timeout+240 + (0 if is_producer else experiment.duration), experiment, True, device.name, log_pull_barrier, finish_barrier):
        log("BROKEN_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
        destroyWorker(worker, device)
        return
    adb.screenOff(device)
    log("WAIT_ON_BARRIER\tLOG_PULL_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(log_pull_barrier, 30, experiment, True, device.name, finish_barrier):
        log("BROKEN_BARRIER\tLOG_PULL_BARRIER\t%s" % device.name)
        destroyWorker(worker, device)
        return
    try:
        if (experiment.isOK()):
            log("PULLING_LOG\t%s\tLOG" % device.name)
            adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % experiment.name, destination='logs/experiment/%s/%d/%d/%s.csv' % (experiment.name, repetition, seed_repeat, device.name), device=device)
            log("PULLING_LOG\t%s\tLOG\tOK" % device.name)
    except:
        log("PULLING_LOG\t%s\tLOG\tERROR" % device.name)
        experiment.setFail()
        experiment.deviceFail(device.name)
    try:
        log("PULLING_LOG\t%s\tSYS_LOG" % device.name)
        system_log_path = "logs/sys/%s/%d/%d/" % (experiment.name, repetition, seed_repeat)
        os.makedirs(system_log_path, exist_ok=True)
        adb.pullSystemLog(device, system_log_path)
        log("PULLING_LOG\t%s\tSYS_LOG\tOK" % device.name)
    except:
        log("PULLING_LOG\t%s\tSYS_LOG\tERROR" % device.name)
        experiment.deviceFail(device.name)
    log("CHECKING_LOG\t%s" % device.name)
    log_available = False
    for entry in os.listdir('logs/experiment/%s/%d/%d/' % (experiment.name, repetition, seed_repeat)):
        if entry == '%s.csv' % device.name:
            log("CHECKING_LOG\t%s\tOK" % device.name)
            log_available = True
            break
    if not log_available:
        log("CHECKING_LOG\t%s\tFAILED" % device.name)
        experiment.setFail()
        experiment.deviceFail(device.name)
    destroyWorker(worker, device)
    log("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % device.name)
    barrierWithTimeout(finish_barrier)
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
    global PENDING_JOBS, ALL_DEVICES, ASSETS, CURSES

    if CURSES:
        CURSES.add_text(1,200,3,text="EXPERIMENT: {}".format(experiment.name))
        CURSES.add_text(1,200,4,text="PROGRESS:")
        progressBar_0 = CURSES.add_progress_bar(1,60,4,10)
        progressBar_0.updateProgress(0)

    logExperiment(LOG_FILE, experiment)
    experiment_random = random.Random()
    experiment_random.seed(experiment.seed)
    cleanLogs("logs/experiment/%s/" % experiment.name)
    cleanLogs("logs/sys/%s/" % experiment.name)
    ASSETS=os.listdir(experiment.assets)

    #devices = ALL_DEVICES
    devices = getNeededDevicesAvailable(experiment, ALL_DEVICES)
    if (len(devices) < experiment.devices):
        os.system("touch logs/experiment/%s/not_enough_devices_CANCELED"  % experiment.name)
        return

    conf = open("logs/experiment/%s/conf.cfg" % experiment.name, "w+")
    logExperiment(conf, experiment)
    conf.close()

    killLocalCloudlet()
    stopClouds(experiment)

    reboot_barrier_size = 1
    for device in devices:
        if not device.already_rebooted:
            reboot_barrier_size += 1
    reboot_barrier = Barrier(reboot_barrier_size)
    for device in devices:
        if not device.already_rebooted:
            Thread(target=rebootDevice, args=(device,), kwargs={'reboot_barrier':reboot_barrier, 'screenOff':True}).start()
            sleep(2)
    barrierWithTimeout(reboot_barrier, timeout=360, show_error=True, device="MAIN")

    for repetition in range(experiment.repetitions):
        log("=========================\tREPETITION {}\t========================".format(repetition))
        os.makedirs("logs/experiment/%s/%d/" % (experiment.name, repetition), exist_ok=True)
        devices.sort(key=lambda e: e.name, reverse=False)
        experiment_random.shuffle(devices)

        for seed_repeat in range(experiment.repeat_seed):
            if CURSES:
                progressBar_0.updateProgress(int(100*(seed_repeat/experiment.repeat_seed)))
            repeat_tries = 0
            while (True):
                if repeat_tries > 3:
                    os.system("touch logs/experiment/%s/too_many_repeat_retries_CANCELED"  % experiment.name)
                    return
                log("=========================\tSEED_REPEAT {} | ATTEMPT {}\t========================".format(seed_repeat, repeat_tries))
                timeout = False
                experiment.setOK()
                stopClouds(experiment)

                experiment_devices = getNeededDevicesAvailable(experiment, devices)
                if experiment_devices == []:
                    os.system("touch logs/experiment/%s/not_enough_devices_CANCELED"  % experiment.name)
                    log("=========================\tEXPERIMET_FAILED_NOT_ENOUGHT_DEVICES\t{}\t========================".format(experiment.name))
                    return

                # Descartar os dispositivos que mais falharam durante esta experiencia, sempre que possivel.
                failed_devices = []
                failed_devices_map = experiment.getFailedDevices()
                for key in failed_devices_map:
                    failed_devices.append(key)
                failed_devices.sort(key=lambda e: failed_devices_map[e], reverse=True)
                for failed_device in failed_devices[:max(len(experiment_devices)-experiment.devices, 0)]:
                    for dev in experiment_devices:
                        if dev.name == failed_device:
                            experiment_devices.remove(dev)

                os.makedirs("logs/experiment/%s/%d/%d/" % (experiment.name, repetition, seed_repeat), exist_ok=True)
                boot_barrier = Barrier(experiment.devices + 1)
                start_barrier = Barrier(experiment.devices + 1)
                complete_barrier = Barrier(experiment.devices + 1)
                log_pull_barrier = Barrier(experiment.devices + 1)
                finish_barrier = Barrier(experiment.devices + len(experiment.cloudlets) + len(experiment.clouds) + 1)
                servers_finish_barrier = Barrier(len(experiment.cloudlets) + len(experiment.clouds) + 1)

                startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                producers = experiment.producers
                workers = experiment.workers
                i = 0
                for device in experiment_devices[:experiment.devices]:
                    Thread(target = startWorkerThread, args = (experiment, "seed_{}".format(i),repetition, seed_repeat, (producers > 0), (experiment.start_worker and (workers > 0)), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)).start()
                    producers -= 1 # Os primeiros n devices é que produzem conteudo
                    workers -= 1 # Os primeiros n devices é que são workers
                    i += 1
                startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                log("WAIT_ON_BARRIER\tBOOT_BARRIER\tMAIN")
                if not barrierWithTimeout(boot_barrier, 200*experiment.devices, experiment, True, "MAIN"): # 15m
                    log("BROKEN_BARRIER\tBOOT_BARRIER\tMAIN")
                sleep(1)
                log("WAIT_ON_BARRIER\tSTART_BARRIER\tMAIN")
                if not barrierWithTimeout(start_barrier, 60, experiment, True, "MAIN"):
                    log("BROKEN_BARRIER\tSTART_BARRIER\tMAIN")

                completetion_timeout_start = time()
                i=0
                while (PENDING_JOBS > 0 and experiment.isOK()) or (experiment.duration > time()-completetion_timeout_start and experiment.isOK()):
                    sleep(2)
                    if (i % 20) == 0:
                        log("CURRENT_EXPERIMENT_DURATION\t{}s".format(time()-completetion_timeout_start))
                    if (time()-completetion_timeout_start > experiment.duration+experiment.timeout):
                        log("COMPLETION_TIMEOUT_EXCEDED")
                        os.system("touch logs/experiment/%s/%d/%d/completion_timeout_exceded"  % (experiment.name, repetition, seed_repeat))
                        break
                    i+=1
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
            if CURSES:
                progressBar_0.updateProgress(int(100*((seed_repeat+1)/experiment.repeat_seed)))


        if (repetition != experiment.repetitions - 1):
            log("Waiting 5s for next repetition")
            sleep(5)

def getNeededDevicesAvailable(experiment, devices, retries=5):
    if retries < 0:
        experiment.setFail()
        os.system("touch logs/experiment/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
        return []
    to_charge = []
    good_to_use = []
    for device in devices:
        device.battery_level = getBatteryLevel(device)
        if device.battery_level >= experiment.min_battery:
            good_to_use.append(device)
        else:
            to_charge.append(device)
    if len(good_to_use) >= experiment.devices:
        good_to_use.sort(key=lambda d: d.battery_level, reverse=True) #Return sorted by most battery
        return good_to_use
    else:
        discoverable_devices = adb.listDevices(0)
        good_to_charge = []
        for device in to_charge:
            for disc_device in discoverable_devices:
                if disc_device.name == device.name or disc_device.ip == device.ip:
                    good_to_charge.append(device)
        if len(good_to_use) + len(good_to_charge) < experiment.devices:
            experiment.setFail()
            os.system("touch logs/experiment/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
            return []
        battery_barrier = Barrier(experiment.devices - len(good_to_use) + 1)
        for device in good_to_charge:
            Thread(target = chargeDevice, args = (experiment.min_battery, device, battery_barrier)).start()
        barrierWithTimeout(battery_barrier, 3600, show_error=False)
        return getNeededDevicesAvailable(experiment, devices, retries-1)

def rebootDevice(device, retries=3, reboot_barrier=None, screenOff=False):
    if retries < 0:
        log("REBOOT_DEVICE_FAIL\t%s" % device.name)
        if reboot_barrier is not None:
            skipBarriers(None, True, device.name, reboot_barrier)
        return False
    log("REBOOT_DEVICE\t%s" % device.name)
    pre_reboot_worker_ip = getDeviceIp(device)
    if adb.rebootAndWait(device, timeout=180):
        log("REBOOT_DEVICE_COMPLETE\t%s" % device.name)
        if screenOff:
            adb.screenOff(device)
        if reboot_barrier is not None:
            barrierWithTimeout(reboot_barrier, show_error=True, device=device.name)
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
    battery_level = getBatteryLevel(device)
    while (not battery_barrier.broken and (battery_level < max(0, min(100, min_battery)))):
        if (counter % 5 == 0):
            log("CHARGING_DEVICE {} ({}%)".format(device.name, battery_level))
        sleep(120)
        battery_level = getBatteryLevel(device)
        counter += 1
    barrierWithTimeout(battery_barrier, 3600, show_error=False)

def startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloudlet_boot_barrier = Barrier(len(experiment.cloudlets) + 1)
    i = 0
    for cloudlet in experiment.cloudlets:
        Thread(target = startCloudletThread, args = (cloudlet, experiment, "cloudlet_seed_{}".format(i), repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier)).start()
        i += 1
    barrierWithTimeout(cloudlet_boot_barrier, 600, experiment, True, "START_CLOUDLETS", servers_finish_barrier, finish_barrier)

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
    cloudlet_instance.stop()
    cloudlet_instance.connectLauncherService()
    cloudlet_instance.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    cloudlet_instance.startWorker()
    sleep(1)
    cloudlet_instance.connectBrokerService()
    sleep(1)
    if experiment.settings or experiment.mcast_interface:
        cloudlet_instance.setSettings(experiment.settings, experiment.mcast_interface, advertise_worker=True)
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
    barrierWithTimeout(cloudlet_boot_barrier, 600, experiment, True, cloudlet, servers_finish_barrier, finish_barrier) #inform startCloudlets that you have booted
    if (experiment.calibration):
        calibrateWorkerThread(cloudlet_instance, cloudlet_seed, asset_id="%s.jpg" % experiment.asset_quality)
    barrierWithTimeout(servers_finish_barrier) #wait experiment completion to init shutdown
    cloudlet_instance.stop()
    cloudlet_control.stop()
    barrierWithTimeout(finish_barrier)

def pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat):
    log_name = "%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat)
    for cloud in experiment.clouds:
        if (cloud.zone == 'localhost'):
            os.system("cp %s/ODCloud/logs/%s logs/experiment/%s/%s/%s/cloudlet_%s.csv" % (os.environ['HOME'], log_name, experiment.name, repetition, seed_repeat, cloud.address))
        else:
            os.system("scp joaquim@%s:~/ODCloud/logs/%s logs/experiment/%s/%s/%s/%s_%s.csv" % (cloud.address, log_name, experiment.name, repetition, seed_repeat, cloud.instance, cloud.zone))
    for cloudlet in experiment.cloudlets:
        if (cloudlet == '127.0.0.1'):
            os.system("cp %s/ODCloud/logs/%s logs/experiment/%s/%s/%s/cloudlet_%s.csv" % (os.environ['HOME'], log_name, experiment.name, repetition, seed_repeat, cloudlet))
        else:
            os.system("scp joaquim@%s:~/ODCloud/logs/%s logs/experiment//%s/%s/%s/cloudlet_%s.csv" % (cloudlet, log_name, experiment.name, repetition, seed_repeat, cloudlet))

def startCloudThread(cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier):
    log("START_CLOUD_INSTANCE\t{}\t({})".format(cloud.instance, cloud.address))
    stdout.flush()
    if (not experiment.isOK()):
        skipBarriers(experiment, True, cloud.address, cloud_boot_barrier, servers_finish_barrier, finish_barrier)
        return
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
    sleep(1)
    cloud_instance.connectBrokerService()
    sleep(1)
    if experiment.settings:
        cloud_instance.setSettings(experiment.settings)
    sleep(1)
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
    barrierWithTimeout(cloud_boot_barrier, 600, experiment, True, cloud.instance, servers_finish_barrier, finish_barrier)
    if (experiment.calibration):
        calibrateWorkerThread(cloud_instance, "cloud_{}".format(cloud.address), asset_id="%s.jpg" % experiment.asset_quality)
    log("WAIT_ON_BARRIER\tSERVER_FINISH_BARRIER\t%s" % cloud.instance)
    barrierWithTimeout(servers_finish_barrier)
    log("Stopping %s Cloud Instance" % cloud.instance)
    cloud_instance.stop()
    cloud_control.stop()
    log("STOPPING_CLOUD_INSTANCE\t{}\t({})".format(cloud.instance, cloud.address))
    if (not experiment.isOK()):
        skipBarriers(experiment, True, cloud_instance, finish_barrier)
        return
    adb.cloudInstanceStop(cloud.instance, cloud.zone)
    log("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % cloud.instance)
    barrierWithTimeout(finish_barrier)
    log("CLOUD_FINISHED\t%s" % cloud.instance)


def startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloud_boot_barrier = Barrier(len(experiment.clouds) + 1)
    for cloud in experiment.clouds:
        if (cloud.zone == "localhost"):
            Thread(target = startCloudletThread, args = (cloud.address, experiment, "cloudlet_seed_{}".format(cloud.address), repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier)).start()
        else:
            Thread(target = startCloudThread, args = (cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier)).start()
    barrierWithTimeout(cloud_boot_barrier, 600, experiment, True, "START_CLOUDS", servers_finish_barrier, finish_barrier)
    if len(experiment.clouds) > 0:
        log("CLOUDS_BOOTED\tWAIT_5S_FOR_DEVICE_TO_FIND_THEM_ACTIVE")
        sleep(5)

def stopClouds(experiment):
    for cloud in experiment.clouds:
        if (cloud.zone == "localhost"):
            continue
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
    current_repetition = 0
    producers = 0
    repeat_seed = 1
    current_seed_repeat = 0
    timeout = 1500 # 25 Mins
    start_worker = True
    workers = -1
    assets = "assets/sd/"
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
        self.settings["ADVERTISE_WORKER_STATUS"] = "true"

    def setFail(self):
        self._running_status = False

    def setOK(self):
        self._running_status = True

    def isOK(self):
        return self._running_status

    def deviceFail(self, device):
        if device in self._failed_devices:
            self._failed_devices[device] += 1
        else:
            self._failed_devices[device] = 0

    def getFailedDevices(self):
        return self._failed_devices


def readConfig(confName):
    global EXPERIMENTS, SCHEDULED_EXPERIMENTS
    config = configparser.ConfigParser()
    config.read(confName)
    for section in config.sections():
        startTime = None
        endTime = None
        experiment = Experiment(section)
        for option in config.options(section):
            if option == "strategy":
                experiment.scheduler = config[section][option]
            elif option == "model":
                experiment.model = config[section][option]
            elif option == "devices":
                experiment.devices = int(config[section][option])
            elif option == "rebootdevices":
                experiment.reboot = config[section][option].lower() == "true"
            elif option == "generationraterequests":
                experiment.request_rate = int(config[section][option])
            elif option == "generationrateseconds":
                experiment.request_time = int(config[section][option])
                if (experiment.request_time == 0): experiment.request_time = 1
            elif option == "duration":
                experiment.duration = int(config[section][option])
            elif option == "clouds":
                clouds = []
                cloud_settings = ""
                for entry in config[section][option].split(','):
                    cloud_zone_address = entry.split("/")
                    clouds.append(grpcControls.Cloud(cloud_zone_address[0], cloud_zone_address[1], cloud_zone_address[2]))
                    experiment.clouds = clouds
                    cloud_settings += "{}/".format(cloud_zone_address[2])
                if (cloud_settings != ""):
                    experiment.settings["CLOUD_IP"] = cloud_settings.rstrip("/")
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
                experiment.start_worker = config[section][option].lower() == "true"
            elif option == "workers":
                experiment.workers = int(config[section][option])
            elif option == "assets":
                experiment.assets = config[section][option]
            elif option == "assettype":
                experiment.asset_type = config[section][option]
            elif option == "calibration":
                experiment.calibration = config[section][option].lower() == "true"
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
            elif option == "runbetween":
                try:
                    times = config[section][option].split("-")
                    startTime = int(times[0])
                    endTime = int(times[1])
                except:
                    None
        if (experiment.producers == 0 or experiment.producers > experiment.devices):
            experiment.producers = experiment.devices
        if (experiment.workers == -1 or experiment.workers > experiment.devices):
            experiment.workers = experiment.devices
        if startTime is None or endTime is None:
            log("ADDED_EXPERIMENT\t{}".format(experiment.name))
            EXPERIMENTS.append(experiment)
        else:
            log("ADDED_SCHEDULED_EXPERIMENT\t{}".format(experiment.name))
            SCHEDULED_EXPERIMENTS[experiment] = (startTime, endTime)

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
                    RunBetween              = Define the experiment run interval (hour - hour)

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
                    [*] workerStatusUpdateInterval     default 5000 (5s)  LOCAL WORKER INFO UPDATE DELAY
                    [*] AUTO_STATUS_UPDATE_INTERVAL_MS  default 5000 (5s) PROACTIVE REQUEST FOR WORKER DETAILS
                    RTTDelayMillisFailRetry
                    RTTDelayMillisFailAttempts
                    DEVICE_ID
                    [*] BANDWIDTH_ESTIMATE_TYPE: [ACTIVE/PASSIVE/ALL]
                    MCAST_INTERFACE
                    BANDWIDTH_ESTIMATE_CALC_METHOD      [mean/median]  default: mean
                    [*] ADVERTISE_WORKER_STATUS: [true/false] default: true ENABLES DEVICE ADVERTISMENT Use when want LOCAL + CLOUDLET
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
    global ALL_DEVICES, LOG_FILE, EXPERIMENTS, SCHEDULED_EXPERIMENTS, CURSES, DEBUG, ADB_DEBUG_FILE, ADB_LOGS_LOCK, GRPC_DEBUG_FILE, GRPC_LOGS_LOCK, CURSES_LOGS

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-c', '--configs', default=[], nargs='+', required=False)
    argparser.add_argument('--show-help', default=False, action='store_true', required=False)
    argparser.add_argument('-i', '--install', default=False, action='store_true', required=False)
    argparser.add_argument('-da', '--debug-adb', default=False, action='store_true', required=False)
    argparser.add_argument('-al', '--adb-log-level', action='store', required=False, help="ALL / ACTION / COMMAND")
    argparser.add_argument('-dg', '--debug-grpc', default=False, action='store_true', required=False)
    argparser.add_argument('-p', '--use-stdout', default=False, action='store_true', required=False)
    argparser.add_argument('-nc', '--use-curses', default=False, action='store_true', required=False)
    argparser.add_argument('-ip', '--ip-mask', action='store', required=False)
    argparser.add_argument('-r', '--reboot-devices', default=False, action='store_true', required=False)

    args = argparser.parse_args()

    now = datetime.now()
    experiment_name = "exp_{}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
    os.makedirs("logs/workbench/{}".format(experiment_name))
    completed_experiments = open("logs/workbench/{}/completed".format(experiment_name), "w")
    in_progress_experiments = open("logs/workbench/{}/in_progress".format(experiment_name), "w")
    missing_experiments = open("logs/workbench/{}/missing".format(experiment_name), "w")
    new_experiments = "logs/workbench/{}/new_experiments/".format(experiment_name)
    loaded_experiments = "logs/workbench/{}/loaded_experiments/".format(experiment_name)
    os.makedirs(new_experiments)
    os.makedirs(loaded_experiments)

    log("Starting... Please wait")

    if not args.use_stdout:
        LOG_FILE = open("logs/workbench/{}/output.log".format(experiment_name), "w")

    log("Searching for devices...")
    if args.debug_adb:
        adb.DEBUG = True
        adb.ADB_DEBUG_FILE = LOG_FILE
        adb.ADB_LOGS_LOCK = LOGS_LOCK
        if args.adb_log_level in ["ALL", "ACTION", "COMMAND"]:
            adb.LOG_LEVEL = args.adb_log_level
        else:
            if args.adb_log_level is not None:
                print("# WARNING: Invalid log level ({}). Logging ALL".format(args.adb_log_level))
                adb.LOG_LEVEL = "ALL"
    if args.ip_mask:
        ALL_DEVICES = adb.listDevices(0, True, ip_mask=args.ip_mask)
    else:
        ALL_DEVICES = adb.listDevices(0, True)
    if args.show_help:
        help()
        return
    if args.install:
        log('INSTALLING_APKS')
        for device in ALL_DEVICES:
            adb.uninstallPackage(device)
            log('PACKAGE_UNINSTALLED\t%s' % device.name)
            adb.pushFile('apps', 'ODLauncher-release.apk', path='', device=device)
            log('PACKAGE_PUSHED\t%s' % device.name)
            adb.pmInstallPackage('apps', 'ODLauncher-release.apk', device)
            log('PACKAGE_INSTALLED\t%s' % device.name)
    if args.debug_grpc:
        grpcControls.DEBUG = True
        grpcControls.GRPC_DEBUG_FILE = LOG_FILE
        grpcControls.GRPC_LOGS_LOCK = LOGS_LOCK
    log("============\tDEVICES\t============")
    for device in ALL_DEVICES:
        log("{} ({})".format(device.name, device.ip))
    log("===================================")
    for device in ALL_DEVICES:
        adb.screenOff(device)
        if not adb.checkPackageInstalled(device):
            log('PACKAGE_MISSING\t%s' % device.name)
            log('CLEANING_SYSTEM\t%s' % device.name)
            adb.uninstallPackage(device)
            log('PUSHING_PACKAGE\t%s' % device.name)
            adb.pushFile('apps', 'ODLauncher-release.apk', path='', device=device)
            log('INSTALLING_PACKAGE\t%s' % device.name)
            adb.pmInstallPackage('apps', 'ODLauncher-release.apk', device)
            log('PACKAGE_INSTALLED\t%s' % device.name)
        if args.reboot_devices:
            adb.rebootAndWait(device)
    for cfg in args.configs:
        readConfig(cfg)
        shutil.copy(cfg, "{}/{}.loaded".format(loaded_experiments,cfg.split("/")[-1]))
    EXPERIMENTS.sort(key=lambda e: e.devices+e.producers-e.request_time+len(e.cloudlets), reverse=False)

    if args.use_curses and not args.use_stdout:
        CURSES = draw_curses()
        complete_progress = CURSES.add_text(1,60,0,text="LOGS: {}".format(experiment_name))
        CURSES_LOGS = deque(maxlen=max(0, CURSES.maxHeight()-5))
        CURSES.add_text(1,10,2,text="PROGRESS:")
        progressBar_0 = CURSES.add_progress_bar(1,60,2,10)
        progressBar_0.updateProgress(0)
        complete_progress = CURSES.add_text(1,15,1)

    i = 0
    while i < len(EXPERIMENTS) or len(SCHEDULED_EXPERIMENTS) > 0:
        run_scheduled = False
        next_experiment = None
        for e,t in SCHEDULED_EXPERIMENTS.items():
            if (t[0] <= gmtime().tm_hour and t[1] >= gmtime().tm_hour and t[1] >= t[0]) or (t[1] < t[0] and (t[0] <= gmtime().tm_hour or t[1] >= gmtime().tm_hour)):
                run_scheduled = True
                next_experiment = e
                SCHEDULED_EXPERIMENTS.pop(e, None)
                break
        missing_experiments.truncate(0)
        if not run_scheduled:
            next_experiment = EXPERIMENTS[i]
            for e in EXPERIMENTS[i+1:]:
                missing_experiments.write(e.name+"\n")
        else:
            for e in EXPERIMENTS[i:]:
                missing_experiments.write(e.name+"\n")
        for e,t in SCHEDULED_EXPERIMENTS.items():
            missing_experiments.write(e.name+"\t({} - {})\n".format(t[0], t[1]))
        missing_experiments.flush()
        in_progress_experiments.write(next_experiment.name+"\n")
        in_progress_experiments.flush()
        if args.use_curses:
            progressBar_0.updateProgress(100*(i/max(len(EXPERIMENTS), 1)))
            complete_progress.updateText("COMPLETE {}/{}".format(i,len(EXPERIMENTS)))
            sleep(2)
        runExperiment(next_experiment)
        in_progress_experiments.truncate(0)
        completed_experiments.write(next_experiment.name+"\n")
        completed_experiments.flush()
        for file in os.listdir(new_experiments):
            if os.path.isfile("{}/{}".format(new_experiments,file)):
                readConfig("{}/{}".format(new_experiments,file))
                shutil.move("{}/{}".format(new_experiments,file), "{}/{}.loaded".format(loaded_experiments,file))
        if not run_scheduled:
            i += 1
    if args.use_curses:
        progressBar_0.updateProgress(100)
        complete_progress.updateText("")


if __name__ == '__main__':
    main()
