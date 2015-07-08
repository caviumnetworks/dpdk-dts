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

Test the support of VLAN Offload Features by Poll Mode Drivers.

"""

import dts
import time


from test_case import TestCase
from pmd_output import PmdOutput


class TestVlan(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Vlan Prerequistites
        """
        global dutRxPortId
        global dutTxPortId

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports()

        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports")

        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        dutRxPortId = valports[0]
        dutTxPortId = valports[1]
        portMask = dts.create_mask(valports[:2])

        self.pmdout = PmdOutput(self.dut)
        self.pmdout.start_testpmd("all", "--portmask=%s" % portMask )

        self.dut.send_expect("set verbose 1", "testpmd> ")
        out = self.dut.send_expect("set fwd mac", "testpmd> ")

        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "redrockcanyou"]:
            self.dut.send_expect("set promisc all off", "testpmd> ")
            self.dut.send_expect("vlan set filter on %s"%dutRxPortId, "testpmd> ")

        self.dut.send_expect("vlan set strip off %s" % dutRxPortId, "testpmd> ")
        self.verify('Set mac packet forwarding mode' in out, "set fwd rxonly error")
        self.vlan = 51
    
    def start_tcpdump(self):
        port = self.tester.get_local_port(dutTxPortId)
        rxItf = self.tester.get_interface(port)

        self.tester.send_expect("rm -rf ./vlan_test.cap","#")
        self.tester.send_expect("tcpdump -i %s -w ./vlan_test.cap 2> /dev/null& "%rxItf,"#" )
    
    def get_tcpdump_package(self):
        self.tester.send_expect("killall tcpdump","#")
        return self.tester.send_expect("tcpdump -nn -e -v -r ./vlan_test.cap","#")
    def vlan_send_packet(self, vid, num=1):
        """
        Send $num of packet to portid
        """
        # The package stream : testTxPort->dutRxPort->dutTxport->testRxPort
        port = self.tester.get_local_port(dutRxPortId)
        txItf = self.tester.get_interface(port)
        self.smac = self.tester.get_mac(port)

        port = self.tester.get_local_port(dutTxPortId)
        rxItf = self.tester.get_interface(port)

        # the package dect mac must is dut tx port id when the port promisc is off
        self.dmac = self.dut.get_mac_address(dutRxPortId)

        # FIXME  send a burst with only num packet

        self.tester.scapy_append('sendp([Ether(src="%s",dst="%s")/Dot1Q(vlan=%s)/IP(len=46)], iface="%s")' % (self.smac, self.dmac, vid, txItf))

        self.tester.scapy_execute()
    def set_up(self):
        """
        Run before each test case.
        """
        pass
    def test_vlan_enable_receipt(self):
        """
        Enable receipt of VLAN packets
        """

        if self.nic == "redrockcanyou" :
            print dts.RED("fm10k not support this case\n")
            return
        self.dut.send_expect("rx_vlan add %d %s" % (self.vlan, dutRxPortId), "testpmd> ")
        self.dut.send_expect("vlan set strip off  %s" % dutRxPortId, "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ", 20)
        
        self.start_tcpdump()
        self.vlan_send_packet(self.vlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %d" % self.vlan in out, "Wrong vlan:" + out)

        self.dut.send_expect("stop", "testpmd> ")


    def test_vlan_disable_receipt(self):
        """
        Disable receipt of VLAN packets
        """


        self.dut.send_expect("rx_vlan rm %d %s" % (self.vlan, dutRxPortId), "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.start_tcpdump()
        self.vlan_send_packet(self.vlan)

        out = self.get_tcpdump_package()
        # fm10k switch will redirect package if not send to nic
        if (not((self.nic == "redrockcanyou") and ("%s > %s"%(self.smac, self.dmac) in out))):
            self.verify("vlan %d" % self.vlan not in out, "Wrong vlan:" + out)

        out = self.dut.send_expect("stop", "testpmd> ")


    def test_vlan_strip_config_on(self):

        self.dut.send_expect("vlan set strip on %s" % dutRxPortId, "testpmd> ", 20)
        self.dut.send_expect("rx_vlan add %d %s" % (self.vlan, dutRxPortId), "testpmd> ", 20)
        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ", 20)
        self.verify("strip on" in out, "Wrong strip:" + out)

        self.dut.send_expect("start", "testpmd> ", 120)
        self.start_tcpdump()
        self.vlan_send_packet(self.vlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %d" % self.vlan not in out, "Wrong vlan:" + out)
        out = self.dut.send_expect("quit", "#", 120)

    def test_vlan_strip_config_off(self):

        if self.nic == "redrockcanyou" :
            print dts.RED("fm10k not support this case\n")
            return
        self.dut.send_expect("vlan set strip off %s" % dutRxPortId, "testpmd> ", 20)
        self.dut.send_expect("rx_vlan add %d %s" % (self.vlan, dutRxPortId), "testpmd> ", 20)
        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ", 20)
        self.verify("strip off" in out, "Wrong strip:" + out)
        self.dut.send_expect("set nbport 2", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.start_tcpdump()
        self.vlan_send_packet(self.vlan)
        out = self.get_tcpdump_package()
        self.verify("vlan %d" % self.vlan in out, "Wrong strip vlan:" + out)
        out = self.dut.send_expect("stop", "testpmd> ", 120)

    def test_vlan_enable_vlan_insertion(self):
        """
        Enable VLAN header insertion in transmitted packets
        """

        port = self.tester.get_local_port(dutTxPortId,)
        intf = self.tester.get_interface(port)

        self.dut.send_expect("set nbport 2", "testpmd> ")
        self.dut.send_expect("tx_vlan set %d %s" % (self.vlan, dutTxPortId), "testpmd> ")

        self.tester.scapy_background()
        self.tester.scapy_append('p = sniff(iface="%s", count=1, timeout=5)' % intf)
        self.tester.scapy_append('RESULT=str(p)')
        self.tester.scapy_foreground()

        self.tester.scapy_execute()
        time.sleep(2)
        self.dut.send_expect("start tx_first", "testpmd> ")
        time.sleep(2)

        out = self.tester.scapy_get_result()
        self.verify("vlan=%dL" % self.vlan in out, "Wrong vlan: " + out)
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "redrockcanyou"]:
            self.dut.send_expect("tx_vlan reset %s" % dutTxPortId, "testpmd> ", 30)
            self.dut.send_expect("stop", "testpmd> ", 30)
        else:
            self.dut.send_expect("quit", "# ", 30)

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
