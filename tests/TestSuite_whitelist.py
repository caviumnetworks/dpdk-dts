# <COPYRIGHT_TAG>

"""
DPDK Test suite.

Test the support of Whitelist Features by Poll Mode Drivers

"""

import dcts
import time


from test_case import TestCase

#
#
# Test class.
#


class TestWhitelist(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        Whitelist Prerequistites:
            Two Ports
            testpmd can normally started
        """

        self.frames_to_send = 1

        # Based on h/w type, choose how many ports to use
        self.dutPorts = self.dut.get_ports(self.nic)

        # Verify that enough ports are available
        self.verify(len(self.dutPorts) >= 1, "Insufficient ports")

        cores = self.dut.get_core_list('1S/2C/1T')
        coreMask = dcts.create_mask(cores)

        portMask = dcts.create_mask(self.dutPorts[:2])

        cmd = "./%s/build/app/test-pmd/testpmd -c %s -n 3 -- -i --burst=1 --rxpt=0 \
        --rxht=0 --rxwt=0 --txpt=36 --txht=0 --txwt=0 --txrst=32 --txfreet=32 --rxfreet=64 --mbcache=250 --portmask=%s" % (self.target, coreMask, portMask)
        self.dut.send_expect("%s" % cmd, "testpmd> ", 120)
        self.dut.send_expect("set verbose 1", "testpmd> ")

        # get dest address from self.target port
        out = self.dut.send_expect("show port info %d" % self.dutPorts[0], "testpmd> ")

        self.dest = self.dut.get_mac_address(self.dutPorts[0])
        mac_scanner = r"MAC address: (([\dA-F]{2}:){5}[\dA-F]{2})"

        ret = dcts.regexp(out, mac_scanner)
        self.verify(ret is not None, "MAC address not found")
        self.verify(cmp(ret.lower(), self.dest) == 0, "MAC address wrong")

        self.max_mac_addr = dcts.regexp(out, "Maximum number of MAC addresses: ([0-9]+)")

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def whitelist_send_packet(self, portid, destMac="00:11:22:33:44:55"):
        """
        Send 1 packet to portid.
        """

        itf = self.tester.get_interface(self.tester.get_local_port(portid))

        self.tester.scapy_foreground()
        self.tester.scapy_append('sendp([Ether(dst="%s", src="52:00:00:00:00:00")], iface="%s", count=%d)' % (destMac,
                                                                                                              itf,
                                                                                                              self.frames_to_send))
        self.tester.scapy_execute()

        time.sleep(5)

    def test_whitelist_add_remove_mac_address(self):
        """
        Add mac address and check packet can received
        Remove mac address and check packet can't received
        """
        # initialise first port without promiscuous mode
        fake_mac_addr = "01:01:01:00:00:00"
        portid = self.dutPorts[0]
        self.dut.send_expect("set promisc %d off" % portid, "testpmd> ")

        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        pre_rxpkt = dcts.regexp(out, "RX-packets: ([0-9]+)")

        # send one packet with the portid MAC address
        self.whitelist_send_packet(portid, self.dest)
        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        cur_rxpkt = dcts.regexp(out, "RX-packets: ([0-9]+)")
        # check the packet increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt) + self.frames_to_send,
                    "Packet has not been received on default address")
        # send one packet to a different MAC address
        # new_mac = self.dut.get_mac_address(portid)
        self.whitelist_send_packet(portid, fake_mac_addr)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        cur_rxpkt = dcts.regexp(out, "RX-packets: ([0-9]+)")

        # check the packet DO NOT increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt),
                    "Packet has been received on a new MAC address that has not been added yet")
        # add the different MAC address
        out = self.dut.send_expect("mac_addr add %d" % portid + " %s" % fake_mac_addr, "testpmd>")

        # send again one packet to a different MAC address
        self.whitelist_send_packet(portid, fake_mac_addr)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        cur_rxpkt = dcts.regexp(out, "RX-packets: ([0-9]+)")

        # check the packet increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt) + self.frames_to_send,
                    "Packet has not been received on a new MAC address that has been added to the port")

        # remove the fake MAC address
        out = self.dut.send_expect("mac_addr remove %d" % portid + " %s" % fake_mac_addr, "testpmd>")

        # send again one packet to a different MAC address
        self.whitelist_send_packet(portid, fake_mac_addr)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        cur_rxpkt = dcts.regexp(out, "RX-packets: ([0-9]+)")

        # check the packet increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt),
                    "Packet has been received on a new MAC address that has been removed from the port")
        self.dut.send_expect("stop", "testpmd> ")

    def test_whitelist_invalid_addresses(self):
        """
        Invalid operation:
            Add NULL MAC should not be added
            Remove using MAC will be failed
            Add Same MAC twice will be failed
            Add more than MAX number will be failed
        """

        portid = self.dutPorts[0]
        fake_mac_addr = "00:00:00:00:00:00"

        # add an address with all zeroes to the port (-EINVAL)
        out = self.dut.send_expect("mac_addr add %d" % portid + " %s" % fake_mac_addr, "testpmd>")
        self.verify("Invalid argument" in out, "Added a NULL MAC address")

        # remove the default MAC address (-EADDRINUSE)
        out = self.dut.send_expect("mac_addr remove %d" % portid + " %s" % self.dest, "testpmd>")
        self.verify("Address already in use" in out, "default address removed")

        # add same address 2 times
        fake_mac_addr = "00:00:00:00:00:01"
        out = self.dut.send_expect("mac_addr add %d" % portid + " %s" % fake_mac_addr, "testpmd>")
        out = self.dut.send_expect("mac_addr add %d" % portid + " %s" % fake_mac_addr, "testpmd>")
        self.verify("error" not in out, "added 2 times the same address with an error")

        # add 1 address more that max number
        i = 0
        base_addr = "01:00:00:00:00:"
        while i <= int(self.max_mac_addr):
            new_addr = base_addr + "%0.2X" % i
            out = self.dut.send_expect("mac_addr add %d" % portid + " %s" % new_addr, "testpmd>")
            i = i + 1

        self.verify("No space left on device" in out, "added 1 address more than max MAC addresses")

    def tear_down(self):
        """
        Run after each test case.
        Nothing to do.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.send_expect("quit", "# ", 10)
