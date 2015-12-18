#!/usr/bin/python3
import os
import sys
import subprocess
import time

_restart_msg = b' * Will now restart\r\n'
_restart_timeout = 60
_login_prompt = b'crashkernel-test login: '
_login_timeout = 60


class TestVM(object):

    def __init__(self):
        self.hostname = 'crashkernel-test'
        self.console_file = '/var/log/libvirt/qemu/crashkernel-test.log'
        self.memory = '22528'
        self.disksize = '100'
        self.console = None

    def Start(self):
        try:
            os.unlink(self.console_file)
            print("Starting %s VM" % self.hostname)
            subprocess.check_output(
                ["uvt-kvm", "create", self.hostname, "--memory", self.memory,
                 "--disk", self.disksize,  "--cpu", "2", "--user-data",
                 "crashkernel.cloud", "--log-console-output"],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to create %s VM" % self.hostname)

    def Destroy(self):
        try:
            print("Terminating %s VM" % self.hostname)
            subprocess.check_output(
                ["uvt-kvm", "destroy", self.hostname],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to destroy %s VM" % self.hostname)

    def Open_console(self):
        try:
            self.console = open(self.console_file, 'br')

        except FileNotFoundError:
            print("Cannot find %s" % self.console)
            pass

    def Close_console(self):
        self.console.close()

    def Read_console(self):
        return self.console.readlines()

# class CrashTest(object):
#     """crashkernel test to be executed"""
#     def __init__(self):
#IsRebooted="LTS $Hostname ttyS0"
#IsShutdown="reboot: Power down"
#HasCrashed="SysRq : Trigger a crash"


def Wait_restart(vm):

    print("Waiting for restart to appear")
    loop = 0
    output = vm.Read_console()
    while _restart_msg not in output and loop <= _restart_timeout:
        time.sleep(5)
        output = vm.Read_console()
        loop += 5
    if loop > _restart_timeout:
        raise TimeoutError("Timed out waiting for restart")

    print("Got restart")


def Wait_login_prompt(vm):
    print("Waiting for boot prompt to appear")
    loop = 0
    output = vm.Read_console()
    while _login_prompt not in output and loop <= _login_timeout:
        time.sleep(5)
        output = vm.Read_console()
        loop += 5
    if loop > _login_timeout:
        raise TimeoutError("Timed out waiting for login prompt")

    print("Got login prompt")
    return


def main():
    if os.getuid() != 0:
        print("This script must be run as root !")
        exit(1)

    test_vm = TestVM()
    test_vm.Start()
    test_vm.Open_console()
    try:
        Wait_restart(test_vm)
    except TimeoutError as err:
        print("TimeoutError : %s" % err)
    try:
        Wait_login_prompt(test_vm)
    except TimeoutError as err:
        print("TimeoutError : %s" % err)

    test_vm.panic()
    try:
        Wait_login_prompt(test_vm)
    except TimeoutError as err:
        print("TimeoutError : %s" % err)

    test_vm.Destroy()

if __name__ == '__main__':
    main()
