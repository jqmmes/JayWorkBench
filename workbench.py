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
import socket
import struct
import subprocess
from datetime import datetime
import argparse
from collections import deque
from func_timeout import func_timeout, FunctionTimedOut, func_set_timeout
from meross_iot.manager import MerossManager
from meross_iot.http_api import MerossHttpClient
import json


EXPERIMENTS = []
SCHEDULED_EXPERIMENTS = {}
PENDING_TASKS = 0
PENDING_TASKS_LOCK = Lock()
PENDING_TASKS_WORKER = {}
PENDING_WORKERS = 0
LAST_REBOOT_TIME = 0
ALL_DEVICES = []
DEVICE_BLACKLIST = []
FNULL = open(os.devnull, "w")
LOG_FILE = stdout
CURSES = None
CURSES_LOGS = None
CURSES_LOGS_LOCK = Lock()
LOGS_LOCK = Lock()
REBOOT_ON_RUN_EXPERIMENT = False
USE_SMART_PLUGS = False
SCREEN_BRIGHTNESS = 0
LOG_PULL_LOCK = Lock()
SYS_LOG_PULL_LOCK = Lock()
LOG_PULL_SCREEN_ON_FLAG = True
LOG_PULL_SCREEN_ON_LOCK = Lock()
TAP_TO_KEEP_SCREEN_ON_FLAG = True
TAP_TO_KEEP_SCREEN_INTERVAL_SECONDS = 120
PLUGS = []
IDLE_BENCHMARK = False
IDLE_BENCHMARK_DURATION = 1200 # 20mins
LAST_RECEIVED_TASK_COMPLETION = None


async def merros_init():
    user_info = json.loads(open("meross.json", "r").read())
    merross_http_manager = http_api_client = await MerossHttpClient.async_from_user_password(email=user_info["user"], password=user_info["pass"])
    manager = MerossManager(merross_http_manager)
    manager.start()

def readIFTTTKey():
    try:
        return open("ifttt.key", "r").read().strip("\n")
    except:
        return ""

def power_on(smart_plug="SHP7"):
    ifttt_key = readIFTTTKey()
    if (ifttt_key == ""):
        return False
    subprocess.run(['curl', "https://maker.ifttt.com/trigger/Turn%20" + smart_plug + "%20on/with/key/"+ifttt_key], stdout=subprocess.PIPE, stderr=FNULL)
    return True

def power_off(smart_plug="SHP7", checkPlug=True, retries=5):
    global ALL_DEVICES
    ifttt_key = readIFTTTKey()
    if (ifttt_key == ""):
        return False
    subprocess.run(['curl', "https://maker.ifttt.com/trigger/Turn%20" + smart_plug + "%20off/with/key/"+ifttt_key], stdout=subprocess.PIPE, stderr=FNULL)
    if checkPlug:
        sleep(2)
        if adb.isCharging(random.choice(ALL_DEVICES)) and retries > 0:
            log("POWER_OFF_FAILED_RETRYING")
            sleep(2)
            return power_off(smart_plug, checkPlug, retries - 1)
    return True

@func_set_timeout(1)
def write_to_file(f, str, end, show_date=True):
    if show_date:
        f.write(ctime()+"\t"+str+end)
    else:
        f.write(str+end)
    f.flush()

def log(str, end="\n", show_date=True):
    global LOG_FILE, CURSES_LOGS, LOGS_LOCK
    try:
        write_to_file(LOG_FILE,str,end,show_date)
    except:
        pass
    if CURSES:
        CURSES_LOGS.append(str)
        write_curses_logs()
    elif LOG_FILE.name != "<stdout>":
        if show_date:
            print(ctime()+"\t"+str, end=end)
        else:
            print(str, end=end)

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

def createTask(worker, asset_id, deadline=None):
    global PENDING_TASKS, PENDING_TASKS_LOCK, PENDING_TASKS_WORKER
    PENDING_TASKS_LOCK.acquire()
    PENDING_TASKS += 1
    if worker.name not in PENDING_TASKS_WORKER.keys():
        PENDING_TASKS_WORKER[worker.name] = 0
    PENDING_TASKS_WORKER[worker.name] += 1
    PENDING_TASKS_LOCK.release()
    log("{}\t{}\tTASK_SUBMIT\t{}\t{}".format(time(), asset_id, worker.name, PENDING_TASKS_WORKER[worker.name]))
    try:
        if not worker.createTask(asset_id, deadline):
            log("{}\t{}\tTASK_FAILED\tFAILED_SCHEDULE\t{}\t{}".format(time(), asset_id, worker.name, PENDING_TASKS_WORKER[worker.name] - 1))
        else:
            log("{}\t{}\tTASK_COMPLETE\t{}\t{}".format(time(), asset_id, worker.name, PENDING_TASKS_WORKER[worker.name] - 1))
    except Exception as task_exception:
        log("{}\t{}\tTASK_FAILED\t{}TASK_EXCEPTION\t{}\t{}".format(time(), asset_id, worker.name, PENDING_TASKS_WORKER[worker.name] - 1))
    PENDING_TASKS_LOCK.acquire()
    PENDING_TASKS -= 1
    PENDING_TASKS_WORKER[worker.name] -= 1
    LAST_RECEIVED_TASK_COMPLETION = time()
    PENDING_TASKS_LOCK.release()

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

    log("{}\t{}\tTASK_SUBMIT\t{}\t{}".format(time(), "CALIBRATION_TASK", asset, worker.name))
    try:
        if not worker.calibrateWorker(asset):
            log("{}\t{}\tCALIBRATION_FAILED\tFAILED_CALIBRATION\t{}".format(time(), "CALIBRATION_TASK", worker.name))
        else:
            log("{}\t{}\tCALIBRATION_COMPLETE\t{}".format(time(), "CALIBRATION_TASK", worker.name))
    except Exception as task_exception:
        log("{}\t{}\tCALIBRATION_FAILED\t{}CALIBRATION_EXCEPTION\t{}".format(time(), "CALIBRATION_TASK", worker.name))

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
        if experiment.isOK():
            log("SKIP_BARRIERS\tEXPERIMENT_SET_FAIL")
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

def experimentRebootDevice(device, device_random, max_sleep_random=10, retries=2):
    global LAST_REBOOT_TIME, DEVICE_BLACKLIST
    while True:
        sleep_duration = device_random.randint(0,max_sleep_random)
        sleep(sleep_duration)
        if (time()-LAST_REBOOT_TIME > 2):
            LAST_REBOOT_TIME = time()
            log("REBOOT_WORKER\t%s" % device.name)
            pre_reboot_worker_ip = getDeviceIp(device)
            if adb.rebootAndWait(device, timeout=180):
                log("REBOOT_WORKER_COMPLETE\t%s" % device.name)
                if device.name in DEVICE_BLACKLIST:
                    DEVICE_BLACKLIST.remove(device.name)
                return True
            else:
                if (retries > 0):
                    log("REBOOT_WORKER_RETRY\t%s" % device.name)
                    return experimentRebootDevice(device, device_random, 10, retries - 1)
                else:
                    log("REBOOT_WORKER_FAIL\t%s" % device.name)
                    if device.name not in DEVICE_BLACKLIST:
                        DEVICE_BLACKLIST.append(device.name)
                    return False

def destroyWorker(worker, launcher, device):
    try:
        log("STOP_WORKER\tSTART\t%s" % device.name)
        worker.destroy()
        launcher.destroy()
        adb.stopAll(device)
        log("STOP_WORKER\tCOMPLETE\t%s" % device.name)
    except:
        log("STOP_WORKER\tERROR\t%s" % device.name)



def selectTaskExecutor(experiment, jay_instance, custom_task_executor=None):
    selected_task_executor = custom_task_executor if (custom_task_executor != None) else experiment.task_executor
    task_executors = jay_instance.listTaskExecutors()
    for task_executor in task_executors.taskExecutors:
        if task_executor.name == selected_task_executor:
            log("SELECTED TASK EXECUTOR \"{}\"\t{}".format(selected_task_executor, jay_instance.name))
            jay_instance.selectTaskExecutor(task_executor)
    sleep(1)

def setTaskExecutorSettings(experiment, jay_instance, custom_settings_map):
    if custom_settings_map is not None:
        jay_instance.setTaskExecutorSettings(custom_settings_map)
    elif experiment.task_executor_settings is not None:
        jay_instance.setTaskExecutorSettings(experiment.task_executor_settings)
    sleep(1)

def selectModel(experiment, jay_instance, custom_model):
    models = jay_instance.listModels()
    if (models is None):
        log("SELECT_MODEL\tEXPERIMENT_SET_FAIL")
        experiment.setFail()
    selected_model = custom_model if (custom_model != None) else experiment.model
    for model in models.models:
        if model.name == selected_model and experiment.isOK():
            if (jay_instance.setModel(model) is None):
                break
            log("SELECTED MODEL \"{}\"\t{}".format(selected_model, jay_instance.name))
            return True
    return False

