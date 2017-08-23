import tornado.web
import tornado.ioloop
import tornado.httpserver
import os
import configparser

from netto_configure_web.scheduler import SchedulerHandler
from netto_configure_web.app import AppHandler


def main():
    conf = configparser.ConfigParser()
    conf.read("web.ini")
    settings = {'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
                'static_path': os.path.join(os.path.dirname(__file__), 'static'),
                'static_url_prefix': '/static/'}
    application = tornado.web.Application([
        (r'/', SchedulerHandler), (r'/scheduler', SchedulerHandler), (r'/app', AppHandler)
    ], **settings)
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(conf.get("web", "port"))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
