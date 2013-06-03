#!/usr/bin/env python
import logging
import time
import threading
import tornado.escape

from manager.clients_manager import ClientsManager
from manager.actions_manager import ActionsManager
from manager.groups_manager import GroupsManager

class MessageManager:

	'''
	receives a message from user
	'''
	@staticmethod
	def on_message(handler, client, message):
		message_object = None

		try:
			message_object = tornado.escape.json_decode(message)
		except ValueError:
			logging.error('invalid message \'%s\'. Wrong JSON format.' % message)
			return None
		
		if not MessageManager.validate_message(message_object):
			logging.error('invalid message \'%s\'. No \'a\' (action) specified.' % message)
			return None

		action_name = message_object['a']
		data = None
		if 'd' in message_object:
			data = message_object['d']

		ActionsManager.run_action(handler, action_name, client, data)

	'''
	validates received message
	'''
	@staticmethod
	def validate_message(message_object):
		return 'a' in message_object

	'''
	converts the message object to string, adds sender info and timestamp
	'''
	@staticmethod
	def wrap_message(message, sender):
		sender_cid = -1
		if sender:
			sender_cid = sender.cid
		message_object = {'i': sender_cid, 'd': message, 't': time.time()}
		
		try:
			message_string = tornado.escape.json_encode(message_object)
			return message_string
		except ValueError:
			logging.error('could not encode message to send. Wrong JSON format.')
			return None

	'''
	broadcasts message to all connected users
	'''
	@staticmethod
	def broadcast_message(message, sender, synchronous=False, send_to_self=False):
		clients = ClientsManager.get_all()

		cids = set()

		for client in clients:
			if send_to_self or client != sender:
				cids.add(client.cid)

		MessageManager.send_message_to_cids(cids, message, sender, synchronous=synchronous)

	'''
	sends message to a set of users given their cids
	'''
	@staticmethod
	def send_message_to_cids(cids, message, sender, synchronous=False):

		message_string = MessageManager.wrap_message(message, sender)

		if synchronous:

			#calculate send times and delays
			max_send_time = 0
			send_times_by_cid = {}
			delays_by_cid = {}
			send_time_measurement_message_string = MessageManager.wrap_message({'action': 'stm'}, None)

			# send send time measurement messages
			for cid in cids:
				send_times_by_cid[cid] = MessageManager.send_message_to_cid(cid, send_time_measurement_message_string, None)
				if send_times_by_cid[cid] > max_send_time:
					max_send_time = send_times_by_cid[cid]

			# send synchronised messages with forced delay
			for cid in cids:
				MessageManager.send_delayed_message_to_cid(cid, message_string, sender, max_send_time - send_times_by_cid[cid])

		else:

			for cid in cids:
				MessageManager.send_message_to_cid(cid, message_string, sender)

	@staticmethod
	def send_delayed_message_to_cid(cid, message, sender, delay):
		# check if message needs wrapping
		message_string = message
		if not isinstance(message_string, str):
			message_string = MessageManager.wrap_message(message, sender)

		# send message at delay
		t = None
		def handler():
			t.cancel()
			MessageManager.send_message_to_cid(cid, message_string, sender)
		t = threading.Timer(delay + 0.001, handler)
		t.start()

	'''
	sends message to a particular user given his cid
	'''
	@staticmethod
	def send_message_to_cid(cid, message, sender):
		client = ClientsManager.get_by_cid(cid)
		
		# check if message needs wrapping
		message_string = message
		if not isinstance(message_string, str):
			message_string = MessageManager.wrap_message(message, sender)

		if client:
			return client.send(message_string)

	'''
	sends message to a set of user groups given their gids
	'''
	@staticmethod
	def send_message_to_gids(gids, message, sender, synchronous=False, send_to_self=False):

		cids = set()

		for gid in gids:
			group = GroupsManager.get_by_gid(gid)
			if group:
				for client in group.clients:
					cids.add(client.cid)

		MessageManager.send_message_to_cids(cids, message, sender, synchronous=synchronous)

	'''
	sends message to a particular group of users given the gid
	'''
	@staticmethod
	def send_message_to_gid(gid, message, sender, synchronous=False, send_to_self=False):
		group = GroupsManager.get_by_gid(gid)
		
		if group:
			cids = set()
			for client in group.clients:
				if client != sender or send_to_self:
					cids.add(client.cid)

			MessageManager.send_message_to_cids(cids, message, sender, synchronous=synchronous)
