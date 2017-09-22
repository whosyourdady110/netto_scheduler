import os
import json
import tornado.web
import configparser
from netto_scheduler_agent.scripts.schedule_db import SchedulerDb
from netto_scheduler_agent.scripts.task import TaskParam
from netto_scheduler_agent.scripts.task import TaskEnvironment
from netto_configure_web.configure_db import SchedulerConfigureDb


class SchedulerHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        conf = configparser.ConfigParser()
        conf.read("web.ini")
        self.db = SchedulerConfigureDb(conf)

    def get(self):
        args = self.get_query_arguments("a")
        if len(args) > 0:
            action = self.get_argument("a")
            if action == 'tasks':
                env = self.get_argument('env')
                tasks_info = self.db.query_tasks_info(env)
                list1 = []
                for task_info in tasks_info:
                    list1.append(json.dumps(task_info))
                self.write(json.dumps(list1))
            elif action == 'task':
                param_id = self.get_argument('id')
                param = self.db.query_task_param(param_id)
                self.write(param.to_json_string())
            else:
                pass
        else:
            title = "netto configure web"
            environments = self.db.query_all_environments()
            # if len(environments) > 0:
            #     cur_env = environments[0]
            # else:
            #     cur_env = TaskEnvironment("netto", [])
            # self.render("scheduler.html", title=title, environments=environments, cur_env=cur_env)
            self.render("scheduler.html", title=title, environments=environments)

    def post(self):
        data = json.loads(self.request.body.decode())
        if data['a'] == 'ct':
            env = data["env"]
            if env != '' and type(env) != 'NoneType':
                temps = env.split('.')
                param = TaskParam(temps[0], "", {}, temps[1])
            else:
                param = TaskParam("", "", {}, "")
            self.write(param.to_json_string())
        elif data['a'] == 'sv':
            try:
                param = TaskParam.from_json_string(json.dumps(data['task']))
                self.db.save_task_param(param)
                self.write(json.dumps({'has_err': False}))
            except Exception as e:
                self.write(json.dumps({'has_err': True, 'message': e.__str__()}))
        elif data['a'] == 'stop':
            param_id = data["param_id"]
            self.db.stop_task_param(param_id)
            self.write(json.dumps({'has_err': False}))
        elif data['a'] == 'start':
            param_id = data["param_id"]
            self.db.start_task_param(param_id)
            self.write(json.dumps({'has_err': False}))
        elif data['a'] == 'allEnv':
            list = []
            environments = self.db.query_all_environments()
            for environment in  environments :
                list.append(environment.__dict__ )
            self.write(json.dumps(list))

