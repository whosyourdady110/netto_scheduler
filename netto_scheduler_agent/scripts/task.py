import re
import hashlib
import json


class TaskEnvironment:
    def __init__(self, app, owners, group="*", ):
        self.app = app
        self.group = group
        self.env = app + "." + group
        self.owners = owners


class TaskParam:
    def __init__(self, app, cmd, params, group="*"):
        self.env = app + "." + group
        self.cmd = cmd
        self.app = app
        self.group = group
        self.params = params
        self.status = "on"  # on run off stop
        md5 = hashlib.md5()
        md5_str = ''.join(cmd.split())
        md5_str += ''.join(app.split())
        md5_str += ''.join(group.split())
        md5.update(md5_str.encode('ascii'))
        self.id = md5.hexdigest()

    def get_invoke_args(self):
        if 'invoke_args' not in self.params.keys():
            self.params['invoke_args'] = {}

        if 'invoke_count' not in self.params['invoke_args'].keys():
            self.params['invoke_args']['invoke_count'] = 4

        if 'cron_express' not in self.params['invoke_args'].keys():
            self.params['invoke_args']['cron_express'] = ''

        if 'sleep_seconds' not in self.params['invoke_args'].keys():
            self.params['invoke_args']['sleep_seconds'] = 2  # 秒

        if 'timeout_seconds' not in self.params['invoke_args'].keys():
            self.params['invoke_args']['timeout_seconds'] = 50  # 秒

        return self.params['invoke_args']

    def get_service_args(self):
        if 'service_args' not in self.params.keys():
            self.params['service_args'] = {}

        if 'fetch_count' not in self.params['service_args'].keys():
            self.params['service_args']['fetch_count'] = 100  # 秒

        if 'data_retry_count' not in self.params['service_args'].keys():
            self.params['service_args']['data_retry_count'] = 10

        if 'retry_after_seconds' not in self.params['service_args'].keys():
            self.params['service_args']['retry_after_seconds'] = 30  # 秒

        if 'execute_thread_count' not in self.params['service_args'].keys():
            self.params['service_args']['execute_thread_count'] = 10  # 个

        if 'execute_count' not in self.params['service_args'].keys():
            self.params['service_args']['execute_count'] = 10  # 个

        if 'self_defined' not in self.params['service_args'].keys():
            self.params['service_args']['self_defined'] = ''
        return self.params['service_args']

    def create_task_instances(self):
        instances = []
        temps = self.params['service_args']['self_defined'].split(',')
        for temp in temps:
            task_obj = TaskInstance(temp, self.id)
            instances.append(task_obj)
        return instances

    def to_json_string(self):
        self.get_invoke_args()
        self.get_service_args()
        return json.dumps(self.__dict__)

    def has_diff(self, task_param):
        if task_param is None:
            return True
        if self.cmd != task_param.cmd:
            return True
        if self.env != task_param.env:
            return True
        invoke_param1 = self.get_invoke_args()
        invoke_param2 = task_param.get_invoke_args()
        if invoke_param1['invoke_count'] != invoke_param1['invoke_count']:
            return True
        if invoke_param1['cron_express'] != invoke_param1['cron_express']:
            return True
        if invoke_param1['sleep_seconds'] != invoke_param1['sleep_seconds']:
            return True
        if invoke_param1['timeout_seconds'] != invoke_param1['timeout_seconds']:
            return True
        service_param1 = self.get_service_args()
        service_param2 = task_param.get_service_args()
        if service_param1['fetch_count'] != service_param2['fetch_count']:
            return True
        if service_param1['data_retry_count'] != service_param2['data_retry_count']:
            return True
        if service_param1['retry_after_seconds'] != service_param2['retry_after_seconds']:
            return True
        if service_param1['execute_thread_count'] != service_param2['execute_thread_count']:
            return True
        if service_param1['execute_count'] != service_param2['execute_count']:
            return True
        if service_param1['self_defined'] != service_param2['self_defined']:
            return True
        return False

    @staticmethod
    def from_json_string(json_string):
        param_dic = json.loads(json_string)
        param_obj = TaskParam(param_dic['app'], param_dic['cmd'], param_dic, param_dic['group'])
        param_obj.__dict__ = param_dic
        if 'status' not in param_dic.keys():
            param_obj.status = "on"
        return param_obj


class TaskInstance:
    def __init__(self, task_name, task_param_id):
        self.task_name = task_name
        self.task_param_id = task_param_id
        md5 = hashlib.md5()
        md5_str = ''.join(task_param_id.split())
        md5_str += ''.join(task_name.split())
        md5.update(md5_str.encode("ascii"))
        self.id = md5.hexdigest()
        self.invoker_id = ''

    def set_invoker_id(self, invoker_id):
        self.invoker_id = invoker_id

    def to_json_string(self):
        return json.dumps(self.__dict__)

    @staticmethod
    def from_json_string(json_string):
        instance_dic = json.loads(json_string)
        task_name = instance_dic['task_name']
        task_param_id = instance_dic['task_param_id']
        instance_obj = TaskInstance(task_name, task_param_id)
        instance_obj.__dict__ = instance_dic
        return instance_obj
