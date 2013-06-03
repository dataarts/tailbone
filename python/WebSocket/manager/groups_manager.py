#!/usr/bin/env python
import logging
from manager.connection_code_manager import ConnectionCodeManager

class GroupsManager:

	''' static '''
	groups = set()
	groups_by_gid = {}

	@staticmethod
	def add(group):
		GroupsManager.groups.add(group)
		GroupsManager.groups_by_gid[group.gid] = group
		return group

	@staticmethod
	def remove(group):
		GroupsManager.groups.remove(group)
		del GroupsManager.groups_by_gid[group.gid]
		return group

	@staticmethod
	def get_by_gid(gid):
		gid_int = None
		try:
			gid_int = int(gid)
		except ValueError:
			if ConnectionCodeManager.USE_WORDS:
				gid_int = ConnectionCodeManager.from_word(gid)
			else:
				return None

		if gid_int in GroupsManager.groups_by_gid:
			return GroupsManager.groups_by_gid[gid_int]
			
		return None