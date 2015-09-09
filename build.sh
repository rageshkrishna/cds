#!/bin/bash

# This script launches the worker inside a container. It takes care of resetting·
# file system permissions, activating the VE and launching the process
export INSTALL_REQS=false

## If this script is invoked with 'install' argument
## then set the INSTALL_REQS flag to true
if [[ $# > 0 ]]; then
  if [[ "$1" == "install" ]]; then
    export INSTALL_REQS=true
  else
    export INSTALL_REQS=false
  fi
fi

CDS_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $CDS_DIR

SUDO=`which sudo`

$SUDO mkdir -p /home/shippable/build/logs
$SUDO mkdir -p /shippableci
$SUDO chown -R $USER:$USER /home/shippable/build/logs
$SUDO chown -R $USER:$USER /home/shippable/build


# Set up the virtual environment for the worker
PIP=`which pip`
GIT=`which git`

if [ "$PIP" == "" ] || [ "$GIT" == "" ]; then
  echo "Installing python-pip and git"
  $SUDO apt-get update && $SUDO apt-get install -y python-pip ssh git-core
  pip install -I virtualenv==1.11.4
fi;

PIP=`which pip`
{
  echo "Installing virtualenv 1.11.4"
  if [[ ! -z "$SUDO" ]]; then
    $SUDO $PIP install -I virtualenv==1.11.4
  else
    $PIP install -I virtualenv==1.11.4
  fi
}||{
  wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
  python get-pip.py
  if [[ ! -z "$SUDO" ]]; then
    $SUDO $PIP install -I virtualenv==1.11.4
  else
    $PIP install -I virtualenv==1.11.4
  fi
}

echo "Installing requirements"
if [[ $INSTALL_REQS == true ]]; then
  virtualenv -p `which python2.7` $HOME/ve
  source $HOME/ve/bin/activate
  pip install -r requirements.txt
else
  if [ -f /deps_updated.txt ]; then
    echo "Build dependencies already updated..."
  else
    echo "Build dependencies not updated, installing..."
    pip install -r requirements.txt
  fi
  env
fi

mkdir -p $HOME/.ssh
mkdir -p /shippableci
touch $HOME/.ssh/config

# Turn off strict host key checking
echo -e "\nHost *\n\tStrictHostKeyChecking no" >> $HOME/.ssh/config
cat $HOME/.ssh/config
echo "Boot successful"
sleep .5

if [ -e '/home/shippable/terminate' ]; then
    rm -f /home/shippable/terminate
fi

for i in `seq 1 5`;
do
    if [ ! -e '/home/shippable/terminate' ]; then
        {
            python main.py
            echo "boot successful"
        } || {
            potential_error=true
        }
        sleep 3s
    else
        echo "boot successful"
        break;
    fi
done
