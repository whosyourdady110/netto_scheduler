import unittest

from netto_scheduler.netto_scheduler_agent.scripts.executor import HttpExecutor
from netto_scheduler.netto_scheduler_agent.scripts.task import TaskParam


class TestHttp(unittest.TestCase):
    def tearDown(self):
        super().tearDown()

    def setUp(self):
        super().setUp()

    def test_http(self):
        url = "http://localhost:8080/taskService"
        dic1 = {}
        param = TaskParam(url, "http", dic1)
        tasks = param.create_task_instances()
        for task in tasks:
            HttpExecutor(task).execute()
