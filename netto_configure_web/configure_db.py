import pymysql
import json
from netto_scheduler_agent.scripts.schedule_db import SchedulerDb
from netto_scheduler_agent.scripts.task import TaskEnvironment


class ConfigureDb:
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
            sql = "select s_app,s_group,owners,last_time from system_env"
            cursor.execute(sql)
            environments = []
            for row in cursor.fetchall():
                env = TaskEnvironment(row[0], json.loads(row[2]), row[1])
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
