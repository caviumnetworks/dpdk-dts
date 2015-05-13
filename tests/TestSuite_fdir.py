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
Test 82599 Flow Director Support in DPDK
"""

import dts
import time


from test_case import TestCase
from pmd_output import PmdOutput


class TestFdir(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        ports = self.dut.get_ports()
        self.verify(len(ports) >= 2, "Not enough ports available")

        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def send_and_verify(self, condition, packet):
        """
        Send packages and verify behavior.
        """
        self.tester.scapy_foreground()
        self.tester.scapy_append('sys.path.append("./")')
        self.tester.scapy_append('from sctp import *')
        self.tester.scapy_append(packet)
        self.dut.send_expect("start", "testpmd>")
        self.tester.scapy_execute()
        time.sleep(.5)
        out = self.dut.send_expect("stop", "testpmd>")
        if condition:
            self.verify("PKT_RX_FDIR" in out, "FDIR hash not displayed when required")
        else:
            self.verify("PKT_RX_FDIR" not in out, "FDIR hash displayed when not required")

    def test_fdir_space(self):
        """
        Setting memory reserved for FDir filters.
        """

        dutPorts = self.dut.get_ports()

        self.pmdout.start_testpmd("all", "--rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K")
        out = self.dut.send_expect("show port fdir %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("quit", "# ", 30)
        self.verify("free:     2048" in out, "Free space doesn't match the expected value")

        self.pmdout.start_testpmd("all", "--rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=128K")
        out = self.dut.send_expect("show port fdir %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("quit", "# ", 30)
        self.verify("free:     4096" in out, "Free space doesn't match the expected value")

        self.pmdout.start_testpmd("all", "--rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=256K")
        out = self.dut.send_expect("show port fdir %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("quit", "# ", 30)
        self.verify("free:     8192" in out, "Free space doesn't match the expected value")

    def test_fdir_signatures(self):
        """
        FDir signature matching mode.
        There are three different reporting modes, that can be set in testpmd using the ``--pkt-filter-report-hash`` command line
        argument:
            --pkt-filter-report-hash=none
            --pkt-filter-report-hash=match
            --pkt-filter-report-hash=always
        The test for each mode is following the steps below.
          - Start the ``testpmd`` application by using paramter of each mode.
          - Send the ``p_udp`` packet with Scapy on the traffic generator and check that FDir information is printed
        """

        dutPorts = self.dut.get_ports()
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=none" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=match" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("upd_perfect_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("rm_perfect_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0 soft 0x14" % dutPorts[0], "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=always" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_matching(self):
        """
        FDir matching mode
        This test adds signature filters to the hardware, and then checks
        whether sent packets match those filters.
        The test for each mode is following the steps below.
          - Start the ``testpmd`` application
          - Add filter with upd, tcp sctp, IP4 or IP6
          - Send the packet and validate the filter function.
        """

        dutPorts = self.dut.get_ports()
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=signature --pkt-filter-report-hash=match" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("upd_signature_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("rm_signature_filter %s udp src 192.168.1.1 0 dst 192.168.1.2 0 flexbytes 0x800 vlan 0" % dutPorts[0], "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.1.1", dst="192.168.1.2")/UDP(sport=0,dport=0)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s tcp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s sctp src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="2001:0db8:85a3:0000:0000:8a2e:0370:7000", dst="2001:0db8:85a3:0000:0000:8a2e:0370:7338")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_signature_filter %s udp src 2001:0db8:85a3:0000:0000:8a2e:0370:7000 1024 dst 2001:0db8:85a3:0000:0000:8a2e:0370:7338 1024 flexbytes 0x86dd vlan 0 queue 1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IPv6(src="2001:0db8:85a3:0000:0000:8a2e:0370:7000", dst="2001:0db8:85a3:0000:0000:8a2e:0370:7338")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_perfect_matching(self):
        """
        FDir perfect matching mode.
        This test adds perfect-match filters to the hardware, and then checks whether sent packets match those filters.
        The test for each mode is following the steps below.
          - Start the ``testpmd`` application with perfect match;
          - Add filter with upd, tcp sctp, IP4;
          - Send the packet and validate the perfect filter function.
        """

        dutPorts = self.dut.get_ports()
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=match" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x14" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s tcp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x15" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s sctp src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x16" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x17" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_filter_masks(self):
        """
        FDir filter masks.
        This tests the functionality of the setting FDir masks to to affect which
        fields, or parts of fields are used in the matching process.
        """

        dutPorts = self.dut.get_ports()
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K --pkt-filter-report-hash=match" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffff00 0xffff dst_mask 0xffffff00 0xffff flexbytes 1 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.0 1024 dst 192.168.0.0 1024 flexbytes 0x800 vlan 0 queue 1 soft 0x17" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.15", dst="192.168.0.15")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.1.1")/UDP(sport=1024,dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffffff 0xff00 dst_mask 0xffffffff 0xff00 flexbytes 1 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s udp src 10.11.12.1 0x4400 dst 10.11.12.2 0x4500 flexbytes 0x800 vlan 0 queue 1 soft 0x4" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4400,dport=0x4500)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4411,dport=0x4517)], iface="%s")' % (itf, itf))

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4500,dport=0x5500)], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 1 src_mask 0xffffffff 0x0 dst_mask 0xffffffff 0x0 flexbytes 1 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1 soft 0x42" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/TCP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/SCTP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_flexbytes_filtering(self):
        """
        FDir flexbytes filtering
        The FDir feature supports setting up filters that can match on any two byte field
        within the first 64 bytes of a packet. Which byte offset to use is set by passing
        command line arguments to ``testpmd``. In this test a value of ``18`` corresponds
        to the bytes at offset 36 and 37, as the offset is in 2-byte units
        """

        dutPorts = self.dut.get_ports()
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.pmdout.start_testpmd("all", "--portmask=%s --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K --pkt-filter-report-hash=match --pkt-filter-flexbytes-offset=18" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 3", "testpmd>")

        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x1 vlan 0 queue 1 soft 0x1" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0x1)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0xff vlan 0 queue 1 soft 0xff" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0xff)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffffff 0xffff dst_mask 0xffffffff 0xffff flexbytes 0 vlan_id 1 vlan_prio 1" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x0 vlan 0 queue 1 soft 0x42" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0x1)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0xFF)/IP()/UDP()], iface="%s")' % (itf, itf))

        self.dut.send_expect("quit", "# ", 30)

    def test_fdir_vlanfiltering(self):
        """
        FDir VLAN field filtering
        """

        dutPorts = self.dut.get_ports()
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)

        self.dut.kill_all()
        self.pmdout.start_testpmd("all", "--portmask=%s --nb-cores=2 --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect" % dts.create_mask([dutPorts[0]]))
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        # "rx_vlan add all" has been removed from testpmd
        self.dut.send_expect("rx_vlan add 0xFFF %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("rx_vlan add 0x001 %s" % dutPorts[0], "testpmd>")
        self.dut.send_expect("rx_vlan add 0x017 %s" % dutPorts[0], "testpmd>")

        self.send_and_verify(False, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x0FFF)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x8100 vlan 0xfff queue 1 soft 0x47" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x0FFF)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

        self.dut.send_expect("set_masks_filter %s only_ip_flow 0 src_mask 0xffffffff 0xffff  dst_mask 0xffffffff 0xffff flexbytes 1 vlan_id 0 vlan_prio 0" % dutPorts[0], "testpmd>")
        self.dut.send_expect("add_perfect_filter %s udp src 192.168.0.1 1024 dst 192.168.0.2 1024 flexbytes 0x8100 vlan 0 queue 1 soft 0x47" % dutPorts[0], "testpmd>")
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x001)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))
        self.send_and_verify(True, 'sendp([Ether(src=get_if_hwaddr("%s"), dst="00:1B:21:8E:B2:30")/Dot1Q(vlan=0x0017)/IP(src="192.168.0.1", dst="192.168.0.2")/UDP(sport=1024, dport=1024)], iface="%s")' % (itf, itf))

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
