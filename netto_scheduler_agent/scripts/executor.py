
import logging
import logging.config


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



