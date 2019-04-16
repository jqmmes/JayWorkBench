import grpcControls
from time import sleep

def main():
    worker = grpcControls.remoteClient('192.168.1.13')
    worker.connectLauncherService()
    worker.startWorker()
    worker.startScheduler()
    worker.connectBrokerService()
    sleep(1)
    worker.setScheduler(worker.listSchedulers().scheduler[0])
    worker.setModel(worker.listModels().models[0])
    job = grpcControls.Job()
    with open("img.jpg", "rb") as image:
        f = image.read()
        b = bytes(f)
        job.addBytes(b)
    print(worker.scheduleJob(job))






if __name__ == '__main__':
    main()
