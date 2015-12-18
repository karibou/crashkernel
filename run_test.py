#!/usr/bin/python3
import os
import sys
import subprocess


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

def Wait_boot_end(vm):
    
    output = vm.Read_console()
    # Need to continue here
    return

def main():
    test_vm = TestVM()
    test_vm.Start()
    test_vm.Open_console()
    Wait_boot_end(test_vm)
    test_vm.Destroy()

if __name__ == '__main__':
    main()
