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

Test DPDK2.3 feature: 
1.Fortville support granularity configuration of RSS.
By default Fortville uses hash input set preloaded from NVM image which includes all fields
- IPv4/v6+TCP/UDP port. Potential problem for this is global configuration per device and can
affect all ports. It is required that hash input set can be configurable,  such as using IPv4
only or IPv6 only or IPv4/v6+TCP/UDP.

2.Fortville support 32-bit GRE keys.
By default Fortville extracts only 24 bits of GRE key to FieldVector (NVGRE use case) but
for Telco use cases full 32-bit GRE key is needed. It is required that both 24-bit and 32-bit
keys for GRE should be supported. the test plan is to test the API to switch between 24-bit and
32-bit keys

Support 4*10G, 1*40G and 2*40G NICs.
"""
import time
import random
import re
import dts
import dut

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
class TestFortvilleRssGranularityConfig(TestCase):
    #
    #
    # Utility methods and other non-test code.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.
        """

        self.verify(self.nic in ["fortville_eagle", "fortville_spirit",
                    "fortville_spirit_single"],
                    "NIC Unsupported: " + str(self.nic))
        global reta_num
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single"]:
            reta_num = 512
        else:
            self.verify(False, "NIC Unsupported:%s" % str(self.nic))
        ports = self.dut.get_ports(self.nic)
        self.verify(len(ports) >= 1, "Not enough ports available")

    def set_up(self):
        """
        Run before each test case.
        """
        pass
    def send_packet(self, itf, tran_type):
        """
        Sends packets.
        """
        global reta_lines
        global reta_num
	self.tester.scapy_foreground()
        self.dut.send_expect("start", "testpmd>")
        mac = self.dut.get_mac_address(0)

        # send packet with different source and dest ip
	i = 0
        if tran_type == "ipv4-other":
            packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d", proto=47)/GRE(key_present=1,proto=2048,key=67108863)/IP()], iface="%s")' % (
                mac, itf, i + 1, i + 2, itf)
            self.tester.scapy_append(packet)
            self.tester.scapy_execute()
            time.sleep(.5)
        elif tran_type == "ipv4-tcp":
            packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d")/TCP(sport=1024,dport=1024)], iface="%s")' % (
                mac, itf, i + 1, i + 2, itf)
            self.tester.scapy_append(packet)
            self.tester.scapy_execute()
            time.sleep(.5)
        elif tran_type == "ipv4-udp":
            packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IP(src="192.168.0.%d", dst="192.168.0.%d")/UDP(sport=1024,dport=1024)], iface="%s")' % (
                mac, itf, i + 1, i + 2, itf)
            self.tester.scapy_append(packet)
            self.tester.scapy_execute()
            time.sleep(.5)
        elif tran_type == "l2_payload":
            packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/Dot1Q(id=0x8100,vlan=%s)/Dot1Q(id=0x8100,vlan=%s)], iface="%s")' % (
                mac, itf, i + 1, i + 2, itf)
	    self.tester.scapy_append(packet)
            self.tester.scapy_execute()
            time.sleep(.5)
        elif tran_type == "ipv6-tcp":
            packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/TCP(sport=1024,dport=1024)], iface="%s")' % (
                mac, itf, i + 1, i + 2, itf)
            self.tester.scapy_append(packet)
            self.tester.scapy_execute()
            time.sleep(.5)
        elif tran_type == "ipv6-udp":
            packet = r'sendp([Ether(dst="%s", src=get_if_hwaddr("%s"))/IPv6(src="3ffe:2501:200:1fff::%d", dst="3ffe:2501:200:3::%d")/UDP(sport=1024,dport=1024)], iface="%s")' % (
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
                for item in line.split("-"):
                    item = item.strip()
                    if(item.startswith("RSS hash")):
                        name, value = item.split("=", 1)

                reta_line[name.strip()] = value.strip()
                reta_lines.append(reta_line)
        
	self.append_result_table()
 
    def append_result_table(self):
        """
        Append the hash value and queue id into table.
        """

        global reta_lines
        global reta_num

        #append the the hash value and queue id into table
        dts.results_table_add_header(
            ['packet index', 'hash value', 'hash index', 'queue id'])

        i = 0

        for tmp_reta_line in reta_lines:
            
            # compute the hash result of five tuple into the 7 LSBs value.
            hash_index = int(tmp_reta_line["RSS hash"], 16) % reta_num
	    dts.results_table_add_row(
                [i, tmp_reta_line["RSS hash"], hash_index, tmp_reta_line["queue"]])
            i = i + 1


    def test_ipv4_tcp(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
	global reta_lines
        flag = 1
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --portmask=0x3 --rxq=%d --txq=%d --txqflags=0" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            self.dut.send_expect("set verbose 8", "testpmd> ")
            self.dut.send_expect("set fwd rxonly", "testpmd> ")

            self.dut.send_expect("port stop all", "testpmd> ")
            self.dut.send_expect(
                "set_hash_global_config  0 toeplitz ipv4-tcp enable", "testpmd> ")
            self.dut.send_expect("port start all", "testpmd> ")
            self.dut.send_expect(
                "port config all rss tcp", "testpmd> ")
            self.send_packet(itf, "ipv4-tcp")
	    
	    #set hash input set to "none" by testpmd on dut
	    self.dut.send_expect("set_hash_input_set 0 ipv4-tcp none select", "testpmd> ")
	    self.send_packet(itf, "ipv4-tcp")

	    #set hash input set by testpmd on dut, enable src-ipv4 & dst-ipv4
	    self.dut.send_expect("set_hash_input_set 0 ipv4-tcp src-ipv4 add", "testpmd> ")
	    self.dut.send_expect("set_hash_input_set 0 ipv4-tcp dst-ipv4 add", "testpmd> ")
            self.send_packet(itf, "ipv4-tcp")

	    #set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4, tcp-src-port, tcp-dst-port
	    self.dut.send_expect("set_hash_input_set 0 ipv4-tcp tcp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-tcp tcp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv4-tcp")

	    #set hash input set by testpmd on dut, enable tcp-src-port, tcp-dst-port
	    self.dut.send_expect("set_hash_input_set 0 ipv4-tcp none select", "testpmd> ")
	    self.dut.send_expect("set_hash_input_set 0 ipv4-tcp tcp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-tcp tcp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv4-tcp")

        self.dut.send_expect("quit", "# ", 30)
	dts.results_table_print()
	self.verify(len(dts.results_table_rows) > 1, "There is no data in the table, testcase failed!")

	
	if ((dts.results_table_rows[1][1]==dts.results_table_rows[2][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[2][3])):
	    flag = 0
	    self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
	elif ((dts.results_table_rows[1][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
	elif ((dts.results_table_rows[2][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
	elif ((dts.results_table_rows[1][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
	elif ((dts.results_table_rows[3][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[3][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
	elif ((dts.results_table_rows[1][1]!=dts.results_table_rows[4][1])or(dts.results_table_rows[1][3]!=dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are different, rss_granularity_config failed!")

	reta_lines = []
    
    def test_ipv4_udp(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        global reta_lines
        flag = 1
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --portmask=0x3 --rxq=%d --txq=%d --txqflags=0" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            self.dut.send_expect("set verbose 8", "testpmd> ")
            self.dut.send_expect("set fwd rxonly", "testpmd> ")

            self.dut.send_expect("port stop all", "testpmd> ")
            self.dut.send_expect(
                "set_hash_global_config  0 toeplitz ipv4-udp enable", "testpmd> ")
            self.dut.send_expect("port start all", "testpmd> ")
            self.dut.send_expect(
                "port config all rss udp", "testpmd> ")
            self.send_packet(itf, "ipv4-udp")

            #set hash input set to "none" by testpmd on dut
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp none select", "testpmd> ")
            self.send_packet(itf, "ipv4-udp")

            #set hash input set by testpmd on dut, enable src-ipv4 & dst-ipv4
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp src-ipv4 add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp dst-ipv4 add", "testpmd> ")
            self.send_packet(itf, "ipv4-udp")

            #set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4, udp-src-port, udp-dst-port
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp udp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp udp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv4-udp")

            #set hash input set by testpmd on dut, enable udp-src-port, udp-dst-port
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp none select", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp udp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-udp udp-dst-port add", "testpmd> ")
	    self.send_packet(itf, "ipv4-udp")

        self.dut.send_expect("quit", "# ", 30)
        dts.results_table_print()
        self.verify(len(dts.results_table_rows) > 1, "There is no data in the table, testcase failed!")

        #check the results   
        if ((dts.results_table_rows[1][1]==dts.results_table_rows[2][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[2][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[3][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[3][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]!=dts.results_table_rows[4][1])or(dts.results_table_rows[1][3]!=dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are different, rss_granularity_config failed!")

        reta_lines = []

    def test_ipv6_tcp(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        global reta_lines
        flag = 1
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --portmask=0x3 --rxq=%d --txq=%d --txqflags=0" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            self.dut.send_expect("set verbose 8", "testpmd> ")
            self.dut.send_expect("set fwd rxonly", "testpmd> ")

            self.dut.send_expect("port stop all", "testpmd> ")
            self.dut.send_expect(
                "set_hash_global_config  0 toeplitz ipv6-tcp enable", "testpmd> ")
            self.dut.send_expect("port start all", "testpmd> ")
            self.dut.send_expect(
                "port config all rss tcp", "testpmd> ")
            self.send_packet(itf, "ipv6-tcp")

            #set hash input set to "none" by testpmd on dut
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp none select", "testpmd> ")
            self.send_packet(itf, "ipv6-tcp")

            #set hash input set by testpmd on dut, enable src-ipv6 & dst-ipv6
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp src-ipv6 add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp dst-ipv6 add", "testpmd> ")
            self.send_packet(itf, "ipv6-tcp")

            #set hash input set by testpmd on dut, enable src-ipv6, dst-ipv6, tcp-src-port, tcp-dst-port
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp tcp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp tcp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv6-tcp")

            #set hash input set by testpmd on dut, enable tcp-src-port, tcp-dst-port
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp none select", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp tcp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-tcp tcp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv6-tcp")

	self.dut.send_expect("quit", "# ", 30)
        dts.results_table_print()
        self.verify(len(dts.results_table_rows) > 1, "There is no data in the table, testcase failed!")

        #check the results
        if ((dts.results_table_rows[1][1]==dts.results_table_rows[2][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[2][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[3][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[3][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]!=dts.results_table_rows[4][1])or(dts.results_table_rows[1][3]!=dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are different, rss_granularity_config failed!")

        reta_lines = []

    def test_ipv6_udp(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        global reta_lines
        flag = 1
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --portmask=0x3 --rxq=%d --txq=%d --txqflags=0" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            self.dut.send_expect("set verbose 8", "testpmd> ")
            self.dut.send_expect("set fwd rxonly", "testpmd> ")

            self.dut.send_expect("port stop all", "testpmd> ")
            self.dut.send_expect(
                "set_hash_global_config  0 toeplitz ipv6-udp enable", "testpmd> ")
            self.dut.send_expect("port start all", "testpmd> ")
            self.dut.send_expect(
                "port config all rss udp", "testpmd> ")
            self.send_packet(itf, "ipv6-udp")

            #set hash input set to "none" by testpmd on dut
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp none select", "testpmd> ")
            self.send_packet(itf, "ipv6-udp")

            #set hash input set by testpmd on dut, enable src-ipv6 & dst-ipv6
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp src-ipv6 add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp dst-ipv6 add", "testpmd> ")
            self.send_packet(itf, "ipv6-udp")

            #set hash input set by testpmd on dut, enable src-ipv6, dst-ipv6, udp-src-port, udp-dst-port
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp udp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp udp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv6-udp")

            #set hash input set by testpmd on dut, enable udp-src-port, udp-dst-port
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp none select", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp udp-src-port add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv6-udp udp-dst-port add", "testpmd> ")
            self.send_packet(itf, "ipv6-udp")

        self.dut.send_expect("quit", "# ", 30)
        dts.results_table_print()
        self.verify(len(dts.results_table_rows) > 1, "There is no data in the table, testcase failed!")

        #check the results
        if ((dts.results_table_rows[1][1]==dts.results_table_rows[2][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[2][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[2][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[2][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[3][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[3][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]!=dts.results_table_rows[4][1])or(dts.results_table_rows[1][3]!=dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are different, rss_granularity_config failed!")

        reta_lines = []

    def test_dual_vlan(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        global reta_lines
        flag = 1
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --portmask=0x3 --rxq=%d --txq=%d --txqflags=0" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            self.dut.send_expect("set verbose 8", "testpmd> ")
            self.dut.send_expect("set fwd rxonly", "testpmd> ")

            self.dut.send_expect("port stop all", "testpmd> ")
            self.dut.send_expect("vlan set qinq on 0", "testpmd> ")
	    self.dut.send_expect(
                "set_hash_global_config  0 toeplitz l2_payload enable", "testpmd> ")
            self.dut.send_expect("port start all", "testpmd> ")
            self.dut.send_expect(
                "port config all rss ether", "testpmd> ")
            self.send_packet(itf, "l2_payload")

            #set hash input set to "none" by testpmd on dut
            self.dut.send_expect("set_hash_input_set 0 l2_payload none select", "testpmd> ")
            self.send_packet(itf, "l2_payload")

            #set hash input set by testpmd on dut, enable ovlan
            self.dut.send_expect("set_hash_input_set 0 l2_payload ovlan add", "testpmd> ")
            self.send_packet(itf, "l2_payload")

            #set hash input set by testpmd on dut, enable ovlan & ivlan
            self.dut.send_expect("set_hash_input_set 0 l2_payload ivlan add", "testpmd> ")
            self.send_packet(itf, "l2_payload")


	self.dut.send_expect("quit", "# ", 30)
        dts.results_table_print()
        self.verify(len(dts.results_table_rows) > 1, "There is no data in the table, testcase failed!")

        #check the results
        if ((dts.results_table_rows[1][1]!=dts.results_table_rows[2][1])or(dts.results_table_rows[1][3]!=dts.results_table_rows[2][3])):
            flag = 0
            self.verify(flag, "The two hash values are different, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[3][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[4][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[3][1]==dts.results_table_rows[4][1])or(dts.results_table_rows[3][3]==dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")

        reta_lines = []

    def test_GRE_keys(self):
        dutPorts = self.dut.get_ports(self.nic)
        localPort = self.tester.get_local_port(dutPorts[0])
        itf = self.tester.get_interface(localPort)
        global reta_num
        global reta_lines
        flag = 1
        self.dut.kill_all()

        # test with different rss queues
        for queue in testQueues:
            self.dut.send_expect(
                "./%s/app/testpmd  -c fffff -n %d -- -i --coremask=0xffffe --portmask=0x3 --rxq=%d --txq=%d --txqflags=0" %
                (self.target, self.dut.get_memory_channels(), queue, queue), "testpmd> ", 120)

            self.dut.send_expect("set verbose 8", "testpmd> ")
            self.dut.send_expect("set fwd rxonly", "testpmd> ")

            self.dut.send_expect("port stop all", "testpmd> ")
            self.dut.send_expect(
                "set_hash_global_config  0 toeplitz ipv4-other enable", "testpmd> ")
            self.dut.send_expect("port start all", "testpmd> ")
            self.dut.send_expect(
                "port config all rss all", "testpmd> ")
            self.send_packet(itf, "ipv4-other")

            #set hash input set to "none" by testpmd on dut
            self.dut.send_expect("set_hash_input_set 0 ipv4-other none select", "testpmd> ")
            self.send_packet(itf, "ipv4-other")

            #set hash input set by testpmd on dut, enable src-ipv4 & dst-ipv4
            self.dut.send_expect("set_hash_input_set 0 ipv4-other src-ipv4 add", "testpmd> ")
            self.dut.send_expect("set_hash_input_set 0 ipv4-other dst-ipv4 add", "testpmd> ")
	    self.send_packet(itf, "ipv4-other")

            #set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4, gre-key-len 3
            self.dut.send_expect("global_config 0 gre-key-len 3", "testpmd> ")
	    self.dut.send_expect("set_hash_input_set 0 ipv4-other gre-key add", "testpmd> ")
            self.send_packet(itf, "ipv4-other")

	    #set hash input set by testpmd on dut, enable src-ipv4, dst-ipv4, gre-key-len 4
            self.dut.send_expect("global_config 0 gre-key-len 4", "testpmd> ")
	    self.send_packet(itf, "ipv4-other")

        self.dut.send_expect("quit", "# ", 30)
        dts.results_table_print()
        self.verify(len(dts.results_table_rows) > 1, "There is no data in the table, testcase failed!")

        #check the results
  	if ((dts.results_table_rows[1][1]==dts.results_table_rows[2][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[2][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]!=dts.results_table_rows[3][1])or(dts.results_table_rows[1][3]!=dts.results_table_rows[3][3])):
            flag = 0
            self.verify(flag, "The two hash values are different, rss_granularity_config failed!")
        elif ((dts.results_table_rows[1][1]==dts.results_table_rows[4][1])or(dts.results_table_rows[1][3]==dts.results_table_rows[4][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")
        elif ((dts.results_table_rows[4][1]==dts.results_table_rows[5][1])or(dts.results_table_rows[4][3]==dts.results_table_rows[5][3])):
            flag = 0
            self.verify(flag, "The two hash values are the same, rss_granularity_config failed!")

        reta_lines = []

	
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
