##
# @author Doug Fritz dougfritz@google.com
# @author Maciej Zasada maciej@unit9.com
##

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
nodes_by_id = {}
meshes_by_id = {}
mesh_id_by_node = {}


def enter(node, mesh_id):
  """Joins a node to a mesh. Creates new mesh if needed."""
  node.id = new_node_id()
  node.is_initiator_by_peer_node_id = {}
  nodes.append(node)
  nodes_by_id[node.id] = node

  if not mesh_id in meshes_by_id:
    meshes_by_id[mesh_id] = []
  mesh = meshes_by_id[mesh_id]
  mesh.append(node)
  mesh_id_by_node[node] = mesh_id

  logging.debug('enter (node ID: %s, mesh ID: %s)' % (node.id, mesh_id))
  # exist should be the first thing sent
  send_to_node(node, node, json.dumps(['connect'] + get_exist(mesh, node.id)))
  # make the enter call be a self message for routing
  msg = json.dumps(['enter', node.id])
  for n in mesh:
    if n != node:
      send_to_node(n, n, msg)

  # send_to_mesh(mesh, node, ['enter', node.id])
  return True


def leave(node):
  """Removes node from meshes, disconnects node."""
  if not node:
    return
  mesh_id = mesh_id_by_node[node]
  mesh = meshes_by_id[mesh_id]
  del mesh_id_by_node[node]
  mesh.remove(node)
  if len(mesh) == 0:
    del meshes_by_id[mesh_id]
  else:
    msg = json.dumps(['leave', node.id])
    for n in mesh:
      if n != node:
        send_to_node(n, n, msg)
  nodes.remove(node)
  del nodes_by_id[node.id]
  try:
    node.close()
  except:
    pass
  logging.debug('leave (node ID: %s, mesh ID: %s)' % (node.id, mesh_id))


def parse_message(node, message):
  """Interprets node message and directs it forward."""
  mesh_id = mesh_id_by_node[node]
  message_object = None
  to_nodes = None
  message_data = None
  print 'received %s (node ID: %s, mesh ID: %s)' % (message, node.id, mesh_id)
  try:
    message_object = json.loads(message)
    to_nodes = message_object[0]
    # check if it is a list of messages
    if type(to_nodes[0]) is list:
      for msg in message_object:
        to_nodes, message_data = msg
        send_to_node_ids(to_nodes, node, message_data)
      return
    message_data = message_object[1]
  except AttributeError as e:
    print e
    return
  send_to_node_ids(to_nodes, node, message_data)


def wrap_message(message, sender_node):
  """Wraps message with sender ID and timestamp."""
  try:
    message_string = json.dumps([sender_node.id, time.time(), message])
    return message_string
  except:
    return None


def send_to_node(node, sender_node, message):
  """Sends message to a node."""
  message_string = wrap_message(message, sender_node)
  if message_string:
    logging.info('sending to node %s (node ID: %s, to ID: %s)' % (message_string, sender_node.id, node.id))
    try:
      node.write_message(message_string)
    except:
      pass


def send_to_node_ids(node_ids, sender_node, message):
  """Sends message to array of nodes."""
  for node_id in node_ids:
    if node_id in nodes_by_id:
      send_to_node(nodes_by_id[node_id], sender_node, message)
 

def send_to_mesh(mesh, sender_node, message):
  """Sends message to a mesh."""
  message_string = wrap_message(message, sender_node)
  if message_string:
    logging.info('sending to mesh %s (node ID: %s, mesh ID: *)' % (message_string, sender_node.id))
    for node in mesh:
      if node != sender_node:
        try:
          node.write_message(message_string)
        except:
          pass
  else:
    logging.warning('invalid message format %s' % message)


def get_exist(mesh, ignore):
  """Gets a list of connected node IDs by mesh."""
  return [node.id for node in mesh if node.id != ignore]


def new_node_id():
  """Generates new node ID."""
  global node_id_seed
  node_id = node_id_seed
  node_id_seed = node_id_seed + 1
  return node_id


class Handler(tornado.websocket.WebSocketHandler):
  """WebSocket connection and message handler."""

  def open(self):
    enter(self, self.request.path[1:])

  def on_message(self, message):
    parse_message(self, message)

  def on_close(self):
    leave(self)


def main():
  """Instantiates WebSocket server Usage: TODO: add usage notes"""
  parser = OptionParser()
  parser.add_option('-d', '--debug', dest='debug', action='store_true', help='enables debug mode', metavar='DEBUG', default=False)
  parser.add_option('-p', '--port', dest='port', help='port number to run the server on', metavar='PORT', default=2345)
  parser.add_option('-u', '--url', dest='url', help='base URL for connections', metavar='URL', default='')
  parser.add_option('-r', '--report', dest='report', help='URL to report load to', metavar='REPORT', default='')
  (options, args) = parser.parse_args()

  server = tornado.httpserver.HTTPServer(tornado.web.Application([(options.url + '/.*', Handler)]))
  logging.getLogger().setLevel(logging.DEBUG if options.debug else logging.INFO)
  server.listen(options.port)
  logging.debug('starting server on port %s' % options.port)
  tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
  main()
