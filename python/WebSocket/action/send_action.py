#!/usr/bin/env python
import logging
import tornado.ioloop

from action import Action
from manager.message_manager import MessageManager

class SendAction(Action):

	def run(self, client, data):
		Action.run(self, client, data)

		broadcast = 'broadcast' in data and (data['broadcast'] == True or data['broadcast'] == 'true')
		synchronous = 'synchronous' in data and (data['synchronous'] == True or data['synchronous'] == 'true')
		send_to_self = 'sendToSelf' in data and (data['sendToSelf'] == True or data['sendToSelf'] == 'true')

		message_data = None
		if 'data' in data:
			message_data = data['data']

		if 'cid' in data:
			MessageManager.send_message_to_cid(data['cid'], message_data, client, synchronous=synchronous)

		if 'cids' in data:
			MessageManager.send_message_to_cids(data['cids'], message_data, client, synchronous=synchronous)

		if 'gid' in data:
			MessageManager.send_message_to_gid(data['gid'], message_data, client, synchronous=synchronous, send_to_self=send_to_self)

		if 'gids' in data:
			MessageManager.send_message_to_gids(data['gids'], message_data, client, synchronous=synchronous, send_to_self=send_to_self)

		if broadcast:
			MessageManager.broadcast_message(message_data, client, synchronous=synchronous, send_to_self=send_to_self)
