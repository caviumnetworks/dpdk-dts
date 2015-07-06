# BSD LICENSE
#
# Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import sys
import traceback
from random import randint
from itertools import imap

import dts
import exception
from dut import Dut
from config import VirtConf
from config import VIRTCONF
from logger import getLogger
from settings import CONFIG_ROOT_PATH
from virt_dut import VirtDut
from utils import remove_old_rsa_key


class VirtBase(object):
    """
    Basic module for customer special virtual type. This module implement
    functions configurated and composed the VM boot command. With these
    function, we can get and set the VM boot command, and instantiate the VM.
    """

    def __init__(self, dut, vm_name, suite_name):
        """
        Initialize the VirtBase.
        dut: the instance of Dut
        vm_name: the name of VM which you have confiured in the configure
        suite_name: the name of test suite
        """
        self.host_dut = dut
        self.vm_name = vm_name
        self.suite = suite_name

        # init the host session and logger for VM
        self.host_dut.init_host_session()

        # replace dut session
        self.host_session = self.host_dut.host_session
        self.host_logger = self.host_dut.logger
        # base_dir existed for host dut has prepared it
        self.host_session.send_expect("cd %s" % self.host_dut.base_dir, "# ")

        # init the host resouce pool for VM
        self.virt_pool = self.host_dut.virt_pool

        if not self.has_virtual_ability():
            if not self.enable_virtual_ability():
                raise Exception(
                    "Dut [ %s ] cannot have the virtual ability!!!")

        self.virt_type = self.get_virt_type()

        self.params = []

        # default call back function is None
        self.callback = None

    def get_virt_type(self):
        """
        Get the virtual type, such as KVM, XEN or LIBVIRT.
        """
        NotImplemented

    def has_virtual_ability(self):
        """
        Check if the host have the ability of virtualization.
        """
        NotImplemented

    def enable_virtual_ability(self):
        """
        Enalbe the virtual ability on the DUT.
        """
        NotImplemented

    def load_global_config(self):
        """
        Load global configure in the path DTS_ROOT_PAHT/conf.
        """
        conf = VirtConf(VIRTCONF)
        conf.load_virt_config(self.virt_type)
        global_conf = conf.get_virt_config()
        for param in global_conf:
            for key in param.keys():
                self.__save_local_config(key, param[key])

    def load_local_config(self, suite_name):
        """
        Load local configure in the path DTS_ROOT_PATH/conf.
        """
        # load local configuration by suite and vm name
        conf = VirtConf(CONFIG_ROOT_PATH + suite_name + '.cfg')
        conf.load_virt_config(self.vm_name)
        local_conf = conf.get_virt_config()
        # replace global configurations with local configurations
        for param in local_conf:
            if 'mem' in param.keys():
                self.__save_local_config('mem', param['mem'])
                continue
            if 'cpu' in param.keys():
                self.__save_local_config('cpu', param['cpu'])
                continue
            # save local configurations
            for key in param.keys():
                self.__save_local_config(key, param[key])

    def __save_local_config(self, key, value):
        """
        Save the local config into the global dict self.param.
        """
        for param in self.params:
            if key in param.keys():
                param[key] = value
                return

        self.params.append({key: value})

    def compose_boot_param(self):
        """
        Compose all boot param for starting the VM.
        """
        for param in self.params:
            key = param.keys()[0]
            value = param[key]
            try:
                param_func = getattr(self, 'add_vm_' + key)
                if callable(param_func):
                    for option in value:
                        param_func(**option)
                else:
                    print dts.RED("Virt %s function not callable!!!" % key)
            except AttributeError:
                    print dts.RED("Virt %s function not implemented!!!" % key)
            except Exception:
                raise exception.VirtConfigParamException(key)

    def find_option_index(self, option):
        """
        Find the boot option in the params which is generated from
        the global and local configures, and this function will
        return the index by which option can be indexed in the
        param list.
        """
        index = 0
        for param in self.params:
            key = param.keys()[0]
            if key.strip() == option.strip():
                return index
            index += 1

        return None

    def generate_unique_mac(self):
        """
        Generate a unique MAC based on the DUT.
        """
        mac_head = '00:00:00:'
        mac_tail = ':'.join(
            ['%02x' % x for x in imap(lambda x:randint(0, 255), range(3))])
        return mac_head + mac_tail

    def get_vm_ip(self):
        """
        Get the VM IP.
        """
        NotImplemented

    def get_pci_mappings(self):
        """
        Get host and VM pass-through device mapping
        """
        NotImplemented

    def isalive(self):
        """
        Check whether VM existed.
        """
        vm_status = self.host_session.send_expect(
            "ps aux | grep qemu | grep 'name %s '| grep -v grep"
            % self.vm_name, "# ")

        if self.vm_name in vm_status:
            return True
        else:
            return False

    def load_config(self):
        """
        Load configurations for VM
        """
        # load global and suite configuration file
        self.load_global_config()
        self.load_local_config(self.suite)

    def start(self, load_config=True, set_target=True, auto_portmap=True, bind_dev=True):
        """
        Start VM and instantiate the VM with VirtDut.
        """
        try:
            if load_config is True:
                self.load_config()
            # compose boot command for different hypervisors
            self.compose_boot_param()

            # start virutal machine
            self._start_vm()

            # connect vm dut and init running environment
            vm_dut = self.instantiate_vm_dut(set_target, auto_portmap)
        except Exception as vm_except:
            if self.handle_exception(vm_except):
                print dts.RED("Handled expection " + str(type(vm_except)))
            else:
                print dts.RED("Unhandled expection " + str(type(vm_except)))

            if callable(self.callback):
                self.callback()

            return None
        return vm_dut

    def handle_exception(self, vm_except):
        # show exception back trace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                                  limit=2, file=sys.stdout)
        if type(vm_except) is exception.ConfigParseException:
            # nothing to handle just return True
            return True
        elif type(vm_except) is exception.VirtConfigParseException:
            # nothing to handle just return True
            return True
        elif type(vm_except) is exception.VirtConfigParamException:
            # nothing to handle just return True
            return True
        elif type(vm_except) is exception.StartVMFailedException:
            # start vm failure
            return True
        elif type(vm_except) is exception.VirtDutConnectException:
            # need stop vm
            self.stop()
            return True
        elif type(vm_except) is exception.VirtDutInitException:
            # need close session
            vm_except.vm_dut.close_sessions()
            # need stop vm
            self.stop()
            return True
        else:
            return False

    def _start_vm(self):
        """
        Start VM.
        """
        NotImplemented

    def _stop_vm(self):
        """
        Stop VM.
        """
        NotImplemented

    def instantiate_vm_dut(self, set_target=True, auto_portmap=True, bind_dev=True):
        """
        Instantiate the Dut class for VM.
        """
        crb = self.host_dut.crb.copy()
        crb['bypass core0'] = False
        vm_ip = self.get_vm_ip()
        crb['IP'] = vm_ip
        username, password = self.get_vm_login()
        crb['user'] = username
        crb['pass'] = password

        # remove default key
        remove_old_rsa_key(self.host_dut.tester, crb['IP'])

        serializer = self.host_dut.serializer

        try:
            vm_dut = VirtDut(
                self,
                crb,
                serializer,
                self.virt_type,
                self.vm_name,
                self.suite)
        except:
            raise exception.VirtDutConnectException
            return None

        vm_dut.nic_type = 'any'
        vm_dut.tester = self.host_dut.tester
        vm_dut.host_dut = self.host_dut
        vm_dut.host_session = self.host_session

        read_cache = False
        skip_setup = self.host_dut.skip_setup
        base_dir = self.host_dut.base_dir
        vm_dut.set_speedup_options(read_cache, skip_setup)
        func_only = self.host_dut.want_func_tests
        perf_only = self.host_dut.want_perf_tests
        vm_dut.set_test_types(func_tests=func_only, perf_tests=perf_only)
        # base_dir should be set before prerequisites
        vm_dut.set_directory(base_dir)

        try:
            # setting up dpdk in vm, must call at last
            vm_dut.prerequisites(dts.Package, dts.Patches, auto_portmap)
            if set_target:
                target = self.host_dut.target
                vm_dut.set_target(target, bind_dev)
        except:
            raise exception.VirtDutInitException(vm_dut)
            return None

        return vm_dut

    def stop(self):
        """
        Stop the VM.
        """
        self._stop_vm()
        self.virt_pool.free_all_resource(self.vm_name)

    def register_exit_callback(self, callback):
        """
        Call register exit call back function
        """
        self.callback = callback
