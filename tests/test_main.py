import unittest
import sys
import os
import mock
import run_test
import tempfile
import shutil

class run_testTests(unittest.TestCase):
    @classmethod
    def setUp(letest):
        letest.workdir = tempfile.mkdtemp()
        run_test.PWD = letest.workdir

        letest.vm_args = {'memory': [22], 'disksize': ['100'],
                          'stop_timeout': [60], 'restart_timeout': [60],
                          'login_timeout': [60]}

    @classmethod
    def tearDown(letest):
        shutil.rmtree(letest.workdir)
    def test_parse_args(self):
        with mock.patch('sys.argv', ['run_test', '-d', '200', '-m', '30',
                        '-s', '100', '-r', '200', '-l', '300']):
            test_args = run_test.parse_arguments(sys.argv[1:])
            self.assertEquals(test_args['disksize'][0], '200')
            self.assertEquals(test_args['memory'][0], 30)
            self.assertEquals(test_args['stop_timeout'][0], 100)
            self.assertEquals(test_args['restart_timeout'][0], 200)
            self.assertEquals(test_args['login_timeout'][0], 300)

    def test_new_TestVM(self):
        newvm = run_test.TestVM(self.vm_args)
        self.assertEquals(newvm.memory, str(22*1024))
        self.assertEquals(newvm.disksize, '100')
