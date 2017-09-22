import redis
import json
import time
from netto_scheduler_agent.scripts.task import TaskInstance
from netto_scheduler_agent.scripts.task import TaskParam
from netto_scheduler_agent.scripts.task import TaskEnvironment

###reids tables
TASK_INVOKERS = "task_invokers"
TASK_PARAMS = "task_params"
WAITING_RUN_TASKS = "waiting_run_tasks"
WAITING_STOP_TASKS = "waiting_stop_tasks"
TASK_INSTANCES = "task_instances"

### redis indexes
ENV_PARAM_INDEX = "env_param_index:"
PARAM_INSTANCE_INDEX = "param_instance_index:"
INVOKER_INSTANCE_INDEX = "invoker_instance_index:"
INVOKER_LOGS_INDEX = "invoker_logs:"


class SchedulerDb:
    """
    redis db create delete update query
    """

    def __init__(self, host, port, timeout):
        self.pool = redis.ConnectionPool(host=host, port=port, socket_timeout=timeout)

    def register_invoker(self, invoker_id, max_tasks, live_seconds):
        r = redis.Redis(connection_pool=self.pool)
        invoker_exist = r.exists(INVOKER_INSTANCE_INDEX + invoker_id)
        if invoker_exist:
            raise Exception("error:invoker %s exist" % invoker_id)
        pipe = r.pipeline(transaction=True)
        invoker_dic = {'create_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                       'max_tasks': max_tasks}
        pipe.hset(TASK_INVOKERS, invoker_id, json.dumps(invoker_dic))
        pipe.sadd(INVOKER_INSTANCE_INDEX + invoker_id, "")
        pipe.expire(INVOKER_INSTANCE_INDEX + invoker_id, live_seconds)
        pipe.execute()

    def update_invoker_time(self, invoker_id, task_instance_ids, live_seconds):
        """
        心跳更新時間
        :param invoker_id:
        :param task_instance_ids:
        :param live_seconds:
        :return:
        """
        r = redis.Redis(connection_pool=self.pool)
        for task_instance_id in task_instance_ids:
            r.sadd(INVOKER_INSTANCE_INDEX + invoker_id, task_instance_id)
        r.expire(INVOKER_INSTANCE_INDEX + invoker_id, live_seconds)

    def query_invoker_tasks(self, invoker_id):

        r = redis.Redis(connection_pool=self.pool)
        list1 = r.smembers(INVOKER_INSTANCE_INDEX + invoker_id)
        tasks = []
        for instance_id in list1:
            tasks.append(instance_id.decode())
        return tasks

    def invoker_is_live(self, invoker_id):
        """
        判断调用者是否活着
        :param invoker_id:
        :return:
        """
        r = redis.Redis(connection_pool=self.pool)
        flag = r.exists(INVOKER_INSTANCE_INDEX + invoker_id)
        if not flag:
            r.hdel(TASK_INVOKERS, invoker_id)
        return flag

    def add_task_waiting_stop(self, task_instance_id, invoker_id):
        r = redis.Redis(connection_pool=self.pool)
        r.hset(WAITING_STOP_TASKS, task_instance_id, invoker_id)

    def query_need_stop_tasks(self, invoker_id):
        r = redis.Redis(connection_pool=self.pool)
        need_stop_tasks = r.hgetall(WAITING_STOP_TASKS)
        stop_instances = []
        for task in need_stop_tasks.keys():
            if need_stop_tasks[task].decode() == invoker_id:
                stop_instances.append(task)

        running_instances = r.smembers(INVOKER_INSTANCE_INDEX + invoker_id)
        temps = list(set(stop_instances).intersection(set(running_instances)))
        stop_tasks = []
        for temp in temps:
            stop_tasks.append(temp.decode())
        return stop_tasks

    def add_task_waiting_run(self, task_instance_id):
        """
        把任务放入待调度队列，同时清空调用者信息
        :param task_instance_id:
        :return:
        """
        r = redis.Redis(connection_pool=self.pool)
        task_instance = TaskInstance.from_json_string(r.hget(TASK_INSTANCES, task_instance_id).decode())
        pipe = r.pipeline()
        task_instance.set_invoker_id("")
        pipe.hset(TASK_INSTANCES, task_instance_id, task_instance.to_json_string())
        pipe.sadd(WAITING_RUN_TASKS, task_instance_id)
        pipe.execute()

    def lock_invoker_instance(self, invoker_id, task_instance_id, live_seconds=0):
        '''
        对于调用器和task确定关系的要在db中lock
        :param invoker_id:
        :param task_instance_id:
        :param live_seconds:
        :return:
        '''
        r = redis.Redis(connection_pool=self.pool)
        task_instance = TaskInstance.from_json_string(r.hget(TASK_INSTANCES, task_instance_id).decode())
        task_instance.set_invoker_id(invoker_id)
        pipe = r.pipeline()
        pipe.hset(TASK_INSTANCES, task_instance_id, task_instance.to_json_string())
        pipe.sadd(INVOKER_INSTANCE_INDEX + invoker_id, task_instance_id)
        pipe.srem(WAITING_RUN_TASKS, task_instance_id)
        if live_seconds > 0:
            pipe.expire(INVOKER_INSTANCE_INDEX + invoker_id, live_seconds)

        pipe.execute()

    def unlock_invoker_instance(self, invoker_id, task_instance_id, live_seconds):
        '''
        对于调用器和task确定关系的要在db中unlock
        :param invoker_id:
        :param instance_id:
        :return:
        '''
        r = redis.Redis(connection_pool=self.pool)
        if not r.hexists(TASK_INSTANCES, task_instance_id):
            return

        task_instance = TaskInstance.from_json_string(r.hget(TASK_INSTANCES, task_instance_id).decode())
        task_instance.set_invoker_id("")
        pipe = r.pipeline()
        pipe.hset(TASK_INSTANCES, task_instance_id, task_instance.to_json_string())
        pipe.srem(INVOKER_INSTANCE_INDEX + invoker_id, task_instance_id)
        pipe.expire(INVOKER_INSTANCE_INDEX + invoker_id, live_seconds)
        pipe.hdel(WAITING_STOP_TASKS, task_instance_id)
        pipe.execute()

    def query_waiting_run_tasks(self, invoker_id, count=1, lock=True):
        """
        領取任務
        :return: task_instance
        """
        r = redis.Redis(connection_pool=self.pool)
        task_instance_ids = r.srandmember(WAITING_RUN_TASKS, count)
        if len(task_instance_ids) == 0:
            return self._get_task_instances(invoker_id, count, lock)

        task_instances = []
        task_params = []
        for b_str in task_instance_ids:
            task_instance_id = b_str.decode()
            if not r.hexists(TASK_INSTANCES, task_instance_id):
                continue
            task_instance = TaskInstance.from_json_string(r.hget(TASK_INSTANCES, task_instance_id).decode())
            if lock:
                self.lock_invoker_instance(invoker_id, task_instance_id)
            task_param = self.query_task_param(task_instance.task_param_id)
            task_instances.append(task_instance)
            task_params.append(task_param)
        return task_instances, task_params

    def _get_task_instances(self, invoker_id, count, lock):
        # 没有调用者调用的任务，加入到待处理队列中
        r = redis.Redis(connection_pool=self.pool)
        dic1 = r.hgetall(TASK_INSTANCES)
        task_instances = []
        task_params = []
        i = 0
        for b_key in dic1.keys():
            if i >= count:
                return task_instances, task_params
            instance_id = b_key.decode()
            status, task_instance = self.get_task_instance_status(instance_id)
            if not status:
                task_param = self.query_task_param(task_instance.task_param_id)
                if task_param.status == 'on':
                    task_instances.append(task_instance)
                    task_params.append(task_param)
                    if lock:
                        self.lock_invoker_instance(invoker_id, instance_id)

        return task_instances, task_params

    def get_task_instance_status(self, task_instance_id):
        '''
        得到task运行状态
        :param task_instance_id:
        :return: true运行 false停止
        '''
        r = redis.Redis(connection_pool=self.pool)
        if not r.hexists(TASK_INSTANCES, task_instance_id):
            return False, None
        task_instance = TaskInstance.from_json_string(r.hget(TASK_INSTANCES, task_instance_id).decode())
        if task_instance.invoker_id == "":
            return False, task_instance
        else:
            # 如果调度器已经不存在，要重新处理
            # 如果调度器存在，看看他的列表中是否有该任务，没有也要执行
            if not r.exists(INVOKER_INSTANCE_INDEX + task_instance.invoker_id):
                return False, task_instance
            else:
                instance_list = r.smembers(INVOKER_INSTANCE_INDEX + task_instance.invoker_id)
                if not task_instance.id.encode() in instance_list:
                    return False, task_instance
        return True, task_instance

    def query_all_invokers(self):
        r = redis.Redis(connection_pool=self.pool)
        dic1 = r.hgetall(TASK_INVOKERS)
        dic2 = {}
        for b_key in dic1.keys():
            dic2[b_key.decode()] = dic1[b_key].decode()
        return dic2

    def query_tasks_info(self, env):
        '''
        task的调用情况信息
        :param env:
        :return:
        '''
        r = redis.Redis(connection_pool=self.pool)
        list1 = r.smembers(ENV_PARAM_INDEX + env)
        tasks_info = []
        for b_str in list1:
            param_id = b_str.decode()
            param_json_string = r.hget(TASK_PARAMS, param_id).decode()
            param = TaskParam.from_json_string(param_json_string)
            instances = r.smembers(PARAM_INSTANCE_INDEX + param_id)
            success_count = 0
            fail_count = 0
            run_count = 0
            stop_count = 0
            for instance_id in instances:
                # 先处理日志信息
                dic1 = r.hgetall(INVOKER_LOGS_INDEX + instance_id.decode())
                for service_num in dic1.keys():
                    log = json.loads(dic1[service_num].decode())
                    success_count += log['success_count']
                    fail_count += log['fail_count']
                # 处理task状态
                status, task_instance = self.get_task_instance_status(instance_id)
                if task_instance is not None:
                    if status:
                        run_count += 1
                    else:
                        stop_count += 1

            if param.get_invoke_args()['cron_express'] != '':
                invoke_type = param.get_invoke_args()['cron_express']
            else:
                invoke_type = "间隔" + str(param.get_invoke_args()['sleep_seconds']) + "秒"
            task_info = {"id": param.id, 'cmd': param.cmd, "env": param.env,
                         "task_args": param.get_service_args()['self_defined'], 'invoke_type': invoke_type,
                         'task_count': len(instances), 'run_count': run_count,
                         'stop_count': stop_count,'status': param.status,
                         'success_count': success_count, 'fail_count': fail_count}
            tasks_info.append(task_info)

        return tasks_info

    def query_task_instance(self, task_instance_id):
        r = redis.Redis(connection_pool=self.pool)
        str1 = r.hget(TASK_INSTANCES, task_instance_id)
        if str1 is None:
            return None
        return TaskInstance.from_json_string(str1.decode())

    def query_task_param(self, task_param_id):
        r = redis.Redis(connection_pool=self.pool)
        if not r.hexists(TASK_PARAMS, task_param_id):
            return None
        param_json_string = r.hget(TASK_PARAMS, task_param_id).decode()
        return TaskParam.from_json_string(param_json_string)

    def stop_task_param(self, task_param_id):
        # 被调用者调用的任务，加入到待停止队列中
        r = redis.Redis(connection_pool=self.pool)
        # 取出待运行队列里有和task的instance，先处理掉
        need_run_instances = r.smembers(WAITING_RUN_TASKS)
        task_instance_ids = r.smembers(PARAM_INSTANCE_INDEX + task_param_id)
        temps = list(need_run_instances.intersection(task_instance_ids))
        task_param = self.query_task_param(task_param_id)

        pipe = r.pipeline()
        for temp in temps:
            pipe.srem(WAITING_RUN_TASKS, temp)
        for task_instance_id in task_instance_ids:
            status, task_instance = self.get_task_instance_status(task_instance_id)
            if status:
                pipe.hset(WAITING_STOP_TASKS,
                          task_instance.id, task_instance.invoker_id)

        task_param.status = "off"
        pipe.hset(TASK_PARAMS, task_param_id, task_param.to_json_string())
        pipe.execute()

    def start_task_param(self, task_param_id):
        # 没有调用者调用的任务，加入到待处理队列中
        r = redis.Redis(connection_pool=self.pool)

        # 取出待停止队列里有和task的instance，先处理掉
        need_stop_tasks = r.hgetall(WAITING_STOP_TASKS)
        stop_instances = []
        for task in need_stop_tasks.keys():
            stop_instances.append(task)

        task_instance_ids = r.smembers(PARAM_INSTANCE_INDEX + task_param_id)
        temps = list(set(stop_instances).intersection(task_instance_ids))
        task_param = self.query_task_param(task_param_id)
        pipe = r.pipeline()
        for temp in temps:
            pipe.hdel(WAITING_STOP_TASKS, temp)
        for task_instance_id in task_instance_ids:
            status, task_instance = self.get_task_instance_status(task_instance_id)
            if not status:
                pipe.sadd(WAITING_RUN_TASKS, task_instance.id)

        task_param.status = "on"
        pipe.hset(TASK_PARAMS, task_param_id, task_param.to_json_string())
        pipe.execute()

    def save_task_param(self, task_param):
        if not task_param.has_diff(self.query_task_param(task_param.id)):
            return

        task_instances = task_param.create_task_instances()
        r = redis.Redis(connection_pool=self.pool)
        instance_ids = r.smembers(PARAM_INSTANCE_INDEX + task_param.id)

        # 看看是否有需要停止的任务
        for b_str in instance_ids:
            instance_id = b_str.decode()
            if not r.hexists(TASK_INSTANCES, instance_id):
                continue
            status, task_instance = self.get_task_instance_status(instance_id)
            if status:
                self.add_task_waiting_stop(instance_id, task_instance.invoker_id)

            r.hdel(TASK_INSTANCES, instance_id)

        pipe = r.pipeline()
        pipe.sadd(ENV_PARAM_INDEX + task_param.env, task_param.id)
        pipe.hset(TASK_PARAMS, task_param.id, task_param.to_json_string())
        pipe.delete(PARAM_INSTANCE_INDEX + task_param.id)

        for task_instance in task_instances:
            pipe.sadd(PARAM_INSTANCE_INDEX + task_param.id, task_instance.id)
            pipe.hsetnx(TASK_INSTANCES, task_instance.id, task_instance.to_json_string())
            if task_param.status == 'on':
                pipe.sadd(WAITING_RUN_TASKS, task_instance.id)

        pipe.execute()

    def save_task_logs(self, invoke_logs):
        if invoke_logs is None:
            return
        if len(invoke_logs.keys()) == 0:
            return
        r = redis.Redis(connection_pool=self.pool)
        for instance_id in invoke_logs.keys():
            for invoker_num in invoke_logs[instance_id].keys():
                r.hset(INVOKER_LOGS_INDEX + instance_id, invoker_num,
                       json.dumps(invoke_logs[instance_id][invoker_num]))
            r.expire(INVOKER_LOGS_INDEX + instance_id, 1 * 60 * 60)
