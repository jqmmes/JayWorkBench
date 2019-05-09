#!/usr/bin/env python
#!/usr/bin/python3
import subprocess
from time import sleep

PACKAGE = 'pt.up.fc.dcc.hyrax.odlib'
LAUNCHER_PACKAGE = 'pt.up.fc.dcc.hyrax.od_launcher'
LAUNCHER_SERVICE = '.ODLauncherService'
BROKER = '.services.BrokerAndroidService'
SCHEDULER = '.services.SchedulerAndroidService'
WORKER = '.services.WorkerAndroidService'
DEBUG = True

def adb(cmd, device=None):
    selected_device = []
    if(device != None):
        selected_device = ['-s', device]
    debug = "adb"
    for i in selected_device:
        debug += " " + i
    for i in cmd:
        debug += " " + i
    if (DEBUG):
        print(debug)
    result = subprocess.run(['adb'] + selected_device + cmd, stdout=subprocess.PIPE, stderr=None)
    return result.stdout.decode('UTF-8')

def gcloud(cmd):
  result = subprocess.run(['gcloud'] + cmd, stdout=subprocess.PIPE)
  return result.stdout.decode('UTF-8')

def getBatteryLevel(device=None):
    battery_details = adb(['shell', 'dumpsys', 'battery'], device)
    level_start = battery_details.find('level:')
    if (level_start == -1):
        return 0
    battery_details = battery_details[level_start + 7:]
    level_end = battery_details.find('\n')
    if (level_end == -1):
        return 0
    return int(battery_details[:level_end])

def listDevices(minBattery = 15):
    devices_raw = adb(['devices']).split('\n')[1:]
    devices = []
    for dev in devices_raw:
        splitted = dev.split('\t')
        if (len(splitted) > 1 and splitted[1] == 'device'):
            if (getBatteryLevel(splitted[0]) >= minBattery):
                devices.append(splitted[0])
    return devices

def clearSystemLog(device=None):
    adb(['logcat', '-d'], device)

def pullSystemLog(device=None, path=""):
    destinationFile="system_log.txt"
    if path != "" and path[-1] != "/":
        path += "/"
    if device is not None:
        destinationFile = device + "_" + destinationFile
    with open("%s%s" % (path, destinationFile), "w+") as log:
        log.write(adb(['logcat', 'd'], device))
        log.close()

def screenOn(device = None):
    adb(['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'], device)

def screenOff(device = None):
    status = adb(['shell', 'dumpsys', 'power'], device)
    if (status.find('Display Power: state=ON') != -1):
        adb(['shell', 'input', 'keyevent', 'KEYCODE_POWER'], device)

def startService(service, package=PACKAGE, device=None, wait=False):
    adb(['shell', 'am', 'startservice', "%s/%s" % (package, service)], device)
    if wait:
        while not isServiceRunning(device, service):
            sleep(0.5)
        sleep(4)

def stopService(service, package=PACKAGE, device=None):
    adb(['shell', 'am', 'stopservice', "%s/%s" % (package, service)], device)

def stopAll(device=None):
    stopService(LAUNCHER_SERVICE, LAUNCHER_PACKAGE, device)
    forceStopApplication(PACKAGE, device=device)
    stopService("%s%s" % (PACKAGE, WORKER), LAUNCHER_PACKAGE, device)
    stopService("%s%s" % (PACKAGE, SCHEDULER), LAUNCHER_PACKAGE, device)
    stopService("%s%s" % (PACKAGE, BROKER), LAUNCHER_PACKAGE, device)

def init():
    adb(['start-server'])

def close():
    adb(['kill-server'])

def checkPackageInstalled(device=None):
    return (PACKAGE in adb(['shell', 'pm', 'list', 'packages'], device))

def installPackage(package, device=None):
    adb(['install', package], device)

def removePackage(device=None):
    adb(['shell', 'pm', 'clear', PACKAGE], device)
    adb(['shell', 'pm', 'reset-permissions', PACKAGE], device)
    adb(['shell', 'pm', 'uninstall', PACKAGE], device)

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

def startApplication(applicationName = 'pt.up.fc.dcc.hyrax.odlib', entryPoint = 'MainActivity', device=None):
    adb(['shell', 'am', 'start', '-n', "%s/%s.%s" % (PACKAGE, applicationName, entryPoint)], device)


def forceStopApplication(applicationName = 'pt.up.fc.dcc.hyrax.odlib', device=None):
    adb(['shell', 'am', 'force-stop', applicationName], device)

def pullLog(applicationName=PACKAGE, path="files/log", format="csv", destination=".", device=None):
    adb(['pull', "/sdcard/Android/data/%s/%s.%s" % (applicationName, path, format), destination], device)

def getDeviceIp(device):
    info = adb(['shell', 'ip', 'addr', 'show', 'wlan0'], device)
    info = info[info.find('inet ')+5:]
    return info[:info.find('/')]

def rebootAndWait(device):
    adb(['reboot'], device)
    adb(['wait-for-device'], device)
    while (adb(['shell', 'getprop', 'dev.bootcomplete'], device).find('1') == -1):
        sleep(5)

def isServiceRunning(device, service):
    service_info = adb(['shell', 'dumpsys', 'activity', 'services', service], device)
    return service_info.find(service) != -1
