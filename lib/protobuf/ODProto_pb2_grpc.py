# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import lib.protobuf.ODProto_pb2 as ODProto__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
from google.protobuf import wrappers_pb2 as google_dot_protobuf_dot_wrappers__pb2


class BrokerServiceStub(object):
  """Internal and External communication Broker
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.ping = channel.unary_unary(
        '/BrokerService/ping',
        request_serializer=ODProto__pb2.Ping.SerializeToString,
        response_deserializer=ODProto__pb2.Ping.FromString,
        )
    self.executeJob = channel.unary_unary(
        '/BrokerService/executeJob',
        request_serializer=ODProto__pb2.Job.SerializeToString,
        response_deserializer=ODProto__pb2.Results.FromString,
        )
    self.scheduleJob = channel.unary_unary(
        '/BrokerService/scheduleJob',
        request_serializer=ODProto__pb2.Job.SerializeToString,
        response_deserializer=ODProto__pb2.Results.FromString,
        )
    self.advertiseWorkerStatus = channel.unary_unary(
        '/BrokerService/advertiseWorkerStatus',
        request_serializer=ODProto__pb2.Worker.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.diffuseWorkerStatus = channel.unary_unary(
        '/BrokerService/diffuseWorkerStatus',
        request_serializer=ODProto__pb2.Worker.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.requestWorkerStatus = channel.unary_unary(
        '/BrokerService/requestWorkerStatus',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Worker.FromString,
        )
    self.getModels = channel.unary_unary(
        '/BrokerService/getModels',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Models.FromString,
        )
    self.setModel = channel.unary_unary(
        '/BrokerService/setModel',
        request_serializer=ODProto__pb2.Model.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.updateWorkers = channel.unary_unary(
        '/BrokerService/updateWorkers',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
        )
    self.getSchedulers = channel.unary_unary(
        '/BrokerService/getSchedulers',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Schedulers.FromString,
        )
    self.setScheduler = channel.unary_unary(
        '/BrokerService/setScheduler',
        request_serializer=ODProto__pb2.Scheduler.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.listenMulticast = channel.unary_unary(
        '/BrokerService/listenMulticast',
        request_serializer=google_dot_protobuf_dot_wrappers__pb2.BoolValue.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.announceMulticast = channel.unary_unary(
        '/BrokerService/announceMulticast',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.enableHearBeats = channel.unary_unary(
        '/BrokerService/enableHearBeats',
        request_serializer=ODProto__pb2.WorkerTypes.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.enableBandwidthEstimates = channel.unary_unary(
        '/BrokerService/enableBandwidthEstimates',
        request_serializer=ODProto__pb2.BandwidthEstimate.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.disableHearBeats = channel.unary_unary(
        '/BrokerService/disableHearBeats',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.disableBandwidthEstimates = channel.unary_unary(
        '/BrokerService/disableBandwidthEstimates',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.updateSmartSchedulerWeights = channel.unary_unary(
        '/BrokerService/updateSmartSchedulerWeights',
        request_serializer=ODProto__pb2.Weights.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.announceServiceStatus = channel.unary_unary(
        '/BrokerService/announceServiceStatus',
        request_serializer=ODProto__pb2.ServiceStatus.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.stopService = channel.unary_unary(
        '/BrokerService/stopService',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.calibrateWorker = channel.unary_unary(
        '/BrokerService/calibrateWorker',
        request_serializer=ODProto__pb2.Job.SerializeToString,
        response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
        )
    self.createJob = channel.unary_unary(
        '/BrokerService/createJob',
        request_serializer=ODProto__pb2.String.SerializeToString,
        response_deserializer=ODProto__pb2.Results.FromString,
        )


class BrokerServiceServicer(object):
  """Internal and External communication Broker
  """

  def ping(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def executeJob(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def scheduleJob(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def advertiseWorkerStatus(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def diffuseWorkerStatus(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def requestWorkerStatus(self, request, context):
    """ExternalBroker::diffuseWorkerStatus
    SchedulerService::notifyWorkerUpdate
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def getModels(self, request, context):
    """SchedulerService::notifyWorkerUpdate

    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def setModel(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def updateWorkers(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def getSchedulers(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def setScheduler(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def listenMulticast(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def announceMulticast(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def enableHearBeats(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def enableBandwidthEstimates(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def disableHearBeats(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def disableBandwidthEstimates(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def updateSmartSchedulerWeights(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def announceServiceStatus(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def stopService(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def calibrateWorker(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def createJob(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_BrokerServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'ping': grpc.unary_unary_rpc_method_handler(
          servicer.ping,
          request_deserializer=ODProto__pb2.Ping.FromString,
          response_serializer=ODProto__pb2.Ping.SerializeToString,
      ),
      'executeJob': grpc.unary_unary_rpc_method_handler(
          servicer.executeJob,
          request_deserializer=ODProto__pb2.Job.FromString,
          response_serializer=ODProto__pb2.Results.SerializeToString,
      ),
      'scheduleJob': grpc.unary_unary_rpc_method_handler(
          servicer.scheduleJob,
          request_deserializer=ODProto__pb2.Job.FromString,
          response_serializer=ODProto__pb2.Results.SerializeToString,
      ),
      'advertiseWorkerStatus': grpc.unary_unary_rpc_method_handler(
          servicer.advertiseWorkerStatus,
          request_deserializer=ODProto__pb2.Worker.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'diffuseWorkerStatus': grpc.unary_unary_rpc_method_handler(
          servicer.diffuseWorkerStatus,
          request_deserializer=ODProto__pb2.Worker.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'requestWorkerStatus': grpc.unary_unary_rpc_method_handler(
          servicer.requestWorkerStatus,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Worker.SerializeToString,
      ),
      'getModels': grpc.unary_unary_rpc_method_handler(
          servicer.getModels,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Models.SerializeToString,
      ),
      'setModel': grpc.unary_unary_rpc_method_handler(
          servicer.setModel,
          request_deserializer=ODProto__pb2.Model.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'updateWorkers': grpc.unary_unary_rpc_method_handler(
          servicer.updateWorkers,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
      ),
      'getSchedulers': grpc.unary_unary_rpc_method_handler(
          servicer.getSchedulers,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Schedulers.SerializeToString,
      ),
      'setScheduler': grpc.unary_unary_rpc_method_handler(
          servicer.setScheduler,
          request_deserializer=ODProto__pb2.Scheduler.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'listenMulticast': grpc.unary_unary_rpc_method_handler(
          servicer.listenMulticast,
          request_deserializer=google_dot_protobuf_dot_wrappers__pb2.BoolValue.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'announceMulticast': grpc.unary_unary_rpc_method_handler(
          servicer.announceMulticast,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'enableHearBeats': grpc.unary_unary_rpc_method_handler(
          servicer.enableHearBeats,
          request_deserializer=ODProto__pb2.WorkerTypes.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'enableBandwidthEstimates': grpc.unary_unary_rpc_method_handler(
          servicer.enableBandwidthEstimates,
          request_deserializer=ODProto__pb2.BandwidthEstimate.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'disableHearBeats': grpc.unary_unary_rpc_method_handler(
          servicer.disableHearBeats,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'disableBandwidthEstimates': grpc.unary_unary_rpc_method_handler(
          servicer.disableBandwidthEstimates,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'updateSmartSchedulerWeights': grpc.unary_unary_rpc_method_handler(
          servicer.updateSmartSchedulerWeights,
          request_deserializer=ODProto__pb2.Weights.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'announceServiceStatus': grpc.unary_unary_rpc_method_handler(
          servicer.announceServiceStatus,
          request_deserializer=ODProto__pb2.ServiceStatus.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'stopService': grpc.unary_unary_rpc_method_handler(
          servicer.stopService,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'calibrateWorker': grpc.unary_unary_rpc_method_handler(
          servicer.calibrateWorker,
          request_deserializer=ODProto__pb2.Job.FromString,
          response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
      ),
      'createJob': grpc.unary_unary_rpc_method_handler(
          servicer.createJob,
          request_deserializer=ODProto__pb2.String.FromString,
          response_serializer=ODProto__pb2.Results.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'BrokerService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))


class SchedulerServiceStub(object):
  """Broker > SchedulerBase
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.schedule = channel.unary_unary(
        '/SchedulerService/schedule',
        request_serializer=ODProto__pb2.Job.SerializeToString,
        response_deserializer=ODProto__pb2.Worker.FromString,
        )
    self.notifyWorkerUpdate = channel.unary_unary(
        '/SchedulerService/notifyWorkerUpdate',
        request_serializer=ODProto__pb2.Worker.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.notifyWorkerFailure = channel.unary_unary(
        '/SchedulerService/notifyWorkerFailure',
        request_serializer=ODProto__pb2.Worker.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.setScheduler = channel.unary_unary(
        '/SchedulerService/setScheduler',
        request_serializer=ODProto__pb2.Scheduler.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.listSchedulers = channel.unary_unary(
        '/SchedulerService/listSchedulers',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Schedulers.FromString,
        )
    self.updateSmartSchedulerWeights = channel.unary_unary(
        '/SchedulerService/updateSmartSchedulerWeights',
        request_serializer=ODProto__pb2.Weights.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.testService = channel.unary_unary(
        '/SchedulerService/testService',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.ServiceStatus.FromString,
        )
    self.stopService = channel.unary_unary(
        '/SchedulerService/stopService',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )


class SchedulerServiceServicer(object):
  """Broker > SchedulerBase
  """

  def schedule(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def notifyWorkerUpdate(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def notifyWorkerFailure(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def setScheduler(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def listSchedulers(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def updateSmartSchedulerWeights(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def testService(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def stopService(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_SchedulerServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'schedule': grpc.unary_unary_rpc_method_handler(
          servicer.schedule,
          request_deserializer=ODProto__pb2.Job.FromString,
          response_serializer=ODProto__pb2.Worker.SerializeToString,
      ),
      'notifyWorkerUpdate': grpc.unary_unary_rpc_method_handler(
          servicer.notifyWorkerUpdate,
          request_deserializer=ODProto__pb2.Worker.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'notifyWorkerFailure': grpc.unary_unary_rpc_method_handler(
          servicer.notifyWorkerFailure,
          request_deserializer=ODProto__pb2.Worker.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'setScheduler': grpc.unary_unary_rpc_method_handler(
          servicer.setScheduler,
          request_deserializer=ODProto__pb2.Scheduler.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'listSchedulers': grpc.unary_unary_rpc_method_handler(
          servicer.listSchedulers,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Schedulers.SerializeToString,
      ),
      'updateSmartSchedulerWeights': grpc.unary_unary_rpc_method_handler(
          servicer.updateSmartSchedulerWeights,
          request_deserializer=ODProto__pb2.Weights.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'testService': grpc.unary_unary_rpc_method_handler(
          servicer.testService,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.ServiceStatus.SerializeToString,
      ),
      'stopService': grpc.unary_unary_rpc_method_handler(
          servicer.stopService,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'SchedulerService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))


class WorkerServiceStub(object):
  """Broker > WorkerService
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.execute = channel.unary_unary(
        '/WorkerService/execute',
        request_serializer=ODProto__pb2.Job.SerializeToString,
        response_deserializer=ODProto__pb2.Results.FromString,
        )
    self.selectModel = channel.unary_unary(
        '/WorkerService/selectModel',
        request_serializer=ODProto__pb2.Model.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )
    self.listModels = channel.unary_unary(
        '/WorkerService/listModels',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Models.FromString,
        )
    self.testService = channel.unary_unary(
        '/WorkerService/testService',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.ServiceStatus.FromString,
        )
    self.stopService = channel.unary_unary(
        '/WorkerService/stopService',
        request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
        response_deserializer=ODProto__pb2.Status.FromString,
        )


class WorkerServiceServicer(object):
  """Broker > WorkerService
  """

  def execute(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def selectModel(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def listModels(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def testService(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def stopService(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_WorkerServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'execute': grpc.unary_unary_rpc_method_handler(
          servicer.execute,
          request_deserializer=ODProto__pb2.Job.FromString,
          response_serializer=ODProto__pb2.Results.SerializeToString,
      ),
      'selectModel': grpc.unary_unary_rpc_method_handler(
          servicer.selectModel,
          request_deserializer=ODProto__pb2.Model.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
      'listModels': grpc.unary_unary_rpc_method_handler(
          servicer.listModels,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Models.SerializeToString,
      ),
      'testService': grpc.unary_unary_rpc_method_handler(
          servicer.testService,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.ServiceStatus.SerializeToString,
      ),
      'stopService': grpc.unary_unary_rpc_method_handler(
          servicer.stopService,
          request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
          response_serializer=ODProto__pb2.Status.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'WorkerService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
