#!/usr/bin/env python
#!/usr/bin/python3
import subprocess
from time import sleep, time
from re import match
import os

PACKAGE = 'pt.up.fc.dcc.hyrax.odlib'
LAUNCHER_PACKAGE = 'pt.up.fc.dcc.hyrax.od_launcher'
LAUNCHER_SERVICE = '.ODLauncherService'
BROKER = '.services.BrokerAndroidService'
SCHEDULER = '.services.SchedulerAndroidService'
WORKER = '.services.WorkerAndroidService'
DEBUG = False

# TODO: Listar todos os dispositivos disponiveis.
#       1º availar todos os dispositivos ligados por USB
#       2º tentar ligar o ADB Wifi em Todos estes
#       3º discoverWifiADBDevices (pode-se evitar os que já se conhece)
#       4º criar novos Device que só existam por ADB Wifi
#       5º tentar ler o nome do dispositivo por ADB para identificar o dispositivo


class Device:
    name = ""
    ip = ""
    status = False
    connected_wifi = False
    connected_usb = True

    def __init__(self, name, ip = "", status = False, wifi = False, usb=True):
        self.name = name
        self.ip = ip
        self.status = status
        self.connected_wifi = wifi
        self.connected_usb = usb

FNULL = open(os.devnull, "w")

def adb(cmd, device=None, force_usb=False):
    selected_device = []
    if(device != None):
        if (device.connected_wifi and not force_usb):
            selected_device = ['-s', "%s:5555" % device.ip]
        elif (device.connected_usb):
            selected_device = ['-s', device.name]
    if (DEBUG):
        if device is not None:
            if (device.connected_wifi and not force_usb):
                debug = "[{}/{}:5555]\twifi_adb".format(device.name, device.ip)
            elif (device.connected_usb):
                debug = "[%s]\tadb" % device.name
            else:
                debug = "[%s]\terror_adb" % device.name
        else:
            if (device.connected_wifi and not force_usb):
                debug = "wifi_adb"
            elif (device.connected_usb):
                debug = "adb"
            else:
                debug = "error_adb"
        for i in selected_device:
            debug += " " + i
        for i in cmd:
            debug += " " + i
        #print(debug)
    result = subprocess.run(['adb'] + selected_device + cmd, stdout=subprocess.PIPE, stderr=FNULL)
    return result.stdout.decode('UTF-8')

def setBrightness(device=None, brightness=0):
    adb(['shell', 'settings', 'put', 'system', 'screen_brightness_mode', str(0)], device)
    adb(['shell', 'settings', 'put', 'system', 'screen_brightness', str(brightness)], device)

def gcloud(cmd):
  result = subprocess.run(['gcloud'] + cmd, stdout=subprocess.PIPE, stderr=FNULL)
  return result.stdout.decode('UTF-8')

def getBatteryLevel(device=None):
    battery_details = adb(['shell', 'dumpsys', 'battery'], device)
    level_start = battery_details.find('level:')
    if (level_start == -1):
        return -1
    battery_details = battery_details[level_start + 7:]
    level_end = battery_details.find('\n')
    if (level_end == -1):
        return -1
    return int(battery_details[:level_end])

def enableWifiADB(device):
    adb(['tcpip', '5555'], device)

def connectWifiADB(device):
    status = adb(['connect', "%s:5555" % device.ip])
    if (status == "connected to %s:5555\n" % device.ip) or (status == "already connected to %s:5555\n" % device.ip):
        device.connected_wifi = True
        return (device, True)
    return (device, False)

def disconnectWifiADB(device):
    adb(['disconnect', "%s:5555" % device.ip])
    device.connected_wifi = False

def listDevices(minBattery = 15):
    devices_raw = adb(['devices']).split('\n')[1:]
    devices = []
    for dev in devices_raw:
        splitted = dev.split('\t')
        if (len(splitted) > 1 and splitted[1] == 'device'):
            new_device = Device(splitted[0], status = (splitted[1] == 'device' ))
            if (getBatteryLevel(new_device) >= minBattery):
                new_device.ip = getDeviceIp(new_device)
                if (len(new_device.name) > 5 and new_device.name[:-5] == new_device.ip):
                    continue
                device_wifi_adb = False
                for sub_dev in devices_raw:
                    if "%s:5555" % new_device.ip in sub_dev.split('\t')[0]:
                        new_device.connected_wifi = True
                        break
                devices.append(new_device)
    return devices

