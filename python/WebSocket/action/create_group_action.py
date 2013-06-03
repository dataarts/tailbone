#!/usr/bin/env python
import logging
import tornado.ioloop

from action import Action
from model.group import Group
from manager.groups_manager import GroupsManager
from manager.connection_code_manager import ConnectionCodeManager

class CreateGroupAction(Action):

	def run(self, client, data):
		Action.run(self, client, data)
		gid = GroupsManager.add(Group()).gid
		logging.info('client creates new group (CID %s) (GID %s)' %(client.cid, gid))
		out_gid = gid
		if ConnectionCodeManager.USE_WORDS:
			out_gid = ConnectionCodeManager.to_word(gid)
		self.send_success({'gid': out_gid})