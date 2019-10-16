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
mkdir ~/ODCloud/
mkdir ~/ODCloud/logs/
mkdir ~/ODCloud/assets/
cd ~/ODCloud/
wget -x http://od-data.duckdns.org/apps/ODCloud.jar -O $HOME/ODCloud/ODCloud.jar
wget -x http://od-data.duckdns.org/scripts/CloudletControl.py -O $HOME/ODCloud/CloudletControl.py
mkdir -p $HOME/ODCloud/lib/protobuf/cloudlet
wget -x http://od-data.duckdns.org/scripts/lib/protobuf/cloudlet/CloudletControl_pb2.py -O $HOME/ODCloud/lib/protobuf/cloudlet/CloudletControl_pb2.py
wget -x http://od-data.duckdns.org/scripts/lib/protobuf/cloudlet/CloudletControl_pb2_grpc.py -O $HOME/ODCloud/lib/protobuf/cloudlet/CloudletControl_pb2_grpc.py
cd ~/ODCloud/assets/
wget -x http://od-data.duckdns.org/assets/sd/000000060521.jpg -O $HOME/ODCloud/assets/SD.jpg
wget -x http://od-data.duckdns.org/assets/hd/C10_HD.jpg -O $HOME/ODCloud/assets/HD.jpg
wget -x http://od-data.duckdns.org/assets/uhd/C14_UHD.jpg -O $HOME/ODCloud/assets/UHD.jpg
echo "crontab -e"
echo "@reboot tmux new -s odcloud -d  `which python3` $HOME/ODCloud/CloudletControl.py"
echo "*/5 * * * * $HOME/duckdns/duck.sh >/dev/null 2>&1"
echo "@reboot $HOME/duckdns/duck.sh >/dev/null 2>&1"