def discoverWifiADBDevices(ip_mask="192.168.1.{}", range_min=0, range_max=256):
    devices = []
    for n in range(range_min, range_max):
        status = adb(['connect', "{}:5555".format(ip_mask.format(n))])
        if (status == "connected to {}:5555\n".format(ip_mask.format(n))) or (status == "already connected to {}:5555\n".format(ip_mask.format(n))):
            devices.append(ip_mask.format(n))
    return devices

def mkdir(path='Android/data/pt.up.fc.dcc.hyrax.od_launcher/files/', basepath='/sdcard/', device=None):
    status = adb(['shell', 'mkdir', '%s%s' % (basepath, path)], device)
    if ('File exists' in status):
        return True # Return true if folder already exists
    return False

def rmFiles(path='Android/data/pt.up.fc.dcc.hyrax.od_launcher/files/', basepath='/sdcard/', device=None):
    status = adb(['shell', 'rm', '-rf', '%s%s/' % (basepath, path)], device)
    mkdir(path, basepath, device)

def pushFile(filePath, fileName, path='Android/data/pt.up.fc.dcc.hyrax.od_launcher/files/', basepath='/sdcard/', device=None):
    adb(['push', '%s/%s' % (filePath, fileName), '%s%s/%s' % (basepath, path, fileName)], device)

def listFiles(filePath='Android/data/pt.up.fc.dcc.hyrax.od_launcher/files/', basepath='/sdcard/', device=None):
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

def screenOn(device = None):
    #adb(['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'], device)
    status = adb(['shell', 'dumpsys', 'power'], device)
    if (status.find('Display Power: state=OFF') != -1):
        adb(['shell', 'input', 'keyevent', 'KEYCODE_POWER'], device)

def screenOff(device = None):
    status = adb(['shell', 'dumpsys', 'power'], device)
    if (status.find('Display Power: state=ON') != -1):
        adb(['shell', 'input', 'keyevent', 'KEYCODE_POWER'], device)

def startService(service, package=PACKAGE, device=None, wait=False, timeout=120): # 2mins timeout
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
                adb(['shell', 'am', 'startservice', "%s/%s" % (package, service)], device)
        sleep(4)
    return True

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

def pmInstallPackage(packagePath, package, device=None):
    adb(['shell', 'pm', 'install', '/sdcard/%s' % package], device)

def uninstallPackage(device=None):
    adb(['shell', 'pm', 'uninstall', LAUNCHER_PACKAGE], device)

def removePackage(device=None):
    adb(['shell', 'pm', 'clear', LAUNCHER_PACKAGE], device)
    adb(['shell', 'pm', 'reset-permissions', LAUNCHER_PACKAGE], device)
    uninstallPackage(device)

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

def getDeviceIp(device, timeout=120):
    start_time = time()
    while time()-start_time < timeout:
        info = adb(['shell', 'ip', 'addr', 'show', 'wlan0'], device)
        info = info[info.find('inet ')+5:]
        ip = info[:info.find('/')]
        if (match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",ip)):
            return ip
        sleep(2)
    return None

def rebootAndWait(device, timeout=300):
    start_time = time()
    #adb(['reboot'], device, True)
    #sleep(2)
    adb(['reboot'], device)
    if (device.connected_wifi):
        device.connected_wifi = False
        while (not connectWifiADB(device)[1]):
            if (time()-start_time > timeout):
                return False
            sleep(5)
    else:
        adb(['wait-for-device'], device)
    while (adb(['shell', 'getprop', 'dev.bootcomplete'], device).find('1') == -1):
        if (time()-start_time > timeout):
            return False
        sleep(5)
    return True


def isServiceRunning(device, service):
    service_info = adb(['shell', 'dumpsys', 'activity', 'services', service], device)
    return service_info.find(service) != -1
