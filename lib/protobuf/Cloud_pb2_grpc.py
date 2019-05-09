# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import lib.protobuf.Cloud_pb2 as Cloud__pb2


class LauncherServiceStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.StartWorker = channel.unary_unary(
        '/odcloudservice.LauncherService/StartWorker',
        request_serializer=Cloud__pb2.Empty.SerializeToString,
        response_deserializer=Cloud__pb2.BoolValue.FromString,
        )
    self.SetLogName = channel.unary_unary(
        '/odcloudservice.LauncherService/SetLogName',
        request_serializer=Cloud__pb2.String.SerializeToString,
        response_deserializer=Cloud__pb2.BoolValue.FromString,
        )


class LauncherServiceServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def StartWorker(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def SetLogName(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_LauncherServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'StartWorker': grpc.unary_unary_rpc_method_handler(
          servicer.StartWorker,
          request_deserializer=Cloud__pb2.Empty.FromString,
          response_serializer=Cloud__pb2.BoolValue.SerializeToString,
      ),
      'SetLogName': grpc.unary_unary_rpc_method_handler(
          servicer.SetLogName,
          request_deserializer=Cloud__pb2.String.FromString,
          response_serializer=Cloud__pb2.BoolValue.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'odcloudservice.LauncherService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
