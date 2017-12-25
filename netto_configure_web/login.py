# -*- coding: UTF-8 -*-
import tornado.web
import configparser

from netto_configure_web.configure_db import ConfigureDb
from netto_configure_web.base import BaseHandler

class HomeHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        conf = configparser.ConfigParser()
        conf.read("web.ini")
        mysql_host = conf.get("mysql", "host")
        mysql_port = conf.getint("mysql", "port")
        mysql_passwd = conf.get("mysql", "passwd")
        mysql_user = conf.get("mysql", "user")
        mysql_db = conf.get("mysql", "db")
        self.configurationDb = ConfigureDb(mysql_host, mysql_port, mysql_user, mysql_passwd, mysql_db)
    @tornado.web.authenticated
    def get(self):
        title = "netto configure web"
        self.render('homePage.html', username=self.current_user, title=title)
    def post(self):
        self.set_header("Content-Type", "application/json")
        try:
            data = tornado.escape.json_decode(self.request.body)
            if data["cmd_type"] == "getAllAppGroup":
                result = self.configurationDb.app_group_by_user('admin@meicai.cn')
                self.write({'ret': 200, "apps": result})
        except Exception as e:
            self.write({'ret': 500});
        finally:
            self.finish();


class LoginHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        conf = configparser.ConfigParser()
        conf.read("web.ini")
        mysql_host = conf.get("mysql", "host")
        mysql_port = conf.getint("mysql", "port")
        mysql_passwd = conf.get("mysql", "passwd")
        mysql_user = conf.get("mysql", "user")
        mysql_db = conf.get("mysql", "db")
        self.configurationDb = ConfigureDb(mysql_host,mysql_port,mysql_user,mysql_passwd,mysql_db)

    def get(self):
        title = "netto configure web"
        self.render("login.html", title=title)

    def post(self):
        self.set_header("Content-Type", "application/json");
        try:
            data = tornado.escape.json_decode(self.request.body)
            user = data["user"];
            result = self.configurationDb.check_user(user);
            if result == {}:
                self.write({'ret': 200, "errorCode":1, "message": "登錄名或密碼錯誤"});
            else:
                self.write({'ret': 200, "errorCode":0, "message": "登陸成功，正在跳轉","username":result["username"]});
                self.set_secure_cookie("netto_username", result["username"], expires_days=1)
        except Exception as e:
            self.write({'ret':500});
        finally:
            self.finish();

class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("netto_username")
        self.redirect("/")