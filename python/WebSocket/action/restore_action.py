#!/usr/bin/env python
import logging

from action import Action
from manager.clients_manager import ClientsManager

class RestoreAction(Action):

	def run(self, client, data):
		Action.run(self, client, data)

		if 'cid' in data:
			restore_info = ClientsManager.restore_client_to_cid(client, data['cid'])
			if restore_info:
				return self.send_success(restore_info)
			else:
				return self.send_error('could not restore')
		else:
			return self.send_error('no CID specified')