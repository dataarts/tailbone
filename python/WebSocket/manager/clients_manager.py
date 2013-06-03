#!/usr/bin/env python
import sys
import time
import logging

from manager.groups_manager import GroupsManager
from manager.actions_manager import ActionsManager

class ClientsManager:

	''' const '''
	RESTORE_TIMEOUT = 5	# 5 seconds

	''' static '''
	clients = set()
	clients_by_cid = {}
	disconnection_times_by_cid = {}
	backup_by_cid = {}

	@staticmethod
	def on_client_connect(handler, client):
		ClientsManager.clients.add(client)
		ClientsManager.clients_by_cid[client.cid] = client
		ActionsManager.on_client_connect(handler, client)
		client.send_connection_info()
		logging.info('client connected (CID %s)' % client.cid)

	@staticmethod
	def on_client_disconnect(handler, client):
		ClientsManager.clients.remove(client)
		ClientsManager.save_disconnection_time(client)
		del ClientsManager.clients_by_cid[client.cid]
		ActionsManager.on_client_disconnect(handler, client)
		logging.info('client disconnected (CID %s)' % client.cid)

	@staticmethod
	def get_by_cid(cid):
		if cid in ClientsManager.clients_by_cid:
			return ClientsManager.clients_by_cid[cid]
		return None

	@staticmethod
	def get_all():
		return ClientsManager.clients

	@staticmethod
	def get_time_since_cid_disconnection(cid):
		if str(cid) in ClientsManager.disconnection_times_by_cid:
			return time.time() - ClientsManager.disconnection_times_by_cid[str(cid)]
		else:
			return sys.maxint

	@staticmethod
	def save_disconnection_time(client):
		ClientsManager.disconnection_times_by_cid[str(client.cid)] = time.time()

	@staticmethod
	def can_restore_client_to_cid(client, cid):
		return cid not in ClientsManager.clients_by_cid and str(cid) in ClientsManager.backup_by_cid and ClientsManager.get_time_since_cid_disconnection(cid) < ClientsManager.RESTORE_TIMEOUT

	@staticmethod
	def backup_client(client):
		backup = {'groups': set()}
		
		# backup groups
		for group in client.groups:
			backup['groups'].add(group.gid)

		ClientsManager.backup_by_cid[str(client.cid)] = backup
		

	@staticmethod
	def restore_client_to_cid(client, cid):
		cid = int(cid)
		if ClientsManager.can_restore_client_to_cid(client, cid):
			
			backup_data = ClientsManager.backup_by_cid[str(cid)]

			# change CID
			old_cid = client.cid
			client.cid = cid
			ClientsManager.clients_by_cid[client.cid] = client
			del ClientsManager.clients_by_cid[old_cid]

			# join groups
			joined_groups = []
			for gid in backup_data['groups']:
				group = GroupsManager.get_by_gid(gid)
				if group:
					client.join_group(group)
					joined_groups.append(group.gid)

			logging.info('restored client (CID %s) to (CID %s)' %(old_cid, client.cid))

			# return restore data
			return {'cid': client.cid, 'groups': joined_groups}

		else:
			return False