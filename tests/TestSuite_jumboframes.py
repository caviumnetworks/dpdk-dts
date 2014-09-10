# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test the support of Jumbo Frames by Poll Mode Drivers

"""

import dcts
import re
from time import sleep

from test_case import TestCase
from pmd_output import PmdOutput

#
#
# Test class.
#


class TestJumboframes(TestCase):
    #
    #
    # Utility methods and other non-test code.
    #

    # Insert or move non-test functions here.

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

        gp0tx_pkts, _, gp0tx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.dut_ports[0], "tx")]
        gp1rx_pkts, gp1rx_err, gp1rx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.dut_ports[1], "rx")]

        itf = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1]))
        mac = self.dut.get_mac_address(self.dut_ports[1])

        pktlen = pktsize - 18
        padding = pktlen - 20

        self.tester.scapy_foreground()
        self.tester.scapy_append('nutmac="%s"' % mac)
        self.tester.scapy_append('sendp([Ether(dst=nutmac, src="52:00:00:00:00:00")/IP(len=%s)/Raw(load="\x50"*%s)], iface="%s")' % (pktlen, padding, itf))

        out = self.tester.scapy_execute()
        sleep(5)

        p0tx_pkts, _, p0tx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.dut_ports[0], "tx")]
        # p0tx_pkts, p0tx_err, p0tx_bytes
        p1rx_pkts, p1rx_err, p1rx_bytes = [int(_) for _ in self.jumboframes_get_stat(self.dut_ports[1], "rx")]

        p0tx_pkts -= gp0tx_pkts
        p0tx_bytes -= gp0tx_bytes
        p1rx_pkts -= gp1rx_pkts
        p1rx_bytes -= gp1rx_bytes
        p1rx_err -= gp1rx_err

        if received:
            self.verify(p0tx_pkts == p1rx_pkts and p0tx_bytes == pktsize and p1rx_bytes == pktsize,
                        "packet pass assert error")

        else:
            self.verify(p0tx_pkts == p1rx_pkts and (p1rx_err == 1 or p1rx_pkts == 0),
                        "packet drop assert error")

        return out

    #
    #
    #
    # Test cases.
    #
    def set_up_all(self):
        """
        Run at the start of each test suite.


        Dynamic config Prerequistites
        """

        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports")

        cores = self.dut.get_core_list('1S/2C/2T')
        self.coremask = dcts.create_mask(cores)

        self.port_mask = dcts.create_mask([self.dut_ports[0], self.dut_ports[1]])

        self.tester.send_expect("ifconfig %s mtu %s" % (self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0])), 9200), "# ")
        self.tester.send_expect("ifconfig %s mtu %s" % (self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1])), 9200), "# ")

        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_jumboframes_normal_nojumbo(self):
        """
        Dynamic config default mode test
        """

        self.dut.kill_all()

        cmd = r"./%s/build/app/test-pmd/testpmd -c%s -n 3 -- -i --rxd=1024 --txd=1024 \
      --burst=144 --txpt=32 --txht=0 --txfreet=0 --rxfreet=64 \
      --mbcache=200 --portmask=%s --mbuf-size=2048 --max-pkt-len=1518" % (self.target, self.coremask, self.port_mask)

        self.dut.send_expect(cmd, "testpmd> ", 120)

        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(1517)
        self.jumboframes_send_packet(1518)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_jumbo_nojumbo(self):
        """
        Dynamic config diable promiscuous test
        """

        self.dut.kill_all()

        cmd = r"./%s/build/app/test-pmd/testpmd -c%s -n 3 -- -i --rxd=1024 --txd=1024 \
      --burst=144 --txpt=32 --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 \
      --mbcache=200 --portmask=%s --mbuf-size=2048 --max-pkt-len=1518" % (self.target, self.coremask, self.port_mask)

        self.dut.send_expect(cmd, "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(1519, False)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_normal_jumbo(self):
        """
        Dynamic config enable promiscuous test
        """

        self.dut.kill_all()

        cmd = r"./%s/build/app/test-pmd/testpmd -c%s -n 3 -- -i --rxd=1024 --txd=1024 \
      --burst=144 --txpt=32 --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 \
      --mbcache=200 --portmask=%s --mbuf-size=2048 --max-pkt-len=%s" % (self.target, self.coremask, self.port_mask, 9000)

        self.dut.send_expect(cmd, "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(1517)
        self.jumboframes_send_packet(1518)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_jumbo_jumbo(self):
        """
        Dynamic config enable promiscuous test
        """

        self.dut.kill_all()

        cmd = r"./%s/build/app/test-pmd/testpmd -c%s -n 3 -- -i --rxd=1024 --txd=1024 \
      --burst=144 --txpt=32 --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 \
      --mbcache=200 --portmask=%s --mbuf-size=2048 --max-pkt-len=%s" % (self.target, self.coremask, self.port_mask, 9000)

        self.dut.send_expect(cmd, "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(1519)
        self.jumboframes_send_packet(9000 - 1)
        self.jumboframes_send_packet(9000)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)

    def test_jumboframes_bigger_jumbo(self):
        """
        Dynamic config enable promiscuous test
        """

        self.dut.kill_all()

        cmd = r"./%s/build/app/test-pmd/testpmd -c%s -n 3 -- -i --rxd=1024 --txd=1024 \
      --burst=144 --txpt=32 --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 \
      --mbcache=200 --portmask=%s --mbuf-size=2048 --max-pkt-len=%s" % (
            self.target, self.coremask, self.port_mask, 9000)

        self.dut.send_expect(cmd, "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        self.jumboframes_send_packet(9000 + 1, False)

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
