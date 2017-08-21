import datetime
import configparser
import logging
import logging.config
import copy
import apscheduler.events as events

from apscheduler.schedulers.background import BlockingScheduler
from netto_scheduler.netto_scheduler_agent.scripts.db import RedisDb
from netto_scheduler.netto_scheduler_agent.scripts.executor import HttpExecutor


class Scheduler:
    def __init__(self):
        conf = configparser.ConfigParser()
        conf.read("../agent.ini")
        ip = conf.get("redis", "ip")
        port = conf.getint("redis", "port")
        timeout = conf.getint("redis", "timeout")
        self.invoker_id = conf.get("invoker", "id")
        self.max_tasks = conf.getint("invoker", "max_tasks")
        self.live_seconds = conf.getint("invoker", "live_seconds")
        self.db = RedisDb(ip, port, timeout)
        logging.config.fileConfig("../logger.ini")
        self.logger = logging.getLogger("main")
        executors = {
            'default': {'type': 'processpool', 'max_workers': self.max_tasks + 1}
        }
        self.blockScheduler = BlockingScheduler()
        self.jobs = {}

    def task_invoke(self, task_instance, task_param):
        if task_param.cmd.startswith('http'):
            executor = HttpExecutor(self.db, task_instance, task_param)
            executor.execute()
        else:
            pass

    def break_heart(self):
        """
        invoker每隔一段时间就心跳一下，看看是否有新任务，是否有任务需要更新
        :param bs:
        :return:
        """
        # 先看看参数是否有变化的把调度重启或者关闭
        self.refresh_local_invoker()
        self.refresh_other_invokers()
        if len(self.jobs) >= self.max_tasks:
            return
        task_instance, task_param = self.db.query_one_run_task(self.invoker_id, lock=True)
        if task_instance is None:
            return
        if task_instance.id not in self.jobs.keys():
            self.logger.info("分配了新任务%s", task_instance.id)
            job = self.blockScheduler.add_job(self.task_invoke,
                                              next_run_time=(datetime.datetime.now() + datetime.timedelta(seconds=2)),
                                              args=[task_instance, task_param], id=task_instance.id)
            self.jobs[job.id] = job
            self.db.lock_invoker_instance(self.invoker_id, task_instance.id, self.live_seconds)
        else:
            self.logger.error("%s任务已经在运行", task_instance.id)

    def refresh_local_invoker(self):
        """
        调度的参数是否发生变化，如有需要重启调度
        :param bs:
        :return:
        """

        self.db.update_invoker_time(self.invoker_id, self.jobs.keys(), self.live_seconds)
        self.logger.info("%s心跳更新成功！", self.invoker_id)
        # 看看是否有需要停止的任务再自己这里，释放掉
        stop_tasks = self.db.query_need_stop_tasks(self.invoker_id)
        for stop_task in stop_tasks:
            if stop_task in self.jobs.keys():
                try:
                    job = self.jobs[stop_task]
                    job.pause()
                    job.remove()
                except Exception as e:
                    self.logger.error(e)
                    self.jobs.pop(stop_task)
                    try:
                        self.blockScheduler.remove_job(stop_task)
                    except Exception as e1:
                        self.logger.error(e1)

            self.logger.info("人工停止了任务%s", stop_task)
            self.db.unlock_invoker_instance(self.invoker_id, stop_task, self.live_seconds)

        # 是否有参数变化的任务需要重启
        c_jobs = copy.copy(self.jobs)
        for key in c_jobs.keys():
            if key not in self.jobs.keys():
                break
            job = self.jobs[key]
            task_instance = job.args[0]
            old_task_param = job.args[1]
            # 判断参数是否发生变化，如果有变化重新执行任务
            new_task_param = self.db.query_task_param(task_instance.task_param_id)
            # if new_task_param
            if not new_task_param.has_diff(old_task_param):
                break;

            try:
                job.pause()
                job.remove()
            except Exception as e:
                self.logger.error(e)
                self.jobs.pop(key)
                try:
                    self.blockScheduler.remove_job(key)
                except Exception as e1:
                    self.logger.error(e1)
            self.logger.info("参数变化停止了任务%s", task_instance.id)
            self.db.unlock_invoker_instance(self.invoker_id, task_instance.id, self.live_seconds)
            self.db.add_task_waiting_run(task_instance.id)

    def refresh_other_invokers(self):
        """
        遍历所有的invoker，判断invoker是否超过存活期
        :return:
        """
        invokers = self.db.query_all_invokers()
        for invoker_id in invokers.keys():
            if not self.db.invoker_is_live(self.invoker_id):
                task_instance_list = self.db.query_invoker_tasks(self.invoker_id)
                for task_instance_id in task_instance_list:
                    self.db.add_task_waiting_run(task_instance_id)

    def main(self):
        try:
            self.db.register_invoker(self.invoker_id, self.max_tasks, self.live_seconds);
            self.blockScheduler.add_listener(self._job_listener,
                                             events.EVENT_JOB_ERROR | events.EVENT_JOB_MISSED)

            self.blockScheduler.add_job(self.break_heart, "interval", seconds=self.live_seconds / 2,
                                        id="break_heart")
            self.logger.info("开始启动调度...")
            self.blockScheduler.start()
            self.logger.info("启动调度成功！")
        except KeyboardInterrupt as e:
            self.logger.info(e)
            self.blockScheduler.shutdown()

    def _job_listener(self, ev):
        """
        监听job的事件，job完成后再发起下次调用，对于异常也要处理
        :param ev:
        :return:
        """
        if ev.code == events.EVENT_JOB_ERROR:
            self.logger.error(ev.exception)
            self.logger.error(ev.traceback)
        else:
            pass


if __name__ == '__main__':
    Scheduler().main()
