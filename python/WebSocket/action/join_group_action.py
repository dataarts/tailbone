#!/usr/bin/env python
import logging
import tornado.ioloop

from action import Action
from manager.groups_manager import GroupsManager
from manager.connection_code_manager import ConnectionCodeManager

class JoinGroupAction(Action):

	def run(self, client, data):
		Action.run(self, client, data)
		
		if 'gid' in data:
			group = GroupsManager.get_by_gid(data['gid'])
			if group:
				client.join_group(group)
				out_gid = group.gid
				if ConnectionCodeManager.USE_WORDS:
					out_gid = ConnectionCodeManager.to_word(group.gid)
				return self.send_success({'gid': out_gid})

			return self.send_error({'gid': data['gid']})

		return self.send_error()