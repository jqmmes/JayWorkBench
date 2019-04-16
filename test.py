import grpcControls
from time import sleep
import random
import threading
import os

RATE = 1/5 # Events/Seconds --> Events per seconds
ASSETS=os.listdir("assets")

def main():
    worker = grpcControls.remoteClient('192.168.1.13')
    worker.connectLauncherService()
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





if __name__ == '__main__':
    main()
