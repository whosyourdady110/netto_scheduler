import tornado.web
import configparser
from tornado.escape import json_encode

from netto_scheduler_agent.scripts.schedule_db import SchedulerDb
from netto_configure_web.configure_db import ConfigureDb
from netto_scheduler_agent.scripts.task import TaskEnvironment


class AppHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        conf = configparser.ConfigParser()
        conf.read("web.ini")
        ip = conf.get("redis", "ip")
        port = conf.getint("redis", "port")
        timeout = conf.getint("redis", "timeout")
        self.db = SchedulerDb(ip, port, timeout)

        mysql_host = conf.get("mysql", "host")
        mysql_port = conf.getint("mysql", "port")
        mysql_passwd = conf.get("mysql", "passwd")
        mysql_user = conf.get("mysql", "user")
        mysql_db = conf.get("mysql", "db")
        self.configurationDb = ConfigureDb(mysql_host,mysql_port,mysql_user,mysql_passwd,mysql_db)

    def get(self, cmd_type):
        title = "netto configure web"
        environments = self.db.query_all_environments()
        if len(environments) > 0:
            cur_env = environments[0]
        else:
            cur_env = TaskEnvironment("netto", [])
        if(cmd_type=="index"):
            self.render("app.html", title=title, environments=environments, cur_env=cur_env )
        if(cmd_type=="edit"):
            appName = self.get_argument('app_name');
            self.render("app_edit.html", title=title, environments=environments, cur_env=cur_env,cur_app=appName)
        elif(cmd_type=="app_list"):
            self.set_header("Content-Type", "application/json");
            self.write(json_encode({"ret":200,"apps":self.configurationDb.list_app()}));
        elif (cmd_type == "app_detail"):
            self.set_header("Content-Type", "application/json");
            appName = self.get_argument('app_name');
            app = self.configurationDb.get_app_detail(appName);
            self.write(json_encode({"ret":200,"app":app}));
        elif (cmd_type == "app_server_groups"):
            self.set_header("Content-Type", "application/json");
            appName = self.get_argument('app_name');
            serverGroups = self.configurationDb.get_app_server_groups(appName)
            self.write(json_encode({"ret": 200, "serverGroups": serverGroups}));


    def post(self, cmd_type):
        self.set_header("Content-Type", "application/json");
        try:
            data = tornado.escape.json_decode(self.request.body)
            if cmd_type == "saveApp":
                app  = data["app"];
                self.configurationDb.save_app(app);
                self.write({'ret': 200, "cmd_type": cmd_type});
            elif cmd_type == "removeApp":
                appName = data["appName"];
                self.configurationDb.remove_app(appName)
                self.write({'ret': 200, "cmd_type": cmd_type});
            elif cmd_type == "removeServerGroup":
                appName = data["appName"];
                groupName = data["groupName"]
                self.configurationDb.remove_group(appName,groupName)
                self.write({'ret': 200, "cmd_type": cmd_type});
            elif cmd_type == "saveServerGroup":
                appName = data["appName"];
                group = data["serverGroup"]
                servers = group["server_strs"];
                routerKeys = group["router_keys"];
                groupName = group["group_name"]
                self.configurationDb.create_server_group(appName,groupName,servers,routerKeys)
                self.write({'ret': 200, "cmd_type": cmd_type});

        except Exception as e:
            self.write( {'ret':500});
        finally:
            self.finish();