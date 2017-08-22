import urllib3
import time, datetime
import copy

from apscheduler.schedulers.background import BlockingScheduler
import apscheduler.events as events
import logging
import logging.config
import json


class TaskExecutor:
    def __init__(self, task_instance, task_param):
        self.task_instance = task_instance
        self.task_param = task_param
        # invoke log
        self.invoke_log_map = {}
        self.jobs = {}
        logging.config.fileConfig("../logger.ini")
        self.logger = logging.getLogger("taskExecutor")

    def execute(self):
        pass

    def _invoke_break_heart(self):
        self.db.save_task_logs(self.invoke_log_map)


class HttpExecutor(TaskExecutor):
    def __init__(self, db, task_instance, task_param):
        super().__init__(task_instance, task_param)
        self.http = urllib3.PoolManager(retries=False)
        self.db = db
        invoke_count = int(self.task_param.get_invoke_args()['invoke_count'])
        executors = {
            'default': {'type': 'threadpool', 'max_workers': invoke_count + 1}
        }
        self.scheduler = BlockingScheduler(executors=executors)

    def execute(self):
        invoke_args = self.task_param.get_invoke_args()
        invoke_count = int(invoke_args['invoke_count'])
        service_args = self.task_param.get_service_args()
        self.scheduler.add_listener(self._job_listener,
                                    events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR | events.EVENT_JOB_ADDED | events.EVENT_JOB_MISSED)
        for invoker_number in range(invoke_count):
            if invoke_args['cron_express'] != "":
                # minute hour day month dayofweek
                tmp = invoke_args['cron_express'].split()
                self.scheduler.add_job(self._invoke_service, 'cron', minute=tmp[0], hour=tmp[1], day=tmp[2],
                                       month=tmp[3],
                                       dayofweek=tmp[4],
                                       args=[invoker_number])
            else:
                invoke_key = "$" + self.task_instance.id + ":" + str(invoker_number)
                self.scheduler.add_job(self._invoke_service,
                                       next_run_time=(datetime.datetime.now() + datetime.timedelta(seconds=2)),
                                       id=invoke_key,
                                       args=[invoker_number])
        # invoke_log_map up server
        self.scheduler.add_job(self._invoke_break_heart, "interval", seconds=2)
        try:
            self.scheduler.start()
        except Exception as e:
            print(e)
            self.scheduler.shutdown(wait=True)

    def _invoke_break_heart(self):
        if self.task_instance.status == 'off':
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                try:
                    job.pause()
                    job.remove()
                except Exception as e:
                    self.logger.error(e)
        super()._invoke_break_heart()

    def _job_listener(self, ev):
        """
        监听job的事件，job完成后再发起下次调用，对于异常也要处理
        :param ev:
        :return:
        """
        if self.task_instance.status == 'off':
            return
        if ev.code == events.EVENT_JOB_ADDED:
            self.jobs[ev.job_id] = self.scheduler.get_job(ev.job_id)
        elif ev.code == events.EVENT_JOB_EXECUTED or ev.code == events.EVENT_JOB_ERROR:
            if ev.code == events.EVENT_JOB_ERROR:
                self.logger.error(ev.exception)
                self.logger.error(ev.traceback)
            job = self.jobs[ev.job_id]
            self.scheduler.add_job(job.func,
                                   next_run_time=(
                                       datetime.datetime.now() + datetime.timedelta(seconds=1)),
                                   id=ev.job_id, args=job.args)
        else:
            pass

    def _invoke_service(self, invoker_number):
        if self.task_instance.id not in self.invoke_log_map.keys():
            self.invoke_log_map[self.task_instance.id] = {}
        log_key = 's:' + str(invoker_number)
        if log_key not in self.invoke_log_map[self.task_instance.id].keys():
            self.invoke_log_map[self.task_instance.id][log_key] = {'call_count': 0, 'success_count': 0,
                                                                   'fail_count': 0}

        invoke_log = self.invoke_log_map[self.task_instance.id][log_key]
        try:
            invoke_log['call_count'] += 1
            self.logger.info("开始调用:%s", self.task_param.cmd)
            timeout = int(self.task_param.get_invoke_args()['timeout_seconds'])
            pos = self.task_param.cmd.rfind('/')
            if pos > 0:
                l_pos = pos + 1
                r_pos = len(self.task_param.cmd)
                service_name = self.task_param.cmd[l_pos:r_pos]
            else:
                service_name = ""
            req = {'serviceName': service_name, 'methodName': 'execute',
                   'args': [{'invokerCount': self.task_param.get_invoke_args()['invoke_count'],
                             'selfDefined': self.task_instance.task_name,
                             'fetchCount': self.task_param.get_service_args()['fetch_count'],
                             'executeCount': self.task_param.get_service_args()[
                                 'execute_count'],
                             'executeThreadCount': self.task_param.get_service_args()[
                                 'execute_thread_count'],
                             'dataRetryCount': self.task_param.get_service_args()[
                                 'data_retry_count'],
                             'retryTimeInterval': self.task_param.get_service_args()[
                                 'retry_after_seconds']},
                            invoker_number]}

            if timeout > 0:
                response = self.http.request(method="POST", url=self.task_param.cmd,
                                             headers={'Content-Type': 'application/json'},
                                             body=json.dumps(req),
                                             timeout=urllib3.Timeout(connect=timeout,
                                                                     read=timeout))
            else:
                response = self.http.request(method="POST", url=self.task_param.cmd,
                                             headers={'Content-Type': 'application/json'},
                                             body=json.dumps(req))
            if response.status != 200:
                self.logger.info("调用:%s失败!", self.task_param.cmd)
                invoke_log['fail_count'] += 1
                sleep_seconds = 9 * int(self.task_param.get_invoke_args()['sleep_seconds'])
                if sleep_seconds > 30:
                    sleep_seconds = 30
                time.sleep(sleep_seconds)
            else:
                self.logger.info("调用:%s成功!", self.task_param.cmd)
                invoke_log['success_count'] += 1
        except Exception as e:
            self.logger.error(e)
            invoke_log['fail_count'] += 1
            sleep_seconds = 9 * int(self.task_param.get_invoke_args()['sleep_seconds'])
            if sleep_seconds > 30:
                sleep_seconds = 30
            time.sleep(sleep_seconds)

    class ScriptExecutor(TaskExecutor):
        """
        脚本执行器
        """

        def __init__(self, task_instance):
            super().__init__(task_instance)

        def execute(self, task_instance):
            pass
