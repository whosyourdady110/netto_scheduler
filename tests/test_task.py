import unittest

from netto_scheduler_agent.scripts.task import TaskParam
from netto_scheduler_agent.scripts.task import TaskInstance


class TestTask(unittest.TestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_create_task_param(self):
        cmd = "http://localhost:8081/taskService"
        group = "test"
        dic1 = {'invokeArgs': {'taskNames': ['test1', 'test2', 'test3']}}
        param = TaskParam(group, cmd, dic1)
        print(param.get_invoke_args())
        tasks = param.create_task_instances()
        self.assertEqual(len(tasks), 3, 'task count not equal 3')

    def test_create_task_instance(self):
        cmd = "http://localhost:8081/taskService"
        group = "test"
        param = TaskParam(group, cmd, {})
        print(param.get_invoke_args())
        print(param.get_service_args())
        ti = TaskInstance("test", param)
        print(ti)

    def test_json_task_param(self):
        cmd = "http://localhost:8081/taskService"
        group = "test"
        dic1 = {'invokeArgs': {'taskNames': ['test1', 'test2', 'test3']}}
        param = TaskParam(group, cmd, dic1)
        print(param.to_json_string())

    def test_object_task_param(self):
        cmd = "http://localhost:8081/taskService"
        group = "test"
        dic1 = {'invokeArgs': {'taskNames': ['test1', 'test2', 'test3']}}
        param = TaskParam(group, cmd, dic1)
        param1 = TaskParam.from_json_string(param.to_json_string())
        print(param.to_json_string())
        print(param1.to_json_string())

    def test_json_task_instance(self):
        cmd = "http://localhost:8081/taskService"
        group = "test"
        dic1 = {'invokeArgs': {'taskNames': ['test1', 'test2', 'test3']}}
        param = TaskParam(group, cmd, dic1)
        print(param.create_task_instances()[0].to_json_string())

    def test_object_task_instance(self):
        cmd = "http://localhost:8081/taskService"
        group = "test"
        dic1 = {'invokeArgs': {'taskNames': ['test1', 'test2', 'test3']}}
        param = TaskParam(group, cmd, dic1)
        task_instance = param.create_task_instances()[0]
        task_instance2 = TaskInstance.from_json_string(task_instance.to_json_string())

        print(task_instance.to_json_string())
        print(task_instance2.to_json_string())
