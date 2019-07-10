#!/bin/bash

if [[ $OSTYPE == "darwin"* ]]
then
  JAVA_HOME=`/usr/libexec/java_home -v 1.8`
  PATH=$JAVA_HOME/bin:$PATH
elif [[ $OSTYPE == "linux-gnu"* ]]
then
  PATH=/usr/lib/jvm/java-8-openjdk-amd64/bin:$PATH
  JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
fi

$(which python3) processLogs.py
