#!/usr/bin/python

# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A program to check load level and report to Load Balancer.

Periodically checks load level and report the result to AppEngine.
The file is passed to Compute Engine instances as a start up script.
At that time, template variables are filled with real values.
"""


import os
import socket
import subprocess
import time
import urllib


class CpuUsageFetcher(object):
  """Class to get CPU usage information of the system and report."""

  NUM_PLAYERS_FILE = '/num_players'
  REGISTER_URL = 'http://{{ hostname }}/register'
  UPDATE_URL = 'http://{{ hostname }}/load'

  def __init__(self):
    self.hostname = socket.gethostname()
    self.prev_idle = 0
    self.prev_total = 0

  def Register(self):
    """Registers this Compute Engine instance to AppEngine load balancer."""
    urllib.urlopen(self.REGISTER_URL,
                   data=urllib.urlencode({'name': self.hostname}))

  def _GetNumPlayers(self):
    try:
      return int(open(self.NUM_PLAYERS_FILE).read())
    except IOError:
      return 0

  def Check(self):
    """Checks CPU usage and reports to AppEngine load balancer."""
    # 8 Players are the max.
    load_level = int(12.5 * self._GetNumPlayers())

    # Send POST request to /load.
    urllib.urlopen(self.UPDATE_URL,
                   urllib.urlencode({'name': self.hostname,
                                     'load': load_level}))


class GameSetUp(object):
  """Class to retrieve game server start up script and execute it."""

  GAME_SETUP_AND_START_URL = 'http://{{ hostname }}/setup-and-start-game'

  def Start(self):
    response = urllib.urlopen(self.GAME_SETUP_AND_START_URL)
    local_script_file = 'startup-and-start'
    f = open(local_script_file, 'w')
    f.write(response.read())
    f.close()
    os.chmod(local_script_file, 0700)
    subprocess.call('./' + local_script_file)


def main():
  GameSetUp().Start()
  cpu_fetcher = CpuUsageFetcher()
  cpu_fetcher.Register()
  time.sleep(5)
  while True:
    cpu_fetcher.Check()
    time.sleep(5)


if __name__ == '__main__':
  main()
