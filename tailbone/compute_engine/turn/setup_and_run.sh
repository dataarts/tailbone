# setup and start a turn server

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

# load turnserver
curl -O http://rfc5766-turn-server.googlecode.com/files/turnserver-1.8.7.0-binary-linux-wheezy-ubuntu-mint-x86-64bits.tar.gz
tar xvfz turnserver-1.8.7.0-binary-linux-wheezy-ubuntu-mint-x86-64bits.tar.gz
dpkg -i rfc5766-turn-server_1.8.7.0-1_amd64.deb
apt-get -f install
turnserver --use-auth-secret -v -a -X -f --static-auth-secret notasecret -r localhost -r appspot.com
