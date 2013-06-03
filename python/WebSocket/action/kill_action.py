#!/usr/bin/env python
import logging
import tornado.ioloop
from action import Action

class KillAction(Action):

	def run(self, client, data):
		Action.run(self, client, data)
		logging.info('received kill action from CID %s, shutting down' % client.cid)
		tornado.ioloop.IOLoop.instance().stop()