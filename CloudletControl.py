import lib.protobuf.cloudlet.CloudletControl_pb2 as CloudletControl_pb2
import lib.protobuf.cloudlet.CloudletControl_pb2_grpc as CloudletControl_pb2_grpc
import os
import subprocess
import grpc
import concurrent.futures
from time import sleep
import subprocess


class CloudletControl(CloudletControl_pb2_grpc.CloudletControlServicer):

    def startODLauncher(self, request, context):
        path = "/usr/lib/jvm/java-1.8.0-openjdk-amd64/bin/java"
        if os.path.exists("/usr/lib/jvm/java-1.11.0-openjdk-amd64/bin/java"):
            path = "/usr/lib/jvm/java-1.11.0-openjdk-amd64/bin/java"
        if not os.path.exists(path):
            if os.path.exists("/Library/Java/JavaVirtualMachines/openjdk-12.0.1.jdk/Contents/Home/bin/java"):
                path = "/Library/Java/JavaVirtualMachines/openjdk-12.0.1.jdk/Contents/Home/bin/java"
        od_path = os.environ['HOME']
        os.system("%s -jar %s/ODCloud/ODCloud.jar&" % (path, od_path))
        return CloudletControl_pb2.Empty()

    def stopODLauncher(self, request, context):
        pid = os.popen("jps -lV | grep ODCloud.jar | cut -d' ' -f1").read()[:-1]
        if pid != '':
            subprocess.run(['kill', '-9', pid])
        return CloudletControl_pb2.Empty()

def serve():
  print("STARTING CLOUDLET CONTROL")
  server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
  CloudletControl_pb2_grpc.add_CloudletControlServicer_to_server(
      CloudletControl(), server)
  server.add_insecure_port('[::]:50049')
  server.start()
  while True:
      sleep(1)

def checkInterfaces():
    iface_raw = subprocess.run(["ip", "link", "show"], stdout=subprocess.PIPE).stdout.decode("UTF-8").split("\n")
    ifaces = []
    for line in iface_raw:
        if line.find("state UP") != -1:
            ifaces.append(line.split()[1][:-1])
    if "flannel.1" in ifaces:
        subprocess.run(["sudo", "ip", "link", "set", "flannel.1", "down"])
    print("AVAILABLE INTERFACES:")
    for iface in ifaces:
        print("\t[*] {}".format(iface))

if __name__ == '__main__':
    checkInterfaces()
    serve()
