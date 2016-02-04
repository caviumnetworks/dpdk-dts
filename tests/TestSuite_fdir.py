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

"""
DPDK Test suite.

Test 82599 and fortville Flow Director Support in DPDK
"""

import re
import time
import string
from time import sleep
from scapy.utils import struct, socket, PcapWriter

import dts
from etgen import IxiaPacketGenerator
from test_case import TestCase
from settings import HEADER_SIZE
from pmd_output import PmdOutput

import sys
reload(sys)
sys.setdefaultencoding('utf8')
#
#
# Test class.
#


class TestFdir(TestCase, IxiaPacketGenerator):

    #
    #
    # Utility methods and other non-test code.
    #
    ###########################################################################

    def send_and_verify(self, condition, packet):
        """
        Send packages and verify behavior.
        """
        self.tester.scapy_foreground()
        self.tester.scapy_append('sys.path.append("./")')
        self.tester.scapy_append('from sctp import *')
        self.tester.scapy_append(packet)
        self.dut.send_expect("start", "testpmd>")
        self.tester.scapy_execute()
        time.sleep(.5)
        out = self.dut.get_session_output()
        self.dut.send_expect("stop", "testpmd>")

        if(self.nic in ["kawela", "niantic", "fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            if ("fwd" == self.fdir_type):
                if condition:
                    self.queue = 2
                else:
                    self.queue = 0
            elif("drop" == self.fdir_type):
                if condition:
                    self.queue = 0
                else:
                    self.queue = -1

            result_scanner = r"port ([0-9]+)/queue ([0-9]+): received ([0-9]+) packets\s*src=[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2} - dst=[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}:[A-F\d]{2}"
            scanner = re.compile(result_scanner, re.DOTALL)
            m = scanner.search(out)

            print "**************Print sub-case result****************"
            if m:
                m.groups()
                if (self.queue == int(m.group(2))):
                    print dts.GREEN("Pass: queue id is " + m.group(2))
                    self.verify(1, "Pass")
                else:
                    print dts.RED("Fail: queue id is " + m.group(2))
                    self.verify(0, "Fail")
                    print out
            else:
                print "not match"
                if (-1 == self.queue):
                    print dts.GREEN("Pass: fdir should not match ")
                    self.verify(1, "Pass")
                else:
                    print dts.RED("Fail")
                    self.verify(0, "Fail")
                    print out
            print "**************Print sub-case result****************"

    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.

        PMD prerequisites.
        """
        self.tester.extend_external_packet_generator(TestFdir, self)
        #self.verify('bsdapp' not in self.target, "FDIR not support freebsd")
        # this feature support Fortville, Niantic
        #self.verify(self.nic in ["kawela_2", "niantic", "bartonhills", "82545EM",
        #                         "82540EM", "springfountain", "fortville_eagle",
        #                         "fortville_spirit", "fortville_spirit_single"],
        #            "NIC Unsupported: " + str(self.nic))

        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports(self.nic)
        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports for testing")

        # Verify that enough threads are available
        self.all_cores_mask = dts.create_mask(self.dut.get_core_list("all"))
        cores = self.dut.get_core_list("1S/5C/1T")
        self.verify(cores is not None, "Insufficient cores for speed testing")
        self.coreMask = dts.create_mask(cores)
        self.portMask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])
        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])
        self.dut_rx_port = self.tester.get_local_port(self.dut_ports[0])
        self.dut_rx_interface = self.tester.get_interface(self.dut_rx_port)
        self.dut_tx_port = self.tester.get_local_port(self.dut_ports[1])
        self.dut_tx_interface = self.tester.get_interface(self.dut_rx_port)

        self.blacklist = ""

        self.headers_size = HEADER_SIZE['eth'] + HEADER_SIZE[
            'ip'] + HEADER_SIZE['udp']
        self.src_ip = "192.168.1.1"
        self.dst_ip = "192.168.2.1"
        self.default_queue = 2

        # performance test parameter
        # self.frame_sizes = [1500]
        self.frame_sizes = [64, 65, 128, 256, 512, 1024, 1280, 1500]
        self.rxfreet_values = [0, 8, 16, 32, 64, 128]
        """
        self.test_cycles = [{'cores': '1S/1C/1T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/1C/2T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/2C/1T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/2C/2T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/4C/2T', 'Mpps': {}, 'pct': {}}
                            ]
        """
        self.test_cycles = [{'cores': '1S/4C/2T', 'Mpps': {}, 'pct': {}}]

        # Nianatic only support 2bytes payload, Fotville support 16 bytes
        self.flexbytes = [{'length': 2, 'flexbytes': '0x11,0x11', 'payload': '\\x11\\x11'},
                          {'length': 16, 'flexbytes': '0x11,0x11,0x22,0x22,0x33,0x33,0x44,0x44,0x55,0x55,0x66,0x66,0x77,0x77,0x88,0x88', 'payload': '\\x11\\x11\\x22\\x22\\x33\\x33\\x44\\x44\\x55\\x55\\x66\\x66\\x77\\x77\\x88\\x88'}
                          ]

        # self.test_types = ['fdir_2flexbytes']
        self.test_types = ['fdir_disable', 'fdir_enable', 'fdir_noflexbytes', 'fdir_2flexbytes', 'fdir_16flexbytes']
        """
        self.flows= [{"flows":1, "rules":1},
                     {"flows":64, "rules":16},
                     {"flows":64, "rules":512}
                     #{"flows":8192, "rules":8192}
                     ]
        """
        self.flows = [{"flows": 8192, "rules": 8192}]
        # performance report head line
        self.table_header = ['Frame Size']
        for test_cycle in self.test_cycles:
            self.table_header.append("%s Mpps" % test_cycle['cores'])
            self.table_header.append("% linerate")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def fdir_set_rule(self):
        """
        Fdir Performance Benchmarking set rules
        """
        self.dut.send_expect("port stop %s" % self.dut_ports[0], "testpmd>")
        if(self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_flex_payload %s l2 (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)" % self.dut_ports[0], "testpmd>")
            self.dut.send_expect("flow_director_flex_payload %s l3 (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)" % self.dut_ports[0], "testpmd>")
            self.dut.send_expect("flow_director_flex_payload %s l4 (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)" % self.dut_ports[0], "testpmd>")
            self.dut.send_expect("flow_director_flex_mask %s flow all (0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff)" % self.dut_ports[0], "testpmd>")
        elif (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_flex_payload %s raw (12,13)" % self.dut_ports[0], "testpmd>")
            self.dut.send_expect("flow_director_flex_mask %s flow raw (0xff,0xff)" % self.dut_ports[0], "testpmd>")
        self.dut.send_expect("port start %s" % self.dut_ports[0], "testpmd>")

    def fdir_get_flexbytes(self, sctp=False):

        """
        Fdir get flexbytes and payload according NIC
        """

        if(self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            if not sctp:
                self.flexbytes = "0x11,0x11,0x22,0x22,0x33,0x33,0x44,0x44,0x55,0x55,0x66,0x66,0x77,0x77,0x88,0x88"
            else:
                self.flexbytes = '0x0,0x0,0x0,0x20,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0'
            self.payload = "\\x11\\x11\\x22\\x22\\x33\\x33\\x44\\x44\\x55\\x55\\x66\\x66\\x77\\x77\\x88\\x88"
            self.flexlength = 16
        elif (self.nic in ["niantic"]):
            self.flexbytes = "0x00,0x00"
            self.payload = "\\x11\\x11\\x22\\x22\\x33\\x33\\x44\\x44\\x55\\x55\\x66\\x66\\x77\\x77\\x88\\x88"
            self.flexlength = 2

    def test_fdir_noflexword_fwd_ipv4(self):
        """
        FDir signature matching mode.
        """

        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=4 --txq=4 --nb-cores=4  --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        # fwd comand testing
        self.fdir_type = "fwd"

        # ipv4 ip
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"),dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

        # update command only work in niantic
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv4 udp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv4 tcp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv4 sctp
        self.fdir_get_flexbytes(sctp=True)
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.fdir_get_flexbytes()

        # ipv4 frag
        # ip-frag only support in fortville
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"),dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_noflexword_fwd_ipv6(self):
        """
        FDir signature matching mode.
        """

        self.dut.kill_all()
        if self.nic in ["niantic"]:
            # Niantic ipv6 only support signature mode
            self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=4 --txq=4 --nb-cores=4  --nb-ports=1 --pkt-filter-mode=signature" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        elif self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]:
            # Fortville ipv6 support perfect mode
            self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=4 --txq=4 --nb-cores=4  --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        # fwd comand testing
        self.fdir_type = "fwd"

        # ipv6 ip
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv6 udp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv6 tcp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        #ipv6 sctp
        self.fdir_get_flexbytes(sctp=True)
        self.dut.send_expect("flow_director_filter 0 mode IP  add flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d "%(2,1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter 0 mode IP  del flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d "%(2,1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter 0 mode IP  add flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d "%(1,1), "testpmd>")
            self.dut.send_expect("flow_director_filter 0 mode IP  update flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d "%(2,1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter 0 mode IP  del flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () fwd pf queue %d fd_id %d "%(2,1), "testpmd>")
        self.fdir_get_flexbytes()

        # ipv6 frag
        # ip-frag only support in fortville
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_noflexword_drop_ipv4(self):
        # drop command testing
        self.dut.kill_all()
        self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=4 --txq=4 --nb-cores=4  --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        # fwd comand testing
        self.fdir_type = "drop"

        # ipv4 ip
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv4 udp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv4 tcp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")

        # ipv4 sctp
        self.fdir_get_flexbytes(sctp=True)
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        self.fdir_get_flexbytes()

        # ipv4 frag
        # ip-frag only support in fortville
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"),dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_noflexword_drop_ipv6(self):
        # drop not support signature mode, niantic only can work in signature  mode with ipv6
        # Niantic is not support in drop ipv6
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]:
            # drop command testing
            self.dut.kill_all()

            self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=4 --txq=4 --nb-cores=4  --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
            self.dut.send_expect("set verbose 1", "testpmd>")
            self.dut.send_expect("set fwd rxonly", "testpmd>")

            # fwd comand testing
            self.fdir_type = "drop"

            # ipv6 ip
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

            # ipv6 udp
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

            # ipv6 tcp
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

            # ipv6 sctp
            self.fdir_get_flexbytes(sctp=True)
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d "%(self.dut_ports[0],2,1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d "%(self.dut_ports[0],2,1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            if (self.nic in ["niantic"]):
                self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d "%(self.dut_ports[0],1,1), "testpmd>")
                self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d "%(self.dut_ports[0],2,1), "testpmd>")
                self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
                self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes () drop pf queue %d fd_id %d "%(self.dut_ports[0],2,1), "testpmd>")
            self.fdir_get_flexbytes()

            # ipv6 frag
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes () drop pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="X"*46)], iface="%s")' % (self.dut_rx_interface, self.dut_rx_interface))

            self.dut.send_expect("quit", "# ", 30)

    def test_fdir_flexword_fwd_ipv4(self):
        """
        FDir signature matching mode.
        """
        # fwd comand testing
        self.fdir_type = "fwd"

        self.dut.kill_all()
        # fwd testing with flexword
        self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss --rxq=4 --txq=4 --nb-cores=4 --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        self.fdir_set_rule()
        self.fdir_get_flexbytes()

        # ipv4 ip
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"),dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")

        # ipv4 udp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")

        # ipv4 tcp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")

        # ipv4 frag
        # ip-frag only support fortville
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"),dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

        # ipv4 sctp
        self.fdir_get_flexbytes(sctp=True)
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 2, 1), "testpmd>")
        self.fdir_get_flexbytes()

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_flexword_fwd_ipv6(self):
        """
        FDir signature matching mode.
        """
        # fwd comand testing
        self.fdir_type = "fwd"

        self.dut.kill_all()
        # fwd testing with flexword
        if self.nic in ["niantic"]:
            # Niantic ipv6 only support signature mode
            self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=4 --txq=4 --nb-cores=4  --nb-ports=1 --pkt-filter-mode=signature" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        elif self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]:
            # fortville ipv6 support perfect mode
            self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss --rxq=4 --txq=4 --nb-cores=4 --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        self.fdir_set_rule()
        self.fdir_get_flexbytes()

        # ipv6 ip
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")

        # ipv6 udp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")

        # ipv6 tcp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 1, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        #ipv6 sctp
        self.fdir_get_flexbytes(sctp=True)
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes,2,1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes,2,1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        if (self.nic in ["niantic"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes,1,1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  update flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes,2,1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=132)/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-sctp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 verify_tag 1 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes,2,1), "testpmd>")
        self.fdir_get_flexbytes()

        # ipv6 frag
        # ip-frag only support fortville
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_flexword_drop_ipv4(self):

        # drop testing with flexword
        self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss --rxq=4 --txq=4 --nb-cores=4 --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        self.fdir_set_rule()
        self.fdir_get_flexbytes()
        # fwd comand testing
        self.fdir_type = "drop"

        # ipv4 ip
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

        # ipv4 udp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-udp src 192.168.0.1 1024 dst 192.168.0.2 1024 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

        # ipv4 tcp
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-tcp src 192.168.0.1 32 dst 192.168.0.2 32 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

        # ipv4 sctp
        self.fdir_get_flexbytes(sctp=True)
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-sctp src 192.168.0.1 32 dst 192.168.0.2 32 verify_tag 1 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d "%(self.dut_ports[0],self.flexbytes, 2, 1), "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=32, dport=32, tag=1)/SCTPChunkData(data="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
        self.fdir_get_flexbytes()

        # ipv4 frag
        # ip-frag only support fortville
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv4-frag src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"),dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2", frag=1, flags="MF")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_flexword_drop_ipv6(self):
        # drop not support signature mode, niantic only can work in signature  mode with ipv6
        # Niantic is not support in drop ipv6
        if (self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]):
            # drop testing with flexword
            self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss --rxq=4 --txq=4 --nb-cores=4 --nb-ports=1 --pkt-filter-mode=perfect" % (self.target, self.coreMask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)
            self.dut.send_expect("set verbose 1", "testpmd>")
            self.dut.send_expect("set fwd rxonly", "testpmd>")

            self.fdir_set_rule()
            self.fdir_get_flexbytes()
            # fwd comand testing
            self.fdir_type = "drop"

            # ipv6 ip
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

            # ipv6 udp
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-udp src FE80:0:0:0:200:1FF:FE00:200 1024 dst 3555:5555:6666:6666:7777:7777:8888:8888 1024 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1024,dport=1024)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

            # ipv6 tcp
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-tcp src FE80:0:0:0:200:1FF:FE00:200 32 dst 3555:5555:6666:6666:7777:7777:8888:8888 32 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=32,dport=32)/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

            # ipv6 frag
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-other src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 3, 1), "testpmd>")
            self.dut.send_expect("flow_director_filter %s mode IP  del flow ipv6-frag src FE80:0:0:0:200:1FF:FE00:200 dst 3555:5555:6666:6666:7777:7777:8888:8888 vlan 0 flexbytes (%s) drop pf queue %d fd_id %d " % (self.dut_ports[0], self.flexbytes, 2, 1), "testpmd>")
            self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888", nh=44)/IPv6ExtHdrFragment()/Raw(load="%s")], iface="%s")' % (self.dut_rx_interface, self.payload, self.dut_rx_interface))

            self.dut.send_expect("quit", "# ", 30)

    def failed_test_fdir_flush(self):
        """
        FDir flush in Fortville.
        """

        self.dut.kill_all()

        self.dut.send_expect("./%s/app/testpmd -c %s -n 4 -- -i --portmask=%s --disable-rss  --rxq=8 --txq=8 --nb-cores=16 --nb-ports=2  --pkt-filter-mode=perfect" % (self.target, self.all_cores_mask, dts.create_mask([self.dut_ports[0]])), "testpmd>", 120)

        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")

        # set up a fdir rule and check guarant_count
        self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src 192.168.0.1 dst 192.168.0.2 vlan 0 flexbytes () fwd pf queue %d fd_id %d " % (self.dut_ports[0], 2, 1), "testpmd>")
        out = self.dut.send_expect("show port fdir all", "testpmd>")
        result_scanner = r"guarant_count: 1"
        scanner = re.compile(result_scanner, re.DOTALL)
        m = scanner.search(out)
        if m:
            self.verify(1, "Pass")
        else:
            self.verify(0, "Fail")

        # flush all fdir rule and check guarant_count
        out = self.dut.send_expect("flush_flow_director %s" % self.dut_ports[0], "testpmd>")
        result_scanner = r"guarant_count: 1"
        scanner = re.compile(result_scanner, re.DOTALL)
        m = scanner.search(out)
        if m:
            self.verify(0, "Fail")
        else:
            self.verify(1, "Pass")

    def increment_ip_address(self, addr, val):
        """
        Returns the IP address from a given one, like
        192.168.1.1 ->193.168.1.1
        If disable ip hw chksum, csum routine will increase ip
        """
        ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
        x = ip2int(addr)
        int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
        return int2ip(x + 1)

    def fdir_perf_set_rules(self, num_rules):

        src_ip_temp = self.src_ip
        dst_ip_temp = self.dst_ip
        for i in range(num_rules):
            src_ip_temp = self.increment_ip_address(src_ip_temp, 1)
            dst_ip_temp = self.increment_ip_address(dst_ip_temp, 1)
            self.dut.send_expect("flow_director_filter %s mode IP  add flow ipv4-other src %s  dst %s vlan 0 flexbytes (%s) fwd pf queue %d fd_id %d " % (self.dut_ports[0], src_ip_temp, dst_ip_temp, self.flexbytes, i % self.queue, i), "testpmd>")

    def fdir_perf_set_flows(self, num_flows, frame_size):
        """
        Fdir Performance Benchmarking set Ixia flows
        """
        flows = []
        src_ip_temp = self.src_ip
        dst_ip_temp = self.dst_ip
        print "*src_ip_temp = " + src_ip_temp + "dst_ip_temp = " + dst_ip_temp
        flows.append('Ether(src="52:00:00:00:00:00", dst="00:1B:21:8E:B2:30")/IP(src="%s",dst="%s")/UDP(sport=%d,dport=%d)/Raw(load="%s" + "X"*(%d - 42 - %d))' % (src_ip_temp, dst_ip_temp, 1021, 1021, self.payload, frame_size, self.flexlength))
        self.tester.scapy_append('wrpcap("test.pcap", [%s])' % string.join(flows, ','))

    def perf_fdir_performance_2ports(self, test_type, num_rules, num_flows):
        """
        fdir Performance Benchmarking with 2 ports.
        """
        # prepare traffic generator input
        tgen_input = []

        tgen_input.append((self.tester.get_local_port(self.dut_ports[0]),
                          self.tester.get_local_port(self.dut_ports[1]),
                          "test.pcap"))
        tgen_input.append((self.tester.get_local_port(self.dut_ports[1]),
                          self.tester.get_local_port(self.dut_ports[0]),
                          "test.pcap"))

        print "self.ports_socket=%s" % (self.ports_socket)
        # run testpmd for each core config
        for test_cycle in self.test_cycles:
            print "******************test cycles*********************\n"
            core_config = test_cycle['cores']

            core_list = self.dut.get_core_list(core_config, socket=self.ports_socket)

            if len(core_list) > 2:
                self.queues = len(core_list) / 2
            else:
                self.queues = 1

            core_mask = dts.create_mask(core_list)
            port_mask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])

            if test_type == "fdir_disable":
                command_line = "./%s/app/testpmd -c 0xff00ff -n %d -- -i --rxq=2 --txq=2  --rxd=512 --txd=512 --burst=32 --rxfreet=64 --txfreet=64 --mbcache=256 \
                --portmask=%s --nb-cores=4 --nb-ports=2 --rss-ip\
                " % (self.target, self.dut.get_memory_channels(), port_mask)
            else:
                command_line = "./%s/app/testpmd -c 0xff00ff -n %d -- -i --rxq=2 --txq=2  --rxd=512 --txd=512 --burst=32 --rxfreet=64 --txfreet=64 --mbcache=256 \
                --portmask=%s --nb-cores=4 --nb-ports=2 --rss-ip\
                --pkt-filter-mode=perfect" % (self.target, self.dut.get_memory_channels(), port_mask)

            info = "Executing PMD using %s\n" % test_cycle['cores']
            self.logger.info(info)
            dts.report(info, annex=True)
            dts.report(command_line + "\n\n", frame=True, annex=True)

            out = self.dut.send_expect(command_line, "testpmd> ", 100)
            print out

            self.dut.send_expect("set verbose 1", "testpmd>")
            self.fdir_get_flexbytes()

            if test_type in ["fdir_noflex", "fdir_2flex", "fdir_16flex"]:
                self.fdir_set_rule()
                self.fdir_perf_set_rules(num_rules)
            out = self.dut.send_expect("start", "testpmd> ")
            print out
            for frame_size in self.frame_sizes:
                print "******************frame size = %d*********************\n" % (frame_size)
                wirespeed = self.wirespeed(self.nic, frame_size, 2)
                # create pcap file
                self.logger.info("Running with frame size %d " % frame_size)
                self.fdir_perf_set_flows(num_flows, frame_size)

                self.tester.scapy_execute()

                """
                tgen_input.append([self.tester.get_local_port(self.dut_ports[0]),
                          self.tester.get_local_port(self.dut_ports[1]),
                          "test.pcap", (512.00 / wirespeed * 100.00), 1])
                tgen_input.append([self.tester.get_local_port(self.dut_ports[1]),
                          self.tester.get_local_port(self.dut_ports[0]),
                          "test.pcap", (512.00 / wirespeed * 100.00), 1])
                """

                """
                # create pcap file
                self.logger.info("Running with frame size %d " % frame_size)
                self.fdir_perf_set_flows(num_flows, frame_size)

                self.tester.scapy_execute()
                """

                # run traffic generator
                _, pps = self.tester.traffic_generator_throughput(tgen_input)
                """
                _, pps, _ = self.throughputRate(tgen_input)
                """

                out = self.dut.send_expect("show port stats all", "testpmd> ")
                print out

                pps /= 1000000.0
                test_cycle['Mpps'][frame_size] = pps
                test_cycle['pct'][frame_size] = pps * 100 / wirespeed

            self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("quit", "# ", 30)
            sleep(5)

        for n in range(len(self.test_cycles)):
            for frame_size in self.frame_sizes:
                self.verify(self.test_cycles[n]['Mpps'][
                            frame_size] > 0, "No traffic detected")

        # Print results
        dts.results_table_add_header(self.table_header)
        for frame_size in self.frame_sizes:
            table_row = [frame_size]
            for test_cycle in self.test_cycles:
                table_row.append(test_cycle['Mpps'][frame_size])
                table_row.append(test_cycle['pct'][frame_size])

            dts.results_table_add_row(table_row)

        dts.results_table_print()

    def ip(self, port, frag, src, proto, tos, dst, chksum, len, version, flags, ihl, ttl, id, options=None):
        """
        Configure IP protocal.
        """
        self.add_tcl_cmd("protocol config -name ip")
        self.add_tcl_cmd('ip config -sourceIpAddr "%s"' % src)
        self.add_tcl_cmd("ip config -sourceIpAddrMode ipIncrHost")
        self.add_tcl_cmd("ip config -sourceIpAddrRepeatCount 64")
        self.add_tcl_cmd('ip config -destIpAddr "%s"' % dst)
        self.add_tcl_cmd("ip config -destIpAddrMode ipIncrHost")
        self.add_tcl_cmd("ip config -destIpAddrRepeatCount 64")
        self.add_tcl_cmd("ip config -ttl %d" % ttl)
        self.add_tcl_cmd("ip config -totalLength %d" % len)
        self.add_tcl_cmd("ip config -fragment %d" % frag)
        # self.add_tcl_cmd("ip config -ipProtocol %d" % proto)
        self.add_tcl_cmd("ip config -ipProtocol ipV4ProtocolReserved255")
        self.add_tcl_cmd("ip config -identifier %d" % id)
        self.add_tcl_cmd("stream config -framesize %d" % (len + 18))
        self.add_tcl_cmd("ip set %d %d %d" % (self.chasId, port['card'], port['port']))

    def test_perf_fdir_performance_2ports(self):
        """
        fdir Performance Benchmarking with 2 ports.
        """
        for test_type in self.test_types:
            print "***************\n"
            print test_type
            print "***************\n"
            if test_type in ["fdir_enable", "fdir_disable"]:
                num_rules = 0
                num_flows = 64
                print "************%d rules/%d flows********************" % (num_rules, num_flows)
                self.perf_fdir_performance_2ports(test_type, num_rules, num_flows)
            elif test_type in ["fdir_noflexbytes", "fdir_2flexbytes", "fdir_16flexbytes"]:
                for flows in self.flows:
                    num_rules = flows["rules"]
                    num_flows = flows["flows"]
                    print "************%d rules/%d flows********************" % (num_rules, num_flows)
                    self.perf_fdir_performance_2ports(test_type, num_rules, num_flows)

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
