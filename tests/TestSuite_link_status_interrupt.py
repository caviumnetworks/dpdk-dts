# BSD LICENSE
#
# Copyright(c) 2010-2017 Intel Corporation. All rights reserved.
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
Test link status.
"""

import utils
import string
import time
import re
from test_case import TestCase
from packet import Packet, sniff_packets, load_sniff_packets


class TestLinkStatusInterrupt(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")
        cores = self.dut.get_core_list("1S/4C/1T")
        self.coremask = utils.create_mask(cores)
        self.portmask = utils.create_mask(self.dut_ports)

        self.path = "./examples/link_status_interrupt/build/link_status_interrupt"

        # build sample app
        out = self.dut.build_dpdk_apps("./examples/link_status_interrupt")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def set_link_status_and_verify(self, dutPort, status):
        """
        set link status verify results
        """
        self.intf = self.tester.get_interface(
            self.tester.get_local_port(dutPort))
        self.tester.send_expect("ifconfig %s %s" %
                                (self.intf, status.lower()), "# ", 10)
        verify_point = "Port %s Link %s" % (dutPort, status)
        self.dut.send_expect("", verify_point, 60)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_link_status_interrupt_change(self):
        """
        Verify Link status change  
        """
        if self.drivername == "igb_uio":
            cmdline = self.path + " -c %s -n %s -- -p %s " % (
                self.coremask, self.dut.get_memory_channels(), self.portmask)
            for mode in ["legacy", "msix"]:
                self.dut.send_expect("rmmod -f igb_uio", "#", 20)
                self.dut.send_expect(
                    'insmod %s/kmod/igb_uio.ko "intr_mode=%s"' % (self.target, mode), "# ")
                self.dut.bind_interfaces_linux()
                self.dut.send_expect(cmdline, "Aggregate statistics", 60)
                self.set_link_status_and_verify(self.dut_ports[0], 'Down')
                self.set_link_status_and_verify(self.dut_ports[0], 'Up')
                self.dut.send_expect("^C", "#", 60)
        elif self.drivername == "vfio-pci":
            for mode in ["legacy", "msi", "msix"]:
                cmdline = self.path + " -c %s -n %s --vfio-intr=%s -- -p %s" % (
                    self.coremask, self.dut.get_memory_channels(), mode, self.portmask)
                self.dut.send_expect(cmdline, "Aggregate statistics", 60)
                self.set_link_status_and_verify(self.dut_ports[0], 'Down')
                self.set_link_status_and_verify(self.dut_ports[0], 'Up')
                self.dut.send_expect("^C", "#", 60)

    def test_link_status_interrupt_port_available(self):
        """
        interrupt all port link, then link them,
        sent packet, check packets received.
        """
        if self.drivername == "igb_uio":
            cmdline = self.path + " -c %s -n %s -- -p %s " % (
                self.coremask, self.dut.get_memory_channels(), self.portmask)
            for mode in ["legacy", "msix"]:
                self.dut.send_expect("rmmod -f igb_uio", "#", 20)
                self.dut.send_expect(
                    'insmod %s/kmod/igb_uio.ko "intr_mode=%s"' % (self.target, mode), "# ")
                self.dut.bind_interfaces_linux()
                self.dut.send_expect(cmdline, "Aggregate statistics", 60)
                for port in self.dut_ports:
                    self.set_link_status_and_verify(
                        self.dut_ports[port], 'Down')
                time.sleep(10)
                for port in self.dut_ports:
                    self.set_link_status_and_verify(self.dut_ports[port], 'Up')
                self.scapy_send_packet(1)
                out = self.dut.get_session_output(timeout=60)
                pkt_send = re.findall("Total packets sent:\s*(\d*)", out)
                pkt_received = re.findall(
                    "Total packets received:\s*(\d*)", out)
                self.verify(pkt_send == pkt_received == '1',
                            "Error: sent packets != received packets")
                self.dut.send_expect("^C", "#", 60)
        elif self.drivername == "vfio-pci":
            for mode in ["legacy", "msi", "msix"]:
                cmdline = self.path + " -c %s -n %s --vfio-intr=%s -- -p %s" % (
                    self.coremask, self.dut.get_memory_channels(), mode, self.portmask)
                self.dut.send_expect(cmdline, "Aggregate statistics", 60)
                for port in self.dut_ports:
                    self.set_link_status_and_verify(
                        self.dut_ports[port], 'Down')
                time.sleep(10)
                for port in self.dut_ports:
                    self.set_link_status_and_verify(self.dut_ports[port], 'Up')
                self.scapy_send_packet(1)
                out = self.dut.get_session_output(timeout=60)
                pkt_send = re.findall("Total packets sent:\s*(\d*)", out)
                pkt_received = re.findall(
                    "Total packets received:\s*(\d*)", out)
                self.verify(pkt_send == pkt_received == '1',
                            "Error: sent packets != received packets")
                self.dut.send_expect("^C", "#", 60)

    def scapy_send_packet(self, num=1):
        """
        Send a packet to port
        """
        self.dmac = self.dut.get_mac_address(self.dut_ports[0])
        txport = self.tester.get_local_port(self.dut_ports[0])
        self.txItf = self.tester.get_interface(txport)
        pkt = Packet(pkt_type='UDP')
        pkt.config_layer('ether', {'dst': self.dmac})
        pkt.send_pkt(tx_port=self.txItf, count=num)

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()
        time.sleep(2)
        for port in self.dut_ports:
            intf = self.tester.get_interface(self.tester.get_local_port(port))
            self.tester.send_expect("ifconfig %s up" % intf, "# ", 10)

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
