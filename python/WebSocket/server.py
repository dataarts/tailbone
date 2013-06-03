#!/usr/bin/env python
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os
import os.path
import uuid

from tornado.options import define, options
from handler.arcade_fire_handler import ArcadeFireHandler

port_number = None

if os.path.dirname(os.path.abspath(__file__)).find('/test/') != -1:
    print 'setting up test version'
    port_number = 12350
elif os.path.dirname(os.path.abspath(__file__)).find('arcade-fire/prod') != -1:
    print 'setting up prod version'
    port_number = 2468
else:
    print 'setting up dev version'
    port_number = 12347


define('port', default = port_number, help = 'run on the given port', type = int)

class Application(tornado.web.Application):
    
    def __init__(self):
        
        handlers = [
            (r'/roomname', ArcadeFireHandler),
        ]

        settings = dict(
            cookie_secret = '^hgsf`@$$@!bcI0@1__XX31#9<$/QQ',
            xsrf_cookies = True,
            autoescape = None,
        )

        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    logging.info('server started on port %s (PID %s)' % (options.port, os.getpid()))
    open('server.pid', 'w').write(str(os.getpid()))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
