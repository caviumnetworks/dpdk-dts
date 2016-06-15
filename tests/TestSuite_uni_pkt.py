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

Unified packet type flag is supposed to recognize packet types and support all
possible PMDs.

This 32 bits of packet_type can be divided into several sub fields to
indicate different packet type information of a packet. The initial design
is to divide those bits into fields for L2 types, L3 types, L4 types, tunnel
types, inner L2 types, inner L3 types and inner L4 types. All PMDs should
translate the offloaded packet types into these 7 fields of information, for
user applications
"""

import dts
from test_case import TestCase
from exception import VerifyFailure
from packet import Packet
import time


class TestUniPacket(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        ports = self.dut.get_ports()
        self.verify(len(ports) >= 2, "Insufficient ports for testing")
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        # start testpmd
        self.dut_port = valports[0]
        tester_port = self.tester.get_local_port(self.dut_port)
        self.tester_iface = self.tester.get_interface(tester_port)
        self.dut.send_expect(
            "./%s/app/testpmd -c f -n 4 -- -i --txqflags=0x0" % self.target, "testpmd>", 20)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def run_test(self, pkt_types):
        time.sleep(1)
        for pkt_type in pkt_types.keys():
            pkt_names = pkt_types[pkt_type]
            pkt = Packet(pkt_type=pkt_type)
            pkt.send_pkt(tx_port=self.tester_iface)
            out = self.dut.get_session_output(timeout=2)
            for pkt_layer_name in pkt_names:
                if pkt_layer_name not in out:
                    print dts.RED("Fail to detect %s" % pkt_layer_name)
                    raise VerifyFailure("Failed to detect %s" % pkt_layer_name)
            print dts.GREEN("Detected %s successfully" % pkt_type)

    def test_l2pkt_detect(self):
        """
        Check whether L2 packet can be detected"
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "L2 packet detect only support by Fortville")
        self.L2_types = {
            "TIMESYNC": "(outer) L2 type: ETHER_Timesync",
            "ARP": "(outer) L2 type: ETHER_ARP",
            "LLDP": "(outer) L2 type: ETHER_LLDP",
        }

        for l2_type in self.L2_types.keys():
            pkt_name = self.L2_types[l2_type]
            pkt = Packet(pkt_type=l2_type)
            pkt.send_pkt(tx_port=self.tester_iface)
            out = self.dut.get_session_output(timeout=2)
            if pkt_name in out:
                print dts.GREEN("Detected L2 %s successfully" % l2_type)
            else:
                raise VerifyFailure("Failed to detect L2 %s" % l2_type)

    def test_IPv4_L4(self):
        """
        checked that whether L3 and L4 packet can be normally detected.
        """
        if "fortville" in self.nic.lower() or "fortpark_TLV" in self.nic.lower():
            outerL4Type = "(outer) L4 type: L4_NONFRAG"
        elif "niantic" in self.nic.lower() or "i350" in self.nic.lower():
            outerL4Type = "(outer) L4 type: Unknown"

        pktType = {
            "MAC_IP_PKT":                ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4", outerL4Type],
            "MAC_IP_UDP_PKT":            ["(outer) L4 type: UDP"],
            "MAC_IP_TCP_PKT":            ["(outer) L4 type: TCP"],
            "MAC_IP_SCTP_PKT":           ["(outer) L4 type: SCTP"],
            "MAC_IP_ICMP_PKT":           ["(outer) L4 type: ICMP"],
            "MAC_IPFRAG_TCP_PKT":        ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4_EXT_UNKNOWN", "(outer) L4 type: L4_FRAG"],
            "MAC_IPihl_PKT":             ["(outer) L3 type: IPV4_EXT", "(outer) L4 type: Unknown"],
            "MAC_IPihl_SCTP_PKT":        ["(outer) L3 type: IPV4_EXT", "(outer) L4 type: SCTP"]
        }

        # delete the unsupported packet based on nic type
        if "fortville" in self.nic.lower() or "fortpark_TLV" in self.nic.lower():
            pktType.pop("MAC_IPihl_PKT")
            pktType.pop("MAC_IPihl_SCTP_PKT")
        elif "niantic" in self.nic.lower() or "i350" in self.nic.lower():
            pktType.pop("MAC_IP_ICMP_PKT")
            pktType.pop("MAC_IPFRAG_TCP_PKT")

        self.run_test(pktType)

    def test_IPv6_L4(self):
        """
        checked that whether IPv6 and L4 packet can be normally detected.
        """
        if "fortville" in self.nic.lower() or "fortpark_TLV" in self.nic.lower():
            outerL4Type = "(outer) L4 type: L4_NONFRAG"
            outerL3Type = "(outer) L3 type: IPV6_EXT_UNKNOWN"
        elif "niantic" in self.nic.lower() or "i350" in self.nic.lower():
            outerL4Type = "(outer) L4 type: Unknown"
            outerL3Type = "(outer) L3 type: IPV6"

        pktType = {
            "MAC_IPv6_PKT":          ["(outer) L2 type: ETHER", outerL3Type, outerL4Type],
            "MAC_IPv6_UDP_PKT":      ["(outer) L4 type: UDP"],
            "MAC_IPv6_TCP_PKT":      ["(outer) L4 type: TCP"],
            "MAC_IPv6FRAG_PKT_F":    ["(outer) L3 type: IPV6_EXT_UNKNOWN", "(outer) L4 type: L4_FRAG"],
            "MAC_IPv6FRAG_PKT_N":    ["(outer) L3 type: IPV6_EXT", "(outer) L4 type: Unknown"]
        }

        # delete the unsupported packet based on nic type
        if "fortville" in self.nic.lower() or "fortpark_TLV" in self.nic.lower():
            pktType.pop("MAC_IPv6FRAG_PKT_N")
        elif "niantic" in self.nic.lower() or "i350" in self.nic.lower():
            pktType.pop("MAC_IPv6FRAG_PKT_F")

        self.run_test(pktType)

    def test_IP_in_IPv4_tunnel(self):
        """
        checked that whether IP in IPv4 tunnel packet can be normally
        detected by Fortville.
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "IP in IPv4 tunnel packet type detect only support by Fortville")

        pktType = {
            "MAC_IP_IPFRAG_UDP_PKT":      ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4_EXT_UNKNOWN", "(outer) L4 type: Unknown", "Tunnel type: IP", "Inner L2 type: Unknown", "Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_IP_PKT":              ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_IP_UDP_PKT":          ["Inner L4 type: UDP"],
            "MAC_IP_IP_TCP_PKT":          ["Inner L4 type: TCP"],
            "MAC_IP_IP_SCTP_PKT":         ["Inner L4 type: SCTP"],
            "MAC_IP_IP_ICMP_PKT":         ["Inner L4 type: ICMP"],
            "MAC_IP_IPv6FRAG_PKT":        ["Inner L3 type: IPV6_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_IPv6_PKT":            ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_IPv6_UDP_PKT":        ["Inner L4 type: UDP"],
            "MAC_IP_IPv6_TCP_PKT":        ["Inner L4 type: TCP"],
            "MAC_IP_IPv6_SCTP_PKT":       ["Inner L4 type: SCTP"],
            "MAC_IP_IPv6_ICMP_PKT":       ["Inner L4 type: ICMP"]
        }

        self.run_test(pktType)

    def test_IPv6_in_IPv4_tunnel(self):
        """
        checked that whether IPv4 in IPv6 tunnel packet can be normally
        detected by Niantic and i350.
        """
        if "niantic" not in self.nic.lower() and "i350" not in self.nic.lower():
            return

        pktType = {
            "MAC_IP_IPv6_PKT":            ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4", "(outer) L4 type: Unknown", "Tunnel type: IP", "Inner L2 type: Unknown", "Inner L3 type: IPV6", "Inner L4 type: Unknown"],
            "MAC_IP_IPv6EXT2_PKT":        ["Inner L3 type: IPV6_EXT"],
            "MAC_IP_IPv6_UDP_PKT":        ["Inner L4 type: UDP"],
            "MAC_IP_IPv6_TCP_PKT":        ["Inner L4 type: TCP"],
            "MAC_IP_IPv6EXT2_UDP_PKT":    ["Inner L3 type: IPV6_EXT", "Inner L4 type: UDP"],
            "MAC_IP_IPv6EXT2_TCP_PKT":    ["Inner L3 type: IPV6_EXT", "Inner L4 type: TCP"]
        }
        self.run_test(pktType)

    def test_IP_in_IPv6_tunnel(self):
        """
        checked that whether IP in IPv6 tunnel packet can be normally
        detected by Fortville.
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "IP in IPv6 tunnel packet type detect only support by Fortville")

        pktType = {
            "MAC_IP_IPFRAG_UDP_PKT":      ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4_EXT_UNKNOWN", "(outer) L4 type: Unknown", "Tunnel type: IP", "Inner L2 type: Unknown", "Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_IP_PKT":              ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_IP_UDP_PKT":          ["Inner L4 type: UDP"],
            "MAC_IP_IP_TCP_PKT":          ["Inner L4 type: TCP"],
            "MAC_IP_IP_SCTP_PKT":         ["Inner L4 type: SCTP"],
            "MAC_IP_IP_ICMP_PKT":         ["Inner L4 type: ICMP"],
            "MAC_IP_IPv6FRAG_PKT":        ["Inner L3 type: IPV6_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_IPv6_PKT":            ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_IPv6_UDP_PKT":        ["Inner L4 type: UDP"],
            "MAC_IP_IPv6_TCP_PKT":        ["Inner L4 type: TCP"],
            "MAC_IP_IPv6_SCTP_PKT":       ["Inner L4 type: SCTP"],
            "MAC_IP_IPv6_ICMP_PKT":       ["Inner L4 type: ICMP"]
        }
        self.run_test(pktType)

    def test_NVGRE_tunnel(self):
        """
        checked that whether NVGRE tunnel packet can be normally detected
        by Fortville.
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "NVGRE tunnel packet type detect only support by Fortville")

        pktType = {
            "MAC_IP_NVGRE_MAC_IPFRAG_PKT":              ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4_EXT_UNKNOWN", "(outer) L4 type: Unknown", "Tunnel type: GRENAT", "Inner L2 type: ETHER", "Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_NVGRE_MAC_IP_PKT":                  ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_NVGRE_MAC_VLAN_PKT":                ["Inner L2 type: ETHER_VLAN", "Inner L4 type: Unknown"],
            "MAC_IP_NVGRE_MAC_VLAN_IPFRAG_PKT":         ["Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_NVGRE_MAC_VLAN_IP_PKT":             ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_NVGRE_MAC_VLAN_IP_UDP_PKT":         ["Inner L4 type: UDP"],
            "MAC_IP_NVGRE_MAC_VLAN_IP_TCP_PKT":         ["Inner L4 type: TCP"],
            "MAC_IP_NVGRE_MAC_VLAN_IP_SCTP_PKT":        ["Inner L4 type: SCTP"],
            "MAC_IP_NVGRE_MAC_VLAN_IP_ICMP_PKT":        ["Inner L4 type: ICMP"],
            "MAC_IP_NVGRE_MAC_VLAN_IPv6FRAG_PKT":       ["Inner L3 type: IPV6_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_NVGRE_MAC_VLAN_IPv6_PKT":           ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_NVGRE_MAC_VLAN_IPv6_UDP_PKT":       ["Inner L4 type: UDP"],
            "MAC_IP_NVGRE_MAC_VLAN_IPv6_TCP_PKT":       ["Inner L4 type: TCP"],
            "MAC_IP_NVGRE_MAC_VLAN_IPv6_SCTP_PKT":      ["Inner L4 type: SCTP"],
            "MAC_IP_NVGRE_MAC_VLAN_IPv6_ICMP_PKT":      ["Inner L4 type: ICMP"]
        }
        self.run_test(pktType)

    def test_NVGRE_in_IPv6_tunnel(self):
        """
        checked that whether NVGRE in IPv6 tunnel packet can be normally
        detected by Fortville.
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "NVGRE in IPv6 detect only support by Fortville")

        pkt_types = {
            "MAC_IPv6_NVGRE_MAC_PKT":             ["(outer) L2 type: ETHER", "(outer) L3 type: IPV6_EXT_UNKNOWN", "(outer) L4 type: Unknown", "Tunnel type: GRENAT", "Inner L2 type: ETHER", "Inner L3 type: Unknown", "Inner L4 type: Unknown"],
            "MAC_IPv6_NVGRE_MAC_IPFRAG_PKT":      ["Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IPv6_NVGRE_MAC_IP_PKT":          ["Inner L4 type: L4_NONFRAG"],
            "MAC_IPv6_NVGRE_MAC_IP_UDP_PKT":      ["Inner L4 type: UDP"],
            "MAC_IPv6_NVGRE_MAC_IP_TCP_PKT":      ["Inner L4 type: TCP"],
            "MAC_IPv6_NVGRE_MAC_IP_SCTP_PKT":     ["Inner L4 type: SCTP"],
            "MAC_IPv6_NVGRE_MAC_IP_ICMP_PKT":     ["Inner L4 type: ICMP"],
            "MAC_IPv6_NVGRE_MAC_IPv6FRAG_PKT":    ["Inner L3 type: IPV6_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IPv6_NVGRE_MAC_IPv6_PKT":        ["Inner L4 type: L4_NONFRAG"],
            "MAC_IPv6_NVGRE_MAC_IPv6_UDP_PKT":    ["Inner L4 type: UDP"],
            "MAC_IPv6_NVGRE_MAC_IPv6_TCP_PKT":    ["Inner L4 type: TCP"],
            "MAC_IPv6_NVGRE_MAC_IPv6_SCTP_PKT":   ["Inner L4 type: SCTP"],
            "MAC_IPv6_NVGRE_MAC_IPv6_ICMP_PKT":   ["Inner L4 type: ICMP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPFRAG_PKT": ["Inner L2 type: ETHER_VLAN", "Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IP_PKT":     ["Inner L4 type: L4_NONFRAG"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IP_UDP_PKT": ["Inner L4 type: UDP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IP_TCP_PKT": ["Inner L4 type: TCP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IP_SCTP_PKT": ["Inner L4 type: SCTP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IP_ICMP_PKT": ["Inner L4 type: ICMP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPv6FRAG_PKT": ["Inner L3 type: IPV6_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPv6_PKT":     ["Inner L4 type: L4_NONFRAG"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPv6_UDP_PKT": ["Inner L4 type: UDP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPv6_TCP_PKT": ["Inner L4 type: TCP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPv6_SCTP_PKT": ["Inner L4 type: SCTP"],
            "MAC_IPv6_NVGRE_MAC_VLAN_IPv6_ICMP_PKT": ["Inner L4 type: ICMP"],
        }

        self.run_test(pkt_types)

    def test_GRE_tunnel(self):
        """
        checked that whether GRE tunnel packet can be normally detected by Fortville.
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "GRE tunnel packet type detect only support by Fortville")

        pktType = {
            "MAC_IP_GRE_IPFRAG_PKT":          ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4_EXT_UNKNOWN", "(outer) L4 type: Unknown", "Tunnel type: GRENAT", "Inner L2 type: Unknown", "Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_GRE_IP_PKT":              ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_GRE_IP_UDP_PKT":          ["Inner L4 type: UDP"],
            "MAC_IP_GRE_IP_TCP_PKT":          ["Inner L4 type: TCP"],
            "MAC_IP_GRE_IP_SCTP_PKT":         ["Inner L4 type: SCTP"],
            "MAC_IP_GRE_IP_ICMP_PKT":         ["Inner L4 type: ICMP"],
            "MAC_IP_GRE_PKT":                 ["Inner L3 type: Unknown", "Inner L4 type: Unknown"]
        }
        self.run_test(pktType)

    def test_Vxlan_tunnel(self):
        """
        checked that whether Vxlan tunnel packet can be normally detected by
        Fortville.
        """
        self.verify(("fortville" in self.nic or "fortpark_TLV" in self.nic),
                    "Vxlan tunnel packet type detect only support by Fortville")

        self.dut.send_expect("rx_vxlan_port add 4789 0", "testpmd>", 10)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        pktType = {
            "MAC_IP_UDP_VXLAN_MAC_IPFRAG_PKT":        ["(outer) L2 type: ETHER", "(outer) L3 type: IPV4_EXT_UNKNOWN", "(outer) L4 type: Unknown", "Tunnel type: GRENAT", "Inner L2 type: ETHER", "Inner L3 type: IPV4_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_UDP_VXLAN_MAC_IP_PKT":            ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_UDP_VXLAN_MAC_IP_UDP_PKT":        ["Inner L4 type: UDP"],
            "MAC_IP_UDP_VXLAN_MAC_IP_TCP_PKT":        ["Inner L4 type: TCP"],
            "MAC_IP_UDP_VXLAN_MAC_IP_SCTP_PKT":       ["Inner L4 type: SCTP"],
            "MAC_IP_UDP_VXLAN_MAC_IP_ICMP_PKT":       ["Inner L4 type: ICMP"],
            "MAC_IP_UDP_VXLAN_MAC_IPv6FRAG_PKT":      ["Inner L3 type: IPV6_EXT_UNKNOWN", "Inner L4 type: L4_FRAG"],
            "MAC_IP_UDP_VXLAN_MAC_IPv6_PKT":          ["Inner L4 type: L4_NONFRAG"],
            "MAC_IP_UDP_VXLAN_MAC_IPv6_UDP_PKT":      ["Inner L4 type: UDP"],
            "MAC_IP_UDP_VXLAN_MAC_IPv6_TCP_PKT":      ["Inner L4 type: TCP"],
            "MAC_IP_UDP_VXLAN_MAC_IPv6_SCTP_PKT":     ["Inner L4 type: SCTP"],
            "MAC_IP_UDP_VXLAN_MAC_IPv6_ICMP_PKT":     ["Inner L4 type: ICMP"],
            "MAC_IP_UDP_VXLAN_MAC_PKT":               ["Inner L3 type: Unknown", "Inner L4 type: Unknown"]
        }
        self.run_test(pktType)

    def tear_down(self):
        """
        Run after each test case.
        Nothing to do.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        Nothing to do.
        """
        self.dut.kill_all()
        pass
