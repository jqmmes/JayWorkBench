import lib.protobuf.Launcher_pb2 as Launcher_pb2
import lib.protobuf.Launcher_pb2_grpc as Launcher_pb2_grpc
import lib.protobuf.Cloud_pb2 as Cloud_pb2
import lib.protobuf.Cloud_pb2_grpc as Cloud_pb2_grpc
import lib.protobuf.ODProto_pb2 as ODProto_pb2
import lib.protobuf.ODProto_pb2_grpc as ODProto_pb2_grpc

import lib.protobuf.cloudlet.CloudletControl_pb2 as CloudletControl_pb2
import lib.protobuf.cloudlet.CloudletControl_pb2_grpc as CloudletControl_pb2_grpc

from google.protobuf import empty_pb2 as google_empty
from google.protobuf.wrappers_pb2 import BoolValue as google_bool

import grpc
from grpc import ChannelConnectivity

from time import sleep, time
import uuid
from sys import excepthook, stdout

def exceptionHook(exception_type, exception, traceback):
    print(self,"%s: %s" % (exception_type.__name__, exception))

excepthook = exceptionHook

DEBUG = False
GRPC_DEBUG_FILE = None
GRPC_LOGS_LOCK = None

def getProtoString(str):
    string = ODProto_pb2.String()
    string.str = str
    return string

