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
wget -x https://www.dropbox.com/s/5esu529gqsxj6ha/Jay-x86.jar?dl=1 -O $HOME/Jay-x86/Jay-x86.jar
wget -x https://www.dropbox.com/s/dmt97v19hlx54tw/CloudletControl.py?dl=1 -O $HOME/Jay-x86/CloudletControl.py
mkdir -p $HOME/Jay-x86/lib/protobuf/cloudlet
wget -x https://www.dropbox.com/s/x6qv8m315f5su7r/CloudletControl_pb2.py?dl=1 -O $HOME/Jay-x86/lib/protobuf/cloudlet/CloudletControl_pb2.py
wget -x https://www.dropbox.com/s/crygm6ews8alclx/CloudletControl_pb2_grpc.py?dl=1 -O $HOME/Jay-x86/lib/protobuf/cloudlet/CloudletControl_pb2_grpc.py
cd ~/Jay-x86/assets/
wget -x https://www.dropbox.com/s/1z4foixc8gmayi3/SD.jpg?dl=1 -O $HOME/Jay-x86/assets/SD.jpg
wget -x https://www.dropbox.com/s/6ofu6h07bfjt0s3/HD.jpg?dl=1 -O $HOME/Jay-x86/assets/HD.jpg
wget -x https://www.dropbox.com/s/7rkq106a78dv961/UHD.jpg?dl=1 -O $HOME/Jay-x86/assets/UHD.jpg
echo "crontab -e"
echo "@reboot tmux new -s jay-x86 -d  `which python3` $HOME/Jay-x86/CloudletControl.py"
echo "*/5 * * * * $HOME/duckdns/duck.sh >/dev/null 2>&1"
echo "@reboot $HOME/duckdns/duck.sh >/dev/null 2>&1"
