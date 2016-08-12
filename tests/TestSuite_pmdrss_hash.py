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

Test DPDK1.8 feature: Fortville RSS full support - configuring hash functions.
It can select Toeplitz or simple XOR hash function and it can configure symmetric hash functions.
Support 4*10G, 1*40G and 2*40G NICs.
"""
import time
import random
import re
import utils

testQueues = [16]
reta_entries = []
reta_lines = []
reta_num = 128
# Use scapy to send packets with different source and dest ip.
# and collect the hash result of five tuple and the queue id.
from test_case import TestCase
#
#
# Test class.
#
class TestPmdrssHash(TestCase):
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
        self.dut.send_expect("start", "testpmd>")
        mac = self.dut.get_mac_address(0)

        # send packet with different source and dest ip
        if tran_type == "ipv4-other":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d")], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-tcp":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d")/TCP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-udp":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d")/UDP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-sctp":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d")/SCTP(sport=1024,dport=1024,tag=1)], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-frag":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d",frag=1,flags="MF")], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "l2_payload":
            for i in range(10):
                packet = r'sendp([Ether(src="00:00:00:00:00:0%d",dst="%s")], iface="%s")' % (
                    i + 1, mac, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)

        elif tran_type == "ipv6-other":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-tcp":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/TCP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-udp":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/UDP(sport=1024,dport=1024)], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-sctp":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/SCTP(sport=1024,dport=1024,tag=1)], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-frag":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d",nh=44)/IPv6ExtHdrFragment()], iface="%s")' % (
                    mac, itf, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        else:
            print "\ntran_type error!\n"

        out = self.dut.get_session_output(timeout=1)
        self.dut.send_expect("stop", "testpmd>")
        lines = out.split("\r\n")
        reta_line = {}
        # collect the hash result and the queue id
        for line in lines:
            line = line.strip()
            if len(line) != 0 and line.strip().startswith("port "):
                reta_line = {}
                rexp = r"port (\d)/queue (\d{1,2}): received (\d) packets"
                m = re.match(rexp, line.strip())
                if m:
                    reta_line["port"] = m.group(1)
                    reta_line["queue"] = m.group(2)

            elif len(line) != 0 and line.startswith(("src=",)):
                if "RSS hash" not in line:
                    continue
                for item in line.split("-"):
                    item = item.strip()
                    if(item.startswith("RSS hash")):
                        name, value = item.split("=", 1)

                reta_line[name.strip()] = value.strip()
                reta_lines.append(reta_line)

        self.verifyResult()

    def verifyResult(self):
        """
        Verify whether or not the result passes.
        """

        global reta_lines
        global reta_num
        result = []
        self.result_table_create(
            ['packet index', 'hash value', 'hash index', 'queue id', 'actual queue id', 'pass '])

        i = 0

        for tmp_reta_line in reta_lines:
            status = "false"
            # compute the hash result of five tuple into the 7 LSBs value.
            hash_index = int(tmp_reta_line["RSS hash"], 16) % reta_num
            print reta_entries[hash_index], tmp_reta_line
            if(reta_entries[hash_index] == int(tmp_reta_line["queue"])):
                status = "true"
                result.insert(i, 0)
            else:
                status = "fail"
                result.insert(i, 1)
            self.result_table_add(
                [i, tmp_reta_line["RSS hash"], hash_index, reta_entries[hash_index], tmp_reta_line["queue"], status])
            i = i + 1

        self.result_table_print()
        reta_lines = []
        self.verify(sum(result) == 0, "the reta update function failed!")

    def send_packet_symmetric(self, itf, tran_type):
        """
        Sends packets.
        """
        global reta_lines
        self.tester.scapy_foreground()
        self.dut.send_expect("start", "testpmd>")
        mac = self.dut.get_mac_address(0)

        # send packet with different source and dest ip
        if tran_type == "ipv4-other":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)

        elif tran_type == "ipv4-tcp":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/TCP(sport=1024,dport=1025)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/TCP(sport=1025,dport=1024)], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-udp":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/UDP(sport=1024,dport=1025)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/UDP(sport=1025,dport=1024)], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-sctp":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/SCTP(sport=1024,dport=1025,tag=1)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d")/SCTP(sport=1025,dport=1024,tag=1)], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv4-frag":
            for i in range(10):
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d",frag=1,flags="MF")], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IP(src="192.168.0.%d", dst="192.168.0.%d",frag=1,flags="MF")], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "l2_payload":
            for i in range(10):
                packet = r'sendp([Ether(src="00:00:00:00:00:%02d",dst="%s")], iface="%s")' % (
                    i + 1, mac, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-other":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:3::%d", dst="3ffe:2501:200:1fff::%d")], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)

        elif tran_type == "ipv6-tcp":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/TCP(sport=1024,dport=1025)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:3::%d", dst="3ffe:2501:200:1fff::%d")/TCP(sport=1025,dport=1024)], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)

        elif tran_type == "ipv6-udp":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/UDP(sport=1024,dport=1025)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/UDP(sport=1025,dport=1024)], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-sctp":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/SCTP(sport=1024,dport=1025,tag=1)], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/SCTP(sport=1025,dport=1024,tag=1)], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        elif tran_type == "ipv6-frag":
            for i in range(4):
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d",nh=44)/IPv6ExtHdrFragment()], iface="%s")' % (
                    mac, i + 1, i + 2, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
                packet = r'sendp([Ether(dst="%s")/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d",nh=44)/IPv6ExtHdrFragment()], iface="%s")' % (
                    mac, i + 2, i + 1, itf)
                self.tester.scapy_append(packet)
                self.tester.scapy_execute()
                time.sleep(.5)
        else:
            print "\ntran_type error!\n"

        out = self.dut.get_session_output(timeout=1)
        self.dut.send_expect("stop", "testpmd>")
        lines = out.split("\r\n")

        # collect the hash result of five tuple and the queue id
        for line in lines:
            line = line.strip()
            if len(line) != 0 and line.strip().startswith("port "):
                reta_line = {}
                rexp = r"port (\d)/queue (\d{1,2}): received (\d) packets"
                m = re.match(rexp, line.strip())
                if m:
                    reta_line["port"] = m.group(1)
                    reta_line["queue"] = m.group(2)
            elif len(line) != 0 and line.startswith(("src=",)):
                for item in line.split("-"):
                    item = item.strip()
                    if(item.startswith("RSS hash")):
                        name, value = item.split("=", 1)

                reta_line[name.strip()] = value.strip()
                reta_lines.append(reta_line)

        self.verifyResult_symmetric()

    def verifyResult_symmetric(self):
        """
        Verify whether or not the result passes.
        """

        global reta_lines
        global reta_num
        result = []
        self.result_table_create(
            ['packet index', 'RSS hash', 'hash index', 'queue id', 'actual queue id', 'pass '])

        i = 0
        for tmp_reta_line in reta_lines:
            status = "true"
            # compute the hash result of five tuple into the 7 LSBs value.
            hash_index = int(tmp_reta_line["RSS hash"], 16) % reta_num

            if(i % 2 == 1):
                if(pre_RSS_hash == tmp_reta_line["RSS hash"]):
                    status = "true"
                    result.insert((i - 1) / 2, 0)
                else:
                    status = "fail"
                    result.insert((i - 1) / 2, 1)
            pre_RSS_hash = tmp_reta_line["RSS hash"]

            self.result_table_add(
                [i, tmp_reta_line["RSS hash"], hash_index, reta_entries[hash_index], tmp_reta_line["queue"], status])
            i = i + 1

        self.result_table_print()
        reta_lines = []
        self.verify(
            sum(result) == 0, "the symmetric RSS hash function failed!")

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """

        self.verify(self.nic in ["fortville_eagle", "fortville_spirit",
                    "fortville_spirit_single", "redrockcanyou", "atwood", "boulderrapid", "fortpark_TLV"],
                    "NIC Unsupported: " + str(self.nic))
        global reta_num
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            reta_num = 512
        elif self.nic in ["niantic"]:
            reta_num = 128
        elif self.nic in ["redrockcanyou", "atwood", "boulderrapid"]:
            reta_num = 128
        else:
            self.verify(False, "NIC Unsupported:%s" % str(self.nic))
        ports = self.dut.get_ports(self.nic)
        self.verify(len(ports) >= 1, "Not enough ports available")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_toeplitz(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        iptypes = {'ipv4-sctp': 'sctp',
                   'ipv4-other': 'ip',
                   'ipv4-frag': 'ip',
                   'ipv4-udp': 'udp',
                   'ipv4-tcp': 'tcp',
                   # this hash not support in dpdk2.0
                   # 'l2_payload':'ether',
                   'ipv6-other': 'ip',
                   'ipv6-sctp': 'ip',
                   'ipv6-udp': 'udp',
                   'ipv6-tcp': 'tcp',
                   'ipv6-frag': 'ip'
                   }

        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --rxq=%d --txq=%d" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            for iptype, rsstype in iptypes.items():
                self.dut.send_expect("set verbose 8", "testpmd> ")
                self.dut.send_expect("set fwd rxonly", "testpmd> ")
                self.dut.send_expect(
                    "set nbcore %d" % (queue + 1), "testpmd> ")

                self.dut.send_expect("port stop all", "testpmd> ")
                # self.dut.send_expect("port config all rss ip", "testpmd> ")
                self.dut.send_expect(
                    "set_hash_global_config  0 toeplitz %s enable" % iptype, "testpmd> ")
                self.dut.send_expect("port start all", "testpmd> ")
                out = self.dut.send_expect(
                    "port config all rss %s" % rsstype, "testpmd> ")
                self.verify("error" not in out, "Configuration of RSS hash failed: Invalid argument")
                # configure the reta with specific mappings.
                for i in range(reta_num):
                    reta_entries.insert(i, random.randint(0, queue - 1))
                    self.dut.send_expect(
                        "port config 0 rss reta (%d,%d)" % (i, reta_entries[i]), "testpmd> ")

                self.send_packet(itf, iptype)

        self.dut.send_expect("quit", "# ", 30)

    def test_toeplitz_symmetric(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        iptypes = {'ipv4-sctp': 'sctp',
                   'ipv4-other': 'ip',
                   'ipv4-frag': 'ip',
                   'ipv4-udp': 'udp',
                   'ipv4-tcp': 'tcp',
                   # this hash not support in dpdk2.0
                   # 'l2_payload':'ether',
                   'ipv6-other': 'ip',
                   'ipv6-sctp': 'ip',
                   'ipv6-udp': 'udp',
                   'ipv6-tcp': 'tcp',
                   'ipv6-frag': 'ip'
                   }

        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --rxq=%d --txq=%d" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            for iptype, rsstype in iptypes.items():
                self.dut.send_expect("set verbose 8", "testpmd> ")
                self.dut.send_expect("set fwd rxonly", "testpmd> ")
                self.dut.send_expect(
                    "set nbcore %d" % (queue + 1), "testpmd> ")

                self.dut.send_expect("port stop all", "testpmd> ")
                self.dut.send_expect(
                    "set_hash_global_config 0 toeplitz %s enable" % iptype, "testpmd> ")
                self.dut.send_expect(
                    "set_sym_hash_ena_per_port 0 enable", "testpmd> ")
                self.dut.send_expect("port start all", "testpmd> ")
                out = self.dut.send_expect(
                    "port config all rss %s" % rsstype, "testpmd> ")
                self.verify("error" not in out, "Configuration of RSS hash failed: Invalid argument")

                # configure the reta with specific mappings.
                for i in range(reta_num):
                    reta_entries.insert(i, random.randint(0, queue - 1))
                    self.dut.send_expect(
                        "port config 0 rss reta (%d,%d)" % (i, reta_entries[i]), "testpmd> ")

                self.send_packet_symmetric(itf, iptype)

            self.dut.send_expect("quit", "# ", 30)

    def test_simple(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        iptypes = {'ipv4-sctp': 'sctp',
                   'ipv4-other': 'ip',
                   'ipv4-frag': 'ip',
                   'ipv4-udp': 'udp',
                   'ipv4-tcp': 'tcp',
                   # this hass not support in dpdk 2.0
                   # 'l2_payload':'ether',
                   'ipv6-other': 'ip',
                   'ipv6-sctp': 'ip',
                   'ipv6-udp': 'udp',
                   'ipv6-tcp': 'tcp',
                   'ipv6-frag': 'ip'
                   }

        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --rxq=%d --txq=%d" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            for iptype, rsstype in iptypes.items():
                self.logger.info("***********************%s rss test********************************" % iptype)
                self.dut.send_expect("set verbose 8", "testpmd> ")
                self.dut.send_expect("set fwd rxonly", "testpmd> ")
                self.dut.send_expect(
                    "set nbcore %d" % (queue + 1), "testpmd> ")

                self.dut.send_expect("port stop all", "testpmd> ")
                # some nic not support change hash algorithm
                if self.kdriver not in ["fm10k"]:
                    self.dut.send_expect(
                        "set_hash_global_config 0 simple_xor %s enable" % iptype, "testpmd> ")
                self.dut.send_expect("port start all", "testpmd> ")
                out = self.dut.send_expect(
                    "port config all rss %s" % rsstype, "testpmd> ")
                self.verify("error" not in out, "Configuration of RSS hash failed: Invalid argument")
                # configure the reta with specific mappings.
                for i in range(reta_num):
                    reta_entries.insert(i, random.randint(0, queue - 1))
                    self.dut.send_expect(
                        "port config 0 rss reta (%d,%d)" % (i, reta_entries[i]), "testpmd> ")

                self.send_packet(itf, iptype)

            self.dut.send_expect("quit", "# ", 30)

    def test_simple_symmetric(self):

        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        iptypes = {'ipv4-sctp': 'sctp',
                   'ipv4-other': 'ip',
                   'ipv4-frag': 'ip',
                   'ipv4-udp': 'udp',
                   'ipv4-tcp': 'tcp',
                   # this hash not support in dpdk2.0
                   # 'l2_payload':'ether',
                   'ipv6-other': 'ip',
                   'ipv6-sctp': 'ip',
                   'ipv6-udp': 'udp',
                   'ipv6-tcp': 'tcp',
                   'ipv6-frag': 'ip'
                   }
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --rxq=%d --txq=%d" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            for iptype, rsstype in iptypes.items():
                self.dut.send_expect("set verbose 8", "testpmd> ")
                self.dut.send_expect("set fwd rxonly", "testpmd> ")
                self.dut.send_expect(
                    "set nbcore %d" % (queue + 1), "testpmd> ")

                self.dut.send_expect("port stop all", "testpmd> ")
                # self.dut.send_expect("port config all rss ip", "testpmd> ")
                self.dut.send_expect(
                    "set_hash_global_config 0 simple_xor %s enable" % iptype, "testpmd> ")
                self.dut.send_expect(
                    "set_sym_hash_ena_per_port 0 enable", "testpmd> ")
                self.dut.send_expect("port start all", "testpmd> ")

                out = self.dut.send_expect(
                    "port config all rss %s" % rsstype, "testpmd> ")
                self.verify("error" not in out, "Configuration of RSS hash failed: Invalid argument")
                # configure the reta with specific mappings.
                for i in range(reta_num):
                    reta_entries.insert(i, random.randint(0, queue - 1))
                    self.dut.send_expect(
                        "port config 0 rss reta (%d,%d)" % (i, reta_entries[i]), "testpmd> ")

                self.send_packet_symmetric(itf, iptype)

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
