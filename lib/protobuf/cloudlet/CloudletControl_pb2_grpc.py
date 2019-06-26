# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import lib.protobuf.cloudlet.CloudletControl_pb2 as CloudletControl__pb2


class CloudletControlStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.startODLauncher = channel.unary_unary(
        '/CloudletControl/startODLauncher',
        request_serializer=CloudletControl__pb2.Empty.SerializeToString,
        response_deserializer=CloudletControl__pb2.Empty.FromString,
        )
    self.stopODLauncher = channel.unary_unary(
        '/CloudletControl/stopODLauncher',
        request_serializer=CloudletControl__pb2.Empty.SerializeToString,
        response_deserializer=CloudletControl__pb2.Empty.FromString,
        )


class CloudletControlServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def startODLauncher(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def stopODLauncher(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_CloudletControlServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'startODLauncher': grpc.unary_unary_rpc_method_handler(
          servicer.startODLauncher,
          request_deserializer=CloudletControl__pb2.Empty.FromString,
          response_serializer=CloudletControl__pb2.Empty.SerializeToString,
      ),
      'stopODLauncher': grpc.unary_unary_rpc_method_handler(
          servicer.stopODLauncher,
          request_deserializer=CloudletControl__pb2.Empty.FromString,
          response_serializer=CloudletControl__pb2.Empty.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'CloudletControl', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))