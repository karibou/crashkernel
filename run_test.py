#!/usr/bin/python3
import os
import sys
import subprocess
import time

_events = {'restart': [b' * Will now restart\r\n', 60],
           'login_prompt': [b'crashkernel-test login: ', 60],
           'stop': [b' * Will now halt\r\n', 60],
           }


class TestVM(object):

    def __init__(self):
        self.hostname = 'crashkernel-test'
        self.console_file = '/var/log/libvirt/qemu/crashkernel-test.log'
        self.memory = '22528'
        self.disksize = '100'
        self.keep = False
        self.console = None

    def Create(self):
        try:
            try:
                os.unlink(self.console_file)
            except FileNotFoundError:
                pass
            print("Creating %s VM" % self.hostname)
            subprocess.check_output(
                ["uvt-kvm", "create", self.hostname, "--memory", self.memory,
                 "--disk", self.disksize,  "--cpu", "2", "--user-data",
                 "crashkernel.cloud", "--log-console-output"],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to create %s VM" % self.hostname)
            raise RuntimeError

    def Start(self):
        try:
            print("Starting %s" % self.hostname)
            subprocess.check_output(
                ["virsh", "start", self.hostname], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to start %s" % self.hostname)

    def Stop(self):
        try:
            print("Stopping %s" % self.hostname)
            subprocess.check_output(
                ["virsh", "shutdown", self.hostname],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to stop %s" % self.hostname)

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

    def Panic(self):
        try:
            print("Sending SysRq to %s" % self.hostname)
            subprocess.check_output(
                ["virsh", "send-key", self.hostname, "KEY_LEFTALT",
                 "KEY_SYSRQ", "KEY_C"], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to panic %s VM" % self.hostname)

    def Resize(self, size):
        try:
            print("Resizing %s to %dG" % (self.hostname, size))
            subprocess.check_output(
                ["virsh", "setmaxmem", "--size=%sG" % size, "--config",
                 self.hostname], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable set %s to size %d" % (self.hostname, size))


def Wait_for(event, vm):

    loop = 0
    output = vm.Read_console()
    while event[0] not in output and loop <= event[1]:
        time.sleep(5)
        output = vm.Read_console()
        loop += 5
    if loop > event[1]:
        raise TimeoutError


def main():
    if os.getuid() != 0:
        print("This script must be run as root !")
        exit(1)

    test_vm = TestVM()
    test_vm.keep = True
    try:
        test_vm.Create()
    except RuntimeError:
        exit(1)

    test_vm.Open_console()
    for event in ('restart', 'login_prompt'):
        print("Waiting for %s" % event)
        try:
            Wait_for(_events[event], test_vm)
        except TimeoutError:
            print("TimeoutError waiting for %s" % event)
            exit(1)

    for memsize in range(20, 2, -2):
        time.sleep(10)
        test_vm.Panic()
        try:
            Wait_for(_events['login_prompt'], test_vm)
        except TimeoutError:
            print("TimeoutError waiting for %s" % 'login_prompt')
            exit(1)
        test_vm.Resize(memsize)
        time.sleep(5)
        test_vm.Stop()
        try:
            Wait_for(_events['stop'], test_vm)
        except TimeoutError:
            print("TimeoutError waiting for %s" % 'stop')
            exit(1)
        test_vm.Start()
        try:
            Wait_for(_events['login_prompt'], test_vm)
        except TimeoutError:
            print("TimeoutError waiting for %s" % 'login_prompt')
            exit(1)

    if test_vm.keep:
        test_vm.Stop()
    else:
        test_vm.Destroy()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
