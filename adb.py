#!/usr/bin/env python
#!/usr/bin/python3
import subprocess

PACKAGE = 'pt.up.fc.dcc.hyrax.odlib'
BROKER = '.services.BrokerAndroidService'
SCHEDULER = '.services.SchedulerAndroidService'
WORKER = '.services.WorkerAndroidService'

def adb(cmd):
  result = subprocess.run(['adb'] + cmd, stdout=subprocess.PIPE)
  return result.stdout.decode('UTF-8')

def gcloud(cmd):
  result = subprocess.run(['gcloud'] + cmd, stdout=subprocess.PIPE)
  return result.stdout.decode('UTF-8')

def listDevices():
    devices_raw = adb(['devices']).split('\n')[1:]
    devices = []
    for dev in devices_raw:
        splitted = dev.split('\t')
        if (len(splitted) > 1 and splitted[1] == 'device'):
            devices.append(splitted[0])
    return devices

def startService(service):
    adb(['am', 'startservice', "%s/%s" % (PACKAGE, service)])

def stopService(service):
    adb(['am', 'stopservice', "%s/%s" % (PACKAGE, service)])

def init():
    adb(['start-server'])

def close():
    adb(['kill-server'])

def checkPackageInstalled():
    return (PACKAGE in adb(['shell', 'pm', 'list', 'packages']))

def installPackage(package):
    adb(['install', package])

def removePackage():
    adb(['shell', 'pm', 'clear', PACKAGE])
    adb(['shell', 'pm', 'reset-permissions', PACKAGE])
    adb(['shell', 'pm', 'uninstall', PACKAGE])

def cloudInstanceRunning(instanceName = 'hyrax'):
    instances = gcloud(['compute', 'instances', 'list']).split('\n')
    for instance in instances:
        if instanceName in instance and 'RUNNING' in instance:
            return True
    return False

def cloudInstanceStart(instanceName = 'hyrax'):
    if cloudInstanceRunning(instanceName):
        return
    gcloud(['compute', 'instances', 'start', instanceName])

def cloudInstanceStop(instanceName = 'hyrax'):
    if cloudInstanceRunning(instanceName):
        gcloud(['compute', 'instances', 'stop', instanceName])

def startApplication(applicationName = 'pt.up.fc.dcc.hyrax.odlib', entryPoint = 'MainActivity'):
    adb(['shell', 'am', 'start', '-n', "%s/%s.%s" % (PACKAGE, applicationName, entryPoint)])


def forceStopApplication(applicationName = 'pt.up.fc.dcc.hyrax.odlib', entryPoint = 'MainActivity'):
    adb(['shell', 'am', 'force-stop', PACKAGE])

if __name__ == '__main__':
    startApplication()
    forceStopApplication()
    exit()
    cloudInstanceStart()
    init()
    print(listDevices())
    print(checkPackageInstalled())
    removePackage()
    print(checkPackageInstalled())
    close()
