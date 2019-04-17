import grpcControls
from time import sleep
import random
import threading
import os
import adb
import configparser
from sys import argv


RATE = 1/5 # Events/Seconds --> Events per seconds
ASSETS=os.listdir("assets")

LOG_NAME='Log_03'

def run():
    devices = adb.listDevices()
    for device in devices:
        adb.rebootAndWait(device)
        adb.stopAll()
        adb.startService(adb.LAUNCHER_SERVICE, adb.LAUNCHER_PACKAGE, device, wait=True)
    worker = grpcControls.remoteClient(adb.getDeviceIp(devices[0]), devices[0])
    worker.connectLauncherService()
    worker.setLogName(LOG_NAME)
    worker.startWorker()
    worker.startScheduler()
    worker.connectBrokerService()
    sleep(1)
    print(worker.listSchedulers())
    worker.setScheduler(worker.listSchedulers().scheduler[0])
    worker.setModel(worker.listModels().models[0])
    while True:
        sleep(random.expovariate(RATE))
        threading.Thread(target = runJob, args = (worker,)).start()
    adb.stopAll()
    adb.pullLog(adb.LAUNCHER_PACKAGE, 'files/%s' % LOG_NAME, destination='logs/%s_%s.csv' % (devices[0], LOG_NAME))



def runJob(worker):
    job = grpcControls.Job()
    asset = ASSETS[random.randint(0,len(ASSETS)-1)]

    while (asset[-4:] not in ['.png', '.jpg']):
        asset = ASSETS[random.randint(0,len(ASSETS)-1)]

    with open("assets/%s" % asset, "rb") as image:
        f = image.read()
        b = bytes(f)
        job.addBytes(b)
    print("%s\t%s" % (asset, job.id))
    print(worker.scheduleJob(job))


def main():



if __name__ == '__main__':
    main()
