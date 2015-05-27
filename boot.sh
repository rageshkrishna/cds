#!/bin/bash -e

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
echo "CDS_DIR : $CDS_DIR"
cd $CDS_DIR

if [[ $INSTALL_REQS == true ]]; then
  pip install -r $CDS_DIR/requirements.txt
fi

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
