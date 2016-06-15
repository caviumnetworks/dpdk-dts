# BSD LICENSE
#
# Copyright(c) 2010-2015 Intel Corporation. All rights reserved.
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

Test the support of VLAN Offload Features by Poll Mode Drivers.

"""

import dts
import time


from test_case import TestCase
from pmd_output import PmdOutput
from packet import Packet, sniff_packets, load_sniff_packets


class TestVlan(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.


        Vlan Prerequistites
        """
        global dutRxPortId
        global dutTxPortId

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports()

        # Verify that enough ports are available
        self.verify(len(ports) >= 1, "Insufficient ports")

        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        dutRxPortId = valports[0]
        dutTxPortId = valports[0]
        portMask = dts.create_mask(valports[:1])

        self.pmdout = PmdOutput(self.dut)
        self.pmdout.start_testpmd("Default", "--portmask=%s --port-topology=loop" % portMask)

        self.dut.send_expect("set verbose 1", "testpmd> ")
        out = self.dut.send_expect("set fwd mac", "testpmd> ")

        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.dut.send_expect("vlan set filter on %s" % dutRxPortId, "testpmd> ")

        self.dut.send_expect("vlan set strip off %s" % dutRxPortId, "testpmd> ")
        self.verify('Set mac packet forwarding mode' in out, "set fwd rxonly error")
        self.vlan = 51

        if self.kdriver == "fm10k":
            netobj = self.dut.ports_info[dutRxPortId]['port']
            netobj.add_vlan(vlan_id = self.vlan)

    def get_tcpdump_package(self):
        pkts = load_sniff_packets(self.inst)
        vlans = []
        for packet in pkts:
            vlan = packet.strip_element_dot1q("vlan")
            vlans.append(vlan)
        return vlans

    def vlan_send_packet(self, vid, num=1):
        """
        Send $num of packet to portid, if vid is -1, it means send pakcage not include vlan id.
        """
        # The package stream : testTxPort->dutRxPort->dutTxport->testRxPort
        port = self.tester.get_local_port(dutRxPortId)
        self.txItf = self.tester.get_interface(port)
        self.smac = self.tester.get_mac(port)

        port = self.tester.get_local_port(dutTxPortId)
        self.rxItf = self.tester.get_interface(port)

        # the package dect mac must is dut tx port id when the port promisc is off
        self.dmac = self.dut.get_mac_address(dutRxPortId)

        self.inst = sniff_packets(self.rxItf)
        # FIXME  send a burst with only num packet
        if vid == -1:
            pkt = Packet(pkt_type='UDP')
            pkt.config_layer('ether', {'dst': self.dmac, 'src': self.smac})
        else:
            pkt = Packet(pkt_type='VLAN_UDP')
            pkt.config_layer('ether', {'dst': self.dmac, 'src': self.smac})
            pkt.config_layer('dot1q', {'vlan': vid})

        pkt.send_pkt(tx_port=self.txItf)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_vlan_enable_receipt(self):
        """
        Enable receipt of VLAN packets
        """

        if self.kdriver == "fm10k":
            print dts.RED("fm10k not support this case\n")
            return
        self.dut.send_expect("rx_vlan add %d %s" % (self.vlan, dutRxPortId), "testpmd> ")
        self.dut.send_expect("vlan set strip off  %s" % dutRxPortId, "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ", 20)

        self.vlan_send_packet(self.vlan)
        out = self.get_tcpdump_package()
        self.verify(self.vlan in out, "Wrong vlan:" + str(out))

        self.dut.send_expect("stop", "testpmd> ")

    def test_vlan_disable_receipt(self):
        """
        Disable receipt of VLAN packets
        """

        self.dut.send_expect("rx_vlan rm %d %s" % (self.vlan, dutRxPortId), "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.vlan_send_packet(self.vlan)

        out = self.get_tcpdump_package()
        self.verify(len(out) == 0, "Received unexpected packet, filter not work!!!")
        self.verify(self.vlan not in out, "Wrong vlan:" + str(out))

        out = self.dut.send_expect("stop", "testpmd> ")

    def test_vlan_strip_config_on(self):

        self.dut.send_expect("vlan set strip on %s" % dutRxPortId, "testpmd> ", 20)
        self.dut.send_expect("rx_vlan add %d %s" % (self.vlan, dutRxPortId), "testpmd> ", 20)
        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ", 20)
        self.verify("strip on" in out, "Wrong strip:" + out)

        self.dut.send_expect("start", "testpmd> ", 120)
        self.vlan_send_packet(self.vlan)
        out = self.get_tcpdump_package()
        self.verify(len(out), "Forwarded vlan packet not received!!!")
        self.verify(self.vlan not in out, "Wrong vlan:" + str(out))
        out = self.dut.send_expect("stop", "testpmd> ", 120)

    def test_vlan_strip_config_off(self):

        if self.kdriver == "fm10k":
            print dts.RED("fm10k not support this case\n")
            return
        self.dut.send_expect("vlan set strip off %s" % dutRxPortId, "testpmd> ", 20)
        self.dut.send_expect("rx_vlan add %d %s" % (self.vlan, dutRxPortId), "testpmd> ", 20)
        out = self.dut.send_expect("show port info %s" % dutRxPortId, "testpmd> ", 20)
        self.verify("strip off" in out, "Wrong strip:" + out)
        self.dut.send_expect("set nbport 2", "testpmd> ")
        self.dut.send_expect("start", "testpmd> ", 120)
        self.vlan_send_packet(self.vlan)
        out = self.get_tcpdump_package()
        self.verify(self.vlan in out, "Vlan not found:" + str(out))
        out = self.dut.send_expect("stop", "testpmd> ", 120)

    def test_vlan_enable_vlan_insertion(self):
        """
        Enable VLAN header insertion in transmitted packets
        """
        if self.kdriver == "fm10k":
            netobj = self.dut.ports_info[dutTxPortId]['port']
            netobj.add_vlan(vlan_id = self.vlan)
            netobj.add_txvlan(vlan_id = self.vlan)

        port = self.tester.get_local_port(dutTxPortId)
        intf = self.tester.get_interface(port)

        self.dut.send_expect("set nbport 2", "testpmd> ")
        self.dut.send_expect("tx_vlan set %s %d" % (dutTxPortId, self.vlan), "testpmd> ")

        self.dut.send_expect("start", "testpmd> ")
        self.vlan_send_packet(-1)

        out = self.get_tcpdump_package()
        self.verify(self.vlan in out, "Vlan not found:" + str(out))
        self.dut.send_expect("tx_vlan reset %s" % dutTxPortId, "testpmd> ", 30)
        self.dut.send_expect("stop", "testpmd> ", 30)

        if self.kdriver == "fm10k":
            netobj = self.dut.ports_info[dutTxPortId]['port']
            # not delete vlan for self.vlan will used later
            netobj.delete_txvlan(vlan_id = self.vlan)

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
        if self.kdriver == "fm10k":
            netobj = self.dut.ports_info[dutRxPortId]['port']
            netobj.delete_txvlan(vlan_id = self.vlan)
            netobj.delete_vlan(vlan_id = self.vlan)
