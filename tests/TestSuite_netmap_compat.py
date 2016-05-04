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
Test Netmap_compat.
"""

import dts
import string
import time
import re
from test_case import TestCase
from plotting import Plotting 
from settings import HEADER_SIZE   
from etgen import IxiaPacketGenerator
from packet import Packet, sniff_packets, load_sniff_packets

class TestNetmapCompat(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")
        cores = self.dut.get_core_list("1S/4C/1T")
        self.coremask = dts.create_mask(cores)

        self.path = "./examples/netmap_compat/build/bridge" 

        # build sample app  
        out = self.dut.build_dpdk_apps("./examples/netmap_compat")
        self.verify("Error" not in out, "compilation error 1") 
        self.verify("No such file" not in out, "compilation error 2")
         
    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_netmap_compat_oneport(self):
        """
        Verify netmap compatibility with one port 
        """ 
        cmd = self.path + " -c %s -n %d -- -i %s" % (self.coremask,self.dut.get_memory_channels(),self.dut_ports[0])
      
        #start netmap_compat with one port
        self.dut.send_expect(cmd,"Port %s now in Netmap mode" % self.dut_ports[0],60)

        self.rxItf = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))

        self.inst = sniff_packets(self.rxItf)

        self.scapy_send_packet()

        out = self.get_tcpdump_package()
        mac = self.dut.get_mac_address(self.dut_ports[0])
        self.verify(mac in out, "Wrong: can't get <%s> package" % mac)
         
    def test_netmap_compat_twoport(self):
        """
        Verify netmap compatibility with two port
        """
        cmd = self.path + " -c %s -n %d -- -i %s -i %s" % (self.coremask,self.dut.get_memory_channels(),self.dut_ports[0],self.dut_ports[1])

        #start netmap_compat with two port
        self.dut.send_expect(cmd,"Port %s now in Netmap mode" % self.dut_ports[0], 60)
       
        self.rxItf = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1]))
        self.inst = sniff_packets(self.rxItf)

        self.scapy_send_packet()

        out = self.get_tcpdump_package()
        mac = self.dut.get_mac_address(self.dut_ports[0])
        self.verify(mac in out, "Wrong: can't get <%s> package" % mac)
    def scapy_send_packet(self):
        """
        Send a packet to port  
        """
        txport = self.tester.get_local_port(self.dut_ports[0])
        mac = self.dut.get_mac_address(self.dut_ports[0])
        txItf = self.tester.get_interface(txport)
        self.tester.scapy_append('sendp([Ether(dst="%s")/IP()/UDP()/Raw(\'X\'*18)], iface="%s")' % (mac, txItf))
        self.tester.scapy_execute()


    def get_tcpdump_package(self):  
        pkts = load_sniff_packets(self.inst)
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
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass

