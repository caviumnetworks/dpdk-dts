# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test the support of VLAN Offload Features by Poll Mode Drivers.

"""

import dcts
import time


from test_case import TestCase

#
#
# Test class.
#


class TestVlan(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Vlan Prerequistites
        """

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(self.nic)

        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports")

        cores = self.dut.get_core_list('1S/2C/2T')
        coreMask = dcts.create_mask(cores)

        ports = self.dut.get_ports(self.nic)
        global valports
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]

        portMask = dcts.create_mask(valports[:2])

        cmd = "./%s/build/app/test-pmd/testpmd -c %s -n 3 -- -i --burst=1 \
               --mbcache=250 --portmask=%s" % (self.target, coreMask, portMask)

        self.dut.send_expect("%s" % cmd, "testpmd> ", 120)
        self.dut.send_expect("set verbose 1", "testpmd> ")
        out = self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("vlan set strip off %s" % valports[0], "testpmd> ")
        self.verify('Set mac packet forwarding mode' in out, "set fwd rxonly error")

    def vlan_send_packet(self, vid, num=1):
        """
        Send $num of packet to portid
        """

        port = self.tester.get_local_port(valports[0])
        txItf = self.tester.get_interface(port)

        port = self.tester.get_local_port(valports[1])
        rxItf = self.tester.get_interface(port)

        mac = self.dut.get_mac_address(valports[0])

        # FIXME  send a burst with only num packet
        self.tester.scapy_background()
        self.tester.scapy_append('p=sniff(iface="%s",count=1,timeout=5)' % rxItf)
        self.tester.scapy_append('RESULT=str(p)')

        self.tester.scapy_foreground()
        self.tester.scapy_append('sendp([Ether(dst="%s")/Dot1Q(vlan=%s)/IP(len=46)], iface="%s")' % (mac, vid, txItf))

        self.tester.scapy_execute()

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_vlan_enable_receipt(self):
        """
        Enable receipt of VLAN packets
        """
        self.dut.send_expect("set promisc all off", "testpmd> ")
        self.dut.send_expect("rx_vlan add 1 %s" % valports[0], "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)

        self.vlan_send_packet(1)
        out = self.tester.scapy_get_result()
        self.verify("vlan=1L" in out, "Wrong vlan:" + out)

        self.dut.send_expect("stop", "testpmd> ")

    def test_vlan_disable_receipt(self):
        """
        Disable receipt of VLAN packets
        """

        self.dut.send_expect("rx_vlan rm 1 %s" % valports[0], "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)

        self.vlan_send_packet(1)

        out = self.tester.scapy_get_result()
        self.verify("vlan=1L" not in out, "Wrong vlan:" + out)

        out = self.dut.send_expect("stop", "testpmd> ")

    def test_vlan_strip_config_on(self):
        self.dut.send_expect("vlan set strip on %s" % valports[0], "testpmd> ", 20)
        self.dut.send_expect("set promisc all off", "testpmd> ", 20)
        out = self.dut.send_expect("vlan set strip on %s" % valports[0], "testpmd> ", 20)
        self.verify("strip on" in out, "Wrong strip:" + out)

        self.dut.send_expect("start", "testpmd> ", 120)
        self.vlan_send_packet(1)
        out = self.tester.scapy_get_result()
        self.verify("vlan=1L" not in out, "Wrong vlan:" + out)
        out = self.dut.send_expect("quit", "#", 120)

    def test_vlan_strip_config_off(self):
        self.dut.send_expect("vlan set strip off %s" % valports[0], "testpmd> ", 20)
        out = self.dut.send_expect("show port info %s" % valports[0], "testpmd> ", 20)
        self.verify("strip off" in out, "Wrong strip:" + out)
        self.dut.send_expect("set nbport 2", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.vlan_send_packet(1)
        out = self.tester.scapy_get_result()
        self.verify("vlan=1L" in out, "Wrong strip vlan:" + out)
        out = self.dut.send_expect("stop", "testpmd> ", 120)

    def FAILING_test_vlan_enable_vlan_insertion(self):
        """
        Enable VLAN header insertion in transmitted packets
        """

        port = self.tester.get_local_port(valports[0])
        intf = self.tester.get_interface(port)

        self.dut.send_expect("set nbport 2", "testpmd> ")
        self.dut.send_expect("tx_vlan set 1 %s" % valports[0], "testpmd> ")

        self.dut.send_expect("set promisc all on", "testpmd> ")
        if self.nic == 'hartwell':
            self.dut.send_expect("vlan set strip on %s" % valports[0], "testpmd> ")

        self.tester.scapy_background()
        self.tester.scapy_append('p = sniff(iface="%s", count=1, timeout=5)' % intf)
        self.tester.scapy_append('RESULT=str(p)')
        self.tester.scapy_foreground()

        self.tester.scapy_execute()
        time.sleep(2)
        self.dut.send_expect("start tx_first", "testpmd> ")
        time.sleep(2)

        out = self.tester.scapy_get_result()
        self.verify("vlan=1L" in out, "Wrong vlan: " + out)
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
