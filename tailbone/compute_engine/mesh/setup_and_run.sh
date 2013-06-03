#!/bin/bash

# Place holder run script for compute engine

wget https://pypi.python.org/packages/source/t/tornado/tornado-3.0.1.tar.gz
tar xvfz tornado-3.0.1.tar.gz
cd tornado-3.0.1
python setup.py build
python setup.py install
cd ..

python -c '
{{websocket.py}}
' &