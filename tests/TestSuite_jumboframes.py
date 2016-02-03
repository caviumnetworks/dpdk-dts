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
Test the support of Jumbo Frames by Poll Mode Drivers
"""

import dts
import re
from time import sleep
from test_case import TestCase
from pmd_output import PmdOutput

ETHER_HEADER_LEN = 18
IP_HEADER_LEN = 20
ETHER_STANDARD_MTU = 1518
ETHER_JUMBO_FRAME_MTU = 9000


class TestJumboframes(TestCase):

    def jumboframes_get_stat(self, portid, rx_tx):
        """
        Get packets number from port statistic
        """
        stats = self.pmdout.get_pmd_stats(portid)
        if rx_tx == "rx":
            return [stats['RX-packets'], stats['RX-errors'], stats['RX-bytes']]
        elif rx_tx == "tx":
            return [stats['TX-packets'], stats['TX-errors'], stats['TX-bytes']]
        else:
            return None

    def jumboframes_send_packet(self, pktsize, received=True):
        """
        Send 1 packet to portid
        """
        tx_pkts_ori, _, tx_bytes_ori = [int(_) for _ in self.jumboframes_get_stat(self.rx_port, "tx")]
        rx_pkts_ori, rx_err_ori, rx_bytes_ori = [int(_) for _ in self.jumboframes_get_stat(self.tx_port, "rx")]

        itf = self.tester.get_interface(self.tester.get_local_port(self.tx_port))
        mac = self.dut.get_mac_address(self.tx_port)

        # The packet total size include ethernet header, ip header, and payload.
        # ethernet header length is 18 bytes, ip standard header length is 20 bytes.
        pktlen = pktsize - ETHER_HEADER_LEN
        padding = pktlen - IP_HEADER_LEN

        self.tester.scapy_foreground()
        self.tester.scapy_append('nutmac="%s"' % mac)
        self.tester.scapy_append('sendp([Ether(dst=nutmac, src="52:00:00:00:00:00")/IP(len=%s)/Raw(load="\x50"*%s)], iface="%s")' % (pktlen, padding, itf))

        out = self.tester.scapy_execute()
        sleep(5)

        tx_pkts, _, tx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.rx_port, "tx")]
        # p0tx_pkts, p0tx_err, p0tx_bytes
        rx_pkts, rx_err, rx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.tx_port, "rx")]

        tx_pkts -= tx_pkts_ori
        tx_bytes -= tx_bytes_ori
        rx_pkts -= rx_pkts_ori
        rx_bytes -= rx_bytes_ori
        rx_err -= rx_err_ori

        if received:
            self.verify((tx_pkts == rx_pkts) and ((tx_bytes + 4) == pktsize) and ((rx_bytes + 4) == pktsize),
                        "packet pass assert error")
        else:
            #self.verify(p0tx_pkts == p1rx_pkts and (p1rx_err == 1 or p1rx_pkts == 0),
            self.verify(rx_err == 1 or tx_pkts == 0, "packet drop assert error")
        return out

    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Prerequisite steps for each test suit.
        """
        self.dut_ports = self.dut.get_ports()
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")
        self.rx_port = self.dut_ports[0]
        self.tx_port = self.dut_ports[0]

        cores = self.dut.get_core_list("1S/2C/1T")
        self.coremask = dts.create_mask(cores)

        self.port_mask = dts.create_mask([self.rx_port, self.tx_port])

        if self.kdriver == "fm10k":
            netobj = self.dut.ports_info[self.tx_port]['port']
            netobj.enable_jumbo(framesize = ETHER_JUMBO_FRAME_MTU)
            netobj = self.dut.ports_info[self.rx_port]['port']
            netobj.enable_jumbo(framesize = ETHER_JUMBO_FRAME_MTU)

        self.tester.send_expect("ifconfig %s mtu %s" % (self.tester.get_interface(self.tester.get_local_port(self.rx_port)), ETHER_JUMBO_FRAME_MTU + 200), "# ")
#        self.tester.send_expect("ifconfig %s mtu %s" % (self.tester.get_interface(self.tester.get_local_port(self.tx_port)), ETHER_JUMBO_FRAME_MTU + 200), "# ")

        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        This is to clear up environment before the case run.
        """
        self.dut.kill_all()

    def test_jumboframes_normal_nojumbo(self):
        """
        This case aims to test transmitting normal size packet without jumbo
        f=rame on testpmd app.
        """
        self.pmdout.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop" % (ETHER_STANDARD_MTU))
        self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU - 1)
        self.jumboframes_send_packet(ETHER_STANDARD_MTU)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_jumbo_nojumbo(self):
        """
        This case aims to test transmitting jumbo frame packet on testpmd without
        jumbo frame support.
        """
        # RRC has no ability to set the max pkt len to hardware
        if self.kdriver == "fm10k":
            print dts.RED("fm10k not support this case\n")
            return
        self.pmdout.start_testpmd("Default", "--max-pkt-len=%d --port-topology=loop" % (ETHER_STANDARD_MTU))
        self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU + 1, False)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_normal_jumbo(self):
        """
        When jumbo frame supported, this case is to verify that the normal size
        packet forwrding should be support correct.
        """
        self.pmdout.start_testpmd("Default", "--max-pkt-len=%s --port-topology=loop" % (ETHER_JUMBO_FRAME_MTU))
        self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(1517)
        self.jumboframes_send_packet(1518)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_jumbo_jumbo(self):
        """
        When jumbo frame supported, this case is to verify that jumbo frame
        packet can be forwarded correct.
        """
        self.pmdout.start_testpmd("Default", "--max-pkt-len=%s --port-topology=loop" % (ETHER_JUMBO_FRAME_MTU))
        self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(ETHER_STANDARD_MTU + 1)
        self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU - 1)
        self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_bigger_jumbo(self):
        """
        When the jubmo frame MTU set as 9000, this case is to verify that the
        packet which the length bigger than MTU can not be forwarded.
        """
        self.pmdout.start_testpmd("Default", "--max-pkt-len=%s --port-topology=loop" % (ETHER_JUMBO_FRAME_MTU))
        self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        
        """
        On 1G NICs, when the jubmo frame MTU set as 9000, the software adjust it to 9004.
        """
        if self.nic in ["powerville", "springville", "kawela_4"]:
            self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU + 4 + 1, False)
        else:
            self.jumboframes_send_packet(ETHER_JUMBO_FRAME_MTU + 1, False)

        self.dut.send_expect("quit", "# ", 30)

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        When the case of this test suite finished, the enviroment should
        clear up.
        """
        self.tester.send_expect("ifconfig %s mtu %s" % (self.tester.get_interface(self.tester.get_local_port(self.rx_port)), ETHER_STANDARD_MTU), "# ")
        self.tester.send_expect("ifconfig %s mtu %s" % (self.tester.get_interface(self.tester.get_local_port(self.tx_port)), ETHER_STANDARD_MTU), "# ")
