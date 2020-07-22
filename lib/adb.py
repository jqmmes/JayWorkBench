#!/usr/bin/env python
#!/usr/bin/python3
import subprocess
from time import sleep, time, ctime
from re import match, findall
import os
import platform
import threading
import concurrent.futures
from sys import stdout

JAY_SERVICE_PACKAGE = 'pt.up.fc.dcc.hyrax.jay'
LAUNCHER_APP = 'pt.up.fc.dcc.hyrax.jay_droid_launcher'
LAUNCHER_PACKAGE = 'pt.up.fc.dcc.hyrax.droid_jay_app'
LAUNCHER_SERVICE = 'pt.up.fc.dcc.hyrax.droid_jay_app.DroidJayLauncherService'
BROKER = '.services.BrokerAndroidService'
SCHEDULER = '.services.SchedulerAndroidService'
WORKER = '.services.WorkerAndroidService'
DEBUG = False
ADB_DEBUG_FILE = stdout
ADB_LOGS_LOCK = None
LOG_LEVEL = "ACTION" # "ALL", "ACTION", "COMMAND"
FORCE_USB = False

def getOs():
    if platform.system() == "Darwin":
        return "mac"
    if platform.system() == "Linux":
        return "linux"
    else:
        return ""

ADB_BIN = "{}/lib/adb/{}/adb".format(os.getcwd(), getOs())

class Device:
    name = ""
    ip = ""
    status = False
    connected_wifi = False
    connected_usb = True
    already_rebooted = False
    battery_level = 0

    def __init__(self, name, ip = "", status = False, wifi = False, usb=True):
        self.name = name
        self.ip = ip
        self.status = status
        self.connected_wifi = wifi
        self.connected_usb = usb



FNULL = open(os.devnull, "w")

def log(str, level, end="\n"):
    global ADB_LOGS_LOCK
    if DEBUG and ADB_DEBUG_FILE is not None and (level == LOG_LEVEL or LOG_LEVEL == "ALL"):
        lock_acquired = False
        if ADB_LOGS_LOCK is not None:
            lock_acquired = ADB_LOGS_LOCK.acquire(timeout=2)
        try:
            ADB_DEBUG_FILE.write(ctime()+"\t"+str)
        except:
            None
        try:
            ADB_DEBUG_FILE.write(end)
        except:
            None
        ADB_DEBUG_FILE.flush()
        if lock_acquired:
            ADB_LOGS_LOCK.release()

def adb(cmd, device=None, force_usb=False, log_command=True, timeout=None):
    if (FORCE_USB):
        force_usb = True
    selected_device = []
    if (DEBUG and log_command):
        if device is not None:
            if (device.connected_wifi and not force_usb):
                debug = "[{}/{}:5555]\twifi_adb".format(device.name, device.ip)
            elif (device.connected_usb):
                debug = "[%s]\tadb" % device.name
            else:
                debug = "[%s]\terror_adb" % device.name
        else:
            debug = "adb"
        for i in selected_device:
            debug += " " + i
        for i in cmd:
            debug += " " + i
        log(debug, "COMMAND")
    if(device != None):
        usb_connection_active, wifi_connection_active = getADBStatus(device, log_command=False)
        if (not wifi_connection_active and not device.connected_wifi and not force_usb):
            try:
                enableWifiADB(device)
                connectWifiADB(device)
            except:
                pass
        if (not wifi_connection_active and device.connected_wifi and not force_usb):
            wifi_connection_active = connectWifiADB(device, force_connection=True)[1]
        if (device.connected_wifi and wifi_connection_active and not force_usb):
            selected_device = ['-s', "%s:5555" % device.ip]
        elif (device.connected_usb and usb_connection_active):
            selected_device = ['-s', device.name]
        else:
            return "FAILED_TO_RUN_ADB_PLEASE_CANCEL"
    if timeout != None:
        try:
            result = subprocess.run([ADB_BIN] + selected_device + cmd, stdout=subprocess.PIPE, stderr=FNULL, timeout=timeout)
        except:
            return True
    else:
        result = subprocess.run([ADB_BIN] + selected_device + cmd, stdout=subprocess.PIPE, stderr=FNULL)
    return result.stdout.decode('UTF-8')