class cloudControl:
    protoChannel = None
    channelStatus = ChannelConnectivity.SHUTDOWN
    protoStub = None
    port = 50049
    name = ""
    log_file = stdout

    def __init__(self, ip, name, log_file):
        self.ip = ip
        self.name = name
        self.log_file = log_file

    def log(self, str, end="\n"):
        global GRPC_LOGS_LOCK
        if DEBUG:
            if GRPC_DEBUG_FILE is None:
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.acquire()
                self.log_file.write(str+end)
                self.log_file.flush()
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.release()
            else:
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.acquire()
                GRPC_DEBUG_FILE.write(str+end)
                GRPC_DEBUG_FILE.flush()
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.release()

    def connect(self, retries=5):
        try:
            self.protoChannel = grpc.insecure_channel('%s:50049' % self.ip)
            self.protoStub = CloudletControl_pb2_grpc.CloudletControlStub(self.protoChannel)
            sleep(1)
            self.__checkChannelStatus()
            self.log("GRPC %s connect" % (self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connect(retries-1)
            else:
                self.log("GRPC %s connect FAIL" % (self.ip))

    def channelCallback(self, status):
        self.channelStatus = status

    def __checkChannelStatus(self):
        if (self.channelStatus == ChannelConnectivity.READY):
            return True
        if (self.protoChannel is not None):
            self.protoChannel.subscribe(self.channelCallback, True)
            sleep(0.5)
            return self.channelStatus == ChannelConnectivity.READY
        else:
            return False

    def start(self, retries=5):
        if retries <= 0:
            self.log("GRPC %s start FAIL" % (self.ip))
            return
        if (self.__checkChannelStatus()):
            self.log("GRPC %s start %s" % (self.ip, self.protoStub.startODLauncher(CloudletControl_pb2.Empty())))
        else:
            sleep(5)
            self.start(retries-1)

    def stop(self, retries=5):
        if retries <= 0:
            self.log("GRPC %s stop FAIL" % (self.ip))
            return
        if (self.__checkChannelStatus()):
            self.log("GRPC %s stop %s" % (self.ip, self.protoStub.stopODLauncher(CloudletControl_pb2.Empty())))
        else:
            sleep(5)
            self.stop(retries-1)

class cloudClient:
    launcherChannel = None
    brokerChannel = None
    brokerStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStub = None
    ip = None
    name = ""
    models = None
    log_file = stdout

    def __init__(self, ip, adbName, log_file):
        self.ip = ip
        self.name = adbName
        self.log_file = log_file
        self.log("GRPC %s (%s) __init__" % (self.name, self.ip))

    def log(self, str, end="\n"):
        global GRPC_LOGS_LOCK
        if DEBUG:
            if GRPC_DEBUG_FILE is None:
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.acquire()
                self.log_file.write(str+end)
                self.log_file.flush()
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.release()
            else:
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.acquire()
                GRPC_DEBUG_FILE.write(str+end)
                GRPC_DEBUG_FILE.flush()
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.release()

    def launcherStubStatusCallback(self, status):
        self.launcherStubStatus = status

    def brokerStubStatusCallback(self, status):
        self.brokerStubStatus = status

    def connectLauncherService(self, retries=5):
        try:
            self.launcherChannel = grpc.insecure_channel('%s:50000' % self.ip)
            self.launcherStub = Cloud_pb2_grpc.LauncherServiceStub(self.launcherChannel)
            sleep(1)
            self.launcherStubReady()
            self.log("GRPC %s (%s) connectLauncherService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectLauncherService(retries-1)
            else:
                self.log("GRPC %s (%s) connectLauncherService FAIL" % (self.name, self.ip))

    def connectBrokerService(self, retries=5):
        try:
            self.brokerChannel = grpc.insecure_channel('%s:50051' % self.ip)
            self.brokerStub = ODProto_pb2_grpc.BrokerServiceStub(self.brokerChannel)
            sleep(1)
            self.brokerStubReady()
            self.log("GRPC %s (%s) connectBrokerService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectBrokerService(retries-1)
            else:
                self.log("GRPC %s (%s) connectBrokerService FAIL" % (self.name, self.ip))

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
            self.log("GRPC %s (%s) startWorker FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            self.log("GRPC %s (%s) startWorker %s" % (self.name, self.ip, self.launcherStub.StartWorker(Cloud_pb2.Empty()).value))
        else:
            sleep(5)
            self.startWorker(retries-1)

    def listModels(self, retries=5):
        self.log("GRPC %s (%s) listModels" % (self.name, self.ip))
        if retries <= 0:
            return self.models
        if (self.brokerStubReady()):
            self.models = self.brokerStub.getModels(google_empty.Empty())
        if (self.models is not None):
            return self.models
        sleep(5)
        return self.listModels(retries-1)

    def setModel(self, model, retries=5):
        self.log("GRPC %s (%s) setModel" % (self.name, self.ip))
        if retries <= 0:
            self.log("GRPC %s (%s) setModel FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            status = self.brokerStub.setModel(model)
            self.log("GRPC %s (%s) setModel DONE" % (self.name, self.ip))
            return status
        sleep(5)
        return self.setModel(model, retries-1)

    def setSettings(self, settings_map, mcast_interface = None):
        if (self.brokerStubReady()):
            try:
                settings_proto = ODProto_pb2.Settings()
                if mcast_interface:
                    settings_proto.setting["MCAST_INTERFACE"] = mcast_interface
                for key in settings_map:
                    settings_proto.setting[key] = settings_map[key]
                return self.brokerStub.setSettings(settings_proto)
            except:
                return False

    def setLogName(self, log_name, retries=5):
        if retries <= 0:
            self.log("GRPC %s (%s) setLogName FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            name = Cloud_pb2.String()
            name.str = log_name
            self.log("GRPC %s (%s) setLog('%s') %s" % (self.name, self.ip, log_name, self.launcherStub.SetLogName(name).value))
        else:
            sleep(5)
            self.setLogName(log_name, retries-1)

    def calibrateWorker(self, asset_id):
        if (self.brokerStubReady()):
            try:
                return self.brokerStub.calibrateWorker(getProtoString(asset_id))
            except:
                return False

    def stop(self, retries=5):
        if retries <= 0:
            self.log("GRPC %s (%s) stop FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            self.log("GRPC %s (%s) stop %s" % (self.name, self.ip, self.launcherStub.Stop(Cloud_pb2.Empty()).value))
        else:
            sleep(5)
            self.stop(retries-1)

    def destroy(self):
        if self.launcherChannel is not None:
            try:
                if (self.launcherStubStatus == ChannelConnectivity.TRANSIENT_FAILURE or self.launcherStubStatus == ChannelConnectivity.SHUTDOWN):
                    self.launcherChannel.unsubscribe(self.launcherStubStatusCallback)
                if (self.launcherStubStatus == ChannelConnectivity.TRANSIENT_FAILURE or self.launcherStubStatus == ChannelConnectivity.SHUTDOWN):
                    self.launcherChannel.close()
            except:
                pass
        if self.brokerChannel is not None:
            try:
                if (self.brokerChannel == ChannelConnectivity.TRANSIENT_FAILURE or self.brokerChannel == ChannelConnectivity.SHUTDOWN):
                    self.brokerChannel.unsubscribe(self.brokerStubStatusCallback)
                if (self.brokerChannel == ChannelConnectivity.TRANSIENT_FAILURE or self.brokerChannel == ChannelConnectivity.SHUTDOWN):
                    self.brokerChannel.close()
            except:
                pass

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
    log_file = stdout

    def __init__(self, ip, adbName, log_file):
        self.ip = ip
        self.name = adbName
        self.log_file = log_file
        self.log("GRPC %s (%s) __init__" % (self.name, self.ip))

    def log(self, str, end="\n"):
        global GRPC_LOGS_LOCK
        if DEBUG:
            if GRPC_DEBUG_FILE is None:
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.acquire()
                self.log_file.write(str+end)
                self.log_file.flush()
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.release()
            else:
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.acquire()
                GRPC_DEBUG_FILE.write(str+end)
                GRPC_DEBUG_FILE.flush()
                if GRPC_LOGS_LOCK is not None:
                    GRPC_LOGS_LOCK.release()

    def launcherStubStatusCallback(self, status):
        self.launcherStubStatus = status

    def brokerStubStatusCallback(self, status):
        self.brokerStubStatus = status

    def connectLauncherService(self, retries=5):
        try:
            self.launcherChannel = grpc.insecure_channel('%s:50000' % self.ip)
            self.launcherStub = Launcher_pb2_grpc.LauncherServiceStub(self.launcherChannel)
            sleep(1)
            self.launcherStubReady()
            self.log("GRPC %s (%s) connectLauncherService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectLauncherService(retries-1)
            else:
                self.log("GRPC %s (%s) connectLauncherService FAIL" % (self.name, self.ip))

    def connectBrokerService(self, retries=5):
        try:
            self.brokerChannel = grpc.insecure_channel('%s:50051' % self.ip)
            self.brokerStub = ODProto_pb2_grpc.BrokerServiceStub(self.brokerChannel)
            sleep(1)
            self.brokerStubReady()
            self.log("GRPC %s (%s) connectBrokerService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectBrokerService(retries-1)
            else:
                self.log("GRPC %s (%s) connectBrokerService FAIL" % (self.name, self.ip))

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
            self.log("GRPC %s (%s) startWorker FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            try:
                start_worker = self.launcherStub.StartWorker(Launcher_pb2.Empty()).value
            except:
                start_worker = False
            self.log("GRPC %s (%s) startWorker %s" % (self.name, self.ip, start_worker))
        else:
            sleep(5)
            self.startWorker(retries-1)

    def startScheduler(self, retries=5):
        if retries <= 0:
            self.log("GRPC %s (%s) startScheduler FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            try:
                start_scheduler = self.launcherStub.StartScheduler(Launcher_pb2.Empty()).value
            except:
                start_scheduler = False
            self.log("GRPC %s (%s) startScheduler %s" % (self.name, self.ip, start_scheduler))
        else:
            sleep(5)
            self.startScheduler(retries-1)

    def listSchedulers(self, retries=5):
        self.log("GRPC %s (%s) listSchedulers" % (self.name, self.ip))
        if retries <= 0:
            return self.schedulers
        if (self.brokerStubReady()):
            try:
                self.schedulers = self.brokerStub.getSchedulers(google_empty.Empty())
            except:
                self.schedulers = None
        if (self.schedulers is not None):
            return self.schedulers
        sleep(5)
        return self.listSchedulers(retries-1)

    def listModels(self, retries=5):
        self.log("GRPC %s (%s) listModels" % (self.name, self.ip))
        if retries <= 0:
            return self.models
        if (self.brokerStubReady()):
            try:
                self.models = self.brokerStub.getModels(google_empty.Empty())
            except:
                self.Models = None
        if (self.models is not None):
            return self.models
        sleep(5)
        return self.listModels(retries-1)

    def setScheduler(self, scheduler, retries=5):
        self.log("GRPC %s (%s) setScheduler" % (self.name, self.ip))
        if retries <= 0:
            self.log("GRPC %s (%s) setScheduler FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            self.log("GRPC %s (%s) setScheduler DONE" % (self.name, self.ip))
            try:
                return self.brokerStub.setScheduler(scheduler)
            except:
                return None
        sleep(5)
        return self.setModel(scheduler, retries-1)

    def setModel(self, model, retries=5):
        self.log("GRPC %s (%s) setModel" % (self.name, self.ip))
        if retries <= 0:
            self.log("GRPC %s (%s) setModel FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            self.log("GRPC %s (%s) setModel DONE" % (self.name, self.ip))
            try:
                return self.brokerStub.setModel(model)
            except:
                return None
        sleep(5)
        return self.setModel(model, retries-1)

    def scheduleJob(self, job):
        if (self.brokerStubReady()):
            try:
                return self.brokerStub.scheduleJob(job.getProto())
            except:
                return False

    def createJob(self, asset_id):
        if (self.brokerStubReady()):
            try:
                return self.brokerStub.createJob(getProtoString(asset_id))
            except:
                return False

    def calibrateWorker(self, asset_id):
        if (self.brokerStubReady()):
            try:
                return self.brokerStub.calibrateWorker(getProtoString(asset_id))
            except:
                return False

    def setSettings(self, settings_map):
        if (self.brokerStubReady()):
            try:
                settings_proto = ODProto_pb2.Settings()
                for key in settings_map:
                    settings_proto.setting[key] = settings_map[key]
                return self.brokerStub.setSettings(settings_proto)
            except:
                return False

    def setLogName(self, log_name, retries=5):
        if retries <= 0:
            self.log("GRPC %s (%s) setLogName FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            name = Launcher_pb2.String()
            name.str = log_name
            try:
                log_status = self.launcherStub.SetLogName(name).value
            except Exception:
                self.log(Exception)
                log_status = False
            if log_status:
                self.log("GRPC %s (%s) setLog('%s') %s" % (self.name, self.ip, log_name, log_status))
                return
        sleep(5)
        self.setLogName(log_name, retries-1)

    def destroy(self):
        if self.launcherChannel is not None:
            try:
                if (self.launcherStubStatus == ChannelConnectivity.TRANSIENT_FAILURE or self.launcherStubStatus == ChannelConnectivity.SHUTDOWN):
                    self.launcherChannel.unsubscribe(self.launcherStubStatusCallback)
                if (self.launcherStubStatus == ChannelConnectivity.TRANSIENT_FAILURE or self.launcherStubStatus == ChannelConnectivity.SHUTDOWN):
                    self.launcherChannel.close()
            except:
                pass
        if self.brokerChannel is not None:
            try:
                if (self.brokerChannel == ChannelConnectivity.TRANSIENT_FAILURE or self.brokerChannel == ChannelConnectivity.SHUTDOWN):
                    self.brokerChannel.unsubscribe(self.brokerStubStatusCallback)
                if (self.brokerChannel == ChannelConnectivity.TRANSIENT_FAILURE or self.brokerChannel == ChannelConnectivity.SHUTDOWN):
                    self.brokerChannel.close()
            except:
                pass

class Job:
    id = ""
    data = None

    def __init__(self, id=''):
        if id != '':
            self.id = id
        else:
            self.id = str(uuid.uuid4())

    def addBytes(self, bytes):
        self.data = bytes

    def getProto(self):
        job = ODProto_pb2.Job()
        job.id = self.id
        job.data = self.data
        return job

class Cloud:
    instance = ""
    zone = ""
    address = ""

    def __init__(self, instance, zone, address):
        self.instance = instance
        self.zone = zone
        self.address = address
