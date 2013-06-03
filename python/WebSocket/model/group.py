#!/usr/bin/env python

class Group:

	''' static '''
	id_seed = 0

	''' member '''
	gid = 0
	clients = set()

	@staticmethod
	def get_unique_id():
		unique_id = Group.id_seed
		Group.id_seed = Group.id_seed + 1
		return unique_id

	def __init__(self):
		self.gid = Group.get_unique_id()
		self.clients = set()

	def add_member(self, client):
		self.clients.add(client)

	def remove_member(self, client):
		if client in self.clients:
			self.clients.remove(client)