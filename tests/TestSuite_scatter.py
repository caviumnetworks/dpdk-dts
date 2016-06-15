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
from packet import Packet, sniff_packets, load_sniff_packets, strip_pktload
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
        self.verify(len(dutPorts) >= 1, "Insufficient ports")
        self.port = dutPorts[0]
        tester_port = self.tester.get_local_port(self.port)
        self.intf = self.tester.get_interface(tester_port)

        self.pmdout = PmdOutput(self.dut)
        if self.nic in ["niantic", "sageville", "fortpark", "fortville_eagle",
                        "fortville_spirit", "fortville_spirit_single",
                        "redrockcanyou", "atwood", "boulderrapid",
                        "ironpond", "twinpond", "springfountain", "fortpark_TLV"]:
            self.mbsize = 2048
        else:
            self.mbsize = 1024

        if self.kdriver == "fm10k":
            self.dut.ports_info[self.port]['port'].enable_jumbo(framesize=9000)

        self.tester.send_expect("ifconfig %s mtu 9000" % self.intf, "#")

    def scatter_pktgen_send_packet(self, pktsize):
        """
        Functional test for scatter packets.
        """
        dmac = self.dut.get_mac_address(self.port)

        inst = sniff_packets(self.intf)
        pkt = Packet(pkt_type="IP_RAW", pkt_len=pktsize)
        pkt.config_layer('ether', {'dst': dmac})
        pkt.send_pkt(tx_port=self.intf)
        sniff_pkts = load_sniff_packets(inst)

        res = ""
        if len(sniff_pkts):
            res = strip_pktload(sniff_pkts[0], layer="L4")
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
        out = self.pmdout.start_testpmd(
            "1S/2C/1T", "--mbcache=200 --mbuf-size=%d --portmask=0x1 "
            "--max-pkt-len=9000 --port-topology=loop" % (self.mbsize))

        self.verify("Error" not in out, "launch error 1")

        self.dut.send_expect("set fwd mac", "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        for offset in [-1, 0, 1, 4, 5]:
            ret = self.scatter_pktgen_send_packet(self.mbsize + offset)
            self.verify(
                "58 58 58 58 58 58 58 58" in ret, "packet receive error")

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
        if self.kdriver == "fm10k":
            self.dut.ports_info[self.port]['port'].enable_jumbo(framesize=1518)
        self.tester.send_expect("ifconfig %s mtu 1500" % self.intf, "#")
        pass
