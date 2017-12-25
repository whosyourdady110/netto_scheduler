# -*- coding: UTF-8 -*-
import tornado.web
import configparser
from tornado.escape import json_encode

from netto_scheduler_agent.scripts.schedule_db import SchedulerDb
from netto_configure_web.configure_db import ConfigureDb
from netto_scheduler_agent.scripts.task import TaskEnvironment
from netto_configure_web.base import BaseHandler


class RouterHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        conf = configparser.ConfigParser()
        conf.read("web.ini")
        ip = conf.get("redis", "host")
        port = conf.getint("redis", "port")
        timeout = conf.getint("redis", "timeout")
        self.db = SchedulerDb(ip, port, timeout)

        mysql_host = conf.get("mysql", "host")
        mysql_port = conf.getint("mysql", "port")
        mysql_passwd = conf.get("mysql", "passwd")
        mysql_user = conf.get("mysql", "user")
        mysql_db = conf.get("mysql", "db")
        self.configurationDb = ConfigureDb(mysql_host,mysql_port,mysql_user,mysql_passwd,mysql_db)

    @tornado.web.authenticated
    def get(self):
        title = "netto configure web"
        cur_env = self.get_argument('env');
        self.render("router.html", username=self.current_user, title=title,cur_env=cur_env)


    def post(self):
        self.set_header("Content-Type", "application/json")
        data = tornado.escape.json_decode(self.request.body)
        try:
            if data["cmd_type"] == "getInfo":
                cur_env = data['env'];
                if cur_env is not None:
                    env = cur_env.split(".")
                    app = env[0]
                    routerInfos = self.configurationDb.getRouterInfo(app);
                    self.write({'ret': 200, "routerInfos": routerInfos});
            elif data["cmd_type"] == "getRouterParam":
                id = data['id'];
                routerParams = self.configurationDb.getRouterParamsById(id);
                self.write({"routerParams": routerParams});
            elif data["cmd_type"] == "delete":
                id = data['id'];
                self.configurationDb.getDeleteRouterById(id);
                self.write({'ret': 200});
            elif data["cmd_type"] == "save":
                router = data['routerParams']
                self.configurationDb.saveRouter(router)
                self.write({'ret': 200});

        except Exception as e:
            self.write( {'ret':500});
        finally:
            self.finish();