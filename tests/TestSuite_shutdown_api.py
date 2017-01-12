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

import utils
import time
import re
import os
from test_case import TestCase
from pmd_output import PmdOutput
from settings import HEADER_SIZE, PROTOCOL_PACKET_SIZE
from exception import VerifyFailure

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
        ports = self.dut.get_ports()
        self.verify(len(ports) >= 1, "Insufficient number of ports.")
        self.ports = ports[:1]
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

    def check_forwarding(self, ports=None, pktSize=68, received=True, vlan=False, promisc=False):
        if ports is None:
            ports = self.ports
        if len(ports) == 1:
            self.send_packet(ports[0], ports[0], pktSize, received, vlan, promisc)
            return

    def send_packet(self, txPort, rxPort, pktSize=68, received=True, vlan=False, promisc=False):
        """
        Send packages according to parameters.
        """
        port0_stats = self.get_stats(txPort)
        gp0tx_pkts, gp0tx_bytes = [port0_stats['TX-packets'], port0_stats['TX-bytes']]
        port1_stats = self.get_stats(rxPort)
        gp1rx_pkts, gp1rx_err, gp1rx_bytes = [port1_stats['RX-packets'], port1_stats['RX-errors'], port1_stats['RX-bytes']]
        time.sleep(5)

        itf = self.tester.get_interface(self.tester.get_local_port(rxPort))
        smac = self.tester.get_mac(self.tester.get_local_port(rxPort))
        dmac = self.dut.get_mac_address(rxPort)

        # when promisc is true, destination mac should be fake
        if promisc:
            dmac = "00:00:00:00:00:01"

        if vlan:
            padding = pktSize - HEADER_SIZE['eth'] - HEADER_SIZE['ip'] -4
            pkg = 'Ether(src="%s", dst="%s")/Dot1Q(vlan=1)/IP()/Raw(load="P" * %d)' % (smac, dmac, padding)
        else:
            padding = pktSize - HEADER_SIZE['eth'] - HEADER_SIZE['ip']
            pkg = 'Ether(src="%s", dst="%s")/IP()/Raw(load="P" * %d)' % (smac, dmac, padding)

        self.tester.scapy_foreground()
        self.tester.scapy_append('sendp(%s, iface="%s")' % (pkg, itf))
        self.tester.scapy_execute()
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

        rx_bytes_exp = pktSize
        tx_bytes_exp = pktSize

        if self.kdriver == "fm10k":
            # RRC will always strip rx/tx crc
            rx_bytes_exp -= 4
            tx_bytes_exp -= 4
            if vlan is True:
                # RRC will always strip rx/tx vlan
                rx_bytes_exp -= 4
                tx_bytes_exp -= 4
        else:
            # some NIC will always include tx crc
            rx_bytes_exp -= 4
            tx_bytes_exp -= 4
            if vlan is True:
                # vlan strip default is on
                tx_bytes_exp -= 4
         
        # fortville nic enable send lldp packet function when port setup
        # now the tx-packets size is lldp_size(110) * n + forward packe size
        # so use (tx-packets - forward packet size) % lldp_size, if it is 0, it means forward packet size right
 
        if received:
            self.verify(self.pmdout.check_tx_bytes(p0tx_pkts, p1rx_pkts), "Wrong TX pkts p0_tx=%d, p1_rx=%d" % (p0tx_pkts, p1rx_pkts))
            self.verify(p1rx_bytes == rx_bytes_exp, "Wrong Rx bytes p1_rx=%d, expect=%d" % (p1rx_bytes, rx_bytes_exp))
            self.verify(self.pmdout.check_tx_bytes(p0tx_bytes, tx_bytes_exp) , "Wrong Tx bytes p0_tx=%d, expect=%d" % (p0tx_bytes, tx_bytes_exp))
        else:
            self.verify(self.pmdout.check_tx_bytes(p0tx_pkts), "Packet not dropped p0tx_pkts=%d" % p0tx_pkts)

    def check_ports(self, status=True):
        """
        Check link status of the ports.
        """
        # RRC not support link speed change
        if self.kdriver == "fm10k":
            return

        for port in self.ports:
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
        self.pmdout.start_testpmd("Default", "--portmask=%s  --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()
        self.dut.send_expect("stop", "testpmd> ")
        self.check_forwarding(received=False)
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.check_ports(status=False)
        self.dut.send_expect("port start all", "testpmd> ", 100)
        time.sleep(5)
        self.check_ports(status=True)
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()

    def test_set_promiscuousmode(self):
        """
        Promiscuous mode.
        """
        ports = [self.ports[0]]

        portmask = utils.create_mask(ports)
        self.pmdout.start_testpmd("Default", "--portmask=%s  --port-topology=loop" % portmask, socket = self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("show config rxtx", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        try:
            self.check_forwarding(ports)
        except VerifyFailure as e:
            print 'promiscuous mode is working correctly'
        except Exception as e:
            print "   !!! DEBUG IT: " + e.message
            self.verify(False, e.message)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("set promisc all on", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("show config rxtx", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding(ports, promisc=True)
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_reset_queues(self):
        """
        Reset RX/TX Queues.
        """
        testcorelist = self.dut.get_core_list("1S/8C/1T", socket=self.ports_socket)

        self.pmdout.start_testpmd(testcorelist, "--portmask=%s  --port-topology=loop" % utils.create_mask([self.ports[0]]), socket=self.ports_socket)
        fwdcoremask = utils.create_mask(testcorelist[-3:])

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all rxq 2", "testpmd> ")
        self.dut.send_expect("port config all txq 2", "testpmd> ")
        self.dut.send_expect("set coremask %s" % fwdcoremask, "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify("RX queues=2" in out, "RX queues not reconfigured properly")
        self.verify("TX queues=2" in out, "TX queues not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()
        self.dut.send_expect("quit", "# ", 30)

    def test_reconfigure_ports(self):
        """
        Reconfigure All Ports With The Same Configurations (CRC)
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all crc-strip on", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "CRC stripping enabled" in out, "CRC stripping not enabled properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()


    def test_change_linkspeed(self):
        """
        Change Link Speed.
        """
        if self.kdriver == "fm10k":
            print utils.RED("RRC not support\n")
            return

        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

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
            elif self.nic in ["fortville_eagle"]:
                if config[0] != '10000':
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
            self.check_forwarding()
            self.dut.send_expect("stop", "testpmd> ")

    def test_enable_disablejumbo(self):
        """
        Enable/Disable Jumbo Frames.
        """
        if self.kdriver == "fm10k":
            print utils.RED("RRC not support\n")
            return

        jumbo_size = 2048
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("vlan set strip off all", "testpmd> ")
        self.dut.send_expect("port config all max-pkt-len %d" % jumbo_size, "testpmd> ")
        for port in self.ports:
            self.dut.send_expect("rx_vlan add 1 %d" % port, "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("start", "testpmd> ")

        if self.nic in ['magnolia_park', 'niantic', 'twinpond', 'kawela_4', 'ironpond', 'springfountain', 'springville', 'powerville']:
            # nantic vlan length will not be calculated
            vlan_jumbo_size = jumbo_size + 4
        else:
            vlan_jumbo_size = jumbo_size

        self.check_forwarding(pktSize=vlan_jumbo_size - 1, vlan=True)
        self.check_forwarding(pktSize=vlan_jumbo_size, vlan=True)
        self.check_forwarding(pktSize=vlan_jumbo_size + 1, received=False, vlan=True)

        self.dut.send_expect("stop", "testpmd> ")

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all hw-vlan off", "testpmd> ")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("start", "testpmd> ")
        """
        On 1G NICs, when the jubmo frame MTU set as X, the software adjust it to (X + 4).
        """
        if self.nic in ["powerville", "springville", "kawela_4"]:
            jumbo_size += 4
        self.check_forwarding(pktSize=jumbo_size - 1)
        self.check_forwarding(pktSize=jumbo_size)
        self.check_forwarding(pktSize=jumbo_size + 1, received=False)

    def test_enable_disablerss(self):
        """
        Enable/Disable RSS.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config rss ip", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()

    def test_change_numberrxdtxd(self):
        """
        Change numbers of rxd and txd.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all rxd 1024", "testpmd> ")
        self.dut.send_expect("port config all txd 1024", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "RX desc=1024" in out, "RX descriptor not reconfigured properly")
        self.verify(
            "TX desc=1024" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()

    def test_change_numberrxdtxdaftercycle(self):
        """
        Change the Number of rxd/txd.
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port config all rxd 1024", "testpmd> ")
        self.dut.send_expect("port config all txd 1024", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "RX desc=1024" in out, "RX descriptor not reconfigured properly")
        self.verify(
            "TX desc=1024" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("port stop all", "testpmd> ", 100)
        self.dut.send_expect("port start all", "testpmd> ", 100)
        out = self.dut.send_expect("show config rxtx", "testpmd> ")
        self.verify(
            "RX desc=1024" in out, "RX descriptor not reconfigured properly")
        self.verify(
            "TX desc=1024" in out, "TX descriptor not reconfigured properly")
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()

    def test_change_thresholds(self):
        """
        Change RX/TX thresholds
        """
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

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
        self.dut.send_expect("start", "testpmd> ")
        self.check_forwarding()

    def test_stress_test(self):
        """
        Start/stop stress test.
        """
        stress_iterations = 10

        self.pmdout.start_testpmd("Default", "--portmask=%s  --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)

        tgenInput = []
        for port in self.ports:
            dmac=self.dut.get_mac_address(port)
            self.tester.scapy_append('wrpcap("test%d.pcap",[Ether(src="02:00:00:00:00:0%d",dst=%s)/IP()/UDP()/()])'% (port, port, dmac))
            tgenInput.append((self.tester.get_local_port(port), self.tester.get_local_port(port), "test%d.pcap" % port))
        for _ in range(stress_iterations):
            self.dut.send_expect("port stop all", "testpmd> ", 100)
            self.dut.send_expect("set fwd mac", "testpmd>")
            self.dut.send_expect("port start all", "testpmd> ", 100)
            self.dut.send_expect("start", "testpmd> ")
            self.check_forwarding()
            self.dut.send_expect("stop", "testpmd> ")

        self.dut.send_expect("quit", "# ")

    def test_link_stats(self):
        """
        port link stats test
        """
        if self.kdriver == "fm10k":
            print utils.RED("RRC not support\n")
            return

        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % utils.create_mask(self.ports), socket=self.ports_socket)
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        ports_num = len(self.ports)
        # link down test
        for i in range(ports_num):
            self.dut.send_expect("set link-down port %d" % i, "testpmd>")
        # leep few seconds for NIC link status update
        time.sleep(5)
        self.check_ports(status=False)

        # link up test
        for j in range(ports_num):
            self.dut.send_expect("set link-up port %d" % j, "testpmd>")
        time.sleep(5)
        self.check_ports(status=True)
        self.check_forwarding()

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
