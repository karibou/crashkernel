#!/usr/bin/python3
import os
import sys
import subprocess
import time
import argparse

vm_args = []

def parse_arguments(args):
        """
        Valid arguments are :
        --memory | -m   : Size of VM in Gb
        --disksize | -d : Disksize in Gb
        --stop-timeout | -s : Time to wait for VM to stop
        --restart-timeout | -r  : Time to wait for VM to restart
        --login-timeout | -l    : Time to wait to get the VM prompt
        """
        parser = argparse.ArgumentParser(
                    description='Run crashkernel memory tests')
        parser.add_argument('-m', '--memory', nargs=1, type=int, default=[22],
                            help='VM memory size to use (default: 22G)')
        parser.add_argument('-d', '--disksize', nargs=1, default=['100'],
                            help='VM disksize to use (default: 100G)')
        parser.add_argument('-s', '--stop-timeout', nargs=1, type=int, default=[60],
                            help='Timeout to stop VM (default: 60s)')
        parser.add_argument('-r', '--restart-timeout', nargs=1, type=int, default=[60],
                            help='Timeout to restart VM (default: 60s)')
        parser.add_argument('-l', '--login-timeout', nargs=1, type=int, default=[60],
                            help='Timeout to get login prompt (default: 60s)')
        args = vars(parser.parse_args())
        return(args)

class TestVM(object):

    def __init__(self, args):
        self.hostname = 'crashkernel-test'
        self.console_file = '/var/log/libvirt/qemu/crashkernel-test.log'
        self.memory = str(args['memory'][0]*1024)
        self.disksize = args['disksize'][0]
        self.keep = False
        self.console = None

    def Create(self):
        try:
            try:
                os.unlink(self.console_file)
            except FileNotFoundError:
                pass
            print("Creating %s VM (mem: %dG, disk: %sG)" % (self.hostname,
                  (int(self.memory)/ 1024), self.disksize ))
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

    def Reset(self):
        try:
            print("Resetting %s" % self.hostname)
            subprocess.check_output(
                ["virsh", "reset", self.hostname],
                stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("Unable to reset %s" % self.hostname)
            raise OSError

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

    vm_args = parse_arguments(sys.argv[1:])

    _events = {'restart': [b' * Will now restart\r\n', vm_args['restart_timeout'][0]],
           'login_prompt': [b'crashkernel-test login: ', vm_args['login_timeout'][0]],
           'stop': [b' * Will now halt\r\n', vm_args['stop_timeout'][0]],
           }

    test_vm = TestVM(vm_args)
    test_vm.keep = True
    try:
        test_vm.Create()
    except RuntimeError:
        exit(1)

    test_vm.Open_console()
    for event in ('restart', 'login_prompt'):
        print("Waiting %s sec for %s" % (_events[event][1], event))
        try:
            Wait_for(_events[event], test_vm)
        except TimeoutError:
            print("TimeoutError waiting for %s" % event)
            exit(1)

    for memsize in range(int(vm_args['memory'][0]), 2, -2):
        time.sleep(10)
        test_vm.Panic()
        try:
            print("Waiting %s sec for login prompt" % _events['login_prompt'][1])
            Wait_for(_events['login_prompt'], test_vm)
        except TimeoutError:
            print("TimeoutError waiting for %s" % 'login_prompt')
            print("Will try to reset VM to continue")
            try:
                test_vm.Reset()
                Wait_for(_events['login_prompt'], test_vm)
            except:
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
