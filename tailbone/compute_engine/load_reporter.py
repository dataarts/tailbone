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

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import json
from multiprocessing import Process, Value
import psutil
import time


def UpdateStats(cpu, memory):
  mem_history = []
  cpu_history = []
  buffer_len = 100
  # TODO: remove outliers
  while True:
    vmem = psutil.virtual_memory()
    mem_history.append(vmem.percent)
    mem_history = mem_history[-buffer_len:]
    memory.value = sum(mem_history) / len(mem_history)
    cpu_history.append(psutil.cpu_percent(0))
    cpu_history = cpu_history[-buffer_len:]
    cpu.value = sum(cpu_history) / len(cpu_history)
    time.sleep(20)


def ReportServer(cpu, memory):

  class ReportHandler(BaseHTTPRequestHandler):
    def do_GET(self):
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({
        "cpu": cpu.value,
        "mem": memory.value
      }))

  PORT_NUMBER = 8888
  server = HTTPServer(("", PORT_NUMBER), ReportHandler)
  print("Load reporter started on port ", PORT_NUMBER)
  server.serve_forever()
  server.socket.close()


if __name__ == '__main__':
  cpu = Value('d', 0)
  memory = Value('d', 0)
  server = Process(target=ReportServer, args=(cpu, memory)).start()
  stats = Process(target=UpdateStats, args=(cpu, memory)).start()
