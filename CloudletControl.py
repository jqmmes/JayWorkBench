import lib.protobuf.cloudlet.CloudletControl_pb2 as CloudletControl_pb2
import lib.protobuf.cloudlet.CloudletControl_pb2_grpc as CloudletControl_pb2_grpc
import os
import subprocess
import grpc
import concurrent.futures
from time import sleep


class CloudletControl(CloudletControl_pb2_grpc.CloudletControlServicer):

    def startODLauncher(self, request, context):
        os.system("/usr/lib/jvm/java-1.11.0-openjdk-amd64/bin/java -jar /home/joaquim/ODCloud/ODCloud.jar&")
        return CloudletControl_pb2.Empty()

    def stopODLauncher(self, request, context):
        pid = os.popen("jps -lV | grep ODCloud.jar | cut -d' ' -f1").read()[:-1]
        if pid != '':
            subprocess.run(['kill', '-9', pid])
        return CloudletControl_pb2.Empty()


def serve():
  server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
  CloudletControl_pb2_grpc.add_CloudletControlServicer_to_server(
      CloudletControl(), server)
  server.add_insecure_port('localhost:50049')
  server.start()
  while True:
      sleep(1)


if __name__ == '__main__':
    serve()