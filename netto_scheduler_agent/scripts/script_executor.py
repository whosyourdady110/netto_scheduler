from apscheduler.schedulers.background import BlockingScheduler
from netto_scheduler.netto_scheduler_agent.scripts.executor import TaskExecutor


class ScriptExecutor(TaskExecutor):
    """
    脚本执行器
    """

    def __init__(self, task_instance):
        super().__init__(task_instance)

    def execute(self, task_instance):
        pass
