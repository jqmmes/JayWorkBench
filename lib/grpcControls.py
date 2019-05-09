import lib.protobuf.Launcher_pb2
import lib.protobuf.Launcher_pb2_grpc
import lib.protobuf.Cloud_pb2
import lib.protobuf.Cloud_pb2_grpc
import lib.protobuf.ODProto_pb2
import lib.protobuf.ODProto_pb2_grpc

from google.protobuf import empty_pb2 as google_empty
from google.protobuf.wrappers_pb2 import BoolValue as google_bool

import grpc
from grpc import ChannelConnectivity

from time import sleep
import uuid

class cloudClient:
    launcherChannel = None
    brokerChannel = None
    brokerStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStub = None
    ip = None
    name = ""
    models = None

    def __init__(self, ip, adbName):
        self.ip = ip
        self.name = adbName
        print("GRPC %s (%s) __init__" % (self.name, self.ip))

    def launcherStubStatusCallback(self, status):
        print(status)
        self.launcherStubStatus = status

    def brokerStubStatusCallback(self, status):
        self.brokerStubStatus = status

    def connectLauncherService(self, retries=5):
        try:
            self.launcherChannel = grpc.insecure_channel('%s:50000' % self.ip)
            self.launcherStub = Cloud_pb2_grpc.LauncherServiceStub(self.launcherChannel)
            sleep(1)
            self.launcherStubReady()
            print("GRPC %s (%s) connectLauncherService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectLauncherService(retries-1)
            else:
                print("GRPC %s (%s) connectLauncherService FAIL" % (self.name, self.ip))

    def connectBrokerService(self, retries=5):
        try:
            self.brokerChannel = grpc.insecure_channel('%s:50051' % self.ip)
            self.brokerStub = ODProto_pb2_grpc.BrokerServiceStub(self.brokerChannel)
            sleep(1)
            self.brokerStubReady()
            print("GRPC %s (%s) connectBrokerService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectBrokerService(retries-1)
            else:
                print("GRPC %s (%s) connectBrokerService FAIL" % (self.name, self.ip))

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

    def startWorker(self, retries=5):
        if retries <= 0:
            print("GRPC %s (%s) startWorker FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            print("GRPC %s (%s) startWorker %s" % (self.name, self.ip, self.launcherStub.StartWorker(Cloud_pb2.Empty()).value))
        else:
            sleep(5)
            self.startWorker(retries-1)

    def listModels(self, retries=5):
        print("GRPC %s (%s) listModels" % (self.name, self.ip))
        if retries <= 0:
            return self.models
        if (self.brokerStubReady()):
            self.models = self.brokerStub.getModels(google_empty.Empty())
        if (self.models is not None):
            return self.models
        sleep(5)
        return self.listModels(retries-1)

    def setModel(self, model, retries=5):
        print("GRPC %s (%s) setModel" % (self.name, self.ip))
        if retries <= 0:
            print("GRPC %s (%s) setModel FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            print("GRPC %s (%s) setModel DONE" % (self.name, self.ip))
            return self.brokerStub.setModel(model)
        sleep(5)
        return self.setModel(model, retries-1)

    def setLogName(self, log_name, retries=5):
        if retries <= 0:
            print("GRPC %s (%s) setLogName FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            name = Cloud_pb2.String()
            name.str = log_name
            print("GRPC %s (%s) setLog('%s') %s" % (self.name, self.ip, log_name, self.launcherStub.SetLogName(name).value))
        else:
            sleep(5)
            self.setLogName(log_name, retries-1)

    def destroy(self):
        if self.launcherChannel is not None:
            self.launcherChannel.unsubscribe(self.launcherStubStatusCallback)
            self.launcherChannel.close()
        if self.brokerChannel is not None:
            self.brokerChannel.unsubscribe(self.brokerStubStatusCallback)
            self.brokerChannel.close()

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
        print("GRPC %s (%s) __init__" % (self.name, self.ip))

    def launcherStubStatusCallback(self, status):
        print(status)
        self.launcherStubStatus = status

    def brokerStubStatusCallback(self, status):
        self.brokerStubStatus = status

    def connectLauncherService(self, retries=5):
        try:
            self.launcherChannel = grpc.insecure_channel('%s:50000' % self.ip)
            self.launcherStub = Launcher_pb2_grpc.LauncherServiceStub(self.launcherChannel)
            sleep(1)
            self.launcherStubReady()
            print("GRPC %s (%s) connectLauncherService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectLauncherService(retries-1)
            else:
                print("GRPC %s (%s) connectLauncherService FAIL" % (self.name, self.ip))

    def connectBrokerService(self, retries=5):
        try:
            self.brokerChannel = grpc.insecure_channel('%s:50051' % self.ip)
            self.brokerStub = ODProto_pb2_grpc.BrokerServiceStub(self.brokerChannel)
            sleep(1)
            self.brokerStubReady()
            print("GRPC %s (%s) connectBrokerService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectBrokerService(retries-1)
            else:
                print("GRPC %s (%s) connectBrokerService FAIL" % (self.name, self.ip))

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

    def startWorker(self, retries=5):
        if retries <= 0:
            print("GRPC %s (%s) startWorker FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            print("GRPC %s (%s) startWorker %s" % (self.name, self.ip, self.launcherStub.StartWorker(Launcher_pb2.Empty()).value))
        else:
            sleep(5)
            self.startWorker(retries-1)

    def startScheduler(self, retries=5):
        if retries <= 0:
            print("GRPC %s (%s) startScheduler FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            print("GRPC %s (%s) startScheduler %s" % (self.name, self.ip, self.launcherStub.StartScheduler(Launcher_pb2.Empty()).value))
        else:
            sleep(5)
            self.startScheduler(retries-1)

    def listSchedulers(self, retries=5):
        print("GRPC %s (%s) listSchedulers" % (self.name, self.ip))
        if retries <= 0:
            return self.schedulers
        if (self.brokerStubReady()):
            self.schedulers = self.brokerStub.getSchedulers(google_empty.Empty())
        if (self.schedulers is not None):
            return self.schedulers
        sleep(5)
        return self.listSchedulers(retries-1)

    def listModels(self, retries=5):
        print("GRPC %s (%s) listModels" % (self.name, self.ip))
        if retries <= 0:
            return self.models
        if (self.brokerStubReady()):
            self.models = self.brokerStub.getModels(google_empty.Empty())
        if (self.models is not None):
            return self.models
        sleep(5)
        return self.listModels(retries-1)

    def setScheduler(self, scheduler, retries=5):
        print("GRPC %s (%s) setScheduler" % (self.name, self.ip))
        if retries <= 0:
            print("GRPC %s (%s) setScheduler FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            print("GRPC %s (%s) setScheduler DONE" % (self.name, self.ip))
            return self.brokerStub.setScheduler(scheduler)
        sleep(5)
        return self.setModel(scheduler, retries-1)

    def setModel(self, model, retries=5):
        print("GRPC %s (%s) setModel" % (self.name, self.ip))
        if retries <= 0:
            print("GRPC %s (%s) setModel FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            print("GRPC %s (%s) setModel DONE" % (self.name, self.ip))
            return self.brokerStub.setModel(model)
        sleep(5)
        return self.setModel(model, retries-1)

    def scheduleJob(self, job):
        if (self.brokerStubReady()):
            return self.brokerStub.scheduleJob(job.getProto())

    def setLogName(self, log_name, retries=5):
        if retries <= 0:
            print("GRPC %s (%s) setLogName FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            name = Launcher_pb2.String()
            name.str = log_name
            print("GRPC %s (%s) setLog('%s') %s" % (self.name, self.ip, log_name, self.launcherStub.SetLogName(name).value))
        else:
            sleep(5)
            self.setLogName(log_name, retries-1)

    def destroy(self):
        if self.launcherChannel is not None:
            self.launcherChannel.unsubscribe(self.launcherStubStatusCallback)
            self.launcherChannel.close()
        if self.brokerChannel is not None:
            self.brokerChannel.unsubscribe(self.brokerStubStatusCallback)
            self.brokerChannel.close()

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
