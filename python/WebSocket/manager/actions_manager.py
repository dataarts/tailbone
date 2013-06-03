#!/usr/bin/env python
import logging

class ActionsManager:

	''' static '''
	actions_by_class_by_name = {}

	@staticmethod
	def register_action(class_object, action_name, action):
		class_name = class_object.__class__.__name__

		if not class_name in ActionsManager.actions_by_class_by_name:
			ActionsManager.actions_by_class_by_name[class_name] = {'actions_by_name': {}, 'actions': set()}

		ActionsManager.actions_by_class_by_name[class_name]['actions_by_name'][action_name] = action
		ActionsManager.actions_by_class_by_name[class_name]['actions'].add(action)

	@staticmethod
	def get_action_by_name(class_object, action_name):
		class_name = class_object.__class__.__name__

		if class_name in ActionsManager.actions_by_class_by_name:
			if action_name in ActionsManager.actions_by_class_by_name[class_name]['actions_by_name']:
				return ActionsManager.actions_by_class_by_name[class_name]['actions_by_name'][action_name]

		return None

	@staticmethod
	def get_actions_by_class(class_object):
		class_name = class_object.__class__.__name__

		if class_name in ActionsManager.actions_by_class_by_name:
			return ActionsManager.actions_by_class_by_name[class_name]['actions']

		return None

	@staticmethod
	def run_action(class_object, action_name, client, data):
		action = ActionsManager.get_action_by_name(class_object, action_name)
		
		if action:
			return action.run(client, data)

		return None

	@staticmethod
	def on_client_connect(class_object, client):
		actions = ActionsManager.get_actions_by_class(class_object)
		if actions:
			for action in actions:
				action.on_client_connect(client)

	@staticmethod
	def on_client_disconnect(class_object, client):
		actions = ActionsManager.get_actions_by_class(class_object)
		if actions:
			for action in actions:
				action.on_client_disconnect(client)