def setBrightness(device=None, brightness=0):
    adb(['shell', 'settings', 'put', 'system', 'screen_brightness_mode', str(0)], device)
    adb(['shell', 'settings', 'put', 'system', 'screen_brightness', str(brightness)], device)

def gcloud(cmd):
  result = subprocess.run(['gcloud'] + cmd, stdout=subprocess.PIPE, stderr=FNULL)
  return result.stdout.decode('UTF-8')

def getBatteryLevel(device=None, retries=3):
    if (retries <= 0):
        return -1
    battery_details = adb(['shell', 'dumpsys', 'battery'], device)
    level_start = battery_details.find('level:')
    if (level_start == -1):
        sleep(1)
        return getBatteryLevel(device, retries-1)
    battery_details = battery_details[level_start + 7:]
    level_end = battery_details.find('\n')
    if (level_end == -1):
        sleep(1)
        return getBatteryLevel(device, retries-1)
    return int(battery_details[:level_end])

def enableWifiADB(device):
    adb(['tcpip', '5555'], device, True)
    sleep(5)

def getADBStatus(device, log_command=True):
    devices_raw = adb(['devices'], log_command=log_command).split('\n')[1:]
    connected_usb = False
    connected_wifi = False
    for raw_device in devices_raw:
        splitted = raw_device.split('\t')
        if len(splitted) > 1:
            if splitted[0] == "%s:5555" % device.ip and splitted[1] == 'device':
                connected_wifi = True
            elif splitted[0] == device.name and splitted[1] == 'device':
                connected_usb = True
    return (connected_usb, connected_wifi)

def isADBWiFiOffline(device, log_command=True):
    devices_raw = adb(['devices'], log_command=log_command).split('\n')[1:]
    for raw_device in devices_raw:
        splitted = raw_device.split('\t')
        if len(splitted) > 1:
            if splitted[0] == "%s:5555" % device.ip and splitted[1] == 'offline':
                return True
    return False

