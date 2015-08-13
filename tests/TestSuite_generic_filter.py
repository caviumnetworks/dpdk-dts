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

Test the support of VLAN Offload Features by Poll Mode Drivers.

"""

import dts
import time
import re

from test_case import TestCase
from settings import HEADER_SIZE
from pmd_output import PmdOutput
from settings import DRIVERS


class TestGeneric_filter(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Generic filter Prerequistites
        """

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(self.nic)
        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports")
        cores = self.dut.get_core_list("all")
        self.verify(len(cores) >= 10, "Insufficient core")
        global coreMask
        coreMask = dts.create_mask(cores)
        # Based on h/w type, choose how many ports to use
        global valports
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        global portMask
        portMask = dts.create_mask(valports[:2])
        self.pmdout = PmdOutput(self.dut)
        self.ethertype_filter = "off"

    def request_mbufs(self, queue_num):
        """
        default txq/rxq descriptor is 64
        """
        return 128 * queue_num + 512

    def port_config(self):
        """
         set port queue mapping, fortville not support this function
        """
        if self.nic not in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]:
            self.dut.send_expect(
                "set stat_qmap rx %s 0 0" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 0 0" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 1 1" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 1 1" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 2 2" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 2 2" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 3 3" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 3 3" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "vlan set strip off %s" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "vlan set strip off %s" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "vlan set filter off %s" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "vlan set filter off %s" % valports[1], "testpmd> ")

        self.dut.send_expect("set flush_rx on", "testpmd> ")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def filter_send_packet(self, type):
        """
        Send  packet to portid
        """

        port = self.tester.get_local_port(valports[0])
        txItf = self.tester.get_interface(port)

        port = self.tester.get_local_port(valports[1])
        rxItf = self.tester.get_interface(port)

        mac = self.dut.get_mac_address(valports[0])
        self.tester.scapy_foreground()

        if (type == "syn"):
            self.tester.scapy_append(
                'sendp([Ether(dst="%s")/IP(src="2.2.2.5",dst="2.2.2.4")/TCP(dport=80,flags="S")], iface="%s")' % (mac, txItf))
        elif (type == "arp"):
            self.tester.scapy_append(
                'sendp([Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst="192.168.1.1")], iface="%s")' % (txItf))
        elif (type == "arp_prio"):
            self.tester.scapy_append(
                'sendp([Ether(dst="ff:ff:ff:ff:ff:ff")/Dot1Q(prio=3)/ARP(pdst="192.168.1.1")], iface="%s")' % (txItf))
        elif (type == "fivetuple"):
            if self.nic == "niantic":
                self.tester.scapy_append(
                    'sendp([Ether(dst="%s")/Dot1Q(prio=3)/IP(src="2.2.2.4",dst="2.2.2.5")/TCP(sport=1,dport=1,flags=0)], iface="%s")' % (mac, txItf))
            else:
                self.tester.scapy_append(
                    'sendp([Ether(dst="%s")/Dot1Q(prio=3)/IP(src="2.2.2.4",dst="2.2.2.5")/TCP(sport=1,dport=1)], iface="%s")' % (mac, txItf))
        elif (type == "udp"):
            self.tester.scapy_append(
                'sendp([Ether(dst="%s")/IP(src="2.2.2.4",dst="2.2.2.5")/UDP(dport=64)], iface="%s")' % (mac, txItf))
        elif (type == "ip"):
            self.tester.scapy_append(
                'sendp([Ether(dst="%s")/IP(src="2.2.2.4",dst="2.2.2.5")/TCP(sport=80,dport=80,flags=0)], iface="%s")' % (mac, txItf))
        elif (type == "jumbo"):
            self.tester.scapy_append(
                'sendp([Ether(dst="%s")/IP(src="2.2.2.5",dst="2.2.2.4")/TCP(dport=80,flags="S")/Raw(load="\x50"*1500)], iface="%s")' % (mac, txItf))
        elif (type == "packet"):
            if (filters_index == 0):
                self.tester.scapy_append(
                    'sendp([Ether(dst="%s")/IP(src="2.2.2.4",dst="2.2.2.5")/TCP(sport=1,dport=1,flags=0)], iface="%s")' % (mac, txItf))
            if (filters_index == 1):
                self.tester.scapy_append(
                    'sendp([Ether(dst="%s")/Dot1Q(prio=3)/IP(src="2.2.2.4",dst="2.2.2.5")/TCP(sport=1,dport=2,flags=0)], iface="%s")' % (mac, txItf))
        self.tester.scapy_execute()

    def verify_result(self, outstring, tx_pkts, expect_queue):

        result_scanner = r"Forward Stats for RX Port= %s/Queue= ([0-9]+)" % valports[
            0]

        scanner = re.compile(result_scanner, re.DOTALL)
        m = scanner.search(outstring)
        queue_id = m.group(1)
        if self.nic == "niantic" and self.ethertype_filter == "on" and expect_queue == "0":
            self.ethertype_filter = "off"
            self.verify(queue_id == "0", "packet pass  error")
        if expect_queue != queue_id:
            scanner = re.compile(result_scanner, re.DOTALL)
            m = scanner.search(outstring)
            queue_id = m.group(1)
            result_scanner = r"RX-packets: ([0-9]+) \s*"
            scanner = re.compile(result_scanner, re.DOTALL)
            m = scanner.search(outstring)
            p0tx_pkts = m.group(1)
            
        else:

            result_scanner = r"RX-packets: ([0-9]+) \s*"

            scanner = re.compile(result_scanner, re.DOTALL)
            m = scanner.search(outstring)
            p0tx_pkts = m.group(1)

        self.verify(p0tx_pkts == tx_pkts, "packet pass  error")

    # TODO: failing test even in non-converted version
    def test_syn_filter(self):
        """
        Enable receipt of SYN packets
        """
        self.verify(self.nic in ["niantic", "kawela_4", "bartonhills", "powerville"], "%s nic not support syn filter" % self.nic)
        self.pmdout.start_testpmd(
            "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
        self.port_config()
        self.dut.send_expect(
            "syn_filter %s add priority high queue 2" % valports[0], "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)

        self.filter_send_packet("syn")
        time.sleep(2)

        out = self.dut.send_expect("stop", "testpmd> ")

        self.verify_result(out, tx_pkts="1", expect_queue="2")

        self.dut.send_expect("clear port stats all", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        self.filter_send_packet("arp")
        time.sleep(2)
        out = self.dut.send_expect("stop", "testpmd> ")

        self.verify_result(out, tx_pkts="1", expect_queue="0")

        self.dut.send_expect(
            "syn_filter %s del priority high queue 2" % valports[0], "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.filter_send_packet("syn")
        time.sleep(2)
        out = self.dut.send_expect("stop", "testpmd> ")

        self.verify_result(out, tx_pkts="1", expect_queue="0")
        self.dut.send_expect("quit", "#")

    def test_priority_filter(self):
        """
        priority filter
        """
        self.pmdout.start_testpmd(
            "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
        self.port_config()

        if self.nic == "niantic":
            cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority 3 queue 3 " % (
                valports[0])
            self.dut.send_expect("%s" % cmd, "testpmd> ")
            cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 2 src_port 1 protocol 0x06 mask 0x18 tcp_flags 0x0 priority 2 queue 2 " % (
                valports[0])
            self.dut.send_expect("%s" % cmd, "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("fivetuple")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="3")
            cmd = "5tuple_filter %s del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority 3 queue 3 " % (
                valports[0])
            self.dut.send_expect(cmd, "testpmd> ")

            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("fivetuple")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")
        elif self.nic == "kawela_4":
            cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x02 priority 3 queue 3" % (
                valports[0])
            self.dut.send_expect("%s" % (cmd), "testpmd> ")
            self.dut.send_expect(
                "syn_filter %s add priority high queue 2" % valports[0], "testpmd> ")

            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("fivetuple")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")
            self.dut.send_expect(
                "syn_filter %s del priority high queue 2" % valports[0], "testpmd> ")

            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("fivetuple")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="3")
        elif self.nic in ["bartonhills", "powerville"]:
            self.dut.send_expect(
                "flex_filter %s add len 16 bytes 0x0123456789abcdef0000000008000000 mask 000C priority 2 queue 1" % (valports[0]), "testpmd> ")
            self.dut.send_expect(
                "2tuple_filter %s add dst_port 64 protocol 0x11 mask 1 tcp_flags 0 priority 3 queue 2" % valports[0], "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("udp")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="1")
            self.dut.send_expect(
                "flex_filter %s del len 16 bytes 0x0123456789abcdef0000000008000000 mask 000C priority 2 queue 1" % valports[0], "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("udp")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")
        else:
            self.verify(False, "%s nic not support this test" % self.nic)

    def test_five_tuple_filter(self):
        """
        five tuple filter
        """
        if self.nic in ["niantic", "kawela_4"]:
            self.pmdout.start_testpmd(
                "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
            self.port_config()

            mask = ['0x1f', '0x0']
            for case in mask:
                if case == "0x1f":
                    if self.nic == "niantic":
                        cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x0 priority 3 queue 3" % (
                            valports[0], case)
                    if self.nic == "kawela_4":
                        cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x02 priority 3 queue 3" % (
                            valports[0], case)
                else:
                    if self.nic == "niantic":
                        cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x0 priority 3 queue 3" % (
                            valports[0], case)
                    if self.nic == "kawela_4":
                        cmd = "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x02 priority 3 queue 3" % (
                            valports[0], case)

                self.dut.send_expect("%s" % (cmd), "testpmd> ")
                # if case == "0x1f":
                #    out = self.dut.send_expect("get_5tuple_filter %s index 1" % valports[0], "testpmd> ")
                #    self.verify('Destination IP:  0x02020205    mask: 1' in out, "set 5-tuple filter error")
                #    self.verify('Source IP:       0x02020204    mask: 1' in out, "set 5-tuple filter error")
                self.dut.send_expect("start", "testpmd> ", 120)

                self.filter_send_packet("fivetuple")

                out = self.dut.send_expect("stop", "testpmd> ")
                self.verify_result(out, tx_pkts="1", expect_queue="3")
                self.dut.send_expect("start", "testpmd> ", 120)
                self.filter_send_packet("arp")
                out = self.dut.send_expect("stop", "testpmd> ")
                self.verify_result(out, tx_pkts="1", expect_queue="0")
                if case == "0x1f":
                    if self.nic == "niantic":
                        cmd = "5tuple_filter %s del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x0 priority 3 queue 3" % (
                            valports[0], case)
                    if self.nic == "kawela_4":
                        cmd = "5tuple_filter %s del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x02 priority 3 queue 3" % (
                            valports[0], case)
                else:
                    if self.nic == "niantic":
                        cmd = "5tuple_filter %s del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x0 priority 3 queue 3" % (
                            valports[0], case)
                    if self.nic == "kawela_4":
                        cmd = "5tuple_filter %s del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask %s tcp_flags 0x02 priority 3 queue 3" % (
                            valports[0], case)

                self.dut.send_expect("%s" % (cmd), "testpmd> ")
                self.dut.send_expect("start", "testpmd> ", 120)
                self.filter_send_packet("fivetuple")
                out = self.dut.send_expect("stop", "testpmd> ")
                self.verify_result(out, tx_pkts="1", expect_queue="0")
            self.dut.send_expect("quit", "#")
        else:
            self.verify(False, "%s nic not support syn filter" % self.nic)

    def test_ethertype_filter(self):

        self.verify(self.nic in ["niantic", "kawela_4", "bartonhills", 
                           "powerville", "fortville_eagle", "fortville_spirit",
                           "fortville_spirit_single"], "%s nic not support syn filter" % self.nic)
        self.pmdout.start_testpmd(
            "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
        self.port_config()
        self.ethertype_filter = "on"
        ethertype = "0x0806"
        self.dut.send_expect(
            "ethertype_filter %s add mac_ignr 00:00:00:00:00:00 ethertype %s fwd queue 2" %
            (valports[0], ethertype), "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)

        self.filter_send_packet("arp")
        time.sleep(2)
        out = self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd> ")

        self.verify_result(out, tx_pkts="1", expect_queue="2")
        if self.nic == "niantic":
            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp_prio")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")

        self.dut.send_expect(
            "ethertype_filter %s del mac_ignr 00:00:00:00:00:00 ethertype %s fwd queue 2" %
            (valports[0], ethertype), "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.filter_send_packet("arp")
        time.sleep(2)
        out = self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd> ")

        self.verify_result(out, tx_pkts="1", expect_queue="0")

    def test_multiple_filters_10GB(self):
        if self.nic == "niantic":
            self.pmdout.start_testpmd(
                "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
            self.port_config()
            self.dut.send_expect(
                "syn_filter %s add priority high queue 1" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "ethertype_filter %s add mac_ignr 00:00:00:00:00:00 ethertype 0x0806 fwd queue 2" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority 3 queue 3 " % (valports[0]), "testpmd> ")
            self.dut.send_expect("start", "testpmd> ")

            self.filter_send_packet("syn")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="1")

            self.ethertype_filter = "on"
            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp_prio")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("fivetuple")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="3")

            self.dut.send_expect(
                "5tuple_filter %s del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority 3 queue 3 " % (valports[0]), "testpmd> ")
            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("syn")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="1")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="2")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("fivetuple")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="0")
            self.dut.send_expect(
                "ethertype_filter %s del mac_ignr 00:00:00:00:00:00 ethertype 0x0806 fwd queue 2" % valports[0], "testpmd> ")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="0")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("syn")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="1")

            self.dut.send_expect(
                "syn_filter %s del priority high queue 1" % valports[0], "testpmd> ")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("syn")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("clear port stats all", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="0")

        else:
            self.verify(False, "%s nic not support this test" % self.nic)

    def test_twotuple_filter(self):

        if self.nic in ["powerville", "bartonhills"]:
            self.pmdout.start_testpmd(
                "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
            self.port_config()
            self.dut.send_expect(
                "2tuple_filter %s add dst_port 64 protocol 0x11 mask 1 tcp_flags 0 priority 3 queue 1" % valports[0], "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)

            self.filter_send_packet("udp")
            out = self.dut.send_expect("stop", "testpmd> ")

            self.verify_result(out, tx_pkts="1", expect_queue="1")

            self.dut.send_expect("start", "testpmd> ")

            self.filter_send_packet("syn")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")

            self.verify_result(out, tx_pkts="1", expect_queue="0")
            self.dut.send_expect(
                "2tuple_filter %s del dst_port 64 protocol 0x11 mask 1 tcp_flags 0 priority 3 queue 1" % valports[0], "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)
            self.filter_send_packet("udp")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")

            self.verify_result(out, tx_pkts="1", expect_queue="0")
            self.dut.send_expect("quit", "#")
        else:
            self.verify(False, "%s nic not support two tuple filter" % self.nic)

    def test_flex_filter(self):
        self.verify(self.nic in ["powerville", "bartonhills"], '%s not support flex filter' % self.nic)

        masks = ['000C', '000C']
        self.pmdout.start_testpmd(
            "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
        self.port_config()
        for i in [0, 1]:
            if i == 0:
                self.dut.send_expect(
                    "flex_filter %s add len 16 bytes 0x0123456789abcdef0000000008060000 mask %s priority 3 queue 1" %
                    (valports[0], masks[i]), "testpmd> ")
            else:
                self.dut.send_expect(
                    "flex_filter %s add len 16 bytes 0x0123456789abcdef0000000008000000 mask %s priority 3 queue 1" %
                    (valports[0], masks[i]), "testpmd> ")

            self.dut.send_expect("start", "testpmd> ", 120)

            if i == 0:
                self.filter_send_packet("arp")
            else:
                self.filter_send_packet("ip")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")

            self.verify_result(out, tx_pkts="1", expect_queue="1")

            self.dut.send_expect("start", "testpmd> ")

            if i == 0:
                self.filter_send_packet("syn")
            else:
                self.filter_send_packet("arp")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")

            self.verify_result(out, tx_pkts="1", expect_queue="0")
            if i == 0:
                self.dut.send_expect(
                    "flex_filter %s del len 16 bytes 0x0123456789abcdef0000000008060000 mask %s priority 3 queue 1" %
                    (valports[0], masks[i]), "testpmd> ")
            else:
                self.dut.send_expect(
                    "flex_filter %s del len 16 bytes 0x0123456789abcdef0000000008000000 mask %s priority 3 queue 1" %
                    (valports[0], masks[i]), "testpmd> ")
            self.dut.send_expect("start", "testpmd> ", 120)
            if i == 0:
                self.filter_send_packet("arp")
            else:
                self.filter_send_packet("ip")
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="0")

    def test_multiple_filters_1GB(self):

        if self.nic in ["powerville", "kawela_4", "bartonhills"]:
            self.pmdout.start_testpmd(
                "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
            self.port_config()
            self.dut.send_expect(
                "syn_filter %s add priority high queue 1" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "ethertype_filter %s add mac_ignr 00:00:00:00:00:00 ethertype 0x0806 fwd queue 3" % (valports[0]), "testpmd> ")
            self.dut.send_expect("start", "testpmd> ")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="3")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("syn")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="1")

            # remove all filter

            self.dut.send_expect(
                "syn_filter %s del priority high queue 1" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "ethertype_filter %s del mac_ignr 00:00:00:00:00:00 ethertype 0x0806 fwd queue 3" % valports[0], "testpmd> ")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("arp")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="0")

            self.dut.send_expect("start", "testpmd> ")
            self.filter_send_packet("syn")
            time.sleep(2)
            out = self.dut.send_expect("stop", "testpmd> ")
            self.verify_result(out, tx_pkts="1", expect_queue="0")
        else:
            self.verify(False, "%s nic not support this test" % self.nic)
    def test_jumbo_frame_size(self):
        
        self.verify(self.nic not in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"], "%s nic not support this test" % self.nic)
        self.pmdout.start_testpmd(
            "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1 --mbcache=200 --mbuf-size=2048 --max-pkt-len=9600" % portMask)
        port = self.tester.get_local_port(valports[0])
        txItf = self.tester.get_interface(port)

        port = self.tester.get_local_port(valports[1])
        rxItf = self.tester.get_interface(port)
        self.tester.send_expect("ifconfig %s mtu %s" % (txItf, 9200), "# ")
        self.tester.send_expect("ifconfig %s mtu %s" % (rxItf, 9200), "# ")

        self.dut.send_expect(
            "set stat_qmap rx %s 0 0" % valports[0], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 0 0" % valports[1], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 1 1" % valports[0], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 1 1" % valports[1], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 2 2" % valports[0], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 2 2" % valports[1], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 3 3" % valports[0], "testpmd> ")
        self.dut.send_expect(
            "set stat_qmap rx %s 3 3" % valports[1], "testpmd> ")
        self.dut.send_expect(
            "vlan set strip off %s" % valports[0], "testpmd> ")
        self.dut.send_expect(
            "vlan set strip off %s" % valports[1], "testpmd> ")
        self.dut.send_expect(
            "vlan set filter off %s" % valports[0], "testpmd> ")
        self.dut.send_expect(
            "vlan set filter off %s" % valports[1], "testpmd> ")
        self.dut.send_expect(
            "syn_filter %s add priority high queue 2" % valports[0], "testpmd> ")

        self.dut.send_expect("start", "testpmd> ", 120)

        self.filter_send_packet("jumbo")
        time.sleep(1)

        out = self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd>")

        self.verify_result(out, tx_pkts="1", expect_queue="2")

        self.dut.send_expect("start", "testpmd> ")

        self.filter_send_packet("arp")
        time.sleep(1)
        out = self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd>")

        self.verify_result(out, tx_pkts="1", expect_queue="0")

        self.dut.send_expect(
            "syn_filter %s del priority high queue 2" % valports[0], "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.filter_send_packet("jumbo")
        time.sleep(1)
        out = self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("clear port stats all", "testpmd>")

        self.verify_result(out, tx_pkts="1", expect_queue="0")
        self.tester.send_expect("ifconfig %s mtu %s" % (txItf, 1500), "# ")
        self.tester.send_expect("ifconfig %s mtu %s" % (rxItf, 1500), "# ")

    def test_128_queues(self):
        # testpmd can't support assign queue to received package, so can't test
        self.verify(False, "testpmd not support assign queue 127 received package")
        if self.nic == "niantic":
            global valports
            total_mbufs = self.request_mbufs(128) * len(valports)
            self.pmdout.start_testpmd(
                "all", "--disable-rss --rxq=128 --txq=128 --portmask=%s --nb-cores=8 --total-num-mbufs=%d" % (portMask, total_mbufs))
            self.dut.send_expect(
                "set stat_qmap rx %s 0 0" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "set stat_qmap rx %s 0 0" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "vlan set strip off %s" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "vlan set strip off %s" % valports[1], "testpmd> ")
            self.dut.send_expect(
                "vlan set filter off %s" % valports[0], "testpmd> ")
            self.dut.send_expect(
                "vlan set filter off %s" % valports[1], "testpmd> ")
            frames_to_send = 1
            queue = ['64', '127', '128']

            for i in [0, 1, 2]:
                if i == 2:
                    out = self.dut.send_expect(
                        "set stat_qmap rx %s %s %s" % (valports[0], queue[i], (i + 1)), "testpmd> ")
                    self.verify('Invalid RX queue %s' %
                                (queue[i]) in out, "set filters error")
                    out = self.dut.send_expect(
                        "5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port %s src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority 3 queue %s " % (valports[0], (i + 1), queue[i]), "testpmd> ")
                    self.verify('error' in out, "set filters error")
                    continue
                else:
                    self.dut.send_expect("set stat_qmap rx %s %s %s" %
                                         (valports[0], queue[i], (i + 1)), "testpmd> ")
                    out = self.dut.send_expect("5tuple_filter %s add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port %s src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority %d queue %s " % (
                        valports[0], (i + 1), (3 - i), queue[i]), "testpmd> ")
                    self.dut.send_expect("start", "testpmd> ", 120)
                global filters_index
                filters_index = i
                self.filter_send_packet("packet")
                time.sleep(1)
                out = self.dut.send_expect("stop", "testpmd> ")
                cmd = "Stats reg  %s RX-packets:             ([0-9]+)" % (
                    i + 1)
                result_scanner = r"%s" % cmd
                scanner = re.compile(result_scanner, re.DOTALL)
                m = scanner.search(out)
                cur_pkt = m.group(1)
                self.verify(
                    int(cur_pkt) == frames_to_send, "packet pass assert error")

            self.dut.send_expect("quit", "#")
        else:
            self.verify(False, "%s not support this test" % self.nic)

    def test_perf_generic_filter_perf(self):
        self.pmdout.start_testpmd(
            "all", "--disable-rss --rxq=4 --txq=4 --portmask=%s --nb-cores=8 --nb-ports=1" % portMask)
        self.port_config()
        print valports[0], valports[1]
        tx_port = self.tester.get_local_port(valports[0])
        tx_mac = self.dut.get_mac_address(valports[0])
        txItf = self.tester.get_interface(tx_port)

        rx_port = self.tester.get_local_port(valports[1])
        rxItf = self.tester.get_interface(rx_port)
        package_sizes = [64, 128, 256, 512, 1024, 1280, 1518]
        print tx_mac
        print self.dut.ports_info[valports[0]], self.dut.ports_info[valports[1]]
        test_type = {
            "syn": ["syn_filter add 0 priority high queue 1", "syn_filter del 0 priority high queue 1"],
            "ethertype": ["add_ethertype_filter 0 ethertype 0x0806 priority disable 0 queue 2 index 1", "remove_ethertype_filter 0 index 1"],
            "5tuple": ["5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x02 priority 3 queue 3", "5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x02 priority 3 queue 3"]
        }
        stream_config = {
            "syn": 'Ether(dst="%s")/IP(src="2.2.2.5",dst="2.2.2.4")/TCP(dport=80,flags="S")/("X"*64)',
            "ethertype": 'Ether(dst="%s")/ARP(pdst="192.168.1.1")' % tx_mac,
            "5tuple": 'flows.append(Ether(dst="%s")/IP(src="2.2.2.4",dst="2.2.2.5")/TCP(sport=1,dport=1,flags=0)/("X"*%d))',
        }
        dts.results_table_add_header(
            ['pack_size', "filter_type", "enable", "disable", "perf_compare"])
        for key in test_type.keys():
            if "5tuple" != key:
                pps_lists = []
                for i in range(2):
                    self.dut.send_expect(test_type[key][i], "testpmd> ", 15)
                    self.dut.send_expect("start", "testpmd> ", 120)
                    self.tester.scapy_append('flows = []')
                    self.tester.scapy_append(
                        'flows.append(%s)' % stream_config[key])
                    self.tester.scapy_append(
                        'wrpcap("generic_firlter.pcap",flows)')
                    self.tester.scapy_execute()
                    tgen_input = []
                    tgen_input.append(
                        (tx_port, rx_port, "generic_firlter.pcap"))
                    _, pps = self.tester.traffic_generator_throughput(
                        tgen_input)
                    pps_lists.append(pps)
                dts.results_table_add_row(
                    ["defult", key, pps_lists[0], pps_lists[1], (pps_lists[0] - pps_lists[1]) / float(pps_lists[1])])
            # this is a TCP/IP package, need test different payload_size
            if ("5tuple" == key) and ("niantic" == self.nic):
                for package_size in package_sizes:
                    payload_size = package_size - \
                        HEADER_SIZE["tcp"] - HEADER_SIZE[
                            'ip'] - HEADER_SIZE['eth']
                    pps_lists = []
                    for i in range(2):
                        self.dut.send_expect(
                            test_type[key][i], "testpmd> ", 15)
                        self.dut.send_expect("start", "testpmd> ", 120)
                        self.tester.scapy_append('flows = []')
                        self.tester.scapy_append('flows.append(%s)' % (
                            stream_config[key] % (tx_mac, payload_size)))
                        self.tester.scapy_append(
                            'wrpcap("generic_firlter.pcap",flows)')
                        self.tester.scapy_execute()
                        tgen_input = []
                        # tgen_input.append((txItf, rxItf, "generic_firlter.pcap"))
                        tgen_input.append(
                            (tx_port, rx_port, "generic_firlter.pcap"))
                        print tgen_input
                        _, pps = self.tester.traffic_generator_throughput(
                            tgen_input)
                        pps_lists.append(pps)
                    dts.results_table_add_row(
                        [package_size, key, pps_lists[0], pps_lists[1], (pps_lists[0] - pps_lists[1]) / float(pps_lists[1])])
        dts.results_table_print()

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()
