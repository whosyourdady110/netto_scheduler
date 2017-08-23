import time
import datetime
from netto_scheduler_agent.scripts.executor import TaskExecutor


class ScriptExecutor(TaskExecutor):
    """
    脚本执行器
    """

    def __init__(self, task_instance):
        super().__init__(task_instance)

    def execute(self, task_instance):
        invoke_args = self.task_param.get_invoke_args()
        invoke_count = int(invoke_args['invoke_count'])
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
        super().execute()

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

            self.logger.info("调用:%s成功!", self.task_param.cmd)
            invoke_log['success_count'] += 1
        except Exception as e:
            self.logger.error(e)
            invoke_log['fail_count'] += 1
            sleep_seconds = 9 * int(self.task_param.get_invoke_args()['sleep_seconds'])
            if sleep_seconds > 30:
                sleep_seconds = 30
            time.sleep(sleep_seconds)
