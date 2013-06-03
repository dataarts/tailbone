#!/bin/bash

if [ `python -c '
try:
  import tornado
  print 1
except:
  print 0
'` -ne 1 ] ; then
  echo 'tornado not found, downloading and installing'
  wget https://pypi.python.org/packages/source/t/tornado/tornado-3.0.1.tar.gz
  tar xvfz tornado-3.0.1.tar.gz
  cd tornado-3.0.1
  python setup.py build
  sudo python setup.py install
  cd ..
  sudo rm -rf tornado-3.0.1
  sudo rm tornado-3.0.1.tar.gz
fi

echo 'downloading and running latest websocket server code'
curl https://raw.github.com/dataarts/tailbone/mesh/tailbone/compute_engine/mesh/websocket.py > .websocket.py
python .websocket.py ${@:1:$#}
rm .websocket.py