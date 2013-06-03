##
# @author Doug Fritz dougfritz@google.com
# @author Maciej Zasada maciej@unit9.com
##

import re
import json
import time
from optparse import OptionParser
import logging
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web

node_id_seed = 1
nodes = []
meshes_by_id = {}
mesh_id_by_node = {}

##
# Joins a node to a mesh.
# Creates new mesh if needed.
##
def enter(node, mesh_id):
  node.id = new_node_id()
  nodes.append(node)

  if not mesh_id in meshes_by_id:
    meshes_by_id[mesh_id] = []
  mesh = meshes_by_id[mesh_id]
  mesh.append(node)
  mesh_id_by_node[node] = mesh_id

  logging.debug('enter (node ID: %s, mesh ID: %s)' % (node.id, mesh_id))
  send_to_mesh(mesh, node, ['enter', node.id])
  return True

##
# Removes node from meshes, disconnects node.
##
def leave(node):
  mesh_id = mesh_id_by_node[node]
  mesh = meshes_by_id[mesh_id]
  del mesh_id_by_node[node]
  mesh.remove(node)
  if len(mesh) == 0:
    del meshes_by_id[mesh_id]
  else:
    send_to_mesh(mesh, node, ['leave', node.id])
  nodes.remove(node)
  logging.debug('leave (node ID: %s, mesh ID: %s)' % (node.id, mesh_id))

##
# Interprets node message and directs it forward.
##
def parse_message(node, message):
  mesh_id = mesh_id_by_node[node]
  forward_message = message
  try:
    forward_message = json.loads(message)
  except:
    pass
  print 'received %s (node ID: %s, mesh ID: %s)' % (message, node.id, mesh_id)
  send_to_mesh(meshes_by_id[mesh_id_by_node[node]], node, forward_message)

##
# Sends a message to a node.
##
def send_to_node(node, message):
  pass # node.write_message(message)

##
# Sends a message to a mesh
##
def send_to_mesh(mesh, sender_node, message):
  message_string = None
  try:
    message_string = json.dumps([sender_node.id, time.time(), message])
    logging.info('sending to mesh %s (node ID: %s, mesh ID: *)' % (message_string, sender_node.id))
  except:
    logging.warning('invalid message format %s' % message)
    return

  for node in mesh:
    if node != sender_node:
      node.write_message(message_string)


##
# Generates new node ID.
##
def new_node_id():
  global node_id_seed
  node_id = node_id_seed
  node_id_seed = node_id_seed + 1
  return node_id

##
# WebSocket connection and message handler
##
class Handler(tornado.websocket.WebSocketHandler):
  def open(self):
    enter(self, self.request.path[1:])

  def on_message(self, message):
    parse_message(self, message)

  def on_close(self):
    leave(self)

##
# Instantiates WebSocket server
# Usage: TODO: add usage notes
##
def main():
  parser = OptionParser()
  parser.add_option('-d', '--debug', dest='debug', action='store_true', help='enables debug mode', metavar='DEBUG', default=False)
  parser.add_option('-p', '--port', dest='port', help='port number to run the server on', metavar='PORT', default=2345)
  parser.add_option('-u', '--url', dest='url', help='base URL for connections', metavar='URL', default='')
  (options, args) = parser.parse_args()

  server = tornado.httpserver.HTTPServer(tornado.web.Application([(options.url + '/.*', Handler)]))
  logging.getLogger().setLevel(logging.DEBUG if options.debug else logging.INFO)
  server.listen(options.port)
  logging.debug('starting server on port %s' % options.port)
  tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
  main()