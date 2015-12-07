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
Test the support of Whitelist Features by Poll Mode Drivers
"""

import dts
import time
from test_case import TestCase
from pmd_output import PmdOutput

class TestWhitelist(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        Whitelist Prerequistites:
            Two Ports
            testpmd can normally started
        """
        self.frames_to_send = 1
        # Based on h/w type, choose how many ports to use
        self.dutPorts = self.dut.get_ports()
        # Verify that enough ports are available
        self.verify(len(self.dutPorts) >= 1, "Insufficient ports")
        portMask = dts.create_mask(self.dutPorts[:2])

        self.pmdout = PmdOutput(self.dut)
        self.pmdout.start_testpmd("Default", "--portmask=%s" % portMask)
        self.dut.send_expect("set verbose 1", "testpmd> ")
        self.dut.send_expect("set fwd mac", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ")

        # get dest address from self.target port
        out = self.dut.send_expect("show port info %d" % self.dutPorts[0], "testpmd> ")

        self.dest = self.dut.get_mac_address(self.dutPorts[0])
        mac_scanner = r"MAC address: (([\dA-F]{2}:){5}[\dA-F]{2})"

        ret = dts.regexp(out, mac_scanner)
        self.verify(ret is not None, "MAC address not found")
        self.verify(cmp(ret.lower(), self.dest) == 0, "MAC address wrong")

        self.max_mac_addr = dts.regexp(out, "Maximum number of MAC addresses: ([0-9]+)")

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
        self.tester.scapy_append('sendp([Ether(dst="%s", src="52:00:00:00:00:00")/Raw(load="X"*26)], iface="%s", count=%d)' % (destMac,
                                                                                             itf, self.frames_to_send))
        self.tester.scapy_execute()
        time.sleep(5)

    def test_add_remove_mac_address(self):
        """
        Add mac address and check packet can received
        Remove mac address and check packet can't received
        """
        # initialise first port without promiscuous mode
        fake_mac_addr = "01:01:01:00:00:00"
        portid = self.dutPorts[0]
        txportid = self.dutPorts[1]
        self.dut.send_expect("set promisc %d off" % portid, "testpmd> ")

        out = self.dut.send_expect("show port stats %d" % txportid, "testpmd> ")
        pre_rxpkt = dts.regexp(out, "TX-packets: ([0-9]+)")

        # send one packet with the portid MAC address
        self.dut.send_expect("clear port stats all", "testpmd> ")
        self.whitelist_send_packet(portid, self.dest)
        out = self.dut.send_expect("show port stats %d" % txportid, "testpmd> ")
        cur_rxpkt = dts.regexp(out, "TX-packets: ([0-9]+)")
        # check the packet increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt) + self.frames_to_send,
                    "Packet has not been received on default address")
        # send one packet to a different MAC address
        # new_mac = self.dut.get_mac_address(portid)
        self.whitelist_send_packet(portid, fake_mac_addr)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % txportid, "testpmd> ")
        cur_rxpkt = dts.regexp(out, "TX-packets: ([0-9]+)")

        # check the packet DO NOT increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt),
                    "Packet has been received on a new MAC address that has not been added yet")
        # add the different MAC address
        out = self.dut.send_expect("mac_addr add %d" % portid + " %s" % fake_mac_addr, "testpmd>")

        # send again one packet to a different MAC address
        self.whitelist_send_packet(portid, fake_mac_addr)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % txportid, "testpmd> ")
        cur_rxpkt = dts.regexp(out, "TX-packets: ([0-9]+)")

        # check the packet increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt) + self.frames_to_send,
                    "Packet has not been received on a new MAC address that has been added to the port")

        # remove the fake MAC address
        out = self.dut.send_expect("mac_addr remove %d" % portid + " %s" % fake_mac_addr, "testpmd>")

        # send again one packet to a different MAC address
        self.whitelist_send_packet(portid, fake_mac_addr)

        pre_rxpkt = cur_rxpkt
        out = self.dut.send_expect("show port stats %d" % txportid, "testpmd> ")
        cur_rxpkt = dts.regexp(out, "TX-packets: ([0-9]+)")

        # check the packet increase
        self.verify(int(cur_rxpkt) == int(pre_rxpkt),
                    "Packet has been received on a new MAC address that has been removed from the port")
        self.dut.send_expect("stop", "testpmd> ")

    def test_invalid_addresses(self):
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
