#!/bin/bash

# install deps
apt-get install -y build-essential python-dev

# load reporter
curl -O http://psutil.googlecode.com/files/psutil-0.6.1.tar.gz
tar xvfz psutil-0.6.1.tar.gz
cd psutil-0.6.1
python setup.py install
cd ..
rm -rf psutil-0.6.1
rm psutil-0.6.1.tar.gz
curl -O https://raw.github.com/dataarts/tailbone/mesh/tailbone/compute_engine/load_reporter.py
python load_reporter.py &

# websocket server
curl -O https://pypi.python.org/packages/source/t/tornado/tornado-3.0.1.tar.gz
tar xvfz tornado-3.0.1.tar.gz
cd tornado-3.0.1
python setup.py install
cd ..
rm -rf tornado-3.0.1
rm tornado-3.0.1.tar.gz
curl -O https://raw.github.com/dataarts/tailbone/mesh/tailbone/compute_engine/mesh/websocket.py
python websocket.py 
