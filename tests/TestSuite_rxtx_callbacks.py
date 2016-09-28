#BSD LICENSE
#
# Copyright(c) 2010-2016 Intel Corporation. All rights reserved.
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
Test Rxtx_Callbacks.
"""
import utils
import string
import time
from test_case import TestCase
from plotting import Plotting
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator

from packet import Packet, sniff_packets, load_sniff_packets


class TestRxtxCallbacks(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        timer prerequistites
        """
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")

        cores = self.dut.get_core_list("1S/2C/1T")
        utils.create_mask(cores)
        
        self.mac = self.dut.get_mac_address(self.dut_ports[0])
        self.path = "./examples/rxtx_callbacks/build/rxtx_callbacks"

        out = self.dut.build_dpdk_apps("./examples/rxtx_callbacks")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_rxtx_callbacks(self):
        cmd = self.path + " -c %s -n %d " % (self.coremask,self.dut.get_memory_channels())
        self.dut.send_expect(cmd,"forwarding packets",60)
         
        self.iface_port0 = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))
        self.iface_port1 = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1]))

        self.inst_port1 = sniff_packets(self.iface_port1)
        self.scapy_send_packet(self.iface_port0)

        out_port1 = self.get_tcpdump_package(self.inst_port1)
        self.verify(self.mac in out_port1, "Wrong: can't get package at %s " % self.inst_port1)

    
    def scapy_send_packet(self,iface):
        """
        Send a packet to port
        """
        self.tester.scapy_append('sendp([Ether(dst="%s")/IP()/UDP()/Raw(\'X\'*18)], iface="%s")' % (self.mac, iface))
        self.tester.scapy_execute()

    def get_tcpdump_package(self,inst):
        pkts = load_sniff_packets(inst)
        dsts = []
        for packet in pkts:
            dst = packet.strip_element_layer2("dst")
            dsts.append(dst)
        return dsts

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()
        time.sleep(2)


    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass

