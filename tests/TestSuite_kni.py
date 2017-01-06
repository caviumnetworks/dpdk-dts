# <COPYRIGHT_TAG>
# BSD LICENSE
#
# Copyright(c) 2010-2015 Intel Corporation. All rights reserved.
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

"""
DPDK Test suite.

Test Kernel NIC Interface.
"""

import utils
import re
import time
from random import randint

dut_ports = []
port_virtual_interaces = []

ports_without_kni = 2
flows_without_kni = 2

packet_sizes_loopback = [64, 256]
packet_sizes_routing = [64, 256]

ports_cores_template = '\(P([0123]),(C\{\d.\d.\d\}),(C\{\d.\d.\d\}),(C\{\d.\d.\d\}),?(C\{\d.\d.\d\})?\),?'

default_1_port_cores_config = '(P0,C{1.0.0},C{1.1.0},C{1.0.1})'
default_2_port_cores_config = '(P0,C{1.0.0},C{1.1.0},C{1.0.1}),(P1,C{1.2.0},C{1.3.0},C{1.2.1})'

stress_test_iterations = 50
stress_test_random_iterations = 50

routing_performance_steps = [
    {'kthread_mode': 'single', 'config': '(P0,C{1.0.0},C{1.1.0},C{1.0.1})'},
    {'kthread_mode': 'single', 'config': '(P0,C{1.0.0},C{1.0.1},C{1.1.0})'},
    {'kthread_mode': 'single', 'config': '(P0,C{1.0.0},C{1.1.0},C{1.2.0})'},

    {'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.0.1})'},
    {'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.4.0})'},
    {'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.2.0})'},
    {'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.0.1})'},
    {'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.4.0})'},
    {'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.2.0})'},

    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.3.0})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.3.0})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0})'},

    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.2.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.2.1})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.5.0})'},
    {'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0},C{1.6.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0},C{1.7.0})'}
]

bridge_performance_steps = [
    {'flows': 1, 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.0.1})'},
    {'flows': 1, 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.4.0})'},
    {'flows': 1, 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.2.0})'},
    {'flows': 2, 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.0.1})'},
    {'flows': 2, 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.4.0})'},
    {'flows': 2, 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.2.0})'},

    {'flows': 1, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1})'},
    {'flows': 1, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.3.0})'},
    {'flows': 1, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0})'},
    {'flows': 2, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1})'},
    {'flows': 2, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.3.0})'},
    {'flows': 2, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0})'},

    {'flows': 1, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.2.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.2.1})'},
    {'flows': 1, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.5.0})'},
    {'flows': 1, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0},C{1.6.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0},C{1.7.0})'},
    {'flows': 2, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.2.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.2.1})'},
    {'flows': 2, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.5.0})'},
    {'flows': 2, 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0},C{1.6.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0},C{1.7.0})'}
]

loopback_performance_steps = [
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'single',
        'config': '(P0,C{1.0.0},C{1.1.0},C{1.0.1})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'single',
        'config': '(P0,C{1.0.0},C{1.0.1},C{1.1.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'single',
        'config': '(P0,C{1.0.0},C{1.1.0},C{1.2.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.0.1})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.4.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.2.0})'},

    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple',
        'config': '(P0,C{1.0.0},C{1.1.0},C{1.0.1})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple',
        'config': '(P0,C{1.0.0},C{1.0.1},C{1.1.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple',
        'config': '(P0,C{1.0.0},C{1.1.0},C{1.2.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.3.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0})'},

    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.2.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.3.1})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.1.1},C{1.5.0})'},
    {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0},C{1.6.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0},C{1.7.0})'},

    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode':
        'single', 'config': '(P0,C{1.0.0},C{1.1.0},C{1.0.1})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode':
        'single', 'config': '(P0,C{1.0.0},C{1.0.1},C{1.1.0})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode':
        'single', 'config': '(P0,C{1.0.0},C{1.1.0},C{1.2.0})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.0.1})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.4.0})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'single', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.2.0})'},

    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode':
        'multiple', 'config': '(P0,C{1.0.0},C{1.1.0},C{1.0.1})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode':
        'multiple', 'config': '(P0,C{1.0.0},C{1.0.1},C{1.1.0})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode':
        'multiple', 'config': '(P0,C{1.0.0},C{1.1.0},C{1.2.0})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.0.1}),(P1,C{1.1.0},C{1.3.0},C{1.1.1})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.0.1},C{1.2.0}),(P1,C{1.1.0},C{1.1.1},C{1.3.0})'},
    {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'multiple', 'config':
        '(P0,C{1.0.0},C{1.2.0},C{1.4.0}),(P1,C{1.1.0},C{1.3.0},C{1.5.0})'}
]

loopback_perf_results_header = ['lo_mode', 'kthread_mode', 'Ports', 'Config']
bridge_perf_results_header = ['kthread_mode', 'Flows', 'Config', '64 Mpps']
bridge_perf_no_kni_results_header = ['Flows', '64 Mpps']
routing_perf_results_header = ['kthread_mode', 'Ports', 'Config']
routing_perf_no_kni_results_header = ['Ports']

stress_modes_output = [{'lo_mode': None, 'kthread_mode': None,
                        'output': 'loopback disabled.*DPDK kni module loaded.*Single kernel thread'},
                       {'lo_mode': 'lo_mode_none', 'kthread_mode': None,
                        'output': 'loopback disabled.*DPDK kni module loaded.*Single kernel thread'},
                       {'lo_mode': 'lo_mode_fifo', 'kthread_mode': None,
                        'output': 'loopback mode=lo_mode_fifo enabled.*Single kernel thread'},
                       {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': None,
                        'output': 'loopback mode=lo_mode_fifo_skb enabled.*Single kernel thread'},
                       {'lo_mode': 'lo_mode_random', 'kthread_mode': None,
                        'output': 'Incognizant parameter, loopback disabled.*DPDK kni module loaded.*Single kernel thread'},
                       {'lo_mode': None, 'kthread_mode': 'single',
                        'output': 'loopback disabled.*DPDK kni module loaded.*Single kernel thread'},
                       {'lo_mode': None, 'kthread_mode': 'multiple',
                        'output': 'loopback disabled.*DPDK kni module loaded.*Multiple kernel thread'},
                       {'lo_mode': None, 'kthread_mode': 'singlemulti',
                        'output': 'KNI.* Invalid parameter for kthread_mode'},
                       {'lo_mode': 'lo_mode_fifo', 'kthread_mode': 'multiple',
                        'output': 'loopback mode=lo_mode_fifo enabled.*Multiple kernel thread'},
                       {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'multiple',
                        'output': 'loopback mode=lo_mode_fifo_skb enabled.*Multiple kernel thread'},
                       {'lo_mode': 'lo_mode_fifo_skb', 'kthread_mode': 'singlemulti',
                        'output': 'Invalid parameter for kthread_mode'},
                       {'lo_mode': 'lo_mode_random', 'kthread_mode': 'multiple',
                        'output': 'KNI.* Incognizant parameter, loopback disabled'}
                       ]


from test_case import TestCase

#
#
# Test class.
#


