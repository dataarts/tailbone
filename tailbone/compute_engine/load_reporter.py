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
from itertools import izip, tee

def pairwise(iterable):
  a, b = tee(iterable)
  next(b, None)
  return izip(a, b)


def UpdateStats(cpu, memory, net_in, net_out):
  mem_history = []
  cpu_history = []
  net_in_history = []
  net_out_history = []
  buffer_len = 120
  window = buffer_len / 2
  # to baseline the cpu call
  psutil.cpu_percent(interval=1)
  # TODO: remove outliers
  while True:
    vmem = psutil.virtual_memory()
    mem_history.append(vmem.percent / 100)
    mem_history = mem_history[-buffer_len:]
    l = sorted(mem_history, reverse=True)[:window]
    memory.value = sum(l) / len(l)
    cpu_history.append(psutil.cpu_percent(0) / 100)
    cpu_history = cpu_history[-buffer_len:]
    l = sorted(cpu_history, reverse=True)[:window]
    cpu.value = sum(l) / len(l)
    net = psutil.network_io_counters()
    net_in_history.append(net.bytes_recv)
    net_in_history = net_in_history[-buffer_len:]
    bytes = [y-x for x,y in pairwise(net_in_history)]
    if bytes:
      l = sorted(bytes, reverse=True)[:window]
      net_in.value = sum(l) / len(l)
    net_out_history.append(net.bytes_sent)
    net_out_history = net_out_history[-buffer_len:]
    bytes = [y-x for x,y in pairwise(net_out_history)]
    if bytes:
      l = sorted(bytes, reverse=True)[:window]
      net_out.value = sum(l) / len(l)
    time.sleep(10)


def ReportServer(cpu, memory, net_in, net_out):

  class ReportHandler(BaseHTTPRequestHandler):
    def do_GET(self):
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({
        "cpu": cpu.value,
        "mem": memory.value,
        "net_in": net_in.value,
        "net_out": net_out.value,
      }))

  PORT_NUMBER = 8888
  server = HTTPServer(("", PORT_NUMBER), ReportHandler)
  print("Load reporter started on port ", PORT_NUMBER)
  server.serve_forever()
  server.socket.close()


if __name__ == '__main__':
  cpu = Value('d', 0)
  memory = Value('d', 0)
  net_in = Value('d', 0)
  net_out = Value('d', 0)
  server = Process(target=ReportServer, args=(cpu, memory, net_in, net_out)).start()
  stats = Process(target=UpdateStats, args=(cpu, memory, net_in, net_out)).start()
