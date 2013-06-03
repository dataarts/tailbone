#!/usr/bin/env python
import logging
import tornado.httpserver
import tornado.websocket
import tornado.web

from manager.clients_manager import ClientsManager
from manager.message_manager import MessageManager
from model.client import Client

class U9HandlerBase(tornado.websocket.WebSocketHandler):

	''' static '''
	set_up = set()

	''' member '''
	client = None

	def __init__(self, application, request, **kwargs):
		
		tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
		
		# check if this handler is already set up and set it up if not
		if not self.__class__.__name__ in U9HandlerBase.set_up:
			U9HandlerBase.set_up.add(self.__class__.__name__)
			self.setup()

	def setup(self):
		logging.info('setting up %s' % self.__class__.__name__)

	def broadcast_message(self, message):
		send_count = 0
		for client in self.clients:
			if client != self:
				try:
					client.write_message(message)
					send_count = send_count + 1
				except:
					logging.error('Error sending message', exc_info = True)

	def allow_draft76(self):
		return True

	def open(self):
		self.client = Client(self, self.request.path)
		ClientsManager.on_client_connect(self, self.client)

	def on_close(self):
		ClientsManager.on_client_disconnect(self, self.client)

	def on_message(self, message):
		MessageManager.on_message(self, self.client, message)
