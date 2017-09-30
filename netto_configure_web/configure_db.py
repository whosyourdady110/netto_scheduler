# -*- coding: UTF-8 -*-
import pymysql
import re;
import json
from itertools import groupby
from netto_scheduler_agent.scripts.schedule_db import SchedulerDb
from netto_scheduler_agent.scripts.task import TaskEnvironment

class ConfigureDb:
    def __init__(self, host,port,user,passwd,db ):
        self._host = host;
        self._port = port;
        self._user = user;
        self._db = db;
        self._password = passwd;


    def create_connection(self):
        connection = pymysql.connect(host=self._host,
                                     user=self._user,
                                     password=self._password,
                                     db=self._db,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        return connection;

    def save_app(self,appInfo):
        app = self.get_app(appInfo["appName"]);
        if app is None:
            self.create_app(appInfo);
        else:
            self.update_app(appInfo);
        self.create_server_group(appInfo["appName"],"*",appInfo["defaultServerGroup"],'*');
        return {};

    def create_server_group(self,appName,groupName,servers,routerKeys):
        connection = self.create_connection();
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "delete from t_app_server_group where app_name=%s and group_name=%s";
                cursor.execute(sql, (appName,groupName,))
                serversList = servers.splitlines();
                hostRegex = re.compile("([a-zA-Z0-9\:\.]+)\s*")
                weightRegex = re.compile("weight\=([0-9]+)")
                for serverString in serversList:
                    m = hostRegex.search(serverString);
                    if m is not None:
                        host = m.group(1);
                        port = 8999;
                        hostAndPort = host.split(":");

                        if len(hostAndPort) >1 :
                            host = hostAndPort[0]
                            port = int(hostAndPort[1]);

                        weight = 1;
                        m2 = weightRegex.search(serverString);
                        try:
                            if m2 is not None:
                                weight = int(m2.group(1));
                        except:
                            print("error {}".format(serverString))

                        insert_sql = "insert into t_app_server_group(`app_name`,`group_name`,`host`,`port`,`c_t`,`weight`,`router_keys`) values(%s,%s,%s,%s,now(),%s,%s) ";
                        cursor.execute(insert_sql, (appName,groupName,host,port,weight,routerKeys,))

            connection.commit();
        finally:
            connection.close();

    def list_app(self):
        ret = [];
        connection = self.create_connection();
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT id,app_name,description,protocol FROM  t_app_info"
                cursor.execute(sql)
                result = cursor.fetchall()
                for app in result:
                    appInfo = {"appName":app["app_name"],"id":app["id"],"description":app["description"],"appProtocol":app["protocol"]};
                    defaultServerGroup = self.get_app_server_group("*",app["app_name"]);
                    appInfo["defaultServerGroup"] = "\n".join(defaultServerGroup)
                    ret.append(appInfo);

        finally:
            connection.close();
        return ret;

    def update_app(self,appInfo):
        connection = self.create_connection();
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "update  `t_app_info` set description=%s where app_name=%s"
                cursor.execute(sql, (appInfo["description"],appInfo["appName"],))

            connection.commit();
        finally:
            connection.close();

    def create_app(self,appInfo):
        connection = self.create_connection();
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "INSERT INTO  `t_app_info`(`app_name`,`description`,`c_t`) VALUES(%s,%s,now())"
                cursor.execute(sql, (appInfo["appName"],appInfo["description"],))

            connection.commit();
        finally:
            connection.close();

    def get_app_server_groups(self,appName):
        connection = self.create_connection();
        servers = [];
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT id,host,port,weight,group_name,router_keys FROM  t_app_server_group  WHERE `app_name`=%s "
                cursor.execute(sql, (appName,))
                servers = cursor.fetchall();

        finally:
            connection.close();
        server_groups = [];
        for k, group in groupby(servers, lambda server: server['group_name']):
            group_servers = [];
            router_keys = '';
            for server in group:
                serverStr = "{}:{} weight={}".format(server["host"], server["port"], server["weight"]);
                router_keys = server["router_keys"]
                group_servers.append(serverStr);


            server_groups.append(
                {"group_name":k,"router_keys":router_keys,"servers":group_servers,"server_strs":"\n".join(group_servers)}
            )

        return server_groups;


    def get_app_server_group(self,groupName,appName):
        connection = self.create_connection();
        servers = [];
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT host,port,weight,router_keys FROM  t_app_server_group  WHERE `app_name`=%s and group_name=%s"
                cursor.execute(sql, (appName,groupName,))
                servers = cursor.fetchall();

        finally:
            connection.close();

        ret = []
        for server in servers:
            serverStr = "{}:{} weight={}".format(server["host"],server["port"],server["weight"]);
            ret.append(serverStr);
        return ret;

    def remove_group(self,appName,groupName):
        connection = self.create_connection();

        try:
            with connection.cursor() as cursor:

                sql = "delete from t_app_server_group where group_name=%s and app_name=%s"
                cursor.execute(sql, (groupName,appName,))

            connection.commit();
        finally:
            connection.close();

    def remove_app(self,appName):
        connection = self.create_connection();

        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "delete from t_app_info where app_name=%s"
                cursor.execute(sql, (appName,))
                sql = "delete from t_app_server_group where app_name=%s"
                cursor.execute(sql, (appName,))

            connection.commit();
        finally:
            connection.close();

    def get_app_detail(self,appName):
        app = self.get_app(appName);
        if app is not None:
            defaultServerGroup = self.get_app_server_group("*",appName);
            app["defaultServerGroup"] = "\n".join(defaultServerGroup)
        return app;

    def get_app(self,appName):
        connection = self.create_connection();

        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT id,app_name,description,protocol FROM  t_app_info  WHERE `app_name`=%s"
                cursor.execute(sql, (appName,))
                result = cursor.fetchone()
                if result is not None:
                    return {"appName":result["app_name"],"description":result["description"],"appProtocol":result["protocol"]};

        finally:
            connection.close();



class SchedulerConfigureDb:
    def __init__(self, conf):
        self.db = SchedulerDb(host=conf.get("redis", "host"), port=conf.getint("redis", "port"),
                              timeout=conf.getint("redis", "timeout"))

        self.conn = pymysql.Connect(
            host=conf.get("mysql", "host"),
            port=conf.getint("mysql", "port"),
            user=conf.get("mysql", "user"),
            passwd=conf.get("mysql", "passwd"),
            db=conf.get("mysql", "db"),
            charset='utf8'
        )

    def query_tasks_info(self, env):
        return self.db.query_tasks_info(env)

    def query_task_param(self, param_id):
        return self.db.query_task_param(param_id)

    def query_all_environments(self):
        try:
            cursor = self.conn.cursor()
            # sql = "select s_app,s_group,owners,last_time from system_env"
            sql = "select distinct(sg.app_name),sg.group_name,ao.owner,sg.c_t from t_app_server_group sg inner join t_app_owner ao on sg.app_name = ao.app_name"
            cursor.execute(sql)
            environments = []
            for row in cursor.fetchall():
                # env = TaskEnvironment(row[0], json.loads(row[2]), row[1])
                env = TaskEnvironment(row[0], row[2], row[1])
                environments.append(env)
            return environments
        finally:
            cursor.close()
            self.conn.close()

    def save_task_param(self, param):
        try:
            cursor = self.conn.cursor()
            sql = "replace into task_param(md5_id,s_app,s_group,cmd,invoke_count," \
                  "cron_express,sleep_seconds,timeout_seconds,fetch_count,data_retry_count," \
                  "retry_after_seconds,execute_thread_count,execute_count,self_defined," \
                  "status,last_time) " \
                  "values" \
                  "('%s','%s','%s','%s'," \
                  "'%d','%s','%d','%d'," \
                  "'%d','%d','%d','%d','%d','%s','%s',now())"
            data = (param.id, param.app, param.group, param.cmd,
                    param.get_invoke_args()['invoke_count'],
                    param.get_invoke_args()['cron_express'],
                    param.get_invoke_args()['sleep_seconds'],
                    param.get_invoke_args()['timeout_seconds'],
                    param.get_service_args()['fetch_count'],
                    param.get_service_args()['data_retry_count'],
                    param.get_service_args()['retry_after_seconds'],
                    param.get_service_args()['execute_thread_count'],
                    param.get_service_args()['execute_count'],
                    param.get_service_args()['self_defined'],
                    param.status)
            cursor.execute(sql % data)
            self.conn.commit()
            print('成功插入', cursor.rowcount, '条数据')
        finally:
            cursor.close()
            self.conn.close()
        return self.db.save_task_param(param)

    def stop_task_param(self, param_id):
        return self.db.stop_task_param(param_id)

    def start_task_param(self, param_id):
        return self.db.start_task_param(param_id)