def connectWifiADB(device, retries=3, force_connection=True):
    if retries <= 0 or FORCE_USB:
        return (device, False)
    if (not match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", device.ip)):
        probable_ip = getDeviceIp(new_device)
        if (not match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", probable_ip)):
            return (device, False)
        device.ip = probable_ip
    log("ADB_CONNECT_WIFI_ADB\t{} ({})".format(device.name, device.ip), "ACTION")
    status = adb(['connect', "%s:5555" % device.ip])
    if (status == "connected to %s:5555\n" % device.ip) or (status == "already connected to %s:5555\n" % device.ip):
        device.connected_wifi = True
    if not force_connection:
        if device.connected_wifi:
            return (device, True)
        return (device, False)
    else:
        if device.connected_wifi:
            for x in range(3):
                force_usb, connected = getADBStatus(device, log_command=False)
                if connected:
                    return (device, True)
                else:
                    if isADBWiFiOffline(device, log_command=False):
                        disconnectWifiADB(device)
                        sleep(2)
                        status = adb(['connect', "%s:5555" % device.ip])
                        if (status == "connected to %s:5555\n" % device.ip) or (status == "already connected to %s:5555\n" % device.ip):
                            device.connected_wifi = True
                sleep(5)
        force_usb, _ = getADBStatus(device, log_command=False)
        if force_usb:
            if rebootAndWait(device, connectWifi=True, force_usb=True):
                return (device, True)
            return connectWifiADB(device, retries-1, force_connection)
        else:
            return (device, False)
    return (device, False)

def disconnectWifiADB(device):
    adb(['disconnect', "%s:5555" % device.ip])
    device.connected_wifi = False

def getWifiDeviceNameByIp(device_ip, retries=5):
    if retries <= 0:
        return "unknown_device_{}".format(device_ip)
    result = subprocess.run([ADB_BIN, "-s", "{}:5555".format(device_ip), "shell", "getprop ro.serialno"], stdout=subprocess.PIPE, stderr=FNULL)
    if result.returncode == 0:
        return result.stdout.decode('UTF-8').rstrip("\n")
    else:
        sleep(1)
        return getWifiDeviceNameByIp(device_ip, retries-1)

def listDevices(minBattery = 15, discover_wifi=False, ip_mask="192.168.1.{}", range_min=2, range_max=256):
    repeats = 3
    while(repeats > 0):
        devices_raw = adb(['devices']).split('\n')[1:]
        ok = False
        for dev in devices_raw:
            if (dev != ""):
                ok = True
        if (ok):
            break
        else:
            close()
            init()
        repeats -= 1
    devices = []
    for dev in devices_raw:
        splitted = dev.split('\t')
        if (len(splitted) > 1 and splitted[1] == 'device'):
            # Test if its an ip address
            is_ip = False
            name = splitted[0]
            if (match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",splitted[0])):
                ip = splitted[0][:splitted[0].find(":")]
                is_ip = True
                new_device = Device(getWifiDeviceNameByIp(ip), ip = ip, status = (splitted[1] == 'device' ), wifi=True, usb=False)
            else:
                new_device = Device(splitted[0], status = (splitted[1] == 'device' ))
            if (getBatteryLevel(new_device) >= minBattery):
                if not is_ip:
                    new_device.ip = getDeviceIp(new_device)
                is_new_device = True
                for dev in devices:
                    if dev.name == new_device.name:
                        if not dev.connected_usb and new_device.connected_usb:
                            dev.connected_usb = True
                        if not dev.connected_wifi and new_device.connected_wifi:
                            dev.connected_wifi = True
                            dev.ip = new_device.ip
                        is_new_device = False
                        break
                    if dev.ip == new_device.ip:
                        dev.name = new_device.name
                        if not dev.connected_wifi and new_device.connected_wifi:
                            dev.connected_wifi = True
                            dev.ip = new_device.ip
                        is_new_device = False
                        break
                if not is_new_device:
                    continue
                if not new_device.connected_wifi and new_device.ip != "":
                    new_device, status = connectWifiADB(new_device)
                if not new_device.connected_usb:
                    new_device.connected_usb = getADBStatus(new_device)[0]
                devices.append(new_device)
                log("NEW_DEVICE\t{} ({})\tUSB: {}\tWIFI: {}".format(new_device.name, new_device.ip, new_device.connected_usb, new_device.connected_wifi), "ACTION")
    if discover_wifi:
        log("DISCOVERING_WIFI_DEVICES", "ACTION")
        network_devices = discoverWifiADBDevices(ip_mask, range_min, range_max, devices)
        devices_raw = adb(['devices']).split('\n')[1:]
        for ip in network_devices:
            new_device = Device(getWifiDeviceNameByIp(ip), ip=ip, status=True, wifi=True, usb=False)
            new_device.connected_usb = getADBStatus(new_device)[0]
            log("NEW_DEVICE\t{} ({})\tUSB: {}\tWIFI: {}".format(new_device.name, new_device.ip, new_device.connected_usb, new_device.connected_wifi), "ACTION")
            if (getBatteryLevel(new_device) >= minBattery):
                devices.append(new_device)
    return devices

COUNTER = 0

def ping_thread(hostname, network_devices=[], lock=None):
    global COUNTER
    response = subprocess.run(['ping', '-t 5', '-c 5', hostname], stdout=FNULL, stderr=FNULL)
    #and then check the response..
    if response.returncode == 0 and lock.acquire(timeout=2):
        network_devices.append(hostname)
        lock.release()
    if lock.acquire(timeout=2):
        COUNTER -= 1
        lock.release()

def getIgnoredIps():
    try:
        return open("device.ignore", "r").read().split("\n")
    except:
        return []

def discoverWifiADBDevices(ip_mask="192.168.1.{}", range_min=0, range_max=256, ignore_list=[]):
    global COUNTER
    devices = []
    network_devices = []
    ignored = getIgnoredIps()
    reps = 2
    while (reps > 0):
        response = subprocess.run(['nmap', '-sP', ip_mask.format(1) + "/24", "--host-timeout", "15"], stdout=subprocess.PIPE, stderr=FNULL)
        for entry in findall("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", response.stdout.decode("UTF-8")):
            if entry not in network_devices:
                network_devices.append(entry)
        reps -= 1
        sleep(3)
    for host in network_devices:
        if host in ignored + ignore_list:
            continue
        add_host = True
        for ignore in ignore_list:
            if host == ignore.ip:
                add_host = False
                continue
        if not add_host:
            continue
        response = subprocess.run(['nmap', '-p', "5555", host], stdout=subprocess.PIPE, stderr=FNULL)
        port_open = findall("5555/tcp\s+open", response.stdout.decode("UTF-8"))
        if len(port_open) == 0:
            continue
        retries = 3
        while retries > 0:
            log("CONNECTING_TO_DEVICE\t%s" % host, "ACTION")
            status = adb(['connect', "{}:5555".format(host)])
            if (status == "connected to {}:5555\n".format(host)) or (status == "already connected to {}:5555\n".format(host)):
                devices.append(host)
                break
            else:
                sleep(2)
            retries -= 1
    return devices

def mkdir(path='Android/data/'+LAUNCHER_APP+'/files/', basepath='/sdcard/', device=None):
    status = adb(['shell', 'mkdir', '%s%s' % (basepath, path)], device)
    if ('File exists' in status):
        return True # Return true if folder already exists
    return False

def rmFiles(path='Android/data/'+LAUNCHER_APP+'/files/', basepath='/sdcard/', device=None):
    status = adb(['shell', 'rm', '-rf', '%s%s/' % (basepath, path)], device)
    mkdir(path, basepath, device)

def pushFile(filePath, fileName, path='Android/data/'+LAUNCHER_APP+'/files/', basepath='/sdcard/', device=None):
    adb(['push', '%s/%s' % (filePath, fileName), '%s%s/%s' % (basepath, path, fileName)], device)

def listFiles(filePath='Android/data/'+LAUNCHER_APP+'/files/', basepath='/sdcard/', device=None):
    status = adb(['ls', basepath+filePath], device).split('\n')
    files = []
    for entry in status:
        try:
            files.append(entry.split()[3])
        except:
            continue
    return files

def freeSpace(partition='/sdcard/', device=None):
    try:
        status = adb(['shell', 'df', '-h', partition], device).split('\n')[1].split()[3]
        if (status.find('G') == -1):
            return 0
        return float(status[:status.find('G')])
    except:
        return 0

def clearSystemLog(device=None):
    adb(['logcat', '-c'], device)

def pullSystemLog(device=None, path=""):
    destinationFile="system_log.txt"
    if path != "" and path[-1] != "/":
        path += "/"
    if device is not None:
        destinationFile = device.name + "_" + destinationFile
    with open("%s%s" % (path, destinationFile), "w+") as log:
        log.write(adb(['logcat', '-d'], device))
        log.close()

def screenOn(device = None, retries = 10):
    #adb(['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'], device)
    if retries <= 0:
        return
    status = adb(['shell', 'dumpsys', 'power'], device)
    if (status.find('Display Power: state=OFF') != -1):
        timed_out = adb(['shell', 'input', 'keyevent', 'KEYCODE_POWER'], device, timeout = 3)
        if timed_out:
            sleep(2)
            return screenOn(device, retries - 1)


def screenOff(device = None):
    status = adb(['shell', 'dumpsys', 'power'], device)
    if (status.find('Display Power: state=ON') != -1):
        adb(['shell', 'input', 'keyevent', 'KEYCODE_POWER'], device)

def startService(service, package=JAY_SERVICE_PACKAGE, device=None, wait=False, timeout=120): # 2mins timeout
    adb(['shell', 'am', 'startservice', "%s/%s" % (package, service)], device)
    start_time = time()
    if wait:
        retries = 0
        while not isServiceRunning(device, service):
            retries += 1
            sleep(0.5)
            if (time()-start_time > timeout):
                return False
            if ((retries % 5) == 0):
                #adb(['shell', "\"su -c \'am startservice %s/%s\'\"" % (package, service)], device)
                adb(['shell', 'am', 'startservice', "%s/%s" % (package, service)], device)
        sleep(4)
    return True

def stopService(service, package=JAY_SERVICE_PACKAGE, device=None):
    adb(['shell', 'am', 'stopservice', "%s/%s" % (package, service)], device)

def stopAll(device=None):
    stopService(LAUNCHER_SERVICE, LAUNCHER_PACKAGE, device)
    forceStopApplication(LAUNCHER_APP, device=device)
    stopService("%s%s" % (JAY_SERVICE_PACKAGE, WORKER), JAY_SERVICE_PACKAGE, device)
    stopService("%s%s" % (JAY_SERVICE_PACKAGE, SCHEDULER), JAY_SERVICE_PACKAGE, device)
    stopService("%s%s" % (JAY_SERVICE_PACKAGE, BROKER), JAY_SERVICE_PACKAGE, device)

def init():
    adb(['start-server'])

def close():
    adb(['kill-server'])

def checkPackageInstalled(package=LAUNCHER_APP, device=None):
    return (package in adb(['shell', 'pm', 'list', 'packages'], device))

def installPackage(path, package, device=None):
    adb(['install', "%s/%s" % (path, package)], device)

def pmInstallPackage(packagePath, package, device=None):
    adb(['shell', 'pm', 'install', '/sdcard/%s' % package.replace(" ", "\ ")], device)

def uninstallPackage(package=LAUNCHER_APP, device=None):
    adb(['shell', 'pm', 'uninstall', package], device)

def removePackage(package=LAUNCHER_APP, device=None):
    adb(['shell', 'pm', 'clear', package], device)
    adb(['shell', 'pm', 'reset-permissions', package], device)
    uninstallPackage(device)

def grantPermission(permission, package=LAUNCHER_APP, device=None):
    adb(['shell', 'pm', 'grant', package, permission], device)

def grantedPermissions(package=LAUNCHER_APP, device=None):
    result = adb(['shell', 'dumpsys', 'package', package], device)
    return findall("\s+(\w+\.\w+\.\w+): granted=true", result)

def cloudInstanceRunning(instanceName = 'hyrax'):
    instances = gcloud(['compute', 'instances', 'list']).split('\n')
    for instance in instances:
        if instanceName in instance and 'RUNNING' in instance:
            return True
    return False

def cloudInstanceStart(instanceName = 'hyrax', zone = 'europe-west1-b'):
    if cloudInstanceRunning(instanceName):
        return
    gcloud(['compute', 'instances', 'start', instanceName, '--zone=' + zone])

def cloudInstanceStop(instanceName = 'hyrax', zone = 'europe-west1-b'):
    if cloudInstanceRunning(instanceName):
        gcloud(['compute', 'instances', 'stop', instanceName, '--zone=' + zone])

def startApplication(appName = LAUNCHER_APP, applicationPackage = LAUNCHER_PACKAGE, entryPoint = 'MainActivity', device=None, wait=False, service=LAUNCHER_SERVICE, retries=5):
    if retries <= 0:
        return False
    adb(['shell', 'am', 'start', '-n', "%s/%s.%s" % (appName, applicationPackage, entryPoint)], device)
    if wait:
        sleep(0.5)
        if not isServiceRunning(device, service):
            sleep(4)
            startApplication(appName, appName, entryPoint, device, wait, service, retries-1)
    return True

def forceStopApplication(applicationPackage = LAUNCHER_APP, device=None):
    adb(['shell', 'am', 'force-stop', applicationPackage], device)

def pullLog(applicationName=LAUNCHER_APP, path="files/log", format="csv", destination=".", device=None):
    adb(['pull', "/sdcard/Android/data/%s/%s.%s" % (applicationName, path, format), destination], device)

def getDeviceIp(device, timeout=10):
    start_time = time()
    while time()-start_time < timeout:
        try:
            force_usb = FORCE_USB
            if (not device.connected_wifi):
                force_usb = True
            info = adb(['shell', 'ip', 'addr', 'show', 'wlan0'], device, force_usb)
            info = info[info.find('inet ')+5:]
            ip = info[:info.find('/')]
        except:
            ip = ""
        if (match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",ip)):
            return ip
        sleep(2)
    return ""

def rebootAndWait(device, timeout=300, connectWifi=False, force_usb=False):
    start_time = time()
    adb(['reboot'], device, force_usb=force_usb)
    if (device.connected_wifi or connectWifi):
        device.connected_wifi = False
        while (not connectWifiADB(device, force_connection=False)[1]):
            if (time()-start_time > timeout):
                return False
            sleep(5)
    else:
        adb(['wait-for-device'], device)
    boot_complete = adb(['shell', 'getprop', 'dev.bootcomplete'], device)
    while (boot_complete is None or boot_complete.find('1') == -1):
        if (time()-start_time > timeout):
            return False
        sleep(5)
        boot_complete = adb(['shell', 'getprop', 'dev.bootcomplete'], device)
    device.already_rebooted = True
    return True

def isServiceRunning(device, service):
    service_info = adb(['shell', 'dumpsys', 'activity', 'services', service], device)
    return service_info.find(service) != -1
