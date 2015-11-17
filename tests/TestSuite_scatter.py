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
Test Scattered Packets.
"""
import dts
from test_case import TestCase
from pmd_output import PmdOutput
import time
#
#
# Test class.
#
class TestScatter(TestCase):
    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.
        Scatter Prerequistites
        """
        dutPorts = self.dut.get_ports(self.nic)
        # Verify that enough ports are available
        self.verify(len(dutPorts) >= 2, "Insufficient ports")
        self.pmdout = PmdOutput(self.dut)
        if self.nic in ["niantic", "sageville", "fortpark", "fortville_eagle", "fortville_spirit", "fortville_spirit_single", "redrockcanyou", "ironpond", "twinpond", "springfountain"]:
            self.mbsize = 2048
        else:
            self.mbsize = 1024

    def start_tcpdump(self, tester_rx_intf):
        self.tester.send_expect("rm -rf ./scatter.cap", "#")
        self.tester.send_expect("tcpdump -i %s -x -w ./scatter.cap 2>/dev/null &" % tester_rx_intf, "#")

    def get_tcpdump_packet(self):
        self.tester.send_expect("killall tcpdump", "#")
        return self.tester.send_expect("tcpdump -nn -x -r ./scatter.cap", "#")

    def scatter_pktgen_send_packet(self, sPortid, rPortid, pktsize, num=1):
        """
        Functional test for scatter packets.
        """
        sport = self.tester.get_local_port(sPortid)
        sintf = self.tester.get_interface(sport)
        smac = self.tester.get_mac(sport)
        dmac = self.dut.get_mac_address(sPortid)
        rport = self.tester.get_local_port(rPortid)
        rintf = self.tester.get_interface(rport)
        self.tester.send_expect("ifconfig %s mtu 9000" % sintf, "#")
        self.tester.send_expect("ifconfig %s mtu 9000" % rintf, "#")

        self.start_tcpdump(rintf)

        pktlen = pktsize - 18
        padding = pktlen - 20

        self.tester.scapy_append(
            'sendp([Ether(src="%s",dst="%s")/IP(len=%s)/Raw(load="\x50"*%s)], iface="%s")' % (smac, dmac,pktlen, padding, sintf))
        time.sleep(3)
        self.tester.scapy_execute()
        time.sleep(5) #wait for scapy capture subprocess exit
        res = self.get_tcpdump_packet()
        self.tester.send_expect("ifconfig %s mtu 1500" % sintf, "#")
        self.tester.send_expect("ifconfig %s mtu 1500" % sintf, "#")
        return res

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_scatter_mbuf_2048(self):
        """
        Scatter 2048 mbuf
        """
        cores = self.dut.get_core_list('1S/2C/2T')
        coreMask = dts.create_mask(cores)
        dutPorts = self.dut.get_ports(self.nic)
        portMask = dts.create_mask(dutPorts[:2])

        # set the mbuf size to 1024
        out = self.pmdout.start_testpmd(
                "1S/2C/2T", "--mbcache=200 --mbuf-size=%d --portmask=%s --max-pkt-len=9000" % (self.mbsize, portMask))
        self.verify("Error" not in out, "launch error 1")

        self.dut.send_expect("set fwd mac", "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        for offset in [-1, 0, 1, 4, 5]:
            ret = self.scatter_pktgen_send_packet(
                dutPorts[0], dutPorts[1], self.mbsize + offset)
            self.verify("5050 5050 5050 5050 5050 5050 5050" in ret, "packet receive error")

        self.dut.send_expect("stop", "testpmd> ")
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
