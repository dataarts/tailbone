#!/usr/bin/env python
from manager.message_manager import MessageManager

class Action:

	client = None

	def run(self, client, data):
		self.client = client

	def send_response(self, success, data):
		MessageManager.send_message_to_cid(self.client.cid, {'type': 'response', 'action': self.__class__.__name__, 'success': success, 'data': data}, None)

	def send_success(self, data):
		self.send_response(True, data)

	def send_error(self, data):
		self.send_response(False, data)

	def on_client_connect(self, client):
		pass

	def on_client_disconnect(self, client):
		pass