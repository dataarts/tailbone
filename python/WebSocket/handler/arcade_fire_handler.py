#!/usr/bin/env python
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import uuid

from handler.u9_handler_base import U9HandlerBase
from manager.actions_manager import ActionsManager

from action.kill_action import KillAction
from action.restore_action import RestoreAction
from action.send_action import SendAction
from action.create_group_action import CreateGroupAction
from action.join_group_action import JoinGroupAction
from action.leave_group_action import LeaveGroupAction

class ArcadeFireHandler(U9HandlerBase):

	def setup(self):
		super(ArcadeFireHandler, self).setup()

		# set up actions
		ActionsManager.register_action(self, 'kill', KillAction())
		ActionsManager.register_action(self, 'restore', RestoreAction())
		ActionsManager.register_action(self, 'send', SendAction())
		ActionsManager.register_action(self, 'create_group', CreateGroupAction())
		ActionsManager.register_action(self, 'join_group', JoinGroupAction())
		ActionsManager.register_action(self, 'leave_group', LeaveGroupAction())

	def on_message(self, message):
		super(ArcadeFireHandler, self).on_message(message)