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
Test keep alive
"""

import string
import time
import re
import utils
from test_case import TestCase
from plotting import Plotting 
from settings import HEADER_SIZE   
from etgen import IxiaPacketGenerator
from packet import Packet, sniff_packets, load_sniff_packets

class TestKeepAlive(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")
        cores = self.dut.get_core_list("1S/4C/1T")
        self.coremask = utils.create_mask(cores)

        self.path = "./examples/l2fwd-keepalive/build/l2fwd-keepalive" 

        # build sample app  
        out = self.dut.build_dpdk_apps("./examples/l2fwd-keepalive")
        self.verify("Error" not in out, "compilation error 1") 
        self.verify("No such file" not in out, "compilation error 2")
         
    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_keep_alive(self):
        """
        Verify netmap compatibility with one port 
        """ 
        cmd = self.path + " -c f -n 4 -- -q 8 -p ffff -K 10"
      
        self.dut.send_expect(cmd,"Port statistics",60)

        self.scapy_send_packet(2000)
        out = self.dut.get_session_output(timeout=10)
        print out
        p = re.compile(r'\d+')
        result = p.findall(out)
        amount = 2000 * len(self.dut_ports)
        self.verify(str(amount) in result, "Wrong: can't get <%s> package")
         
    def scapy_send_packet(self,nu):
        """
        Send a packet to port  
        """
        for i in range(len(self.dut_ports)):
            txport = self.tester.get_local_port(self.dut_ports[i])
            mac = self.dut.get_mac_address(self.dut_ports[i])
            txItf = self.tester.get_interface(txport)
            self.tester.scapy_append('sendp([Ether(dst="%s")/IP()/UDP()/Raw(\'X\'*18)], iface="%s",count=%s)' % (mac,txItf,nu))
            self.tester.scapy_execute()

         
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

