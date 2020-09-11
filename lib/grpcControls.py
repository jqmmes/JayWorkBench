import lib.protobuf.Launcher_pb2 as Launcher_pb2
import lib.protobuf.Launcher_pb2_grpc as Launcher_pb2_grpc
import lib.protobuf.Cloud_pb2 as Cloud_pb2
import lib.protobuf.Cloud_pb2_grpc as Cloud_pb2_grpc
import lib.protobuf.JayProto_pb2 as JayProto_pb2
import lib.protobuf.JayProto_pb2_grpc as JayProto_pb2_grpc
import lib.protobuf.JayTensorFlowProto_pb2 as JayTensorFlowProto_pb2

import lib.protobuf.cloudlet.CloudletControl_pb2 as CloudletControl_pb2
import lib.protobuf.cloudlet.CloudletControl_pb2_grpc as CloudletControl_pb2_grpc

from google.protobuf import empty_pb2 as google_empty
from google.protobuf.wrappers_pb2 import BoolValue as google_bool

import grpc
from grpc import ChannelConnectivity

from time import sleep, time, ctime
import uuid
from sys import excepthook, stdout

from func_timeout import func_set_timeout

def exceptionHook(exception_type, exception, traceback):
    print(self,"%s: %s" % (exception_type.__name__, exception))

excepthook = exceptionHook

def getProtoString(str):
    string = JayProto_pb2.String()
    string.str = str
    return string

def genRequest(action, args):
    request = JayProto_pb2.Request()
    request.request = action
    for arg in args:
        if isinstance(arg, str):
            request.args.append(bytes(arg, "utf-8"))
        else:
            request.args.append(bytes(arg))
    return request

def log(str, end="\n"):
    if grpcLogs.debug:
        lock_acquired = False
        if grpcLogs.lock is not None:
            lock_acquired = grpcLogs.lock.acquire(timeout=2)
        grpcLogs.log_file.write(ctime()+"\tGRPC "+str+end)
        grpcLogs.log_file.flush()
        if lock_acquired:
            grpcLogs.lock.release()

class x86RemoteControl:
    protoChannel = None
    channelStatus = ChannelConnectivity.SHUTDOWN
    protoStub = None
    port = 50049
    name = ""

    def __init__(self, ip, name, port=50049):
        self.ip = ip
        self.name = name
        self.port = port

    def connect(self, retries=5):
        try:
            self.protoChannel = grpc.insecure_channel('{}:{}'.format(self.ip, self.port))
            self.protoStub = CloudletControl_pb2_grpc.CloudletControlStub(self.protoChannel)
            sleep(1)
            self.__checkChannelStatus()
            log("%s connect" % (self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connect(retries-1)
            else:
                log("%s connect FAIL" % (self.ip))

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
            log("%s start FAIL" % (self.ip))
            return
        if (self.__checkChannelStatus()):
            log("%s start %s" % (self.ip, self.protoStub.startODLauncher(CloudletControl_pb2.Empty())))
        else:
            sleep(5)
            self.start(retries-1)

    @func_set_timeout(15)
    def stop(self, retries=3):
        if retries <= 0:
            log("%s stop FAIL" % (self.ip))
            return
        if (self.__checkChannelStatus()):
            log("%s stop %s" % (self.ip, self.protoStub.stopODLauncher(CloudletControl_pb2.Empty())))
        else:
            sleep(2)
            self.stop(retries-1)



class x86Launcher:
    launcherChannel = None
    launcherStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStub = None
    port = 50000
    name = ""

    def __init__(self, ip, adbName):
        self.ip = ip
        self.name = adbName
        log("%s (%s) __init__" % (self.name, self.ip))

    def launcherStubStatusCallback(self, status):
        self.launcherStubStatus = status

    def connectLauncherService(self, retries=5):
        try:
            self.launcherChannel = grpc.insecure_channel('%s:50000' % self.ip)
            self.launcherStub = Cloud_pb2_grpc.LauncherServiceStub(self.launcherChannel)
            sleep(1)
            self.launcherStubReady()
            log("%s (%s) connectLauncherService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectLauncherService(retries-1)
            else:
                log("%s (%s) connectLauncherService FAIL" % (self.name, self.ip))

    def launcherStubReady(self):
        if (self.launcherStubStatus == ChannelConnectivity.READY):
            return True
        if (self.launcherChannel is not None):
            self.launcherChannel.subscribe(self.launcherStubStatusCallback, True)
            sleep(0.5)
            return self.launcherStubStatus == ChannelConnectivity.READY
        else:
            return False

    def startWorker(self, retries=5):
        if retries <= 0:
            log("%s (%s) startWorker FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            log("%s (%s) startWorker %s" % (self.name, self.ip, self.launcherStub.StartWorker(Cloud_pb2.Empty()).value))
        else:
            sleep(5)
            self.startWorker(retries-1)

    def setLogName(self, log_name, retries=5):
        if retries <= 0:
            log("%s (%s) setLogName FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            name = Cloud_pb2.String()
            name.str = log_name
            log("%s (%s) setLog('%s') %s" % (self.name, self.ip, log_name, self.launcherStub.SetLogName(name).value))
        else:
            sleep(5)
            self.setLogName(log_name, retries-1)

    @func_set_timeout(15)
    def stop(self, retries=3):
        if retries <= 0:
            log("%s (%s) stop FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            log("%s (%s) stop %s" % (self.name, self.ip, self.launcherStub.Stop(Cloud_pb2.Empty()).value))
        else:
            sleep(2)
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

class droidLauncher:
    launcherChannel = None
    launcherStubStatus = ChannelConnectivity.SHUTDOWN
    launcherStub = None
    port = 50000
    name = ""

    def __init__(self, ip, name, port=50000):
        self.ip = ip
        self.name = name
        self.port = port
        log("%s droidLauncher(%s) __init__" % (self.name, self.ip))

    def launcherStubReady(self):
        if (self.launcherStubStatus == ChannelConnectivity.READY):
            return True
        if (self.launcherChannel is not None):
            self.launcherChannel.subscribe(self.launcherStubStatusCallback, True)
            sleep(0.5)
            return self.launcherStubStatus == ChannelConnectivity.READY
        else:
            return False

    def launcherStubStatusCallback(self, status):
        self.launcherStubStatus = status

    @func_set_timeout(15)
    def connectLauncherService(self, retries=5):
        try:
            self.launcherChannel = grpc.insecure_channel('{}:{}'.format(self.ip, self.port))
            self.launcherStub = Launcher_pb2_grpc.LauncherServiceStub(self.launcherChannel)
            sleep(1)
            self.launcherStubReady()
            log("%s (%s) connectLauncherService" % (self.name, self.ip))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectLauncherService(retries-1)
            else:
                log("%s (%s) connectLauncherService FAIL" % (self.name, self.ip))

    @func_set_timeout(15)
    def startWorker(self, retries=5):
        if retries <= 0:
            log("%s (%s) startWorker FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            try:
                start_worker = self.launcherStub.StartWorker(Launcher_pb2.Empty()).value
            except:
                start_worker = False
            log("%s (%s) startWorker %s" % (self.name, self.ip, start_worker))
        else:
            sleep(5)
            self.startWorker(retries-1)

    @func_set_timeout(15)
    def startScheduler(self, retries=5):
        if retries <= 0:
            log("%s (%s) startScheduler FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            try:
                start_scheduler = self.launcherStub.StartScheduler(Launcher_pb2.Empty()).value
            except:
                start_scheduler = False
            log("%s (%s) startScheduler %s" % (self.name, self.ip, start_scheduler))
        else:
            sleep(5)
            self.startScheduler(retries-1)

    @func_set_timeout(15)
    def setLogName(self, log_name, retries=5):
        if retries <= 0:
            log("%s (%s) setLogName FAIL" % (self.name, self.ip))
            return
        if (self.launcherStubReady()):
            name = Launcher_pb2.String()
            name.str = log_name
            try:
                log_status = self.launcherStub.SetLogName(name).value
            except Exception:
                log(Exception)
                log_status = False
            if log_status:
                log("%s (%s) setLog('%s') %s" % (self.name, self.ip, log_name, log_status))
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

class jayClient:
    brokerChannel = None
    brokerStubStatus = ChannelConnectivity.SHUTDOWN
    ip = None
    name = ""
    schedulers = None
    task_executors = None
    models = None

    def __init__(self, ip, adbName):
        self.ip = ip
        self.name = adbName
        log("%s (%s) __init__" % (self.name, self.ip))

    def brokerStubStatusCallback(self, status):
        self.brokerStubStatus = status

    @func_set_timeout(15)
    def connectBrokerService(self, port="45923", retries=5):
        try:
            self.brokerChannel = grpc.insecure_channel('%s:%s' % (self.ip, port))
            self.brokerStub = JayProto_pb2_grpc.BrokerServiceStub(self.brokerChannel)
            sleep(1)
            self.brokerStubReady()
            log("%s (%s) connectBrokerService(port=%s)" % (self.name, self.ip, port))
        except:
            sleep(5)
            if (retries-1 > 0):
                self.connectBrokerService(retries-1)
            else:
                log("%s (%s) connectBrokerService FAIL" % (self.name, self.ip))

    def __checkChannelStatus(self, channel, channelStatus, callback):
        if (channelStatus == ChannelConnectivity.READY):
            return True
        if (channel is not None):
            channel.subscribe(callback, True)
            sleep(0.5)
            return channelStatus == ChannelConnectivity.READY
        else:
            return False

    def brokerStubReady(self):
        return self.__checkChannelStatus(self.brokerChannel, self.brokerStubStatus, self.brokerStubStatusCallback)

    @func_set_timeout(35)
    def listSchedulers(self, retries=5):
        log("%s (%s) listSchedulers" % (self.name, self.ip))
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

    def listTaskExecutors(self, retries=5):
        log("%s (%s) listTaskExecutors" % (self.name, self.ip))
        if retries <= 0:
            return self.task_executors
        if (self.brokerStubReady()):
            try:
                self.task_executors = self.brokerStub.listTaskExecutors(google_empty.Empty())
            except:
                self.task_executors = None
        if (self.task_executors is not None):
            return self.task_executors
        sleep(5)
        return self.listTaskExecutors(retries-1)

    def selectTaskExecutor(self, taskExecutor, retries=5):
        log("%s (%s) selectTaskExecutor" % (self.name, self.ip))
        if retries <= 0:
            log("%s (%s) selectTaskExecutor FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            log("%s (%s) selectTaskExecutor DONE" % (self.name, self.ip))
            try:
                return self.brokerStub.selectTaskExecutor(taskExecutor)
            except:
                return None
        sleep(5)
        return self.selectTaskExecutor(taskExecutor, retries-1)

    def callExecutorAction(self, action, *args, retries=5):
        log("%s (%s) callExecutorAction(%s [%d args])" % (self.name, self.ip, action, len(args)))
        if retries <= 0:
            return None
        call_return = None
        if (self.brokerStubReady()):
            try:
                call_return = self.brokerStub.callExecutorAction(genRequest(action, args))
            except:
                call_return = None
        if (call_return is not None):
            return call_return
        sleep(5)
        return self.callExecutorAction(action, args, retries-1)

    def runExecutorAction(self, action, *args, retries=5):
        log("%s (%s) runExecutorAction(%s [%d args])" % (self.name, self.ip, action, len(args)))
        if retries <= 0:
            return None
        call_return = None
        if (self.brokerStubReady()):
            try:
                call_return = self.brokerStub.runExecutorAction(genRequest(action, args))
            except:
                call_return = None
        if (call_return is not None):
            return call_return
        sleep(5)
        return self.runExecutorAction(action, args, retries-1)

    '''
        TODO: SET TASK_EXECUTOR_SETTINGS

        Colocar TaskExecutorSettings Geral e custom
    '''

    def setTaskExecutorSettings(self, settings_map, retries=5):
        if retries <= 0:
            log("%s (%s) taskExecutor setSettings FAIL" % (self.name, self.ip))
            return False
        if (self.brokerStubReady()):
            try:
                settings_proto = JayProto_pb2.Settings()
                for key in settings_map:
                    log("{} ({}) taskExecutor settings[{}]: {}".format(self.name, self.ip, key, settings_map[key]))
                    settings_proto.setting[key] = settings_map[key]
                return self.brokerStub.setExecutorSettings(settings_proto)
            except:
                None
        sleep(5)
        return self.setSettings(settings_map, retries-1)

    @func_set_timeout(35)
    def listModels(self, retries=5):
        models = self.callExecutorAction("listModels")
        if models == None:
            return None
        ret_models =  JayTensorFlowProto_pb2.Models()
        ret_models.ParseFromString(models.bytes)
        return ret_models

    @func_set_timeout(300)
    def setModel(self, model, retries=5):
        return self.runExecutorAction("loadModel", model.SerializeToString())

    @func_set_timeout(35)
    def setScheduler(self, scheduler, retries=5):
        log("%s (%s) setScheduler" % (self.name, self.ip))
        if retries <= 0:
            log("%s (%s) setScheduler FAIL" % (self.name, self.ip))
            return None
        if (self.brokerStubReady()):
            log("%s (%s) setScheduler DONE" % (self.name, self.ip))
            try:
                return self.brokerStub.setScheduler(scheduler)
            except:
                return None
        sleep(5)
        return self.setScheduler(scheduler, retries-1)

    def scheduleTask(self, task):
        if (self.brokerStubReady()):
            try:
                return self.brokerStub.scheduleTask(task.getProto())
            except:
                return False

    def createTask(self, asset_id, deadline=None):
        if (self.brokerStubReady()):
            try:
                taskInfo = JayProto_pb2.TaskInfo()
                taskInfo.path = asset_id
                if (deadline):
                    taskInfo.deadline = deadline
                return self.brokerStub.createTask(taskInfo)
            except:
                return False

    def calibrateWorker(self, asset_id):
        if (self.brokerStubReady()):
            try:
                return self.brokerStub.calibrateWorker(getProtoString(asset_id))
            except:
                return False

    def setSettings(self, settings_map, mcast_interface = None, advertise_worker=False, retries=5):
        if retries <= 0:
            log("%s (%s) setSettings FAIL" % (self.name, self.ip))
            return False
        if (self.brokerStubReady()):
            try:
                settings_proto = JayProto_pb2.Settings()
                for key in settings_map:
                    log("{} ({}) settings[{}]: {}".format(self.name, self.ip, key, settings_map[key]))
                    settings_proto.setting[key] = settings_map[key]
                if mcast_interface:
                    log("{} ({}) settings[MCAST_INTERFACE]: {}".format(self.name, self.ip, mcast_interface))
                    settings_proto.setting["MCAST_INTERFACE"] = mcast_interface
                if advertise_worker:
                    log("{} ({}) settings[ADVERTISE_WORKER_STATUS]: true".format(self.name, self.ip))
                    settings_proto.setting["ADVERTISE_WORKER_STATUS"] = "true"
                return self.brokerStub.setSettings(settings_proto)
            except:
                None
        sleep(5)
        return self.setSettings(settings_map, mcast_interface, advertise_worker, retries-1)

    def destroy(self):
        if self.brokerChannel is not None:
            try:
                if (self.brokerChannel == ChannelConnectivity.TRANSIENT_FAILURE or self.brokerChannel == ChannelConnectivity.SHUTDOWN):
                    self.brokerChannel.unsubscribe(self.brokerStubStatusCallback)
                if (self.brokerChannel == ChannelConnectivity.TRANSIENT_FAILURE or self.brokerChannel == ChannelConnectivity.SHUTDOWN):
                    self.brokerChannel.close()
            except:
                pass

class grpcLogs:
    log_file = stdout
    debug = False
    lock = None

class Task:
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
        task = JayProto_pb2.Task()
        task.id = self.id
        task.data = self.data
        return task

class Cloud:
    instance = ""
    zone = ""
    address = ""

    def __init__(self, instance, zone, address):
        self.instance = instance
        self.zone = zone
        self.address = address
