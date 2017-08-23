import logging
import logging.config
import datetime
import apscheduler.events as events
from apscheduler.schedulers.background import BlockingScheduler


class TaskExecutor:
    def __init__(self, db, task_instance, task_param):
        self.task_instance = task_instance
        self.task_param = task_param
        self.db = db
        # invoke log
        self.invoke_log_map = {}
        self.jobs = {}
        logging.config.fileConfig("../logger.ini")
        self.logger = logging.getLogger("taskExecutor")
        invoke_count = int(self.task_param.get_invoke_args()['invoke_count'])
        executors = {
            'default': {'type': 'threadpool', 'max_workers': invoke_count + 1}
        }
        self.scheduler = BlockingScheduler(executors=executors)

    def execute(self):
        self.scheduler.add_listener(self._job_listener,
                                    events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR | events.EVENT_JOB_ADDED | events.EVENT_JOB_MISSED)

        # invoke_log_map up server
        self.scheduler.add_job(self._invoke_break_heart, "interval", seconds=2)
        try:
            self.scheduler.start()
        except Exception as e:
            print(e)
            self.scheduler.shutdown(wait=True)

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

    def _invoke_break_heart(self):
        if self.task_instance.status == 'off':
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                try:
                    job.pause()
                    job.remove()
                except Exception as e:
                    self.logger.error(e)
        self.db.save_task_logs(self.invoke_log_map)