def keepScreenOn(device=None):
    global TAP_TO_KEEP_SCREEN_ON_FLAG, TAP_TO_KEEP_SCREEN_INTERVAL_SECONDS
    sleep(TAP_TO_KEEP_SCREEN_INTERVAL_SECONDS)
    while TAP_TO_KEEP_SCREEN_ON_FLAG:
        log("TAP_SCREEN\t%s" % device.name)
        adb.tapScreen(device)
        sleep(TAP_TO_KEEP_SCREEN_INTERVAL_SECONDS)

def startWorkerThread(experiment, worker_seed, repetition, seed_repeat, is_producer, is_worker, device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier, custom_task_executor=None, custom_model=None, custom_settings_map=None):
    global PENDING_TASKS, PENDING_WORKERS, SCREEN_BRIGHTNESS, TAP_TO_KEEP_SCREEN_ON_FLAG, IDLE_BENCHMARK, IDLE_BENCHMARK_DURATION
    if (adb.freeSpace(device=device) < 1.0):
        log('LOW_SDCARD_SPACE\t%s' % device.name)
        installPackage(device)
    adb.connectWifiADB(device)
    log("START_DEVICE\t%s" % device.name)
    device_random = random.Random()
    device_random.seed(experiment.seed+worker_seed+str(repetition))
    rate = float(experiment.request_rate)/float(experiment.request_time)
    log('GENERATING_TASKS\tRATE: {}\t{}'.format(rate, device.name))
    task_intervals = []
    asset_list = []
    while(sum(task_intervals) < experiment.duration):
        task_intervals.append(device_random.expovariate(rate))
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
    adb.setBrightness(device, SCREEN_BRIGHTNESS)
    adb.clearSystemLog(device)
    log("STOP_ALL_SERVICE\t%s" % device.name)
    adb.stopAll(device)
    sleep(2)
    log("STARTING_LAUNCH_SERVICE\t%s" % device.name)
    if not adb.startApplication(device=device, wait=True):
        log("FAILED_LAUNCH_SERVICE\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        return
    droid_launcher = None
    jay_instance = None
    error = False
    for i in range(2):
        try:
            worker_ip = getDeviceIp(device)
            if (worker_ip is None and retries < 5):
                log("FAILED_OBTAIN_IP\t%s" % device.name)
                skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                experiment.deviceFail(device.name)
                adb.rebootAndWait(device)
                return
            log("STARTING_SERVICES\t%s" % device.name)
            droid_launcher = grpcControls.droidLauncher(worker_ip, device.name)
            jay_instance = grpcControls.jayClient(worker_ip, device.name)
            droid_launcher.connectLauncherService()
            droid_launcher.setLogName(experiment.name)
            log("CONECTED_TO_LAUNCHER\t%s" % device.name)
            sleep(10)
            if is_worker:
                droid_launcher.startWorker()
            droid_launcher.startScheduler()
            break
        except FunctionTimedOut:
            if i == 1:
                log("Error Starting Worker %s\t[FUNCTION_TIMED_OUT]" % device.name)
                error = True
        except Exception:
            if i == 1:
                log("Error Starting Worker %s" % device.name)
                error = True
    '''
    multicast_group = '224.0.0.1'
    server_address = (multicast_group, 50000)
    # Create the socket
    addrinfo = socket.getaddrinfo(multicast_group, None)[0]
    s = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 50000))
    group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
    if addrinfo[0] == socket.AF_INET: # IPv4
        mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    while True:
        print("waiting")
        data, sender = s.recvfrom(1500)
        while data[-1:] == '\0': data = data[:-1] # Strip trailing \0's
        print (str(sender) + '  ' + repr(data))
    '''
    try:
        forceScreenOnViaPower(device, experiment.power_devices)
        sleep(2)
    except:
        pass
    Thread(target=keepScreenOn, args=(device,)).start()

    jay_instance.connectBrokerService()
    sleep(2)
    '''except FunctionTimedOut:
       log("Error Starting Worker %s\t[FUNCTION_TIMED_OUT]" % device.name)
       error = True
    except Exception:
       log("Error Starting Worker %s" % device.name)
       error = True'''
    if error:
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        if jay_instance is not None:
            destroyWorker(jay_instance, droid_launcher, device)
        return

    jay_instance.setSettings(experiment.settings) if experiment.settings else None
    selectTaskExecutor(experiment, jay_instance, custom_task_executor) if is_worker else None
    setTaskExecutorSettings(experiment, jay_instance, custom_settings_map)

    try:
        schedulers = jay_instance.listSchedulers()
    except FunctionTimedOut:
        log("ERROR_GETTING_SCHEDULERS\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        destroyWorker(jay_instance, droid_launcher, device)
        return
    if (schedulers is None):
        log("ERROR_GETTING_MODELS_OR_SCHEDULERS\t%s" % device.name)
        skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
        experiment.deviceFail(device.name)
        destroyWorker(jay_instance, droid_launcher, device)
        return
    for scheduler in schedulers.scheduler:
        if scheduler.name == experiment.scheduler and experiment.isOK():
            if (jay_instance.setScheduler(scheduler) is None):
                log("Failed to setScheduler on %s" % device.name)
                skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
                experiment.deviceFail(device.name)
                destroyWorker(jay_instance, droid_launcher, device)
                return
            break
    if is_worker:
        if not selectModel(experiment, jay_instance, custom_model):
            log("Failed to setModel on %s" % device.name)
            skipBarriers(experiment, True, device.name, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)
            experiment.deviceFail(device.name)
            destroyWorker(jay_instance, droid_launcher, device)

    log("WAIT_ON_BARRIER\tBOOT_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(boot_barrier, 500*experiment.devices, experiment, True, device.name, start_barrier, complete_barrier, log_pull_barrier, finish_barrier):
        log("BROKEN_BARRIER\tBOOT_BARRIER\t%s" % device.name)
        destroyWorker(jay_instance, droid_launcher, device)
        return
    if is_worker and experiment.calibration:
        calibrateWorkerThread(jay_instance, worker_seed, device)
    log("WAIT_ON_BARRIER\tSTART_BARRIER\t%s" % device.name)
    barrierWithTimeout(start_barrier)

    if is_producer:
        if experiment.benchmark and len(asset_list) > 0:
            sleep(2)
            Thread(target = createTask, args = (jay_instance,asset_list[0],experiment.task_deadline)).start()
        else:
            i = 0
            while (i < (len(task_intervals) - 1)  and experiment.isOK() and not IDLE_BENCHMARK):
                log("NEXT_EVENT_IN\t{}".format(task_intervals[i]))
                sleep(task_intervals[i])
                if not experiment.isSequential() or PENDING_TASKS < 1:
                    Thread(target = createTask, args = (jay_instance,asset_list[i],experiment.task_deadline)).start()
                    i = i+1
    if experiment.benchmark:
        sleep(experiment.benchmark_duration)
    if (IDLE_BENCHMARK):
        sleep(IDLE_BENCHMARK_DURATION)
    log("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(complete_barrier, experiment.duration+experiment.timeout+240 + (0 if is_producer else experiment.duration), experiment, True, device.name, log_pull_barrier, finish_barrier):
        log("BROKEN_BARRIER\tCOMPLETE_BARRIER\t%s" % device.name)
        destroyWorker(jay_instance, droid_launcher, device)
        return
    TAP_TO_KEEP_SCREEN_ON_FLAG = False
    log("WAIT_ON_BARRIER\tLOG_PULL_BARRIER\t%s" % device.name)
    if not barrierWithTimeout(log_pull_barrier, 30, experiment, True, device.name, finish_barrier):
        log("BROKEN_BARRIER\tLOG_PULL_BARRIER\t%s" % device.name)
        destroyWorker(jay_instance, droid_launcher, device)
        return
    global LOG_PULL_SCREEN_ON_FLAG, LOG_PULL_SCREEN_ON_LOCK
    LOG_PULL_SCREEN_ON_LOCK.acquire()
    try:
        if LOG_PULL_SCREEN_ON_FLAG:
            forceScreenOnViaPower(device, experiment.power_devices)
            sleep(2)
            LOG_PULL_SCREEN_ON_FLAG = False
    finally:
        LOG_PULL_SCREEN_ON_LOCK.release()
    try:
        if (experiment.isOK()):
            global LOG_PULL_LOCK
            LOG_PULL_LOCK.acquire()
            try:
                log("PULLING_LOG\t%s\tLOG" % device.name)
                adb.pullLog(path='files/%s' % experiment.name, destination='logs/experiment/%s/%d/%d/%s.csv' % (experiment.name, repetition, seed_repeat, device.name), device=device)
                log("PULLING_LOG\t%s\tLOG\tOK" % device.name)
            finally:
                LOG_PULL_LOCK.release()
    except:
        log("PULLING_LOG\t%s\tLOG\tERROR" % device.name)
        log("DEVICE_PULLING_LOG\tEXPERIMENT_SET_FAIL")
        experiment.setFail()
        experiment.deviceFail(device.name)
    try:
        global SYS_LOG_PULL_LOCK
        SYS_LOG_PULL_LOCK.acquire()
        try:
            log("PULLING_LOG\t%s\tSYS_LOG" % device.name)
            system_log_path = "logs/sys/%s/%d/%d/" % (experiment.name, repetition, seed_repeat)
            os.makedirs(system_log_path, exist_ok=True)
            adb.pullSystemLog(device, system_log_path)
            log("PULLING_LOG\t%s\tSYS_LOG\tOK" % device.name)
        finally:
            SYS_LOG_PULL_LOCK.release()
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
        log("DEVICE_CHECKING_LOG\tEXPERIMENT_SET_FAIL")
        experiment.setFail()
        experiment.deviceFail(device.name)
    destroyWorker(jay_instance, droid_launcher, device)
    log("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % device.name)
    adb.screenOff(device)
    sleep(10)
    barrierWithTimeout(finish_barrier)


def cleanLogs(path):
    if os.path.isdir(path):
        for f in os.listdir(path):
            if os.path.isdir("%s/%s" % (path, f)):
                cleanLogs("%s/%s/" % (path, f))
                os.rmdir("%s/%s" % (path, f))
            else:
                os.remove("%s/%s" % (path, f))
    else:
        os.makedirs(path, exist_ok=True)

def runExperiment(experiment):
    global PENDING_TASKS, ALL_DEVICES, DEVICE_BLACKLIST, ASSETS, CURSES, USE_SMART_PLUGS, LOG_PULL_SCREEN_ON_FLAG, TAP_TO_KEEP_SCREEN_ON_FLAG, IDLE_BENCHMARK, IDLE_BENCHMARK_DURATION, LAST_RECEIVED_TASK_COMPLETION

    if CURSES:
        CURSES.add_text(1,200,3,text="EXPERIMENT: {}".format(experiment.name))
        CURSES.add_text(1,200,4,text="PROGRESS:")
        progressBar_0 = CURSES.add_progress_bar(1,60,4,10)
        progressBar_0.updateProgress(0)

    if not os.path.isdir("logs/experiment/%s/" % experiment.name):
        os.makedirs("logs/experiment/%s/" % experiment.name, exist_ok=True)

    logExperiment(LOG_FILE, experiment)
    experiment_random = random.Random()
    experiment_random.seed(experiment.seed)
    ASSETS=os.listdir(experiment.assets)

    log("STOPPING ALL RUNNING INSTANCES IN NETWORK")
    for dev in ALL_DEVICES:
        forceScreenOnViaPower(dev)
        try:
            adb.stopAll(dev)
        except:
            pass

    filtered_devices = []
    if len(experiment.devices_filter) != 0:
        for dev in ALL_DEVICES:
            if dev.name in experiment.devices_filter:
                filtered_devices.append(dev)
    else:
        filtered_devices = ALL_DEVICES
    if len(filtered_devices) - len(DEVICE_BLACKLIST) >= experiment.devices:
        devices_to_test = []
        for dev in filtered_devices:
            if dev.name not in DEVICE_BLACKLIST:
                devices_to_test.append(dev)
        devices = getNeededDevicesAvailable(experiment, devices_to_test)
    else:
        devices = getNeededDevicesAvailable(experiment, filtered_devices)
    if (len(devices) < experiment.devices):
        os.system("touch logs/experiment/%s/not_enough_devices_CANCELED"  % experiment.name)
        return

    conf = open("logs/experiment/%s/conf.cfg" % experiment.name, "w+")
    logExperiment(conf, experiment)
    conf.close()


    if os.path.exists("logs/experiment/%s/lost_devices_mid_experience_CANCELED"):
        os.remove("logs/experiment/%s/lost_devices_mid_experience_CANCELED")
    if os.path.exists("logs/experiment/%s/not_enough_devices_CANCELED"):
        os.remove("logs/experiment/%s/not_enough_devices_CANCELED")

    killLocalCloudlet()
    stopClouds(experiment)

    if REBOOT_ON_RUN_EXPERIMENT:
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

    for repetition in range(experiment.task_iteration_start, experiment.repetitions):
        log("=========================\tREPETITION {}\t========================".format(repetition))
        os.makedirs("logs/experiment/%s/%d/" % (experiment.name, repetition), exist_ok=True)
        devices.sort(key=lambda e: e.name, reverse=False)
        experiment_random.shuffle(devices)

        for seed_repeat in range(experiment.initial_repeat_seed, experiment.repeat_seed):
            TAP_TO_KEEP_SCREEN_ON_FLAG = True
            LOG_PULL_SCREEN_ON_FLAG = True
            LAST_RECEIVED_TASK_COMPLETION = None
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

                if len(devices) - len(DEVICE_BLACKLIST) >= experiment.devices:
                    devices_to_test = []
                    for dev in devices:
                        if dev.name not in DEVICE_BLACKLIST:
                            devices_to_test.append(dev)
                    experiment_devices = getNeededDevicesAvailable(experiment, devices_to_test)
                else:
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

                cleanLogs("logs/experiment/%s/%d/%d/" % (experiment.name, repetition, seed_repeat))
                cleanLogs("logs/sys/%s/%d/%d/" % (experiment.name, repetition, seed_repeat))
                os.makedirs("logs/experiment/%s/%d/%d/" % (experiment.name, repetition, seed_repeat), exist_ok=True)
                boot_barrier = Barrier(experiment.devices + 1)
                start_barrier = Barrier(experiment.devices + 1)
                complete_barrier = Barrier(experiment.devices + 1)
                log_pull_barrier = Barrier(experiment.devices + 1)
                finish_barrier = Barrier(experiment.devices + len(experiment.cloudlets) + len(experiment.clouds) + 1)
                servers_finish_barrier = Barrier(len(experiment.cloudlets) + len(experiment.clouds) + 1)

                startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)
                workers = experiment.workers
                custom_executors_mobile = []
                i = 0
                if (experiment.custom_executors is not None and experiment.custom_executors.mobile != None):
                    for custom_executor in experiment.custom_executors.mobile:
                        for i in range(custom_executor[2]):
                            custom_executors_mobile.append((custom_executor[0], custom_executor[1], custom_executor[3]))
                for device in ALL_DEVICES:
                    forceScreenOnViaPower(device)
                filtered_producers = []
                for device in experiment_devices:
                    if len(filtered_producers) >= experiment.producers:
                        break
                    if (device.name in experiment.producers_filter) or (len(experiment.producers_filter) == 0):
                        filtered_producers.append(device)
                i = 0
                for device in experiment_devices[:experiment.devices]:
                    if (i < len(custom_executors_mobile)):
                        Thread(target = startWorkerThread, args = (experiment, "seed_{}".format(device.name),repetition, seed_repeat, (device in filtered_producers), (experiment.start_worker and (workers > 0)), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier, custom_executors_mobile[i][0], custom_executors_mobile[i][1], custom_executors_mobile[i][2])).start()
                    else:
                        Thread(target = startWorkerThread, args = (experiment, "seed_{}".format(device.name),repetition, seed_repeat, (device in filtered_producers), (experiment.start_worker and (workers > 0)), device, boot_barrier, start_barrier, complete_barrier, log_pull_barrier, finish_barrier)).start()
                    workers -= 1 # Os primeiros n devices é que são workers
                    i += 1
                if USE_SMART_PLUGS:
                    if (experiment.power_devices):
                        if (not power_on(experiment.smart_plug)):
                            log("POWER_ON_FAIL\tEXPERIMENT_SET_FAIL")
                            experiment.setFail()
                    else:
                        if (not power_off(experiment.smart_plug)):
                            log("POWER_OFF_FAIL\tEXPERIMENT_SET_FAIL")
                            experiment.setFail()
                for device in ALL_DEVICES:
                    if device not in experiment_devices[:experiment.devices]:
                        adb.screenOff(device)

                startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier)

                log("WAIT_ON_BARRIER\tBOOT_BARRIER\tMAIN")
                if not barrierWithTimeout(boot_barrier, 500*experiment.devices, experiment, True, "MAIN"): # 15m
                    log("BROKEN_BARRIER\tBOOT_BARRIER\tMAIN")
                sleep(1)
                log("WAIT_ON_BARRIER\tSTART_BARRIER\tMAIN")
                if not barrierWithTimeout(start_barrier, 60, experiment, True, "MAIN"):
                    log("BROKEN_BARRIER\tSTART_BARRIER\tMAIN")

                completetion_timeout_start = time()
                i=0
                while (PENDING_TASKS > 0 and experiment.isOK()) or (experiment.duration > time()-completetion_timeout_start and experiment.isOK()):
                    sleep(2)
                    if (i % 10) == 0:
                        log("PENDING_TASKS\t{}".format(PENDING_TASKS))
                    if (i % 20) == 0:
                        log("CURRENT_EXPERIMENT_DURATION\t{}s".format(time()-completetion_timeout_start))
                    if (time()-completetion_timeout_start > experiment.duration+experiment.timeout):
                        log("COMPLETION_TIMEOUT_EXCEDED")
                        os.system("touch logs/experiment/%s/%d/%d/completion_timeout_exceded"  % (experiment.name, repetition, seed_repeat))
                        break
                    if not (LAST_RECEIVED_TASK_COMPLETION is None):
                        if (time()-LAST_RECEIVED_TASK_COMPLETION > 120):
                            log("TASKS_GOT_STUCK_ON_ERROR")
                            log("TASKS_STUCK_FAIL\tEXPERIMENT_SET_FAIL")
                            experiment.setFail()
                            os.system("touch logs/experiment/%s/%d/%d/tasks_got_stuck"  % (experiment.name, repetition, seed_repeat))
                            break
                    i+=1
                sleep(2)
                if (IDLE_BENCHMARK):
                    sleep(IDLE_BENCHMARK_DURATION)
                log("WAIT_ON_BARRIER\tCOMPLETE_BARRIER\tMAIN_LOOP")
                if (experiment.benchmark):
                    if not barrierWithTimeout(complete_barrier, 240+experiment.benchmark_duration, experiment, True, "MAIN"):
                        log("BROKEN_BARRIER\tCOMPLETE_BARRIER\tMAIN")
                else:
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
                barrierWithTimeout(finish_barrier, 3000, experiment, True, "MAIN", finish_barrier)

                if (experiment.isOK()):
                    break
                repeat_tries += 1
            if CURSES:
                progressBar_0.updateProgress(int(100*((seed_repeat+1)/experiment.repeat_seed)))

        if (repetition != experiment.repetitions - 1):
            log("Waiting 5s for next repetition")
            sleep(5)
    log("FINISHING_EXPERIMENT\t%s" % experiment.name)
    if USE_SMART_PLUGS:
        power_on(experiment.smart_plug)
        sleep(2)
        for device in ALL_DEVICES:
            adb.screenOff(device)

def getNeededDevicesAvailable(experiment, devices, retries=5):
    if retries < 0:
        experiment.setFail()
        log("NOT_ENOUGH_DEVICES\tEXPERIMENT_SET_FAIL")
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
        forceScreenOnViaPower()
        sleep(10)
        power_on()
        discoverable_devices = adb.listDevices(0)
        good_to_charge = []
        for device in to_charge:
            for disc_device in discoverable_devices:
                if disc_device.name == device.name or disc_device.ip == device.ip:
                    good_to_charge.append(device)
        if len(good_to_use) + len(good_to_charge) < experiment.devices:
            log("NOT_ENOUGH_DEVICES\tEXPERIMENT_SET_FAIL")
            experiment.setFail()
            os.system("touch logs/experiment/%s/lost_devices_mid_experience_CANCELED"  % experiment.name)
            return []
        battery_barrier = Barrier(experiment.devices - len(good_to_use) + 1)
        for device in good_to_charge:
            Thread(target = chargeDevice, args = (experiment.min_battery, device, battery_barrier)).start()
        barrierWithTimeout(battery_barrier, 3600, show_error=False)
        sleep(60)
        return getNeededDevicesAvailable(experiment, devices, retries-1)

def rebootDevice(device, retries=2, reboot_barrier=None, screenOff=False):
    global DEVICE_BLACKLIST
    if retries < 0:
        log("REBOOT_DEVICE_FAIL\t%s" % device.name)
        if reboot_barrier is not None:
            skipBarriers(None, True, device.name, reboot_barrier)
        if device.name not in DEVICE_BLACKLIST:
            DEVICE_BLACKLIST.append(device.name)
        return False
    log("REBOOT_DEVICE\t%s" % device.name)
    pre_reboot_worker_ip = getDeviceIp(device)
    if adb.rebootAndWait(device, timeout=180):
        log("REBOOT_DEVICE_COMPLETE\t%s" % device.name)
        if screenOff:
            adb.screenOff(device)
        if reboot_barrier is not None:
            barrierWithTimeout(reboot_barrier, show_error=True, device=device.name)
        if device.name in DEVICE_BLACKLIST:
            DEVICE_BLACKLIST.remove(device.name)
        return True
    else:
        log("REBOOT_DEVICE_RETRY\t%s" % device.name)
        return rebootDevice(device, retries - 1)

def getBatteryLevel(device, retries=2):
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
    sleep(10)
    while (not battery_barrier.broken and (battery_level < max(0, min(100, min_battery)))):
        adb.screenOff(device)
        if (counter % 5 == 0):
            log("CHARGING_DEVICE {} ({}%)".format(device.name, battery_level))
        sleep(120)
        forceScreenOnViaPower()
        sleep(10)
        battery_level = getBatteryLevel(device)
        counter += 1
        sleep(10)
    barrierWithTimeout(battery_barrier, 3600, show_error=False)

def startCloudlets(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloudlet_boot_barrier = Barrier(len(experiment.cloudlets) + 1)
    i = 0
    custom_executors_cloudlet = []
    if (experiment.custom_executors is not None and experiment.custom_executors.cloudlet is not None):
        for custom_executor in experiment.custom_executors.cloudlet:
            for i in range(custom_executor[2]):
                custom_executors_cloudlet.append((custom_executor[0], custom_executor[1], custom_executor[3]))
    for cloudlet in experiment.cloudlets:
        if (i < len(custom_executors_cloudlet)):
            Thread(target = startCloudletThread, args = (cloudlet, experiment, "cloudlet_seed_{}".format(i), repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier, custom_executors_cloudlet[i][0], custom_executors_cloudlet[i][1], custom_executors_cloudlet[i][2])).start()
        else:
            Thread(target = startCloudletThread, args = (cloudlet, experiment, "cloudlet_seed_{}".format(i), repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier)).start()
        i += 1
    barrierWithTimeout(cloudlet_boot_barrier, 600, experiment, True, "START_CLOUDLETS", servers_finish_barrier, finish_barrier)

def killLocalCloudlet():
    pid = os.popen("jps -lV | grep .Jay-x86.jar | cut -d' ' -f1").read()[:-1]
    if pid != '':
        subprocess.run(['kill', '-9', pid])

def startCloudletThread(cloudlet, experiment, cloudlet_seed, repetition, seed_repeat, cloudlet_boot_barrier, servers_finish_barrier, finish_barrier, custom_task_executor=None, custom_model=None, custom_settings_map=None):
    log("Starting %s Cloudlet Instance" % cloudlet)
    device_random = random.Random()
    device_random.seed(experiment.seed+cloudlet_seed+str(repetition))
    x86_remote_control = grpcControls.x86RemoteControl(cloudlet, "%s_cloudlet" % cloudlet)
    x86_remote_control.connect()
    x86_remote_control.stop()
    x86_remote_control.start()
    sleep(1)
    log("Setting up %s Cloudlet Instance" % cloudlet)
    x86_launcher = grpcControls.x86Launcher(cloudlet, "%s_cloudlet" % cloudlet)
    x86_launcher.stop()
    x86_launcher.connectLauncherService()
    log("Setting log name %s Cloudlet Instance" % cloudlet)
    x86_launcher.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    log("Starting Worker %s Cloudlet Instance" % cloudlet)
    x86_launcher.startWorker()
    sleep(1)
    jay_instance = grpcControls.jayClient(cloudlet, "%s_cloudlet" % cloudlet)
    log("Connecting to Broker %s Cloudlet Instance" % cloudlet)

    jay_instance.connectBrokerService()
    sleep(1)
    if experiment.settings or experiment.mcast_interface:
        jay_instance.setSettings(experiment.settings, experiment.mcast_interface, advertise_worker=True)
    sleep(1)

    selectTaskExecutor(experiment, jay_instance, custom_task_executor)
    setTaskExecutorSettings(experiment, jay_instance, custom_settings_map)
    if not selectModel(experiment, jay_instance, custom_model):
        log("Failed to setScheduler on %s" % cloudlet)
        log("CLOUDLET_SET_SCHEDULER_FAIL\tEXPERIMENT_SET_FAIL")
        experiment.setFail()

    barrierWithTimeout(cloudlet_boot_barrier, 600, experiment, True, cloudlet, servers_finish_barrier, finish_barrier) #inform startCloudlets that you have booted
    if (experiment.calibration):
        calibrateWorkerThread(jay_instance, cloudlet_seed, asset_id="%s.jpg" % experiment.asset_quality)
    barrierWithTimeout(servers_finish_barrier) #wait experiment completion to init shutdown
    try:
        x86_launcher.stop()
    except:
        None
    try:
        x86_remote_control.stop()
    except:
        None
    barrierWithTimeout(finish_barrier)

def pullLogsCloudsAndCloudlets(experiment, repetition, seed_repeat):
    log_name = "%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat)
    for cloud in experiment.clouds:
        if (cloud.zone == 'localhost'):
            os.system("cp %s/Jay-x86/logs/%s logs/experiment/%s/%s/%s/cloudlet_%s.csv" % (os.environ['HOME'], log_name, experiment.name, repetition, seed_repeat, cloud.address))
        else:
            os.system("scp -i ~/.ssh/cloudlet joaquim@%s:~/Jay-x86/logs/%s logs/experiment/%s/%s/%s/%s_%s.csv" % (cloud.address, log_name, experiment.name, repetition, seed_repeat, cloud.instance, cloud.zone))
    for cloudlet in experiment.cloudlets:
        if (cloudlet == '127.0.0.1'):
            os.system("cp %s/Jay-x86/logs/%s logs/experiment/%s/%s/%s/cloudlet_%s.csv" % (os.environ['HOME'], log_name, experiment.name, repetition, seed_repeat, cloudlet))
        else:
            os.system("scp -i ~/.ssh/cloudlet joaquim@%s:~/Jay-x86/logs/%s logs/experiment//%s/%s/%s/cloudlet_%s.csv" % (cloudlet, log_name, experiment.name, repetition, seed_repeat, cloudlet))

def startCloudThread(cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier, custom_task_executor=None, custom_model=None, custom_settings_map=None):
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

    x86_remote_control = grpcControls.x86RemoteControl(cloud.address, "{}_{}_cloud".format(cloud.instance, cloud.zone))
    x86_remote_control.connect()
    x86_remote_control.stop()
    x86_remote_control.start()
    sleep(1)

    x86_launcher = grpcControls.x86Launcher(cloud.address, cloud.instance)
    x86_launcher.stop()
    x86_launcher.connectLauncherService()
    x86_launcher.setLogName("%s_%s_%s.csv" % (experiment.name, repetition, seed_repeat))
    x86_launcher.startWorker()
    sleep(1)


    jay_instance = grpcControls.jayClient(cloud.address, cloud.instance)
    jay_instance.connectBrokerService()
    sleep(1)
    if experiment.settings:
        jay_instance.setSettings(experiment.settings)
    sleep(1)

    selectTaskExecutor(experiment, jay_instance, custom_task_executor)
    setTaskExecutorSettings(experiment, setTaskExecutorSettings, custom_task_executor)

    if not selectModel(experiment, jay_instance, custom_model):
        log("Failed to setScheduler on %s" % cloudlet)
        log("CLOUDLET_SET_SCHEDULER_FAIL\tEXPERIMENT_SET_FAIL")
        experiment.setFail()

    log("WAIT_ON_BARRIER\tCLOUD_BOOT_BARRIER\t%s" % cloud.instance)
    barrierWithTimeout(cloud_boot_barrier, 600, experiment, True, cloud.instance, servers_finish_barrier, finish_barrier)
    if (experiment.calibration):
        calibrateWorkerThread(jay_instance, "cloud_{}".format(cloud.address), asset_id="%s.jpg" % experiment.asset_quality)
    log("WAIT_ON_BARRIER\tSERVER_FINISH_BARRIER\t%s" % cloud.instance)
    barrierWithTimeout(servers_finish_barrier)
    log("Stopping %s Cloud Instance" % cloud.instance)
    x86_launcher.stop()
    x86_remote_control.stop()
    log("STOPPING_CLOUD_INSTANCE\t{}\t({})".format(cloud.instance, cloud.address))
    if (not experiment.isOK()):
        skipBarriers(experiment, True, cloud.instance, finish_barrier)
        return
    # Temporary to increase experiment speed
    adb.cloudInstanceStop(cloud.instance, cloud.zone)
    log("WAIT_ON_BARRIER\tFINISH_BARRIER\t%s" % cloud.instance)
    barrierWithTimeout(finish_barrier)
    log("CLOUD_FINISHED\t%s" % cloud.instance)


def startClouds(experiment, repetition, seed_repeat, servers_finish_barrier, finish_barrier):
    cloud_boot_barrier = Barrier(len(experiment.clouds) + 1)
    i = 0
    custom_executors_cloud = []
    if (experiment.custom_executors is not None  and experiment.custom_executors.cloud is not None):
        for custom_executor in experiment.custom_executors.cloud:
            for i in range(custom_executor[2]):
                custom_executors_cloud.append((custom_executor[0], custom_executor[1], custom_executor[3]))
    for cloud in experiment.clouds:
        if (i < len(custom_executors_cloud)):
            if (cloud.zone == "localhost"):
                Thread(target = startCloudletThread, args = (cloud.address, experiment, "cloudlet_seed_{}".format(cloud.address), repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier, custom_executors_cloud[i][0], custom_executors_cloud[i][1], custom_executors_cloud[i][2])).start()
            else:
                Thread(target = startCloudThread, args = (cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier, custom_executors_cloud[i][0], custom_executors_cloud[i][1], custom_executors_cloud[i][2])).start()
        else:
            if (cloud.zone == "localhost"):
                Thread(target = startCloudletThread, args = (cloud.address, experiment, "cloudlet_seed_{}".format(cloud.address), repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier)).start()
            else:
                Thread(target = startCloudThread, args = (cloud, experiment, repetition, seed_repeat, cloud_boot_barrier, servers_finish_barrier, finish_barrier)).start()
        i += 1
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

class CustomExecutors:
    cloud = None
    cloudlet = None
    mobile = None

    def addCloud(self, task_executor, model, num_devices, settings_map):
        if self.cloud is None:
            self.cloud = [(task_executor, model, num_devices, settings_map)]
        else:
            self.cloud.append((task_executor, model, num_devices, settings_map))

    def addCloudlet(self, task_executor, model, num_devices, settings_map):
        if self.cloudlet is None:
            self.cloudlet = [(task_executor, model, num_devices, settings_map)]
        else:
            self.cloudlet.append((task_executor, model, num_devices, settings_map))

    def addMobile(self, task_executor, model, num_devices, settings_map):
        if self.mobile is None:
            self.mobile = [(task_executor, model, num_devices, settings_map)]
        else:
            self.mobile.append((task_executor, model, num_devices, settings_map))

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
    initial_repeat_seed = 0
    current_seed_repeat = 0
    timeout = 1500 # 25 Mins
    start_worker = True
    workers = -1
    assets = "assets/sd/"
    asset_type = "image"
    calibration = False
    asset_quality = "SD"
    mcast_interface = None
    min_battery = 10
    _failed_devices = {}
    _running_status = True
    task_executor = "Tensorflow"
    task_executor_settings = None
    custom_executors = None
    power_devices = True
    smart_plug = "SHP7"
    settings = {}
    devices_filter = []
    producers_filter = []
    benchmark = False
    benchmark_duration = 0
    task_deadline = None
    task_iteration_start = 0


    def __init__(self, name):
        self.name = name
        self.settings = {"ADVERTISE_WORKER_STATUS": "true"}
        self.sequential_mode = False

    def setSetting(self, key, val):
        self.settings[key] = val

    def setTaskExecutorSetting(self, key, val):
        if self.task_executor_settings is None:
            self.task_executor_settings = {}
        self.task_executor_settings[key] = val

    def setSequential(self):
        self.sequential_mode = True

    def isSequential(self):
        return self.sequential_mode

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

def processSettingsMap(raw_settings):
    if raw_settings.strip() == "":
        return None
    map = {}
    for setting in raw_settings.split(";"):
        key_val = setting.strip().split(":")
        if (len(key_val) >= 2):
            map[key_val[0].strip()] = key_val[1].strip()
        if (len(key_val) == 1):
            map[key_val[0].strip()] = ""
    return map

def readConfig(confName):
    global EXPERIMENTS, SCHEDULED_EXPERIMENTS
    config = configparser.ConfigParser()
    config.read(confName)
    for section in config.sections():
        startTime = None
        endTime = None
        experiment = Experiment(section)
        experiment.devices_filter = []
        experiment.producers_filter = []
        experiment.task_iteration_start = 0
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
            elif option == "initialrepeatseed":
                experiment.initial_repeat_seed = int(config[section][option])
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
                    setting = ""
                    setting = entry.split(':')
                    experiment.setSetting(setting[0].strip(), setting[1].strip())
            elif option == "taskexecutorsettings":
                for entry in config[section][option].split(';'):
                    setting = ""
                    setting = entry.split(':')
                    experiment.setTaskExecutorSetting(setting[0].strip(), setting[1].strip())
            elif option == "multicastinterface":
                experiment.mcast_interface = config[section][option]
            elif option == "minbattery":
                experiment.min_battery = int(config[section][option])
            elif option == "sequentialmode":
                if config[section][option].lower() == "true":
                    experiment.setSequential()
            elif option == "runbetween":
                try:
                    times = config[section][option].split("-")
                    startTime = int(times[0])
                    endTime = int(times[1])
                except:
                    None
            elif option == "taskexecutor":
                experiment.task_executor = config[section][option]
            elif option == "customexecutors":
                custom_executors = CustomExecutors()
                for entry in config[section][option].split(';'):
                    executor_model_device_number = entry.split("/")
                    if len(executor_model_device_number) != 5:
                        log("INVALID CUSTOM_EXECUTOR {}".format(entry))
                    elif executor_model_device_number[2].strip().lower() == "cloud":
                        custom_executors.addCloud(executor_model_device_number[0].strip(), executor_model_device_number[1].strip(), int(executor_model_device_number[3]), processSettingsMap(executor_model_device_number[4]))
                    elif executor_model_device_number[2].strip().lower() == "cloudlet":
                        custom_executors.addCloudlet(executor_model_device_number[0].strip(), executor_model_device_number[1].strip(), int(executor_model_device_number[3]), processSettingsMap(executor_model_device_number[4]))
                    elif executor_model_device_number[2].strip().lower() == "mobile":
                        custom_executors.addMobile(executor_model_device_number[0].strip(), executor_model_device_number[1].strip(), int(executor_model_device_number[3]), processSettingsMap(executor_model_device_number[4]))
                    else:
                        log("INVALID DEVICE_TYPE {}".format(entry))
                experiment.custom_executors = custom_executors
            elif option == "powerdevices":
                if config[section][option].lower() == "false":
                    experiment.power_devices = False
            elif option == "smartplug":
                experiment.smart_plug = config[section][option]
            elif option == "filterdevices":
                for dev in config[section][option].split(","):
                    experiment.devices_filter.append(dev.strip())
            elif option == "filterproducers":
                for dev in config[section][option].split(","):
                    experiment.producers_filter.append(dev.strip())
            elif option == "benchmark":
                if config[section][option].lower() == "true":
                    experiment.benchmark = True
            elif option == "benchmarkduration":
                experiment.benchmark_duration = int(config[section][option])
            elif option == "taskdeadline":
                experiment.task_deadline = int(config[section][option])
            elif option == "taskiterationstart":
                experiment.task_iteration_start = int(config[section][option])
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
                    InitialRepeatSeed       = Initial repeat seed [INT]
                    Cloudlets               = IP, ... [LIST]
                    Timeout                 = Max time after experiment duration to cancel execution
                    StartWorkers            = Start Device Worker devices [INT]
                    Workers                 = Number of Workers [BOOL] (Default True)
                    Assets                  = Assets directory [assets] (Default Value)
                    AssetType               = Asset Type (image/video) [image] (Default Value)
                    Calibration             = Run Jay calibration before begin [BOOL] (Default False)
                    Settings                = Set Jay settings (setting: value;...) [LIST]
                    AssetQuality            = Inform about asset quality (SD/HD/UHD) [STR] (Default SD)
                    MultiCastInterface      = MULTICAST_INTERFACE: interface to use in cloudlet [STR]
                    MinBattery              = Minimum battery to run experiment [INT] (Default 20)
                    RunBetween              = Define the experiment run interval (hour - hour)
                    TaskExecutor            = Task executor to use
                    TaskExecutorSettings    = Set Task Executor settings (setting: value;...) [LIST]
                    CustomExecutors         = TaskExecutor/Model/Mobile|Cloud|Cloudlet/Number_of_devices/setting:value;setting:value, ... [LIST]
                    powerDevices            = Power devices though experiment or not [BOOL] (Default True)
                    SmartPlug               = Name of smart plug SHP7/Meross [STR] (Default SHP7)
                    FilterDevices           = Filter Devices to be used in experiment (dev_1, dev_2, ..., dev_n) [LIST]
                    FilterProducers         = Filter Producers to be used in experiment (dev_1, dev_2, ..., dev_n) [LIST]
                    Benchmark               = Wether this experiment is a benchmark [BOOL] (Default False)
                    BenchmarkDuration       = Set benchmark Duration [INT]
                    TaskDeadline            = Set Task Deadline [INT] (Default: None)
                    TaskIterationStart      = The iteration to start task [INT] (Default: 0)

        Models:
            Tensorflow:
                All:
                    ssd_mobilenet_v1_fpn_coco
                    ssd_mobilenet_v1_coco  [FUNCIONA]
                    ssd_mobilenet_v2_coco
                    ssdlite_mobilenet_v2_coco
                    ssd_resnet50_v1_fpn_coco

                Android:
                    ssd_mobilenet_v3_large_coco
                    ssd_mobilenet_v3_small_coco

                x86:
                    faster_rcnn_resnet101_coco
                    faster_rcnn_inception_resnet_v2_atrous_coco
                    faster_rcnn_nas
                    faster_rcnn_nas_lowproposals_coco

            TensorflowLite:
                Lite:
                    ssd_mobilenet_v3_large_coco  (BROKEN RESULTS)
                    ssd_mobilenet_v3_small_coco    [WORKING]
                    ssd_mobilenet_v1_fpn_coco    [WORKING]
                    ssd_resnet50_v1_fpn_coco  [BROKEN URL]
                    ssd_mobilenet_v3_quantized_large_coco

        TaskExecutors:
                    Tensorflow

                    TensorflowLite
                        Settings:
                            CPU -> USE CPU
                            GPU -> USE GPU (BROKEN IN MODELS FOR OD)
                            NNAPI -> USE NNAPI

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

                    EAScheduler [LOCAL]
                    EAScheduler [REMOTE]
                    EAScheduler [CLOUD]
                    EAScheduler [LOCAL, CLOUD]
                    EAScheduler [LOCAL, REMOTE]
                    EAScheduler [REMOTE, CLOUD]
                    EAScheduler [LOCAL, REMOTE, CLOUD]

                    GreenTaskScheduler [LOCAL]
                    GreenTaskScheduler [REMOTE]
                    GreenTaskScheduler [CLOUD]
                    GreenTaskScheduler [LOCAL, CLOUD]
                    GreenTaskScheduler [LOCAL, REMOTE]
                    GreenTaskScheduler [REMOTE, CLOUD]
                    GreenTaskScheduler [LOCAL, REMOTE, CLOUD]
                         Settings:
                            TASK_DEADLINE_BROKEN_SELECTION: EXECUTE_LOCALLY, FASTER_COMPLETION, [LOWEST_ENERGY]
                            USE_FIXED_POWER_ESTIMATIONS: true / false


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
                    MULTICAST_INTERFACE
                    [*] BANDWIDTH_ESTIMATE_CALC_METHOD      [mean/median]  default: mean
                    [*] BANDWIDTH_SCALING_FACTOR             [Float] default: 1.0
                    [*] ADVERTISE_WORKER_STATUS: [true/false] default: true ENABLES DEVICE ADVERTISMENT Use when want LOCAL + CLOUDLET


            Setting Defaults:
                    SINGLE_REMOTE_IP: String = "0.0.0.0"
                    CLOUDLET_ID = ""
                    ADVERTISE_WORKER_STATUS: Boolean = false
                    BANDWIDTH_ESTIMATE_CALC_METHOD: String = "mean"
                    BANDWIDTH_SCALING_FACTOR: Float = 1.0f
                    BROKER_PORT: Int = 50051
                    WORKER_PORT: Int = 50053
                    SCHEDULER_PORT: Int = 50055
                    GRPC_MAX_MESSAGE_SIZE: Int = 150000000
                    RTT_HISTORY_SIZE: Int = 5
                    PING_TIMEOUT: Long = 10000L // 15s
                    RTT_DELAY_MILLIS: Long = 10000L // 10s
                    PING_PAYLOAD_SIZE: Int = 32000 // 32Kb
                    AVERAGE_COMPUTATION_TIME_TO_SCORE: Int = 10
                    WORKING_THREADS: Int = 1
                    WORKER_STATUS_UPDATE_INTERVAL: Long = 1000 // 1s
                    RTT_DELAY_MILLIS_FAIL_RETRY: Long = 500 // 0.5s
                    RTT_DELAY_MILLIS_FAIL_ATTEMPTS: Long = 5
                    MULTICAST_INTERFACE: String? = null
                    MULTICAST_PKT_INTERVAL: Long = 500 // 0.5s
                    READ_SERVICE_DATA_INTERVAL: Long = 500 // 0.5s
                    DEVICE_ID: String = ""
                    BANDWIDTH_ESTIMATE_TYPE = "ALL" // ACTIVE/PASSIVE/ALL

                    MULTICAST_PKT_INTERVAL: Int = 500 // Multicast Advertise Interval
                    USE_CPU_ESTIMATIONS: Boolean = false // Use CpuEstimation on Profiller

                    ---> BENCHMARKS
                    COMPUTATION_BASELINE_DURATION_FLAG = false
                    COMPUTATION_BASELINE_DURATION = 600 // 10 minutess
                    TRANSFER_BASELINE_FLAG = false

                    --> SCHEDULERS:
                    TASK_DEADLINE_BROKEN_SELECTION:
                            EXECUTE_LOCALLY
                            FASTER_COMPLETION
                            RANDOM
                            LOWEST_ENERGY
                    INCLUDE_IDLE_COSTS = true/false

            OS Specific Problems/Fixes:
                MacOS:
                    Too Many Open Files:
                        ulimit -n 10240

                        sysctl kern.maxfiles
                        sysctl kern.maxfilesperproc

                        sysctl -w kern.maxfiles=40480
                        sysctl -w kern.maxfilesperproc=30000
        ================================================ HELP ================================================''')

def logExperiment(conf, experiment):
    conf.write("Experiment: %s\n" % experiment.name)
    conf.write("==============\tCONFIG\t==============\n")
    conf.write("Scheduler: %s\n" % experiment.scheduler)
    conf.write("TensorflowModel: %s\n" % experiment.model)
    conf.write("TaskExecutor: %s\n" % experiment.task_executor)
    conf.write("Devices: %s\n" % str(experiment.devices))
    conf.write("Reboot: %s\n" % experiment.reboot)
    conf.write("Rate: %s\n" % str(experiment.request_rate))
    conf.write("RateTime: %s" % str(experiment.request_time) + "s\n")
    conf.write("Duration: %s" % str(experiment.duration) + "s\n")
    conf.write("Clouds: [")
    for cloud in experiment.clouds:
        conf.write("({}, {}, {})".format(cloud.instance, cloud.zone, cloud.address))
    conf.write("]\n")
    conf.write("Cloudlets: %s\n" % str(experiment.cloudlets))
    conf.write("Seed: %s\n" % experiment.seed)
    conf.write("Repetitions: %s\n" % str(experiment.repetitions))
    conf.write("Workers: %s\n" % experiment.workers)
    conf.write("Producers: %s\n" % experiment.producers)
    conf.write("StartWorkers: %s\n" % experiment.start_worker)
    conf.write("Assets: %s\n" % experiment.assets)
    conf.write("AssetQuality: %s\n" % experiment.asset_quality)
    conf.write("AssetType: %s\n" % experiment.asset_type)
    conf.write("MCastInterface: %s\n" % experiment.mcast_interface)
    conf.write("MinBattery: %d\n" % experiment.min_battery)
    conf.write("Calibration: %s\n" % experiment.calibration)
    conf.write("RepeatSeed: %s\n" % experiment.repeat_seed)
    conf.write("Timeout: %s\n" % experiment.timeout)
    conf.write("Settings: %s\n" % experiment.settings)
    conf.write("TaskExecutorSettings: %s\n" % experiment.task_executor_settings)
    conf.write("CustomExecutors: [")
    if experiment.custom_executors is not None:
        conf.write("Mobile: {}; Cloudlet: {}; Cloud: {}".format(experiment.custom_executors.mobile, experiment.custom_executors.cloudlet, experiment.custom_executors.cloud))
    conf.write("]\n")
    conf.write("======================================\n")

def getESSID(interface):
    interface_data = subprocess.run(["iwlist", interface, "scan"], stdout=subprocess.PIPE, stderr=open(os.devnull, "w")).stdout.decode("UTF-8")
    if interface_data.find("Interface doesn't support scanning.") != -1:
        return ""
    begin = interface_data.find("ESSID:")
    if begin != -1:
        end = interface_data[begin+7:].find("\"")
        return interface_data[begin+7:][:end]
    return ""

def checkInterfaces():
    iface_raw = subprocess.run(["ip", "link", "show"], stdout=subprocess.PIPE, stderr=open(os.devnull, "w")).stdout.decode("UTF-8").split("\n")
    ifaces = []
    for line in iface_raw:
        if line.find("state UP") != -1:
            ifaces.append(line.split()[1][:-1])
    if "flannel.1" in ifaces:
        subprocess.run(["sudo", "ip", "link", "set", "flannel.1", "down"])
    log("AVAILABLE INTERFACES:")
    for iface in ifaces:
        wlan = getESSID(iface)
        if wlan != "":
            log("\t[*] {} ({})".format(iface, wlan))
        else:
            log("\t[*] {}".format(iface))
    log("==========================================================================================")

def installPackage(device):
    forceScreenOnViaPower(device)
    log('CLEANING_SYSTEM\t%s' % device.name)
    adb.uninstallPackage(device=device)
    log('PACKAGE_UNINSTALLED\t%s' % device.name)
    log('PUSHING_PACKAGE\t%s' % device.name)
    adb.pushFile('apps/release/', 'Jay-Android Launcher-release.apk', path='', basepath='/data/local/tmp/', device=device)
    log('PACKAGE_PUSHED\t%s' % device.name)
    log('PM_INSTALL_PACKAGE\t%s' % device.name)
    adb.pmInstallPackage('Jay-Android Launcher-release.apk', device)
    if not adb.checkPackageInstalled(device=device):
        adb.installPackage('apps/release/','Jay-Android Launcher-release.apk', device=device)
    log('PACKAGE_INSTALLED\t%s' % device.name)
    permissions = ["android.permission.INTERNET", "android.permission.READ_PHONE_STATE",
    "android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.FOREGROUND_SERVICE", "android.permission.PACKAGE_USAGE_STATS",
    "android.permission.ACCESS_NETWORK_STATE", "android.permission.BLUETOOTH",
    "android.permission.ACCESS_FINE_LOCATION"]
    for permission in permissions:
        if permission not in adb.grantedPermissions(device=device):
            adb.grantPermission(permission, device=device)
            if permission in adb.grantedPermissions(device=device):
                log('GRANTED_PERMISSION: ' + permission + '\t%s' % device.name)
            else:
                log('GRANT_PERMISSION_FAIL: ' + permission + '\t%s' % device.name)
        else:
            log('ALREADY_GRANTED_PERMISSION: ' + permission + '\t%s' % device.name)
    adb.screenOff(device)

def forceScreenOnViaPower(device=None, power_devices=True):
    if USE_SMART_PLUGS  and not adb.hasScreenOn(device) and not device.connected_usb and device.connected_wifi:
        power_off()
        sleep(2)
        power_on()
        sleep(1)
    sleep(2)
    if not power_devices:
        power_off(checkPlug = True)
        sleep(2)
    adb.screenOn(device)

def fixULimit():
    if adb.getOs() == "mac":
        result = subprocess.run(["ulimit", "-n"], stdout=subprocess.PIPE, stderr=FNULL)
        log("CURRENT_ULIMIT:\t%s" % result.stdout.decode('UTF-8').strip("\n"))
        if int(result.stdout.decode('UTF-8')) < 10240:
            log("MUST_SET_ULIMIT_TO: 10240")
            log("ulimit -n 10240")
            exit(0)
            #log("SETTING_ULIMIT:\t10240")
            #subprocess.run(["ulimit", "-n", "10240"], stdout=FNULL, stderr=FNULL)
            #subprocess.run(["sudo", "ulimit", "-n", "10240"], stdout=FNULL, stderr=FNULL)

def shutdownDevice(device=None, barrier=None):
    log("SHUTING_DOWN:\t%s (%s)" % (device.name, device.ip))
    adb.shutdown(device)
    log("SHUT_DOWN_COMPLETE:\t%s (%s)" % (device.name, device.ip))
    barrier.wait()

def main():
    global ALL_DEVICES, LOG_FILE, EXPERIMENTS, SCHEDULED_EXPERIMENTS, CURSES, DEBUG, ADB_DEBUG_FILE, ADB_LOGS_LOCK, GRPC_DEBUG_FILE, GRPC_LOGS_LOCK, CURSES_LOGS, USE_SMART_PLUGS, FORCE_USB, SCREEN_BRIGHTNESS, IDLE_BENCHMARK, IDLE_BENCHMARK_DURATION

    argparser = argparse.ArgumentParser()
    argparser.add_argument('-c', '--configs', default=[], nargs='+', required=False)
    argparser.add_argument('--show-help', default=False, action='store_true', required=False)
    argparser.add_argument('-i', '--install', default=False, action='store_true', required=False)
    argparser.add_argument('-da', '--debug-adb', default=False, action='store_true', required=False)
    argparser.add_argument('-al', '--adb-log-level', action='store', required=False, help="ALL / ACTION / COMMAND")
    argparser.add_argument('-dg', '--debug-grpc', default=False, action='store_true', required=False)
    argparser.add_argument('-p', '--use-stdout', default=False, action='store_true', required=False)
    argparser.add_argument('-nc', '--use-curses', default=False, action='store_true', required=False)
    argparser.add_argument('-w', '--wifi', default=False, action='store_true', required=False)
    argparser.add_argument('-ip', '--ip-mask', action='store', required=False)
    argparser.add_argument('-r', '--reboot-devices', default=False, action='store_true', required=False)
    argparser.add_argument('-d', '--daemon', default=False, action='store_true', required=False)
    argparser.add_argument('-sp', '--smart-plug', default=False, action='store_true', required=False)
    argparser.add_argument('-u', '--force-usb', default=False, action='store_true', required=False)
    argparser.add_argument('-b', '--brightness', action='store', required=False)
    argparser.add_argument('-on', '--screen-on', default=False, action='store_true', required=False)
    argparser.add_argument('-off', '--screen-off', default=False, action='store_true', required=False)
    argparser.add_argument('-sd', '--shutdown', default=False, action='store_true', required=False)
    argparser.add_argument('-po', '--power-on', default=False, action='store_true', required=False)
    argparser.add_argument('-poff', '--power-off', default=False, action='store_true', required=False)
    argparser.add_argument('-idle', '--idle-benchmark', default=False, action='store_true', required=False)
    argparser.add_argument('-idled', '--idle-benchmark-duration', default=IDLE_BENCHMARK_DURATION, action='store', required=False)

    args = argparser.parse_args()

    if args.show_help:
        help()
        return

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
    try:
        checkInterfaces()
    except:
        None
    log("Starting... Please wait")

    if args.smart_plug:
        USE_SMART_PLUGS = True

    if args.brightness != None:
        try:
            SCREEN_BRIGHTNESS = int(args.brightness)
        except:
            SCREEN_BRIGHTNESS = 0

    if not args.use_stdout:
        LOG_FILE = open("logs/workbench/{}/output.log".format(experiment_name), "w")

    if args.power_on:
        power_on()
        return
    if args.power_off:
        power_off(checkPlug=False)
        return


    log("KILLING_ADB...", end="\t")
    try:
        adb.close()
    except:
        pass
    adb.killAll()
    log("KILLED", "\n", False)
    log("RESTART_ADB...", end="\t")
    adb.init()
    sleep(5)
    log("STARTED", "\n", False)
    #log("DISCONNECTING_OLD_DEVICES...", end="\t")
    #adb.disconnectAll()
    #log("DISCONNECTED")
    #sleep(1)

    if args.wifi:
        log("SEARCHING_DEVICES [USB/WIFI]")
    else:
        log("SEARCHING_DEVICES [USB]")
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
    if args.force_usb:
        adb.FORCE_USB = True

    if args.idle_benchmark:
        IDLE_BENCHMARK = True
        if args.idle_benchmark_duration:
            IDLE_BENCHMARK_DURATION = int(args.idle_benchmark_duration)

    if args.wifi or args.ip_mask:
        power_off(checkPlug=False)
        sleep(2)
        power_on()
        sleep(2)
    if args.ip_mask:
        ALL_DEVICES = adb.listDevices(minBattery = 0, discover_wifi=True, ip_mask=args.ip_mask)
    else:
        ALL_DEVICES = adb.listDevices(minBattery = 0, discover_wifi=args.wifi)
    log("============\t%d DEVICES\t============" % len(ALL_DEVICES))
    for device in ALL_DEVICES:
        log("{} ({})".format(device.name, device.ip))
    if args.shutdown:
        for device in ALL_DEVICES:
            forceScreenOnViaPower(device)
            sleep(1)
        power_off(checkPlug=False)
        shutdownBarrier = Barrier(len(ALL_DEVICES)+1)
        for device in ALL_DEVICES:
            Thread(target = shutdownDevice, args=(device,shutdownBarrier)).start()
            sleep(5)
        shutdownBarrier.wait()
        return
    if args.reboot_devices:
        for device in ALL_DEVICES:
            forceScreenOnViaPower(device)
            sleep(1)
            adb.rebootAndWait(device)
    if args.screen_off:
        for device in ALL_DEVICES:
            adb.screenOff(device)
    if args.screen_on:
        for device in ALL_DEVICES:
            forceScreenOnViaPower(device)
    devices_with_screen_off = []
    for device in ALL_DEVICES:
        if not adb.hasScreenOn(device):
            devices_with_screen_off.append(device)
    if args.install:
        log('INSTALLING_APKS')
        for device in ALL_DEVICES:
            installPackage(device)
    if args.debug_grpc:
        grpcControls.grpcLogs.debug = True
        grpcControls.grpcLogs.log_file = LOG_FILE
        grpcControls.grpcLogs.lock = LOGS_LOCK
    for cfg in args.configs:
        readConfig(cfg)
        shutil.copy(cfg, "{}/{}.loaded".format(loaded_experiments,cfg.split("/")[-1]))
    if len(EXPERIMENTS) > 0 or len(SCHEDULED_EXPERIMENTS) > 0:
        fixULimit()
        log("===================================")
        for device in ALL_DEVICES:
            log("CHECKING_PACKAGE\t%s\t" % device.name, end="")
            forceScreenOnViaPower(device)
            if not adb.checkPackageInstalled(device=device):
                log('MISSING', "\n", False)
                installPackage(device)
            else:
                log('FOUND', "\n", False)
    for device in devices_with_screen_off:
        adb.screenOff(device)
    #EXPERIMENTS.sort(key=lambda e: e.devices+e.producers-e.request_time+len(e.cloudlets), reverse=False)

    if args.use_curses and not args.use_stdout:
        CURSES = draw_curses()
        complete_progress = CURSES.add_text(1,60,0,text="LOGS: {}".format(experiment_name))
        CURSES_LOGS = deque(maxlen=max(0, CURSES.maxHeight()-5))
        CURSES.add_text(1,10,2,text="PROGRESS:")
        progressBar_0 = CURSES.add_progress_bar(1,60,2,10)
        progressBar_0.updateProgress(0)
        complete_progress = CURSES.add_text(1,15,1)

    i = 0
    while i < len(EXPERIMENTS) or len(SCHEDULED_EXPERIMENTS) > 0 or args.daemon:
        run_scheduled = False
        next_experiment = None
        for e,t in SCHEDULED_EXPERIMENTS.items():
            if (t[0] <= gmtime().tm_hour and t[1] >= gmtime().tm_hour and t[1] >= t[0]) or (t[1] < t[0] and (t[0] <= gmtime().tm_hour or t[1] >= gmtime().tm_hour)):
                run_scheduled = True
                next_experiment = e
                SCHEDULED_EXPERIMENTS.pop(e, None)
                break
        missing_experiments.truncate(0)
        missing_experiments.seek(0)
        if not run_scheduled and i < len(EXPERIMENTS):
            next_experiment = EXPERIMENTS[i]
            for e in EXPERIMENTS[i+1:]:
                missing_experiments.write(e.name+"\n")
        else:
            for e in EXPERIMENTS[i:]:
                missing_experiments.write(e.name+"\n")
        for e,t in SCHEDULED_EXPERIMENTS.items():
            missing_experiments.write(e.name+"\t({} - {})\n".format(t[0], t[1]))
        missing_experiments.flush()
        if next_experiment is not None:
            in_progress_experiments.write(next_experiment.name+"\n")
            in_progress_experiments.flush()
        if args.use_curses:
            progressBar_0.updateProgress(100*(i/max(len(EXPERIMENTS), 1)))
            complete_progress.updateText("COMPLETE {}/{}".format(i,len(EXPERIMENTS)))
            sleep(2)
        if next_experiment is not None:
            runExperiment(next_experiment)
            in_progress_experiments.truncate(0)
            in_progress_experiments.seek(0)
            completed_experiments.write(next_experiment.name+"\n")
            completed_experiments.flush()
        else:
            sleep(5)
        for file in os.listdir(new_experiments):
            if os.path.isfile("{}/{}".format(new_experiments,file)):
                readConfig("{}/{}".format(new_experiments,file))
                shutil.move("{}/{}".format(new_experiments,file), "{}/{}.loaded".format(loaded_experiments,file))
        if not run_scheduled and next_experiment is not None:
            i += 1
    for device in ALL_DEVICES:
        adb.screenOff(device)
    if args.use_curses:
        progressBar_0.updateProgress(100)
        complete_progress.updateText("")

if __name__ == '__main__':
    main()