class TestKni(TestCase):

    #
    #
    # Utility methods and other non-test code.
    #
    # Insert or move non-test functions here.

    def set_up_all(self):
        """
        Run at the start of each test suite.

        KNI Prerequisites
        """
        out = self.dut.send_expect("which brctl", "# ")
        self.verify('no brctl' not in out,
                    "The linux tool brctl is needed to run this test suite")

        out = self.dut.send_expect("make -C ./examples/kni/", "# ", 5)
        self.verify('Error' not in out, "Compilation failed")

        self.extract_ports_cores_config(default_1_port_cores_config)
        out = self.start_kni()
        self.verify("Error" not in out, "Error found during kni start")

        self.dut.send_expect("service iptables stop", "# ")
        self.dut.send_expect("service firewalld stop", "# ")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def start_kni(self, lo_mode=None, kthread_mode=None):
        """
        Insert the igb_uio and rte_kni modules with passed parameters and launch
        kni application.
        """
        module_param = ""
        if lo_mode is not None:
            module_param += "lo_mode=%s " % lo_mode

        if kthread_mode is not None:
            module_param += "kthread_mode=%s" % kthread_mode
        self.dut.kill_all()
        out = self.dut.send_expect("rmmod rte_kni", "# ", 10)
        self.verify("in use" not in out, "Error unloading KNI module: " + out)
        if self.drivername == "igb_uio":
            self.dut.send_expect("rmmod igb_uio", "# ", 5)
            self.dut.send_expect(
                'insmod ./%s/kmod/igb_uio.ko' % (self.target), "# ", 20)
        self.dut.bind_interfaces_linux()
        out = self.dut.send_expect(
            'insmod ./%s/kmod/rte_kni.ko %s' % (self.target, module_param), "# ", 10)

        self.verify("Error" not in out, "Error loading KNI module: " + out)

        port_mask = utils.create_mask(self.config['ports'])
        core_mask = utils.create_mask(
            self.config['rx_cores'] + self.config['tx_cores'] + self.config['kernel_cores'])

        config_param = self.build_config_param()

        out_kni = self.dut.send_expect(
            './examples/kni/build/app/kni -c %s -n %d -- -P -p %s %s &' %
            (core_mask, self.dut.get_memory_channels(), port_mask, config_param),
            "APP: Lcore [0-9]+ is reading from port [0-9]+", 20)

        time.sleep(5)
        if kthread_mode == 'single':
            kthread_mask = utils.create_mask(self.config['kernel_cores'])
            out = self.dut.send_expect(
                "taskset -p %s `pgrep -fl kni_single | awk '{print $1}'`" % kthread_mask, "#")
            self.verify(
                'new affinity mask' in out, 'Unable to set core affinity')

        return out_kni

    def extract_ports_cores_config(self, ports_cores_config):
        """
        Parses a ports/cores configuration string into the 'self.config' variable.
        """
        ports_cores_pattern = re.compile(ports_cores_template)
        port_configs = ports_cores_pattern.findall(ports_cores_config)
        dut_ports = self.dut.get_ports(self.nic)

        config = {}
        ports = []
        rx_cores = []
        tx_cores = []
        k_cores = []
        port_details = []
        for port_config in port_configs:
            details = {}

            port_number = int(port_config[0])
            self.verify(
                port_number < len(dut_ports), "Not enough ports available")

            ports.append(dut_ports[port_number])
            details['port'] = dut_ports[port_number]
            rx_cores.append(self.dut.get_lcore_id(port_config[1]))
            details['rx_core'] = self.dut.get_lcore_id(port_config[1])
            tx_cores.append(self.dut.get_lcore_id(port_config[2]))
            details['tx_core'] = self.dut.get_lcore_id(port_config[2])

            details['kernel_cores'] = []
            for k_core in port_config[3:]:
                if k_core != '':
                    k_cores.append(self.dut.get_lcore_id(k_core))
                    details['kernel_cores'].append(
                        self.dut.get_lcore_id(k_core))

            port_details.append(details)

        config['ports'] = ports
        config['rx_cores'] = rx_cores
        config['tx_cores'] = tx_cores
        config['kernel_cores'] = k_cores
        config['port_details'] = port_details

        self.config = config

    def build_config_param(self):
        """
        Formats the '--conf=(xxx)' parameter for kni application calls
        """
        config_param = '--config="%s'
        port_cores = '(%s,%s,%s)'
        port_cores_kernel = '(%s,%s,%s,'

        for port in self.config['port_details']:

            # Kernel threads specified
            if len(port['kernel_cores']) > 0:

                port_config = port_cores_kernel % (port['port'],
                                                   port['rx_core'],
                                                   port['tx_core'])

                for core in port['kernel_cores']:
                    port_config += str(core) + ','

                port_config = port_config[:-1] + ')'

            # No kernel threads specified
            else:
                port_config = port_cores % (port['port'],
                                            port['rx_core'],
                                            port['tx_core'])

            config_param = config_param % port_config + ',%s'

        config_param = config_param.replace(',%s', '"')

        return config_param

    def stripped_config_param(self):
        """
        Removes the '--config=' prefix from the config string.
        Used for reporting.
        """
        config_param = self.build_config_param()
        config_param = config_param.replace('--config="', '')
        config_param = config_param.replace('"', '')
        return config_param

    def virtual_interface_name(self, port, sub_port=0):
        """
        Given a port and subport name, formats the virtual interface name.
        """
        return 'vEth%d_%d' % (port, sub_port)

    def dut_physical_cores(self):
        """
        Returns the number of physical cores in socket 0.
        """
        dut_cores = self.dut.get_all_cores()

        first_core = dut_cores[0]
        cores = []

        for core in dut_cores[1:]:
            if core['core'] not in cores and \
                    core['socket'] == first_core['socket']:
                cores.append(core['core'])

        return len(cores)

    def make_white_list(self, target, nic):
        """
        Create white list with ports.
        """
        white_list = []
        dut_ports = self.dut.get_ports(self.nic)
        self.dut.restore_interfaces()
        allPort = self.dut.ports_info
        if self.drivername in ["igb_uio"]:
            self.dut.send_expect(
                "insmod ./" + self.target + "/kmod/igb_uio.ko", "#")
        for port in range(0, len(allPort)):
            if port in dut_ports:
                white_list.append(allPort[port]['pci'])
        return white_list

    #
    #
    #
    # Test cases.
    #

    def test_ifconfig(self):
        """
        Ifconfig support KNI.
        """

        # Ports and cores configuration set in set_up_all function
        # Check that all virtual interfaces support ifconfig calls.
        out = self.dut.send_expect("ifconfig -a", "# ")
        for port in self.config['ports']:
            virtual_interface = self.virtual_interface_name(port)
            self.verify(
                virtual_interface in out, "ifconfig not supported for %s" % virtual_interface)

        # For each virtual interface perform the following operations
        for port in self.config['ports']:
            virtual_interface = self.virtual_interface_name(port)

            # Set up
            out = self.dut.send_expect(
                "ifconfig %s up" % virtual_interface, "# ")
            self.verify("Configure network interface of %d up" %
                        port in out, "ifconfig up not supported")

            out = self.dut.send_expect(
                "ip -family inet6 address show dev %s" % virtual_interface, "# ")
            self.verify(
                "inet6 " in out, "ifconfig up the port_virtual_interaces not support")

            # Add an IPv6 address
            out = self.dut.send_expect(
                "ifconfig %s add fe80::%d" % (virtual_interface, port + 1), "# ")
            out = self.dut.send_expect(
                "ip -family inet6 address show dev %s" % virtual_interface, "# ")
            self.verify("inet6 fe80::%d" %
                        (port + 1) in out, "ifconfig add ipv6 address not supported")

            # Delete the IPv6 address
            out = self.dut.send_expect(
                "ifconfig %s del fe80::%d" % (virtual_interface, port + 1), "# ")
            out = self.dut.send_expect(
                "ip -family inet6 address show dev %s" % virtual_interface, "# ")
            self.verify("inet6 fe80::%d/128" %
                        (port + 1) not in out, "ifconfig del ipv6 address not supported")

            # Add an IPv4 address
            out = self.dut.send_expect(
                "ifconfig %s 192.168.%d.1 netmask 255.255.255.192" % (virtual_interface, port), "# ")
            out = self.dut.send_expect(
                "ip -family inet address show dev %s" % virtual_interface, "# ")
            self.verify("inet 192.168.%d.1/26" %
                        port in out, "ifconfig set ip address not supported")

            # Set the MTU
            out = self.dut.send_expect(
                "ifconfig %s mtu 1300" % virtual_interface, "# ")
            out = self.dut.send_expect(
                "ip link show %s" % virtual_interface, "# ")
            self.verify("mtu 1300" in out, "mtu setup not supported")

            # Bring down
            self.dut.send_expect("ifconfig %s down" % virtual_interface, "# ")
            out = self.dut.send_expect(
                "ip -family inet6 address show dev %s" % virtual_interface, "# ")
            self.verify("inet6 addr" not in out, "ifconfig down not supported")

    def test_ping(self):
        """
        Ping support KNI.
        """

        # Ports and cores configuration set in set_up_all function
        # Setup IP address on virtual interfaces and tester ports
        self.dut.kill_all()
        self.start_kni()
        for port in self.config['ports']:
            virtual_interface = self.virtual_interface_name(port)

            tx_port = self.tester.get_local_port(port)
            tx_interface = self.tester.get_interface(tx_port)
            out = self.dut.send_expect(
                "ifconfig %s up" % virtual_interface, "# ")
            time.sleep(5)
            self.dut.send_expect(
                 "ifconfig %s 192.168.%d.1 netmask 255.255.255.192" % (virtual_interface, port), "# ")
            self.tester.send_expect(
                 "ifconfig %s 192.168.%d.2 netmask 255.255.255.192" % (tx_interface, port), "# ")
            self.tester.enable_ipv6(tx_interface)
            time.sleep(5)
        # Send ping requests and check for answers
        for port in self.config['ports']:

            tx_port = self.tester.get_local_port(port)
            tx_interface = self.tester.get_interface(tx_port)

            virtual_interface = self.virtual_interface_name(port)

            out = self.dut.send_expect(
                "ping -w 2 -I %s 192.168.%d.1" % (virtual_interface, port), "# ", 10)
            self.verify("64 bytes from 192.168.%d.1:" %
                        port in out, "ping not supported")

            out = self.dut.send_expect(
                "ping -w 2 -I %s 192.168.%d.2" % (virtual_interface, port), "# ", 10)
            self.verify("64 bytes from 192.168.%d.2:" %
                        port in out, "ping not supported")

            out = self.tester.send_expect(
                "ping -w 1 -I %s 192.168.%d.1" % (tx_interface, port), "# ", 10)
            self.verify("64 bytes from 192.168.%d.1:" %
                        port in out, "kni cannot reply ping packet")

            out = self.dut.send_expect(
                "ping -w 1 -I %s 192.168.%d.123" % (virtual_interface, port), "# ", 10)
            self.verify(
                "0 received, 100% packet loss" in out, "ping not supported")

            out = self.dut.send_expect(
                "ip -family inet6 address show dev %s | awk '/inet6/ { print $2 }'| cut -d'/' -f1" % virtual_interface, "# ", 10)
            ipv6_address = out.split('\r\n')[0]

            out = self.dut.send_expect("ping6 -w 1 -I %s %s" %
                                       (virtual_interface, str(ipv6_address)), "# ", 10)
            # FC25 ping6 output info is "64 bytes from ipv6_address%v: icmp_seq=1 ttl=64"
            # other os ping6 output is "64 bytes from ipv6_address: icmp_seq=1 ttl=64"
            self.verify("64 bytes from %s" %
                        ipv6_address in out, "ping6 not supported")

            out = self.tester.send_expect(
                "ping6 -w 1 -I %s %s" % (tx_interface, str(ipv6_address)), "# ", 10)
            self.verify("64 bytes from %s" %
                        ipv6_address in out, "kni cannot reply ping6 packet")

            ipv6list = list(ipv6_address)
            for j in range(10):
                if str(j) == ipv6list[-1]:
                    continue
                else:
                    ipv6list[-1] = str(j)
                    break

            out = self.dut.send_expect("ping6 -w 1 -I %s %s" %
                                       (virtual_interface, ''.join(ipv6list)), "# ", 10)
            self.verify(
                "0 received, 100% packet loss" in out, "ping6 not supported")
            # remove ip from tester
            self.tester.send_expect(
                 "ip addr del 192.168.%d.2 dev %s" % (port, tx_interface), "# ")
          
        for port in self.config['ports']:
            tx_port = self.tester.get_local_port(port)
            tx_interface = self.tester.get_interface(tx_port)
            self.tester.disable_ipv6(tx_interface)
            time.sleep(1)
        
    def test_tcpdump(self):
        """
        Tcpdump support KNI.
        """

        # Ports and cores configuration set in set_up_all function
        self.dut.kill_all()
        self.start_kni()
        for port in self.config['ports']:

            virtual_interface = self.virtual_interface_name(port)

            tx_port = self.tester.get_local_port(port)
            rx_mac = self.dut.get_mac_address(port)
            tx_mac = self.tester.get_mac(tx_port)
            tx_interface = self.tester.get_interface(tx_port)

            self.dut.send_expect("ifconfig %s up" % virtual_interface, "# ")
            time.sleep(5)

            # Start tcpdump with filters for src and dst MAC address, this avoids
            # unwanted broadcast, ICPM6... packets
            out = self.dut.send_expect(
                'tcpdump -i %s -e -w packet.log "ether src %s and ether dst %s"' %
                (virtual_interface, tx_mac, rx_mac),
                "listening on %s" % virtual_interface, 30)

            packets_to_send = [
                'sendp([Ether(src=srcmac,dst=dstmac)/IP()/UDP()/("W"*28)],iface="%s")',
                'sendp([Ether(src=srcmac,dst=dstmac)/IP()/TCP()/("W"*28)],iface="%s")',
                'sendp([Ether(src=srcmac,dst=dstmac)/IP()/ICMP()/("W"*28)],iface="%s")',
                'sendp([Ether(src=srcmac,dst=dstmac)/IP()/("W"*38)],iface="%s")',
                'sendp([Ether(src=srcmac,dst=dstmac)/("W"*46)],iface="%s")'
            ]

            self.tester.scapy_append('dstmac="%s"' % rx_mac)
            self.tester.scapy_append('srcmac="%s"' % tx_mac)

            for packet in packets_to_send:
                self.tester.scapy_append(packet % tx_interface)

            self.tester.scapy_execute()

            out = self.dut.send_expect("^C", "# ", 20)

            self.verify("%d packets captured" % len(packets_to_send) in out,
                        "Wrong number of packets captured")

    def test_ethtool(self):
        """
        Ethtool support KNI.
        """

        # Ports and cores configuration set in set_up_all function
        # For each virtual interface perform the following operations
        for port in self.config['ports']:

            virtual_interface = self.virtual_interface_name(port)

            # Request settings
            out = self.dut.send_expect("ethtool %s" % virtual_interface,
                                       "# ")
            self.verify("Settings for %s" % virtual_interface in out,
                        "ethtool not supported")
            self.verify("Operation not supported" not in out,
                        "ethtool not supported")

            # Request driver information
            out = self.dut.send_expect("ethtool -i %s" % virtual_interface,
                                       "# ")
            self.verify("driver: ixgbe" or "driver: igb" in out,
                        "'ethtool -i' not supported")
            self.verify("Operation not supported" not in out,
                        "'ethtool -i' not supported")

            # Request pause parameters
            out = self.dut.send_expect("ethtool -a %s" % virtual_interface,
                                       "# ")
            self.verify("Pause parameters for %s" % virtual_interface in out,
                        "'ethtool -a' not supported")
            self.verify("Operation not supported" not in out,
                        "ethtool '-a' not supported")

            # Request statistics
            out = self.dut.send_expect("ethtool -S %s" % virtual_interface,
                                       "# ")
            self.verify("NIC statistics" in out,
                        "'ethtool -S' not supported")
            self.verify("Operation not supported" not in out,
                        "ethtool '-S' not supported")

            # Request features status
            out = self.dut.send_expect("ethtool -k %s" % virtual_interface, "# ")
            self.verify(("Features for %s" % virtual_interface in out) or
                        ("Offload parameters for %s" %
                         virtual_interface in out),
                        "'ethtool -k' not supported")
            self.verify("Operation not supported" not in out,
                        "'ethtool -k' not supported")

            # Request ring parameters
            out = self.dut.send_expect("ethtool -g %s" % virtual_interface,
                                       "# ")
            self.verify("Ring parameters for %s" % virtual_interface in out,
                        "'ethtool -g' not supported")
            self.verify("Operation not supported" not in out,
                        "'ethtool -g' not supported")

            # Request coalesce parameters. NOT SUPORTED
            out = self.dut.send_expect("ethtool -c %s" % virtual_interface,
                                       "# ")
            self.verify("Operation not supported" in out,
                        "'ethtool -c' seems to be supported. Check it.")

            # Request register dump
            out = self.dut.send_expect("ethtool -d %s" % virtual_interface,
                                       "# ")
            expectstring = "0x00000: CTRL.*0x00008: STATUS"
            self.verify(len(re.findall(expectstring, out , re.DOTALL)) > 0, "'ethtool -d' not supported")
            self.verify("Operation not supported" not in out,
                        "'ethtool -d' not supported")

            # Request eeprom dump
            out = self.dut.send_expect("ethtool -e %s" % virtual_interface,
                                       "# ")
            self.verify("Offset" and "Values" in out,
                        "'ethtool -e' not support")
            self.verify("Operation not supported" not in out,
                        "'ethtool -e' not support")

    def test_statistics(self):
        """
        KNI Statistics test.
        """
        rx_match = "RX packets.(\d+)"

        self.dut.kill_all()
        self.start_kni(lo_mode='lo_mode_ring_skb')

        # Ports and cores configuration set in set_up_all function
        # For each virtual interface perform the following operations
        for port in self.config['ports']:

            virtual_interface = self.virtual_interface_name(port)

            out = self.dut.send_expect(
                "ifconfig %s up" % virtual_interface, "# ")
            time.sleep(5)
            out = self.dut.send_expect("ifconfig %s" % virtual_interface, "# ")
            m = re.search(rx_match, out)
            previous_rx_packets = int(m.group(1))

            tx_port = self.tester.get_local_port(port)
            rx_mac = self.dut.get_mac_address(port)
            tx_mac = self.tester.get_mac(tx_port)
            tx_interface = self.tester.get_interface(tx_port)

            self.tester.scapy_append('dstmac = "%s"' % rx_mac)
            self.tester.scapy_append('srcmac = "%s"' % tx_mac)

            self.tester.scapy_append(
                'sendp([Ether(src = srcmac,dst=dstmac)/IP()/UDP()/("X"*28)],iface="%s")' % tx_interface)
            self.tester.scapy_append(
                'sendp([Ether(src = srcmac,dst=dstmac)/IP()/TCP()/("X"*28)],iface="%s")' % tx_interface)
            self.tester.scapy_append(
                'sendp([Ether(src = srcmac,dst=dstmac)/IP()/ICMP()/("X"*28)],iface="%s")' % tx_interface)
            self.tester.scapy_append(
                'sendp([Ether(src = srcmac,dst=dstmac)/IP()/("X"*38)],iface="%s")' % tx_interface)
            self.tester.scapy_append(
                'sendp([Ether(src = srcmac,dst=dstmac)/("X"*46)],iface="%s")' % tx_interface)
            self.tester.scapy_execute()

            out = self.dut.send_expect("ifconfig %s" % virtual_interface, "# ")
            m = re.search(rx_match, out)
            rx_packets = int(m.group(1))

            self.verify(rx_packets == (previous_rx_packets + 5),
                        "Rx statistics error in iface %s" % virtual_interface)

        self.dut.kill_all()

    def test_stress(self):
        """
        KNI stress test.
        """
        self.extract_ports_cores_config(default_2_port_cores_config)
        self.dut.send_expect('dmesg -c', "]# ")  # Clean the dmesg ring buffer
        for i in range(stress_test_iterations + stress_test_random_iterations):

            self.dut.kill_all()

            if i < stress_test_iterations:
                step = stress_modes_output[i % len(stress_modes_output)]
            else:
                step = stress_modes_output[
                    randint(0, len(stress_modes_output) - 1)]

            expectedMessage = step['output']

            try:
                out = self.start_kni(step['lo_mode'], step['kthread_mode'])
                self.verify("Error" not in out, "Error found during kni start")
                # kni setup out info by kernel debug function. so should re-build kenel.
                # now not check kni setup out info, only check kni setup ok and setup no error output
                out = self.dut.send_expect('ps -aux', "]# ")
                self.verify("kni" not in out, "kni process setup failed")
            except:
                # some permutations have to fail
                pass

    def test_perf_loopback(self):
        """
        KNI loopback performance
        """
        self.dut.kill_all()

        header = loopback_perf_results_header
        for size in packet_sizes_loopback:
            header.append('%d (pps)' % size)

        self.result_table_create(header)

        # Execute the permutations of the test
        for step in loopback_performance_steps:

            self.extract_ports_cores_config(step['config'])

            total_cores = len(self.config['tx_cores'] + self.config[
                              'rx_cores'] + self.config['kernel_cores'])
            if total_cores > self.dut_physical_cores():
                print utils.RED("Skiping step %s (%d cores needed, got %d)" %
                              (step['config'], total_cores,
                               self.dut_physical_cores())
                              )
                continue

            self.start_kni(
                lo_mode=step['lo_mode'], kthread_mode=step['kthread_mode'])

            pps_results = []

            for size in packet_sizes_loopback:

                payload_size = size - 38

                ports_number = len(self.config['ports'])

                # Set up the flows for the ports
                tgen_input = []
                for port in self.config['ports']:

                    rx_mac = self.dut.get_mac_address(port)
                    tx_port = self.tester.get_local_port(port)
                    self.tester.scapy_append('dstmac = "%s"' % rx_mac)
                    self.tester.scapy_append(
                        'flows = [Ether(dst=dstmac)/IP()/("X"*%d)]' % payload_size)
                    self.tester.scapy_append(
                        'wrpcap("tester%d.pcap",flows)' % tx_port)
                    self.tester.scapy_execute()
                    tgen_input.append(
                        (tx_port, tx_port, "tester%d.pcap" % tx_port))

                time.sleep(1)
                _, pps = self.tester.traffic_generator_throughput(tgen_input)
                pps_results.append(float(pps) / 1000000)

            ports_number = len(self.config['ports'])
            results_row = [step['lo_mode'], step['kthread_mode'], ports_number,
                           self.stripped_config_param()] + pps_results
            self.result_table_add(results_row)

            self.dut.kill_all()

        self.result_table_print()

    def test_perf_bridge(self):
        """
        KNI performance bridge mode.
        """
        self.result_table_create(bridge_perf_results_header)

        self.tester.scapy_append('srcmac="00:00:00:00:00:01"')
        self.tester.scapy_append(
            'wrpcap("kni.pcap", [Ether(src=srcmac, dst="ff:ff:ff:ff:ff:ff")/IP(len=46)/UDP()/("X"*18)])')
        self.tester.scapy_execute()

        for step in bridge_performance_steps:

            self.extract_ports_cores_config(step['config'])

            total_cores = len(self.config['tx_cores'] + self.config[
                              'rx_cores'] + self.config['kernel_cores'])
            if total_cores > self.dut_physical_cores():
                print utils.RED("Skiping step %s (%d cores needed, got %d)" %
                              (step['config'], total_cores,
                               self.dut_physical_cores())
                              )
                continue

            port_virtual_interaces = []
            for port in self.config['port_details']:
                for i in range(len(port['kernel_cores'])):
                    port_virtual_interaces.append(
                        self.virtual_interface_name(port['port'], i))

            self.dut.kill_all()
            self.start_kni(lo_mode=None, kthread_mode=step['kthread_mode'])

            for virtual_interace in port_virtual_interaces:
                out = self.dut.send_expect(
                    "ifconfig %s up" % virtual_interace, "# ")
                self.verify("ERROR" not in out, "Virtual interface not found")

            self.dut.send_expect("brctl addbr \"br_kni\"", "# ")

            for virtual_interace in port_virtual_interaces:
                out = self.dut.send_expect(
                    "brctl addif br_kni %s" % virtual_interace, "# ")
                self.verify("ERROR" not in out, "Device not found")

            self.dut.send_expect("ifconfig br_kni up", "# ")
            time.sleep(3)

            tx_port = self.tester.get_local_port(self.config['ports'][0])
            rx_port = self.tester.get_local_port(self.config['ports'][1])

            tgenInput = []
            tgenInput.append((tx_port, rx_port, "kni.pcap"))

            if step['flows'] == 2:
                tgenInput.append((rx_port, tx_port, "kni.pcap"))

            time.sleep(1)
            _, pps = self.tester.traffic_generator_throughput(tgenInput)
            step['pps'] = float(pps) / 10 ** 6

            results_row = [step['kthread_mode'], step['flows'],
                           self.stripped_config_param(), (float(pps) / 10 ** 6)]

            self.result_table_add(results_row)

            self.dut.send_expect("ifconfig br_kni down", "# ")
            self.dut.send_expect("brctl delbr \"br_kni\"", "# ", 10)

        self.result_table_print()

    def test_perf_bridge_without_kni(self):
        """
        Bridge mode performance without KNI.
        """
        self.result_table_create(bridge_perf_no_kni_results_header)

        self.dut.kill_all()

        dut_ports = self.dut.get_ports(self.nic)

        self.tester.scapy_append('srcmac="00:00:00:00:00:01"')
        self.tester.scapy_append(
            'wrpcap("kni.pcap", [Ether(src=srcmac, dst="ff:ff:ff:ff:ff:ff")/IP(len=46)/UDP()/("X"*18)])')
        self.tester.scapy_execute()

        white_list = self.make_white_list(self.target, self.nic)
        port_virtual_interaces = []
        for port in white_list:
            information = self.dut.send_expect(
                "./usertools/dpdk-devbind.py --status | grep '%s'" % port, "# ")
            data = information.split(' ')
            for field in data:
                if field.rfind("if=") != -1:
                    port_virtual_interaces.append(field.replace("if=", ""))

        self.dut.send_expect("ifconfig %s up" %
                             port_virtual_interaces[0], "# ")
        self.dut.send_expect("ifconfig %s up" %
                             port_virtual_interaces[1], "# ")
        self.dut.send_expect("brctl addbr \"br1\"", "# ")
        self.dut.send_expect("brctl addif br1 %s" %
                             port_virtual_interaces[0], "# ")
        self.dut.send_expect("brctl addif br1 %s" %
                             port_virtual_interaces[1], "# ")
        self.dut.send_expect("ifconfig br1 up", "# ")
        time.sleep(3)

        tx_port = self.tester.get_local_port(dut_ports[0])
        rx_port = self.tester.get_local_port(dut_ports[1])

        for flows in range(1, flows_without_kni + 1):
            tgenInput = []
            tgenInput.append((tx_port, rx_port, "kni.pcap"))

            if flows == 2:
                tgenInput.append((rx_port, tx_port, "kni.pcap"))

            _, pps = self.tester.traffic_generator_throughput(tgenInput)
            self.result_table_add([flows, float(pps) / 10 ** 6])

        self.dut.send_expect("ifconfig br1 down", "# ")
        self.dut.send_expect("brctl delbr \"br1\"", "# ", 30)

        for port in white_list:
            self.dut.send_expect(
                "./usertools/dpdk-devbind.py -b igb_uio %s" % (port), "# ")
        self.result_table_print()

    def test_perf_routing(self):
        """
        Routing performance.
        """

        header = routing_perf_results_header

        for size in packet_sizes_routing:
            header.append("%d Mpps" % size)

        self.result_table_create(header)

        self.dut.send_expect("echo 1 > /proc/sys/net/ipv4/ip_forward", "# ")

        # Run the test steps
        for step in routing_performance_steps:
            self.extract_ports_cores_config(step['config'])

            resutls_row = [step['kthread_mode'], len(
                self.config['ports']), self.stripped_config_param()]

            self.dut.kill_all()
            self.start_kni()

            # Set up the IP addresses, routes and arp entries of the virtual
            # interfaces
            virtual_interaces = {}
            ip_subnet = 0
            for port in self.config['port_details']:

                port_number = port['port']

                # Get the virtual interfaces base on the number of kernel
                # lcores
                port_virtual_interaces = []
                for i in range(len(port['kernel_cores'])):
                    port_virtual_interaces.append(
                        self.virtual_interface_name(port_number, i))

                virtual_interaces[port_number] = port_virtual_interaces

                # Setup IP, ARP and route for each virtual interface
                for interface in range(len(virtual_interaces[port_number])):
                    tx_port = self.tester.get_local_port(port_number)

                    self.dut.send_expect("ifconfig %s 192.170.%d.1" % (
                        virtual_interaces[port_number][interface], ip_subnet), "# ")
                    self.dut.send_expect(
                        "route add -net 192.170.%d.0  netmask 255.255.255.0 gw 192.170.%d.1" % (ip_subnet, ip_subnet), "# ")
                    self.dut.send_expect("arp -s 192.170.%d.2 %s" %
                                         (ip_subnet, self.tester.get_mac(tx_port)), "# ")
                    ip_subnet += 1

            # Get performance for each frame size
            for packet_size in packet_sizes_routing:
                payload_size = packet_size - 38
                tgen_input = []

                # Test one port
                tx_port = self.tester.get_local_port(self.config['ports'][0])
                rx_mac = self.dut.get_mac_address(self.config['ports'][0])
                self.tester.scapy_append('flows = []')

                self.tester.scapy_append('flows = []')
                port_iterator = 0
                for port in self.config['port_details']:
                    port_number = port['port']

                    rx_mac = self.dut.get_mac_address(port_number)
                    tx_port = self.tester.get_local_port(port_number)

                    num_interfaces_per_port = len(
                        virtual_interaces[port_number])

                    # Set flows from and to virtual interfaces in the same port
                    src_ip_subnet = port_iterator * num_interfaces_per_port
                    for interface in range(len(virtual_interaces[port_number])):
                        dst_ip_subnet = (
                            src_ip_subnet + 1) % num_interfaces_per_port
                        dst_ip_subnet += port_iterator * \
                            num_interfaces_per_port
                        self.tester.scapy_append(
                            'flows.append(Ether(dst="%s")/IP(src="192.170.%d.2",dst="192.170.%d.2")/("X"*%d))' %
                            (rx_mac, src_ip_subnet, dst_ip_subnet, payload_size))
                        src_ip_subnet += 1

                    tgen_input.append((tx_port, tx_port, "routePerf.pcap"))

                self.tester.scapy_append('wrpcap("routePerf.pcap",flows)')
                self.tester.scapy_execute()

                time.sleep(1)
                _, pps = self.tester.traffic_generator_throughput(tgen_input)
                resutls_row.append(float(pps) / 10 ** 6)

            self.result_table_add(resutls_row)

        self.result_table_print()

    def test_perf_routing_without_kni(self):
        """
        Routing performance without KNI.
        """

        header = routing_perf_no_kni_results_header

        for size in packet_sizes_routing:
            header.append("%d Mpps" % size)

        self.result_table_create(header)

        self.dut.kill_all()
        self.dut.send_expect("rmmod rte_kni", "# ", 20)

        self.dut.send_expect("systemctl stop NetworkManager.service", "# ")

        dut_ports = self.dut.get_ports(self.nic)

        white_list = self.make_white_list(self.target, self.nic)
        port_virtual_interaces = []

        for port in white_list:

            # Enables the interfaces
            information = self.dut.send_expect(
                "./usertools/dpdk-devbind.py --status | grep '%s'" % port, "# ")
            print information
            data = information.split(' ')
            for field in data:
                if field.rfind("if=") != -1:
                    interface_aux = field.replace("if=", "")
                    port_virtual_interaces.append(interface_aux)
                    self.dut.send_expect(
                        "ifconfig %s up" % interface_aux, "# ")

        self.dut.send_expect("echo 1 > /proc/sys/net/ipv4/ip_forward", "# ")

        for port in range(0, ports_without_kni):
            tx_port = self.tester.get_local_port(dut_ports[port])
            self.dut.send_expect("ifconfig %s 192.170.%d.1 up" %
                                 (port_virtual_interaces[port], port + 100), "# ")
            self.dut.send_expect(
                "route add -net 192.170.%d.0  netmask 255.255.255.0 gw 192.170.%d.1" % (port + 100, port + 100), "# ")
            self.dut.send_expect("arp -s 192.170.%d.2 %s" %
                                 (port + 100, self.tester.get_mac(tx_port)), "# ")

        one_port_resutls_row = [1]
        two_port_resutls_row = [2]
        for packet_size in packet_sizes_routing:

            payload_size = packet_size - 38
            tgen_input = []

            # Prepare test with 1 port
            tx_port = self.tester.get_local_port(dut_ports[0])
            rx_mac = self.dut.get_mac_address(dut_ports[0])
            self.tester.scapy_append('flows = []')
            self.tester.scapy_append(
                'flows.append(Ether(dst="%s")/IP(src="192.170.100.2",dst="192.170.100.2")/("X"*%d))' % (rx_mac, payload_size))
            self.tester.scapy_append('wrpcap("routePerf_1.pcap",flows)')
            self.tester.scapy_execute()

            tgen_input = []
            tgen_input.append((tx_port, tx_port, "routePerf_1.pcap"))

            # Get throughput with 1 port
            _, pps = self.tester.traffic_generator_throughput(tgen_input)
            one_port_resutls_row.append(float(pps) / 10 ** 6)
            self.result_table_add(one_port_resutls_row)

            # Prepare test with 'ports_without_kni' ports
            self.tester.scapy_append('flows = []')
            for port in range(ports_without_kni):
                rx_mac = self.dut.get_mac_address(dut_ports[port])
                tx_port = self.tester.get_local_port(dut_ports[port])
                self.tester.scapy_append(
                    'flows.append(Ether(dst="%s")/IP(src="192.170.%d.2",dst="192.170.%d.2")/("X"*%d))' %
                    (rx_mac, 100 + port, 100 + (port + 1) % ports_without_kni, payload_size))
                tgen_input.append((tx_port, tx_port, "routePerf.pcap"))

            self.tester.scapy_append(
                'wrpcap("routePerf_%d.pcap",flows)' % ports_without_kni)
            self.tester.scapy_execute()

            # Get throughput with 'ports_without_kni' ports
            _, pps = self.tester.traffic_generator_throughput(tgen_input)
            two_port_resutls_row.append(float(pps) / 10 ** 6)
            self.result_table_add(two_port_resutls_row)

        self.result_table_print()

        for port in white_list:
            self.dut.send_expect(
                "./usertools/dpdk-devbind.py -b %s %s" % (self.drivername, port), "# ")

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
        self.dut.send_expect("rmmod rte_kni", "# ", 10)
