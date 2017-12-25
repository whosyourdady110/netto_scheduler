# -*- coding: UTF-8 -*-
import tornado.web
import tornado.ioloop
import tornado.httpserver
import os
import configparser

from netto_configure_web.scheduler import SchedulerHandler
from netto_configure_web.app import AppHandler
from netto_configure_web.login import LoginHandler
from netto_configure_web.login import HomeHandler
from netto_configure_web.login import LogoutHandler
from netto_configure_web.service import ServiceHandler
from netto_configure_web.auth import AuthHandler
from netto_configure_web.group import GroupHandler
from netto_configure_web.router import RouterHandler
from netto_configure_web.setting import SettingHandler

def main():
    conf = configparser.ConfigParser()
    conf.read("web.ini")
    settings = {'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
                'static_path': os.path.join(os.path.dirname(__file__), 'static'),
                'static_url_prefix': '/static/',
                "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
                "login_url": "/login"
                }
    application = tornado.web.Application([
        (r'/', HomeHandler), (r'/scheduler', SchedulerHandler), (r'/app/(.*)', AppHandler),
        (r'/service', ServiceHandler),(r'/login', LoginHandler),(r'/logout', LogoutHandler),
        (r'/auth', AuthHandler),(r'/group', GroupHandler),(r'/router', RouterHandler),(r'/setting', SettingHandler)
    ], **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(conf.get("web", "port"))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
