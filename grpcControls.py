import Launcher_pb2
import Launcher_pb2_grpc
import ODProto_pb2
import ODProto_pb2_grpc

from google.protobuf import empty_pb2 as google_empty
from google.protobuf.wrappers_pb2 import BoolValue as google_bool

import grpc
from grpc import ChannelConnectivity

from time import sleep
import uuid


class remoteClient:
    launcherChannel = None
    brokerChannel = None
    brokerStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStub = None
    ip = None
    name = ""
    schedulers = None
    models = None

    def __init__(self, ip, adbName):
        self.ip = ip
        self.name = adbName

    def launcherStubStatusCallback(self, status):
        self.launcherStubStatus = status

    def brokerStubStatusCallback(self, status):
        self.brokerStubStatus = status

    def connectLauncherService(self):
        self.launcherChannel = grpc.insecure_channel('%s:50000' % self.ip)
        self.launcherStub = Launcher_pb2_grpc.LauncherServiceStub(self.launcherChannel)
        self.launcherStubReady()

    def connectBrokerService(self):
        self.brokerChannel = grpc.insecure_channel('%s:50051' % self.ip)
        self.brokerStub = ODProto_pb2_grpc.BrokerServiceStub(self.brokerChannel)
        self.brokerStubReady()

    def __checkChannelStatus(self, channel, channelStatus, callback):
        if (channelStatus == ChannelConnectivity.READY):
            return True
        if (channel is not None):
            channel.subscribe(callback, True)
            sleep(0.5)
            return channelStatus == ChannelConnectivity.READY
        else:
            return False

    def launcherStubReady(self):
        return self.__checkChannelStatus(self.launcherChannel, self.launcherStubStatus, self.launcherStubStatusCallback)

    def brokerStubReady(self):
        return self.__checkChannelStatus(self.brokerChannel, self.brokerStubStatus, self.brokerStubStatusCallback)

    def startWorker(self):
        if (self.launcherStubReady()):
            print("startWorker")
            print(self.launcherStub.StartWorker(Launcher_pb2.Empty()))

    def startScheduler(self):
        if (self.launcherStubReady()):
            print("startScheduler")
            print(self.launcherStub.StartScheduler(Launcher_pb2.Empty()))

    def listSchedulers(self):
        if (self.brokerStubReady()):
            self.schedulers = self.brokerStub.getSchedulers(google_empty.Empty())
        return self.schedulers

    def listModels(self):
        if (self.brokerStubReady()):
            self.models = self.brokerStub.getModels(google_empty.Empty())
        return self.models

    def setScheduler(self, scheduler):
        if (self.brokerStubReady()):
            return self.brokerStub.setScheduler(scheduler)
        return None

    def setModel(self, model):
        if (self.brokerStubReady()):
            return self.brokerStub.setModel(model)
        return None

    def scheduleJob(self, job):
        if (self.brokerStubReady()):
            return self.brokerStub.scheduleJob(job.getProto())

    def setLogName(self, log_name):
        if (self.launcherStubReady()):
            name = Launcher_pb2.String()
            name.str = log_name
            print(self.launcherStub.SetLogName(name))

class Job:
    id = ""
    data = None

    def __init__(self):
        self.id = str(uuid.uuid4())

    def addBytes(self, bytes):
        self.data = bytes

    def getProto(self):
        job = ODProto_pb2.Job()
        job.id = self.id
        job.data = self.data
        return job
