import pymysql
import re;
from itertools import groupby

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
