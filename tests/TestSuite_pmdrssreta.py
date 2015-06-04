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
Test RSS reta (redirection table) update function.
"""
import time
import random
import re
import dts
testQueues = [16]
reta_entries = []
reta_lines = []

# Use scapy to send packets with different source and dest ip.
# and collect the hash result of five tuple and the queue id.
from test_case import TestCase
from pmd_output import PmdOutput
#
#
# Test class.
#
class TestPmdrssreta(TestCase):
    #
    #
    # Utility methods and other non-test code.
    #
    def send_packet(self, itf, tran_type):
        """
        Sends packets.
        """
        global reta_lines

        self.tester.scapy_foreground()
        self.tester.scapy_append('sys.path.append("./")')
        self.tester.scapy_append('from sctp import *')
        self.dut.send_expect("start", "testpmd>")
        mac = self.dut.get_mac_address(0)
        # send packet with different source and dest ip
        if tran_type == "IPV4":
            for i in range(16):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "IPV4&TCP":
            for i in range(16):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/TCP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "IPV4&UDP":
            for i in range(16):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/UDP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "IPV6":
            for i in range(16):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "IPV6&TCP":
            for i in range(16):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/TCP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "IPV6&UDP":
            for i in range(16):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/UDP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        else:
            print "\ntran_type error!\n"

        out = self.dut.send_expect("stop", "testpmd>")
        lines = out.split("\r\n")
        reta_line = {}

        # collect the hash result of five tuple and the queue id
        for line in lines:
            line = line.strip()
            if len(line) != 0 and line.startswith(("src=",)):
                for item in line.split("-"):
                    item = item.strip()
                    if(item.startswith("RSS hash")):
                        name, value = item.split("=", 1)
                        print name + "-" + value

                reta_line[name.strip()] = value.strip()
                reta_lines.append(reta_line)
                reta_line = {}
            elif len(line) != 0 and line.strip().startswith("port "):
                rexp = r"port (\d)/queue (\d{1,2}): received (\d) packets"
                m = re.match(rexp, line.strip())
                if m:
                    reta_line["port"] = m.group(1)
                    reta_line["queue"] = m.group(2)
            elif len(line) != 0 and line.startswith("stop"):
                break
            else:
                pass

        self.verifyResult()

    def verifyResult(self):
        """
        Verify whether or not the result passes.
        """

        global reta_lines
        result = []
        dts.results_table_add_header(
            ['packet index', 'hash value', 'hash index', 'queue id', 'actual queue id', 'pass '])

        i = 0
        for tmp_reta_line in reta_lines:
            status = "false"
            if(self.nic == "niantic"):
                # compute the hash result of five tuple into the 7 LSBs value.
                hash_index = int(tmp_reta_line["RSS hash"], 16) % 128
            else:
                # compute the hash result of five tuple into the 7 LSBs value.
                hash_index = int(tmp_reta_line["RSS hash"], 16) % 512
            if(reta_entries[hash_index] == int(tmp_reta_line["queue"])):
                status = "true"
                result.insert(i, 0)
            else:
                status = "fail"
                result.insert(i, 1)
            dts.results_table_add_row(
                [i, tmp_reta_line["RSS hash"], hash_index, reta_entries[hash_index], tmp_reta_line["queue"], status])
            i = i + 1

        dts.results_table_print()
        reta_lines = []
        self.verify(sum(result) == 0, "the reta update function failed!")

    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.
        """

        self.verify(
            self.nic in ["niantic", "fortville_eagle", "fortville_spirit", "fortville_spirit_single"],
            "NIC Unsupported: " + str(self.nic))
        ports = self.dut.get_ports(self.nic)
        self.ports_socket = self.dut.get_numa_id(ports[0])
        self.verify(len(ports) >= 1, "Not enough ports available")

        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_pmdrss_reta(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        iptypes = ['IPV4']

        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            if(queue == 16):
                self.pmdout.start_testpmd(
                    "all", "--rxq=%d --txq=%d" % (queue, queue), socket=self.ports_socket)
            else:
                self.pmdout.start_testpmd(
                    "all", "--mbcache=128 --rxq=%d --txq=%d" % (queue, queue), socket=self.ports_socket)

            for iptype in iptypes:
                self.dut.send_expect("set verbose 8", "testpmd> ")
                self.dut.send_expect("set fwd rxonly", "testpmd> ")
                self.dut.send_expect(
                    "set nbcore %d" % (queue + 1), "testpmd> ")

                # self.dut.send_expect("port stop all", "testpmd> ")
                # self.dut.send_expect("port config all rss udp", "testpmd> ")
                # self.dut.send_expect("port start all", "testpmd> ")

                # configure the reta with specific mappings.
                if(self.nic == "niantic"):
                    for i in range(128):
                        reta_entries.insert(i, random.randint(0, queue - 1))
                        self.dut.send_expect(
                            "port config 0 rss reta (%d,%d)" % (i, reta_entries[i]), "testpmd> ")
                else:
                    for i in range(512):
                        reta_entries.insert(i, random.randint(0, queue - 1))
                        self.dut.send_expect(
                            "port config 0 rss reta (%d,%d)" % (i, reta_entries[i]), "testpmd> ")

                self.send_packet(itf, iptype)

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
        self.dut.kill_all()