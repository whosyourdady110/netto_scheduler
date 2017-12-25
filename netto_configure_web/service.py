# -*- coding: UTF-8 -*-
import tornado.web
import configparser
import json
from tornado.escape import json_encode

from netto_scheduler_agent.scripts.schedule_db import SchedulerDb
from netto_configure_web.configure_db import ConfigureDb
from netto_configure_web.base import BaseHandler
from netto_configure_web.service_api import ServiceDescApi
class ServiceHandler(BaseHandler):
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
        self.configurationDb = ConfigureDb(mysql_host, mysql_port, mysql_user, mysql_passwd, mysql_db)

    def get(self):
        title = "netto configure web"
        self.render("service.html", username=self.current_user, title=title)

    def post(self):
        data = json.loads(self.request.body.decode())
        if data['opType'] == 'query':
            desc_obj = ServiceDescApi(data["ip"], data["port"])
            res = desc_obj.find_services()
            if res is not None:
                self.configurationDb.save_service_info(res)
            ret = self.configurationDb.query_service_by_app_service(res, data["ip"], data["port"])
            self.write(json_encode({"ret": 200, "serviceInfoList": ret}))