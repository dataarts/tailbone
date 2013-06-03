#!/usr/bin/env python
import logging
import tornado.ioloop

from action import Action
from manager.groups_manager import GroupsManager

class LeaveGroupAction(Action):

	def run(self, client, data):
		Action.run(self, client, data)

		if 'gid' in data:
			group = GroupsManager.get_by_gid(data['gid'])
			if group:
				client.leave_group(group)
				return self.send_success({'gid': group.gid})

		return self.send_error({'gid': group.gid})

	def on_client_disconnect(self, client):
		Action.on_client_connect(self, client)
		client.leave_all_groups(back_up=False)