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

Test support of RX/TX Checksum Offload Features by Poll Mode Drivers.

"""

import string
import re
import rst
import utils

from test_case import TestCase
from pmd_output import PmdOutput

class TestChecksumOffload(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        Checksum offload prerequisites.
        """
        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports(self.nic)
        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports for testing")
        self.pmdout = PmdOutput(self.dut)
        self.portMask = utils.create_mask([self.dut_ports[0]])
        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

    def set_up(self):
        """
        Run before each test case.
        """
        if self.dut.want_func_tests:
            self.pmdout.start_testpmd("Default", "--portmask=%s " %
                                      (self.portMask) + "--disable-hw-vlan --enable-rx-cksum " +
                                      "--crc-strip --port-topology=loop", socket=self.ports_socket)
            self.dut.send_expect("set verbose 1", "testpmd>")
            self.dut.send_expect("set fwd csum", "testpmd>")

    def checksum_enablehw(self, port):
            self.dut.send_expect("csum set ip hw %d" % port, "testpmd>")
            self.dut.send_expect("csum set udp hw %d" % port, "testpmd>")
            self.dut.send_expect("csum set tcp hw %d" % port, "testpmd>")
            self.dut.send_expect("csum set sctp hw %d" % port, "testpmd>")

    def checksum_enablesw(self, port):
            self.dut.send_expect("csum set ip sw %d" % port, "testpmd>")
            self.dut.send_expect("csum set udp sw %d" % port, "testpmd>")
            self.dut.send_expect("csum set tcp sw %d" % port, "testpmd>")
            self.dut.send_expect("csum set sctp sw %d" % port, "testpmd>")

    def checksum_validate(self, packets_sent, packets_expected):
        """
        Validate the checksum.
        """
        tx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))
        rx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))

        sniff_src = self.dut.get_mac_address(self.dut_ports[0])
        checksum_pattern = re.compile("chksum.*=.*(0x[0-9a-z]+)")

        chksum = dict()
        result = dict()

        self.tester.send_expect("scapy", ">>> ")

        for packet_type in packets_expected.keys():
            self.tester.send_expect("p = %s" % packets_expected[packet_type], ">>>")
            out = self.tester.send_expect("p.show2()", ">>>")
            chksums = checksum_pattern.findall(out)
            chksum[packet_type] = chksums

        self.tester.send_expect("exit()", "#")

        self.tester.scapy_background()
        self.tester.scapy_append('p = sniff(filter="ether src %s", iface="%s", count=%d)' % (sniff_src, rx_interface, len(packets_sent)))
        self.tester.scapy_append('nr_packets=len(p)')
        self.tester.scapy_append('reslist = [p[i].sprintf("%IP.chksum%;%TCP.chksum%;%UDP.chksum%;%SCTP.chksum%") for i in range(nr_packets)]')
        self.tester.scapy_append('import string')
        self.tester.scapy_append('RESULT = string.join(reslist, ",")')

        # Send packet.
        self.tester.scapy_foreground()

        for packet_type in packets_sent.keys():
            self.tester.scapy_append('sendp([%s], iface="%s")' % (packets_sent[packet_type], tx_interface))

        self.tester.scapy_execute()
        out = self.tester.scapy_get_result()
        packets_received = out.split(',')
        self.verify(len(packets_sent) == len(packets_received), "Unexpected Packets Drop")

        for packet_received in packets_received:
            ip_checksum, tcp_checksum, udp_checksup, sctp_checksum = packet_received.split(';')

            packet_type = ''
            l4_checksum = ''
            if tcp_checksum != '??':
                packet_type = 'TCP'
                l4_checksum = tcp_checksum
            elif udp_checksup != '??':
                packet_type = 'UDP'
                l4_checksum = udp_checksup
            elif sctp_checksum != '??':
                packet_type = 'SCTP'
                l4_checksum = sctp_checksum

            if ip_checksum != '??':
                packet_type = 'IP/' + packet_type
                if chksum[packet_type] != [ip_checksum, l4_checksum]:
                    result[packet_type] = packet_type + " checksum error"
            else:
                packet_type = 'IPv6/' + packet_type
                if chksum[packet_type] != [l4_checksum]:
                    result[packet_type] = packet_type + " checksum error"

        return result

    def test_checksum_offload_with_vlan(self):
        """
        Do not insert IPv4/IPv6 UDP/TCP checksum on the transmit packet.
        Verify that the same number of packet are correctly received on the
        traffic generator side.
        """
        mac = self.dut.get_mac_address(self.dut_ports[0])

        pktsChkErr = {'IP/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/Dot1Q(vlan=1)/IP(chksum=0x0)/UDP(chksum=0xf)/("X"*46)' % mac,
                'IP/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/Dot1Q(vlan=1)/IP(chksum=0x0)/TCP(chksum=0xf)/("X"*46)' % mac,
                'IP/SCTP': 'Ether(dst="%s", src="52:00:00:00:00:00")/Dot1Q(vlan=1)/IP(chksum=0x0)/SCTP(chksum=0xf)/("X"*48)' % mac,
                'IPv6/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/Dot1Q(vlan=1)/IPv6(src="::1")/UDP(chksum=0xf)/("X"*46)' % mac,
                'IPv6/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/Dot1Q(vlan=1)/IPv6(src="::1")/TCP(chksum=0xf)/("X"*46)' % mac}

        pkts = {'IP/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/Dot1Q(vlan=1)/IP(src="127.0.0.2")/UDP()/("X"*46)' % mac,
                    'IP/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/Dot1Q(vlan=1)/IP(src="127.0.0.2")/TCP()/("X"*46)' % mac,
                    'IP/SCTP': 'Ether(dst="02:00:00:00:00:00", src="%s")/Dot1Q(vlan=1)/IP(src="127.0.0.2")/SCTP()/("X"*48)' % mac,
                    'IPv6/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/Dot1Q(vlan=1)/IPv6(src="::2")/UDP()/("X"*46)' % mac,
                    'IPv6/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/Dot1Q(vlan=1)/IPv6(src="::2")/TCP()/("X"*46)' % mac}

        if self.kdriver == "fm10k":
            del pktsChkErr['IP/SCTP']
            del pkts['IP/SCTP']

        self.checksum_enablehw(self.dut_ports[0])
        self.dut.send_expect("start", "testpmd>")
        result = self.checksum_validate(pktsChkErr, pkts)
        self.dut.send_expect("stop", "testpmd>")
        self.verify(len(result) == 0, string.join(result.values(), ","))
        
    def test_checksum_offload_enable(self):
        """
        Insert IPv4/IPv6 UDP/TCP/SCTP checksum on the transmit packet.
        Enable Checksum offload.
        Verify that the same number of packet are correctly received on the
        traffic generator side.
        """
        mac = self.dut.get_mac_address(self.dut_ports[0])

        pkts = {'IP/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(chksum=0x0)/UDP(chksum=0xf)/("X"*46)' % mac,
                'IP/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(chksum=0x0)/TCP(chksum=0xf)/("X"*46)' % mac,
                'IP/SCTP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(chksum=0x0)/SCTP(chksum=0xf)/("X"*48)' % mac,
                'IPv6/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="::1")/UDP(chksum=0xf)/("X"*46)' % mac,
                'IPv6/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="::1")/TCP(chksum=0xf)/("X"*46)' % mac}

        pkts_ref = {'IP/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="127.0.0.2")/UDP()/("X"*46)' % mac,
                    'IP/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="127.0.0.2")/TCP()/("X"*46)' % mac,
                    'IP/SCTP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="127.0.0.2")/SCTP()/("X"*48)' % mac,
                    'IPv6/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="::2")/UDP()/("X"*46)' % mac,
                    'IPv6/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="::2")/TCP()/("X"*46)' % mac}

        if self.kdriver == "fm10k":
            del pkts['IP/SCTP']
            del pkts_ref['IP/SCTP']

        self.checksum_enablehw(self.dut_ports[0])

        self.dut.send_expect("start", "testpmd>")

        result = self.checksum_validate(pkts, pkts_ref)

        self.dut.send_expect("stop", "testpmd>")

        self.verify(len(result) == 0, string.join(result.values(), ","))

    def test_checksum_offload_disable(self):
        """
        Do not insert IPv4/IPv6 UDP/TCP checksum on the transmit packet.
        Disable Checksum offload.
        Verify that the same number of packet are correctly received on
        the traffic generator side.
        """
        mac = self.dut.get_mac_address(self.dut_ports[0])
        sndIP = '10.0.0.1'
        sndIPv6 = '::1'
        sndPkts = {'IP/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s",chksum=0x0)/UDP(chksum=0xf)/("X"*46)' % (mac, sndIP),
                   'IP/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="%s",chksum=0x0)/TCP(chksum=0xf)/("X"*46)' % (mac, sndIP),
                   'IPv6/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="%s")/UDP(chksum=0xf)/("X"*46)' % (mac, sndIPv6),
                   'IPv6/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="%s")/TCP(chksum=0xf)/("X"*46)' % (mac, sndIPv6)}

        expIP = "10.0.0.2"
        expIPv6 = '::2'
        expPkts = {'IP/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/UDP()/("X"*46)' % (mac, expIP),
                   'IP/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IP(src="%s")/TCP()/("X"*46)' % (mac, expIP),
                   'IPv6/UDP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="%s")/UDP()/("X"*46)' % (mac, expIPv6),
                   'IPv6/TCP': 'Ether(dst="02:00:00:00:00:00", src="%s")/IPv6(src="%s")/TCP()/("X"*46)' % (mac, expIPv6)}

        self.dut.send_expect("start", "testpmd>")
        result = self.checksum_validate(sndPkts, expPkts)

        self.verify(len(result) == 0, string.join(result.values(), ","))

        self.dut.send_expect("stop", "testpmd>")

    def benchmark(self, lcore, ptype, mode, flow_format, size_list, nic):
        """
        Test ans report checksum offload performance for given parameters.
        """
        Bps = dict()
        Pps = dict()
        Pct = dict()
        dmac = self.dut.get_mac_address(self.dut_ports[0])

        result = [2, lcore, ptype, mode]
        for size in size_list:
            flow = flow_format % (dmac, size)
            self.tester.scapy_append('wrpcap("test.pcap", [%s])' % flow)
            self.tester.scapy_execute()
            tgenInput = []
            tgenInput.append(
                (self.tester.get_local_port(self.dut_ports[0]), self.tester.get_local_port(self.dut_ports[1]), "test.pcap"))
            tgenInput.append(
                (self.tester.get_local_port(self.dut_ports[1]), self.tester.get_local_port(self.dut_ports[0]), "test.pcap"))
            Bps[str(size)], Pps[
                str(size)] = self.tester.traffic_generator_throughput(tgenInput)
            self.verify(Pps[str(size)] > 0, "No traffic detected")
            Pps[str(size)] /= 1E6
            Pct[str(size)] = (Pps[str(size)] * 100) / \
                self.wirespeed(self.nic, size, 2)

            result.append(Pps[str(size)])
            result.append(Pct[str(size)])

        self.result_table_add(result)

    def test_perf_checksum_throughtput(self):
        """
        Test checksum offload performance.
        """
        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports for testing")

        # sizes = [64, 128, 256, 512, 1024]
        sizes = [64, 128]
        pkts = {'IP/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP()/UDP()/("X"*(%d-46))',
                'IP/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP()/TCP()/("X"*(%d-58))',
                'IP/SCTP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IP()/SCTP()/("X"*(%d-50+2))',
                'IPv6/UDP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6()/UDP()/("X"* (lambda x: x - 66 if x > 66 else 0)(%d))',
                'IPv6/TCP': 'Ether(dst="%s", src="52:00:00:00:00:00")/IPv6()/TCP()/("X"* (lambda x: x - 78 if x > 78 else 0)(%d))'}

        if self.kdriver == "fm10k":
            del pkts['IP/SCTP']

        lcore = "1S/2C/1T"
        portMask = utils.create_mask([self.dut_ports[0], self.dut_ports[1]])
        for mode in ["sw", "hw"]:
            self.logger.info("%s performance" % mode)
            rst.write_text(mode + " Performance" + '\r\n')
            tblheader = ["Ports", "S/C/T", "Packet Type", "Mode"]
            for size in sizes:
                tblheader.append("%sB mpps" % str(size))
                tblheader.append("%sB %%   " % str(size))
            self.result_table_create(tblheader)
            self.pmdout.start_testpmd(
                lcore, "--portmask=%s" % self.portMask, socket=self.ports_socket)

            self.dut.send_expect("set verbose 1", "testpmd> ")
            self.dut.send_expect("set fwd csum", "testpmd> ")
            if mode == "hw":
                self.checksum_enablehw(self.dut_ports[0])
                self.checksum_enablehw(self.dut_ports[1])
            else:
                self.checksum_enablesw(self.dut_ports[0])
                self.checksum_enablesw(self.dut_ports[1])

            self.dut.send_expect("start", "testpmd> ", 3)
            for ptype in pkts.keys():
                self.benchmark(
                    lcore, ptype, mode, pkts[ptype], sizes, self.nic)

            self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("quit", "#", 10)
            self.result_table_print()

    def tear_down(self):
        """
        Run after each test case.
        """
        if self.dut.want_func_tests:
            self.dut.send_expect("quit", "#")

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
