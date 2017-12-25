import unittest
import configparser
from netto_configure_web.configure_db import ConfigureDb



class TestDB(unittest.TestCase):
    def test_DB(self):
        self.configurationDb = ConfigureDb('192.168.2.39', '3306', 'super', '0178a34e0a60', 'netto')
        ret = self.configurationDb.app_group_by_user('admin@meicai.cn')
        print(ret)
