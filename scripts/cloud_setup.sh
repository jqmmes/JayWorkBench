#!/bin/bash

sudo apt-get update
sudo apt-get -y upgrade
sudo apt-get -y dist-upgrade
sudo apt-get install -y git nano wget tmux
sudo apt-get install -y openjdk-11-jdk-headless
sudo apt-get install -y python3
sudo apt-get install -y python3-pip
sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install grpcio
sudo python3 -m pip install grpcio-tools
sudo python3 -m pip install tensorflow
sudo apt-get install -y stress
sudo apt-get install -y iperf
cd ~
mkdir ~/Jay-x86/
mkdir ~/Jay-x86/logs/
mkdir ~/Jay-x86/assets/
cd ~/Jay-x86/
wget -x http://od-data.duckdns.org/apps/Jay-x86.jar -O $HOME/Jay-x86/Jay-x86.jar
wget -x http://od-data.duckdns.org/scripts/CloudletControl.py -O $HOME/Jay-x86/CloudletControl.py
mkdir -p $HOME/Jay-x86/lib/protobuf/cloudlet
wget -x http://od-data.duckdns.org/scripts/lib/protobuf/cloudlet/CloudletControl_pb2.py -O $HOME/Jay-x86/lib/protobuf/cloudlet/CloudletControl_pb2.py
wget -x http://od-data.duckdns.org/scripts/lib/protobuf/cloudlet/CloudletControl_pb2_grpc.py -O $HOME/Jay-x86/lib/protobuf/cloudlet/CloudletControl_pb2_grpc.py
cd ~/Jay-x86/assets/
wget -x http://od-data.duckdns.org/assets/sd/000000060521.jpg -O $HOME/Jay-x86/assets/SD.jpg
wget -x http://od-data.duckdns.org/assets/hd/C10_HD.jpg -O $HOME/Jay-x86/assets/HD.jpg
wget -x http://od-data.duckdns.org/assets/uhd/C14_UHD.jpg -O $HOME/Jay-x86/assets/UHD.jpg
echo "crontab -e"
echo "@reboot tmux new -s jay-x86 -d  `which python3` $HOME/Jay-x86/CloudletControl.py"
echo "*/5 * * * * $HOME/duckdns/duck.sh >/dev/null 2>&1"
echo "@reboot $HOME/duckdns/duck.sh >/dev/null 2>&1"
