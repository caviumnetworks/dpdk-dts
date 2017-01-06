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
Test port hot plug.
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

class TestPortHotPlug(TestCase):
    """
    This feature only supports igb_uio now and not support freebsd
    """
    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")
        cores = self.dut.get_core_list("1S/4C/1T")
        self.coremask = utils.create_mask(cores)
        self.port = len(self.dut_ports) - 1

    def set_up(self):
        """
        Run before each test case.
        """
        self.dut.send_expect("./usertools/dpdk-devbind.py -u %s" % self.dut.ports_info[self.port]['pci'],"#",60)

    def attach(self, port):
        """
        attach port
        """
        self.dut.send_expect("port attach %s" % self.dut.ports_info[port]['pci'],"is attached",60)
        self.dut.send_expect("port start %s" % port,"Link Up",60)
        self.dut.send_expect("show port info %s" % port,"testpmd>",60)

    def detach(self, port):
        """
        detach port 
        """
        self.dut.send_expect("port stop %s" % port,"Link Down",60)
        self.dut.send_expect("port close %s" % port,"Closing ports...",60)
        self.dut.send_expect("port detach %s" % port,"is detached",60)

    def test_after_attach(self):
        """
        first run testpmd after attach port
        """
        cmd = "./x86_64-native-linuxapp-gcc/app/testpmd -c %s -n %s -- -i" % (self.coremask,self.dut.get_memory_channels())
        self.dut.send_expect(cmd,"testpmd>",60)
        session_secondary = self.dut.new_session()
        session_secondary.send_expect("./tools/dpdk-devbind.py --bind=igb_uio %s" % self.dut.ports_info[self.port]['pci'], "#", 60)
        self.dut.close_session(session_secondary)
        self.attach(self.port)
        self.dut.send_expect("start","testpmd>",60)
        self.dut.send_expect("port detach %s" % self.port,"Please close port first",60)
        self.dut.send_expect("stop","testpmd>",60)
        self.detach(self.port)
        self.attach(self.port)
   
        self.dut.send_expect("start","testpmd>",60)
        self.dut.send_expect("port detach %s" % self.port,"Please close port first",60)
        self.send_packet(self.port)
        out = self.dut.send_expect("show port stats %s" % self.port ,"testpmd>",60)
        packet = re.search("RX-packets:\s*(\d*)",out)
        sum_packet = packet.group(1)
        self.verify(sum_packet = 1, "Insufficient the received package")
        self.dut.send_expect("quit","#",60)
     
    def send_packet(self, port):
        """
        Send a packet to port
        """
        self.dmac = self.dut.get_mac_address(self.dut_ports[0])
        txport = self.tester.get_local_port(self.dut_ports[0])
        self.txItf = self.tester.get_interface(txport)
        pkt = Packet(pkt_type='UDP')
        pkt.config_layer('ether', {'dst': self.dmac,})
        pkt.send_pkt(tx_port=self.txItf)
                       
    def test_before_attach(self):
        """
        first attach port after run testpmd
        """
        session_secondary = self.dut.new_session()
        session_secondary.send_expect("./usertools/dpdk-devbind.py --bind=igb_uio %s" % self.dut.ports_info[self.port]['pci'], "#", 60)
        self.dut.close_session(session_secondary)
        cmd = "./x86_64-native-linuxapp-gcc/app/testpmd -c %s -n %s -- -i" % (self.coremask,self.dut.get_memory_channels())
        self.dut.send_expect(cmd,"testpmd>",60)
        self.detach(self.port)
        self.attach(self.port)
        self.dut.send_expect("start","testpmd>",60)
        self.dut.send_expect("port detach %s" % self.port, "Please close port first",60)
        self.send_packet(self.port)
        out = self.dut.send_expect("show port stats %s" % self.port ,"testpmd>",60)
        packet = re.search("RX-packets:\s*(\d*)",out)
        sum_packet = packet.group(1)
        self.verify(sum_packet = 1, "Insufficient the received package")
        self.dut.send_expect("quit","#",60)


    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.send_expect("./usertools/dpdk-devbind.py --bind=igb_uio %s" % self.dut.ports_info[self.port]['pci'],"#",60)
        self.dut.kill_all()
        time.sleep(2)
        

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass

