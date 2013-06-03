#!/usr/bin/env python
import time
import logging
from manager.clients_manager import ClientsManager
from manager.message_manager import MessageManager

class Client:

	''' static '''
	id_seed = 0
	
	''' member '''
	cid = 0
	connection = None
	request_path = ''
	groups = set()

	@staticmethod
	def get_unique_id():
		unique_id = Client.id_seed
		Client.id_seed = Client.id_seed + 1
		return unique_id

	def __init__(self, connection, request_path):
		self.cid = Client.get_unique_id()
		self.connection = connection
		self.request_path = request_path
		self.groups = set()

	def send_connection_info(self):
		MessageManager.send_message_to_cid(self.cid, ['connect', self.cid], None)

	def send(self, message):
		if self.connection:
			send_start_time = time.time()
			self.connection.write_message(message)
			return (time.time() - send_start_time) * 1000

	def join_group(self, group, back_up=True):
		group.add_member(self)
		self.groups.add(group)

		if back_up:
			ClientsManager.backup_client(self)

		logging.info('client joins group (CID %s) (GID %s)' %(self.cid, group.gid))

	def leave_group(self, group, back_up=True):
		group.remove_member(self)
		self.groups.remove(group)

		if back_up:
			ClientsManager.backup_client(self)

		logging.info('client leaves group (CID %s) (GID %s)' %(self.cid, group.gid))

	def leave_all_groups(self, back_up=True):
		for group in self.groups:
			group.remove_member(self)
			logging.info('client leaves group (CID %s) (GID %s)' %(self.cid, group.gid))
		self.groups.clear()

		if back_up:
			ClientsManager.backup_client(self)