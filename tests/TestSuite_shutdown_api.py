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

Test Shutdown API Feature

"""

import dts
import time
import re
import os
from test_case import TestCase
from pmd_output import PmdOutput
from settings import HEADER_SIZE

#
#
# Test class.
#


class TestShutdownApi(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.ports = self.dut.get_ports()
        print self.nic, self.ports
        self.verify(len(self.ports) >= 2, "Insufficient number of ports.")
        self.ports_socket = self.dut.get_numa_id(self.ports[0])

        for port in self.ports:
            self.tester.send_expect("ifconfig %s mtu %s" % (
                self.tester.get_interface(self.tester.get_local_port(port)), 5000), "# ")

        self.pmdout = PmdOutput(self.dut)

    def get_stats(self, portid):
        """
        Get packets number from port statistic.
        @param: stop -- stop forward before get stats
        """
        output = PmdOutput(self.dut)
        stats = output.get_pmd_stats(portid)
        return stats

    def check_forwarding(self, ports, nic, testerports=[None, None], pktSize=64, received=True, crcStrip=True, vlan=False, softpkg=True, promisc=False):
        if len(ports) == 1:
            self.send_packet(ports[0], ports[0], self.nic, testerports[0], pktSize, received, crcStrip, vlan, softpkg, promisc)
            return

        for i in range(len(ports)):
            if i % 2 == 0:
                self.send_packet(ports[i], ports[i + 1], self.nic, testerports[1], pktSize, received, crcStrip, vlan, softpkg, promisc)
                self.send_packet(ports[i + 1], ports[i], self.nic, testerports[0], pktSize, received, crcStrip, vlan, softpkg, promisc)

    def send_packet(self, txPort, rxPort, nic, testerports=None, pktSize=64, received=True, crcStrip=True, vlan=False, softpkg=True, promisc=False):
        """
        Send packages according to parameters.
        """
        port0_stats = self.get_stats(txPort)
        gp0tx_pkts, gp0tx_bytes = [port0_stats['TX-packets'], port0_stats['TX-bytes']]
        port1_stats = self.get_stats(rxPort)
        gp1rx_pkts, gp1rx_err, gp1rx_bytes = [port1_stats['RX-packets'], port1_stats['RX-errors'], port1_stats['RX-bytes']]
        time.sleep(5)

        if testerports is None:
            itf = self.tester.get_interface(self.tester.get_local_port(rxPort))
        else:
            itf = testerports
        smac = self.tester.get_mac(self.tester.get_local_port(rxPort))
        dmac = self.dut.get_mac_address(rxPort)
        if promisc:
            dmac = "00:00:00:00:00:01"

        self.tester.scapy_foreground()

        if self.nic in ["fortville_eagle", "fortville_spirit",
                        "fortville_spirit_single", "bartonhills",
                        "powerville", "springville", "hartwell", "redrockcanyou"]:
            pktlen = pktSize - HEADER_SIZE['eth'] -4 
        else:
            pktlen = pktSize - HEADER_SIZE['eth']
        padding = pktlen - HEADER_SIZE['ip']

        pkg = ''

        if vlan:
            if pktSize <= 64:
                pktSize=68
            pkg = 'Ether(src="%s", dst="%s")/Dot1Q(vlan=1)/IP()/Raw(load="P" * %d)' % (smac, dmac, padding)
        else:
            pkg = 'Ether(src="%s", dst="%s")/IP()/Raw(load="P" * %d)' % (smac, dmac, padding)

        if softpkg == True:
            self.tester.scapy_append('sendp(%s, iface="%s")' % (pkg,itf))
            self.tester.scapy_execute()
        else:
            tgenInput = []
            self.tester.scapy_append('wrpcap("test%d.pcap", %s' % (rxPort, pkg))
            tgenInput.append((self.tester.get_local_port(
                rxPort), self.tester.get_local_port(txPort), "test%d.pcap" % rxPort))
            self.tester.traffic_generator_throughput(tgenInput)

        time.sleep(3)

        port0_stats = self.get_stats(txPort)
        p0tx_pkts, p0tx_bytes = [port0_stats['TX-packets'], port0_stats['TX-bytes']]
        port1_stats = self.get_stats(rxPort)
        p1rx_pkts, p1rx_err, p1rx_bytes = [port1_stats['RX-packets'], port1_stats['RX-errors'], port1_stats['RX-bytes']]
        time.sleep(5)

        p0tx_pkts -= gp0tx_pkts
        p0tx_bytes -= gp0tx_bytes
        p1rx_pkts -= gp1rx_pkts
        p1rx_bytes -= gp1rx_bytes
        p1rx_err -= gp1rx_err
        if received:

            self.verify(p0tx_pkts == p1rx_pkts,
                        "Wrong TX pkts p0_tx=%d, p1_rx=%d" % (p0tx_pkts, p1rx_pkts))
            if vlan == False:
                # RRC and FVL always strip crc
                if self.nic in ["redrockcanyou", "fortville_eagle", "fortville_spirit",
                                "fortville_spirit_single", "bartonhills",
                                "powerville", "springville", "hartwell"]:
                    self.verify(p0tx_bytes == pktSize -4,
                                "Wrong TX bytes p0_tx=%d, pktSize=%d" % (p0tx_bytes, pktSize))
                else:
                    if crcStrip:
                        self.verify(p1rx_bytes == pktSize -4,
                                    "Wrong RX bytes CRC strip: p1_rx=%d, pktSize=%d" % (p1rx_bytes, pktSize))
                    else:
                        self.verify(p1rx_bytes == pktSize,
                                    "Wrong RX bytes NO CRC strip: p1_rx=%d, pktSize=%d" % (p0tx_bytes, pktSize))
            else:
                # RRC always strip vlan and crc
                if self.nic in ["redrockcanyou"]:
                    self.verify(p1rx_bytes == pktSize - 8,
                                "Wrong TX bytes p0_tx=%d, pktSize=%d" % (p0tx_bytes, pktSize))
                elif self.nic in ["fortville_eagle", "fortville_spirit",
                                "fortville_spirit_single", "bartonhills",
                                "powerville", "springville", "hartwell"]:
                    self.verify(p1rx_bytes == pktSize - 4,
                                "Wrong TX bytes p0_tx=%d, pktSize=%d" % (p0tx_bytes, pktSize))
                else:
                    if crcStrip:
                        self.verify(p1rx_bytes == pktSize -4,
                                    "Wrong RX bytes CRC strip: p1_rx=%d, pktSize=%d" % (p1rx_bytes, pktSize))
                    else:
                        self.verify(p1rx_bytes == pktSize,
                                    "Wrong RX bytes NO CRC strip: p1_rx=%d, pktSize=%d" % (p0tx_bytes, pktSize))
        else:
            self.verify(
                p0tx_pkts == 0, "Packet not dropped p0tx_pkts=%d" % p0tx_pkts)
            self.verify(
                p0tx_bytes == 0, "Packet not dropped p0tx_bytes=%d" % p0tx_bytes)

    def check_ports(self, ports, status):
        """
            Check link status of the ports.
        """
        for port in ports:
            out = self.tester.send_expect(
                "ethtool %s" % self.tester.get_interface(self.tester.get_local_port(port)), "# ")
            if status:
                self.verify("Link detected: yes" in out, "Wrong link status")
            else:
                self.verify("Link detected: no" in out, "Wrong link status")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_stop_restart(self):
        """
        Stop and Restar.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)
        self.dut.send_expect("stop", "testpmd> ")
        self.check_forwarding(self.ports, self.nic, received=False)
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.check_ports(self.ports, False)
        self.dut.send_expect("port start all", "testpmd> ", 100)
        time.sleep(5)
        self.check_ports(self.ports, True)
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)

    def test_set_promiscuousmode(self):
        """
        Promiscuous mode.
        """
        ports = []
        # RRC is different with other type, inside a switch,
        # so better to use one port to verify promisc mode
        if self.nic == "redrockcanyou":
            ports = [self.ports[0]]
        else:
            ports = [self.ports[0], self.ports[1]]

        portmask = dts.create_mask(ports)
        self.pmdout.start_testpmd("Default", "--portmask=%s" % portmask, self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("show config rxtx", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        try:
            self.check_forwarding(ports, self.nic)
        except dts.VerifyFailure as e:
            print 'promiscuous mode is working correctly'
        except Exception as e:
            print "   !!! DEBUG IT: " + e.message
            self.verify(False, e.message)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("set promisc all on", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("show config rxtx", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(ports, self.nic, promisc=True)
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_reset_queues(self):
        """
        Reset RX/TX Queues.
        """
        testerports = [self.tester.get_interface(self.tester.get_local_port(self.ports[0])),
                       self.tester.get_interface(self.tester.get_local_port(self.ports[1]))
                       ]
        #blackList = self.dut.create_blacklist_string(self.target, self.nic)

        testcorelist = self.dut.get_core_list("1S/8C/1T", socket=self.ports_socket)

        self.pmdout.start_testpmd(testcorelist, "--portmask=%s" % dts.create_mask([self.ports[0], self.ports[1]]), socket=self.ports_socket)
        fwdcoremask = dts.create_mask(testcorelist[-3:])

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all rxq 2", "testpmd> ")
        self.dut.send_expect("port config all txq 2", "testpmd> ")
        #self.dut.send_expect("set coremask 0x1e", "testpmd> ")
        self.dut.send_expect("set coremask %s" % fwdcoremask, "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify("RX queues=2" in out, "RX queues not reconfigured properly")
        self.verify("TX queues=2" in out, "TX queues not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding([0, 1], self.nic, testerports)
        self.dut.send_expect("quit", "# ", 30)
        #self.dut.send_expect("rmmod igb_uio", "# ", 20)
        #self.dut.send_expect("insmod ./%s/kmod/igb_uio.ko" % self.target, "#")
        #self.dut.bind_interfaces_linux()

    def test_reconfigure_ports(self):
        """
        Reconfigure All Ports With The Same Configurations (CRC)
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all crc-strip on", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "CRC stripping enabled" in out, "CRC stripping not enabled properly")
        self.dut.send_expect("start", "testpmd> ")
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "redrockcanyou"]:
            self.check_forwarding(self.ports, self.nic, crcStrip=True)
        else:
            self.check_forwarding(self.ports, self.nic, crcStrip=False)
             

    def test_change_linkspeed(self):
        """
        Change Link Speed.
        """
        if self.nic == "redrockcanyou":
            print dts.RED("RRC not support\n")
            return

        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        out = self.tester.send_expect(
            "ethtool %s" % self.tester.get_interface(self.tester.get_local_port(self.ports[0])), "# ")
        if 'fortville_spirit' == self.nic:
            result_scanner = r"([0-9]+)baseSR4/([A-Za-z]+)"
        else:
            result_scanner = r"([0-9]+)baseT/([A-Za-z]+)"
        scanner = re.compile(result_scanner, re.DOTALL)
        m = scanner.findall(out)
        configs = m[:-(len(m) / 2)]
        for config in configs:
            print config
            if self.nic in ["ironpond"]:
                if config[0] != '1000' or '10000':
                    continue
            self.dut.send_expect("port stop all", "testpmd> ", 100)
            for port in self.ports:
                self.dut.send_expect("port config %d speed %s duplex %s" % (port,
                                                                            config[0], config[1].lower()), "testpmd> ")
            self.dut.send_expect("set fwd mac", "testpmd>")
            self.dut.send_expect("port start all", "testpmd> ", 100)
            time.sleep(5)  # sleep few seconds for link stable

            for port in self.ports:
                out = self.tester.send_expect(
                    "ethtool %s" % self.tester.get_interface(self.tester.get_local_port(port)), "# ")
                self.verify("Speed: %s" % config[0] in out,
                            "Wrong speed reported by the self.tester.")
                self.verify("Duplex: %s" % config[1] in out,
                            "Wrong link type reported by the self.tester.")
            self.dut.send_expect("start", "testpmd> ")
            self.check_forwarding(self.ports, self.nic)
            self.dut.send_expect("stop", "testpmd> ")

    def failed_test_enable_disablejumbo(self):
        """
        Enable/Disable Jumbo Frames.
        """
        if self.nic == "redrockcanyou":
            print dts.RED("RRC not support\n")
            return

        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("vlan set strip off all", "testpmd> ")
        self.dut.send_expect("port config all max-pkt-len 2048", "testpmd> ")
        for port in self.ports:
            self.dut.send_expect("rx_vlan add 1 %d" % port, "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("start", "testpmd> ")

        self.check_forwarding(self.ports, self.nic, pktSize=2047, vlan=True)
        self.check_forwarding(self.ports, self.nic, pktSize=2048, vlan=True)
        self.check_forwarding(self.ports, self.nic, pktSize=2049, received=False, vlan=True)

        self.dut.send_expect("stop", "testpmd> ")

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all hw-vlan off", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("start", "testpmd> ")
        if ((self.nic == "bartonhills") or (self.nic == "powerville") or (self.nic == "springville") or (self.nic == "hartwell")):
            self.check_forwarding(self.ports, self.nic, pktSize=2051)
            self.check_forwarding(self.ports, self.nic, pktSize=2052)
            self.check_forwarding(self.ports, self.nic, pktSize=2053, received=False)
        else:
            self.check_forwarding(self.ports, self.nic, pktSize=2047)
            self.check_forwarding(self.ports, self.nic, pktSize=2048)
            self.check_forwarding(self.ports, self.nic, pktSize=2049, received=False)

    def test_enable_disablerss(self):
        """
        Enable/Disable RSS.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config rss ip", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)

    def test_change_numberrxdtxd(self):
        """
        Change numbers of rxd and txd.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all rxd 1024", "testpmd> ")
        self.dut.send_expect("port config all txd 1024", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "RX desc=1024" in out, "RX descriptor not reconfigured properly")
        self.verify(
            "TX desc=1024" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)

    def test_change_numberrxdtxdaftercycle(self):
        """
        Change the Number of rxd/txd.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all rxd 1024", "testpmd> ")
        self.dut.send_expect("port config all txd 1024", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "RX desc=1024" in out, "RX descriptor not reconfigured properly")
        self.verify(
            "TX desc=1024" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "RX desc=1024" in out, "RX descriptor not reconfigured properly")
        self.verify(
            "TX desc=1024" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)

    def test_change_thresholds(self):
        """
        Change RX/TX thresholds
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all txfreet 32", "testpmd> ")
        self.dut.send_expect("port config all txrst 32", "testpmd> ")
        self.dut.send_expect("port config all rxfreet 32", "testpmd> ")
        self.dut.send_expect("port config all txpt 64", "testpmd> ")
        self.dut.send_expect("port config all txht 64", "testpmd> ")
        self.dut.send_expect("port config all txwt 0", "testpmd> ")
        self.dut.send_expect("port config all rxpt 64", "testpmd> ")
        self.dut.send_expect("port config all rxht 64", "testpmd> ")
        self.dut.send_expect("port config all rxwt 64", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify("RX free threshold=32" in out,
                    "RX descriptor not reconfigured properly")
        self.verify("TX free threshold=32" in out,
                    "TX descriptor not reconfigured properly")
        self.verify("TX RS bit threshold=32" in out,
                    "TX descriptor not reconfigured properly")
        self.verify("pthresh=64" in out, "TX descriptor not reconfigured properly")
        self.verify("hthresh=64" in out, "TX descriptor not reconfigured properly")
        self.verify("wthresh=64" in out, "TX descriptor not reconfigured properly")
        self.verify("pthresh=64" in out, "TX descriptor not reconfigured properly")
        self.verify("hthresh=64" in out, "TX descriptor not reconfigured properly")
        self.verify("wthresh=64" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(self.ports, self.nic)

    def test_stress_test(self):
        """
        Start/stop stress test.
        """
        stress_iterations = 10

        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)

        tgenInput = []
        for port in self.ports:
            dmac=self.dut.get_mac_address(port)
            self.tester.scapy_append('wrpcap("test%d.pcap",[Ether(src="02:00:00:00:00:0%d",dst=%s)/IP()/UDP()/()])'% (port, port, dmac))
            tgenInput.append((self.tester.get_local_port(port), self.tester.get_local_port(port), "test%d.pcap" % port))
        for _ in range(stress_iterations):
            self.dut.send_expect("port stop all", "testpmd> ", 100)
            self.dut.send_expect("set fwd mac", "testpmd>")
            self.dut.send_expect("set promisc all off", "testpmd>")
            self.dut.send_expect("port start all", "testpmd> ", 100)
            self.dut.send_expect("start", "testpmd> ")
            self.check_forwarding(self.ports, self.nic)
            self.dut.send_expect("stop", "testpmd> ")

        self.dut.send_expect("quit", "# ")

    def test_link_stats(self):
        """
        port link stats test
        """
        if self.nic == "redrockcanyou":
            print dts.RED("RRC not support\n")
            return

        self.pmdout.start_testpmd("Default", "--portmask=%s" % dts.create_mask(self.ports), socket=self.ports_socket)
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        # default test
        # self.check_forwarding([0,1], self.nic)

        ports_num = len(self.ports)
        # link down test
        for i in range(ports_num):
            self.dut.send_expect("set link-down port %d" % i, "testpmd>")
        # leep few seconds for NIC link status update
        time.sleep(5)
        self.check_ports(self.ports, False)

        # link up test
        for j in range(ports_num):
            self.dut.send_expect("set link-up port %d" % j, "testpmd>")
        time.sleep(5)
        self.check_ports(self.ports, True)
        self.check_forwarding(self.ports, self.nic)

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
