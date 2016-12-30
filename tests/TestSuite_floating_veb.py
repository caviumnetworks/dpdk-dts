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

Test VEB Switch and floating VEB Features by Poll Mode Drivers.
"""

import re
import time

from virt_dut import VirtDut
from project_dpdk import DPDKdut
from dut import Dut
from test_case import TestCase
from pmd_output import PmdOutput
from settings import HEADER_SIZE
from packet import Packet
from utils import RED


class TestVEBSwitching(TestCase):

    def VEB_get_stats(self, vf0_vf1, portid, rx_tx):
        """
        Get packets number from port statistic
        """
        if vf0_vf1 == "vf0":
            stats = self.pmdout.get_pmd_stats(portid)
        elif vf0_vf1 == "vf1":
            stats = self.pmdout_session_secondary.get_pmd_stats(portid)
        else:
            return None

        if rx_tx == "rx":
            return [stats['RX-packets'], stats['RX-errors'], stats['RX-bytes']]
        elif rx_tx == "tx":
            return [stats['TX-packets'], stats['TX-errors'], stats['TX-bytes']]
        else:
            return None
    
    def veb_get_pmd_stats(self, dev, portid, rx_tx):
        stats = {}
        rx_pkts_prefix = "RX-packets:"
        rx_bytes_prefix = "RX-bytes:"
        rx_error_prefix = "RX-errors:"
        tx_pkts_prefix = "TX-packets:"
        tx_error_prefix = "TX-errors:"
        tx_bytes_prefix = "TX-bytes:"

        if dev == "first":
            out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        elif dev == "second":
            out = self.session_secondary.send_expect("show port stats %d" % portid, "testpmd> ")
        elif dev == "third":
            out = self.session_third.send_expect("show port stats %d" % portid, "testpmd> ")
        else:
            return None

        stats["RX-packets"] = self.veb_get_pmd_value(rx_pkts_prefix, out)
        stats["RX-bytes"] = self.veb_get_pmd_value(rx_bytes_prefix, out)
        stats["RX-errors"] = self.veb_get_pmd_value(rx_error_prefix, out)
        stats["TX-packets"] = self.veb_get_pmd_value(tx_pkts_prefix, out)
        stats["TX-errors"] = self.veb_get_pmd_value(tx_error_prefix, out)
        stats["TX-bytes"] = self.veb_get_pmd_value(tx_bytes_prefix, out)

        if rx_tx == "rx":
            return [stats['RX-packets'], stats['RX-errors'], stats['RX-bytes']]
        elif rx_tx == "tx":
            return [stats['TX-packets'], stats['TX-errors'], stats['TX-bytes']]
        else:
            return None


    def veb_get_pmd_value(self, prefix, out):
        pattern = re.compile(prefix + "(\s+)([0-9]+)")
        m = pattern.search(out)
        if m is None:
            return None
        else:
            return int(m.group(2))

    def send_packet(self, vf_mac, itf, tran_type=""):
        """
        Send 1 packet
        """
        self.dut.send_expect("start", "testpmd>")
        mac = self.dut.get_mac_address(0)

        if tran_type == "vlan":
            pkt = Packet(pkt_type='VLAN_UDP')
            pkt.config_layer('ether', {'dst': vf_mac})
            pkt.config_layer('vlan', {'vlan': 1})
            pkt.send_pkt(tx_port=itf)
            time.sleep(.5)
        else:
            pkt = Packet(pkt_type='UDP')
            pkt.config_layer('ether', {'dst': vf_mac})
            pkt.send_pkt(tx_port=itf)
            time.sleep(.5)
   
    # Test cases.
    
    def set_up_all(self):
        """
        Prerequisite steps for each test suite.
        """
        self.verify(self.nic in ["fortville_eagle", "fortville_spirit",
                    "fortville_spirit_single"],
                    "NIC Unsupported: " + str(self.nic))
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")
        self.session_secondary = self.dut.new_session()
        self.session_third = self.dut.new_session()
        
        self.setup_1pf_ddriver_1vf_env_flag = 0
        self.setup_1pf_ddriver_2vf_env_flag = 0
        self.setup_1pf_ddriver_4vf_env_flag = 0
        self.vf0_mac = "00:11:22:33:44:11"
        self.vf1_mac = "00:11:22:33:44:12"
        self.vf2_mac = "00:11:22:33:44:13"
        self.vf3_mac = "00:11:22:33:44:14"
        
        self.used_dut_port = self.dut_ports[0]
        localPort = self.tester.get_local_port(self.dut_ports[0])
        self.tester_itf = self.tester.get_interface(localPort)
        self.pf_interface = self.dut.ports_info[self.used_dut_port]['intf']
        self.pf_mac_address = self.dut.get_mac_address(0)
        self.pf_pci = self.dut.ports_info[self.used_dut_port]['pci']

    def set_up(self):
        """
        This is to clear up environment before the case run.
        """
        self.dut.kill_all()

    def setup_env(self, driver, vf_num):
        """
        This is to set up 1pf and nvfs environment, which pf bond to 
        dpdk driver, and nvfs(1,2,4)bond to dpdk driver.
        """
        
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port, vf_num, driver)
        self.sriov_vfs_port = self.dut.ports_info[self.used_dut_port]['vfs_port']
        try:

            for port in self.sriov_vfs_port:
                port.bind_driver(driver=self.drivername)
            if vf_num == 1:
                self.setup_1pf_ddriver_1vf_env_flag = 1
            elif vf_num == 2:
                self.setup_1pf_ddriver_2vf_env_flag = 1
            else:
                self.setup_1pf_ddriver_4vf_env_flag = 1
        except Exception as e:
            self.destroy_env(vf_num)
            raise Exception(e)

    def destroy_env(self, vf_num):
        """
        This is to destroy the 1pf and nvfs environment.  
        """
        if vf_num != 1:
            self.session_third.send_expect("quit", "# ")
        time.sleep(2)
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)
        self.dut.send_expect("quit", "# ")
        time.sleep(2)
        self.dut.destroy_sriov_vfs_by_port(self.used_dut_port)
        if vf_num == 1:
            self.setup_1pf_ddriver_1vf_env_flag = 0
        elif vf_num == 2:
            self.setup_1pf_ddriver_2vf_env_flag = 0
        else:
            self.setup_1pf_ddriver_4vf_env_flag = 0
 
    def test_floating_VEB_inter_pf_vf(self):
        """
        DPDK PF, then create 1VF, PF in the host running dpdk testpmd, 
        send traffic from PF to VF0, VF0 can't receive any packets; 
        send traffic from VF0 to PF, PF can't receive any packets either.
        """
        # VF->PF
        self.setup_env(driver=self.drivername, vf_num=1)
        self.dut.send_expect("./%s/app/testpmd -c 0xf -n 4 --socket-mem 1024,1024 -w %s,enable_floating_veb=1 --file-prefix=test1 -- -i" % (self.target, self.pf_pci), "testpmd>", 120)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[0].pci, self.pf_mac_address), "testpmd>", 120)
        self.session_secondary.send_expect("set fwd txonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.dut.send_expect("stop", "testpmd>", 2)

        vf0_tx_stats = self.veb_get_pmd_stats("second", 0, "tx")
        pf_rx_stats = self.veb_get_pmd_stats("first", 0, "rx")
        self.verify(vf0_tx_stats[0] != 0, "no packet was sent by VF0")
        self.verify(pf_rx_stats[0] == 0, "PF can receive packet from VF0, the floating VEB doesn't work")
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)
        self.dut.send_expect("quit", "# ")
        time.sleep(2)

        #PF->VF
        self.dut.send_expect("./%s/app/testpmd -c 0xf -n 4 --socket-mem 1024,1024 -w %s,enable_floating_veb=1 --file-prefix=test1 -- -i --eth-peer=0,%s" % (self.target, self.pf_pci, self.vf0_mac), "testpmd>", 120)
        self.dut.send_expect("set fwd txonly", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")

        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[0].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd rxonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        self.dut.send_expect("start", "testpmd>")
        time.sleep(2)

        self.dut.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)

        vf0_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        pf_tx_stats = self.veb_get_pmd_stats("first", 0, "tx")
        self.verify(pf_tx_stats[0] != 0, "no packet was sent by PF")
        self.verify(vf0_rx_stats[0] == 0, "VF0 can receive packet from PF, the floating VEB doesn't work")
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)
        self.dut.send_expect("quit", "# ")
        time.sleep(2)

        #outside world ->VF
        self.dut.send_expect("./%s/app/testpmd -c 0xf -n 4 --socket-mem 1024,1024 -w %s,enable_floating_veb=1 --file-prefix=test1 -- -i --eth-peer=0,%s" % (self.target, self.pf_pci, self.vf0_mac), "testpmd>", 120)
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all on", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[0].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd mac", "testpmd>")
        self.session_secondary.send_expect("set promisc all on", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.send_packet(self.vf0_mac, self.tester_itf)
        time.sleep(2)
        self.dut.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)

        vf0_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        self.verify(vf0_rx_stats[0] == 0, "VF0 can receive packet from outside world, the floating VEB doesn't work")

    def test_floating_VEB_inter_vfs(self):
        """
        1 DPDK PF, then create 2VF, PF in the host running dpdk testpmd,
        and VF0 are running dpdk testpmd, VF0 send traffic, and set the
        packet's DEST MAC to VF1, check if VF1 can receive the packets.
        Check Inter VF-VF MAC switch when PF is link down as well as up.
        """
        # PF link up, VF0->VF1
        self.setup_env(driver=self.drivername, vf_num=2)
        # start PF
        self.dut.send_expect("./%s/app/testpmd -c 0xf -n 4 --socket-mem 1024,1024 -w %s,enable_floating_veb=1 --file-prefix=test1 -- -i" % (self.target, self.pf_pci), "testpmd>", 120)
        self.dut.send_expect("port start all", "testpmd>")
        time.sleep(2)
        # start VF0
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[0].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd rxonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        # start VF1
        self.session_third.send_expect("./%s/app/testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test3 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[1].pci, self.vf0_mac), "testpmd>", 120)
        self.session_third.send_expect("set fwd txonly", "testpmd>")
        self.session_third.send_expect("set promisc all off", "testpmd>")
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)
 
        self.session_third.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)

        vf0_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        vf1_tx_stats = self.veb_get_pmd_stats("third", 0, "tx")
        self.verify(vf1_tx_stats[0] != 0, "no packet was sent by VF1")
        self.verify(vf0_rx_stats[0] != 0, "no packet was received by VF0")
        self.verify(vf1_tx_stats[0]*0.5 < vf0_rx_stats[0], "VF0 failed to receive most packets from VF1")

        # PF link down, VF0 -> VF1
        self.dut.send_expect("port stop all", "testpmd>", 10)
        self.dut.send_expect("show port info 0", "Link status: down", 10)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_third.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.dut.send_expect("stop", "testpmd>", 2)

        vf1_tx_stats_pfstop = self.veb_get_pmd_stats("third", 0, "tx")
        vf0_rx_stats_pfstop = self.veb_get_pmd_stats("second", 0, "rx")
        vf1_tx_stats_pfstop[0] = vf1_tx_stats_pfstop[0] - vf1_tx_stats[0]
        vf0_rx_stats_pfstop[0] = vf0_rx_stats_pfstop[0] - vf0_rx_stats[0]
        self.verify(vf1_tx_stats_pfstop[0] != 0, "no packet was sent by VF1")
        self.verify(vf0_rx_stats_pfstop[0] != 0, "no packet was received by VF0")
        self.verify(vf1_tx_stats_pfstop[0]*0.5 < vf0_rx_stats_pfstop[0], "VF0 failed to receive most packets from VF1")
        
    def test_floating_VEB_VF_and_legacy_VEB_VF(self):
        """
        DPDK PF, then create 4VF, VF0,VF2,VF3 are floating VEB; VF1 is lagecy
        VEB. Make PF link down(the cable can be pluged out), VFs are running
        dpdk testpmd.
        1. VF0 send traffic, and set the packet's DEST MAC to VF1, 
           check VF1 can not receive the packets. 
        2. VF1 send traffic, and set the packet's DEST MAC to VF0,
           check VF0 can not receive the packets.
        3. VF0 send traffic, and set the packet's DEST MAC to VF2, 
           check VF2 can receive the packets. 
        4. VF3 send traffic, and set the packet's DEST MAC to VF2,
           check VF2 can receive the packets.
        """
        self.setup_env(driver=self.drivername, vf_num=4)
        # start PF
        self.dut.send_expect("./%s/app/testpmd -c 0xf -n 4 --socket-mem 1024,1024 \"-w %s,enable_floating_veb=1,floating_veb_list=0;2-3\" --file-prefix=test1 -- -i" % (self.target, self.pf_pci), "testpmd>", 120)
        self.dut.send_expect("port start all", "testpmd>")
        time.sleep(2)
        # VF1->VF0
        # start VF0
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[0].pci, self.vf1_mac), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd rxonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        # start VF1
        self.session_third.send_expect("./%s/app/testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test3 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[1].pci, self.vf0_mac), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf1_mac, "testpmd>")
        self.session_third.send_expect("set fwd txonly", "testpmd>")
        self.session_third.send_expect("set promisc all off", "testpmd>")
        
        # PF link down
        self.dut.send_expect("port stop all", "testpmd>", 30)
        self.dut.send_expect("show port info 0", "Link status: down", 10)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_third.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)

        vf0_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        vf1_tx_stats = self.veb_get_pmd_stats("third", 0, "tx")
        self.verify(vf1_tx_stats[0] != 0, "no packet was sent by VF1")
        self.verify(vf0_rx_stats[0] == 0, "floating_VEB VF can communicate with legacy_VEB VF")

        # VF0->VF1
        self.session_secondary.send_expect("set fwd txonly", "testpmd>")
        self.session_third.send_expect("set fwd rxonly", "testpmd>")
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.session_third.send_expect("stop", "testpmd>", 2)
        vf1_rx_stats = self.veb_get_pmd_stats("third", 0, "rx")
        vf0_tx_stats = self.veb_get_pmd_stats("second", 0, "tx")
        self.verify(vf0_tx_stats[0] != 0, "no packet was sent by VF0")
        self.verify(vf1_rx_stats[0] == 0, "floating_VEB VF can communicate with legacy_VEB VF")

        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)
        self.session_third.send_expect("quit", "# ")
        time.sleep(2)
 
        # VF0->VF2
        # start VF0
        self.dut.send_expect("port start all", "testpmd>")
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[0].pci, self.vf2_mac), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd txonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        # start VF2
        self.session_third.send_expect("./%s/app/testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test3 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[2].pci), "testpmd>", 120)
        self.session_third.send_expect("mac_addr add 0 %s" % self.vf2_mac, "testpmd>")
        self.session_third.send_expect("set fwd rxonly", "testpmd>")
        self.session_third.send_expect("set promisc all off", "testpmd>")

        # PF link down
        self.dut.send_expect("port stop all", "testpmd>", 30)
        self.dut.send_expect("show port info 0", "Link status: down", 10)
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.session_third.send_expect("stop", "testpmd>", 2)

        vf2_rx_stats = self.veb_get_pmd_stats("third", 0, "rx")
        vf0_tx_stats = self.veb_get_pmd_stats("second", 0, "tx")
        self.verify(vf0_tx_stats[0] != 0, "no packet was sent by VF0")
        self.verify(vf2_rx_stats[0] != 0, "floating_VEB VFs cannot communicate with each other")
        self.verify(vf0_tx_stats[0] * 0.5 < vf2_rx_stats[0], "VF2 failed to receive packets from VF0")
        
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)
        self.session_third.send_expect("quit", "# ")
        time.sleep(2)

        # VF3->VF2
        # start VF3
        self.dut.send_expect("port start all", "testpmd>")
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[3].pci, self.vf2_mac), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd txonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        # start VF2
        self.session_third.send_expect("./%s/app/testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test3 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[2].pci), "testpmd>", 120)
        self.session_third.send_expect("mac_addr add 0 %s" % self.vf2_mac, "testpmd>")
        self.session_third.send_expect("set fwd rxonly", "testpmd>")
        self.session_third.send_expect("set promisc all off", "testpmd>")

        # PF link down
        self.dut.send_expect("port stop all", "testpmd>", 30)
        self.dut.send_expect("show port info 0", "Link status: down", 10)
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.session_third.send_expect("stop", "testpmd>", 2)

        vf2_rx_stats = self.veb_get_pmd_stats("third", 0, "rx")
        vf3_tx_stats = self.veb_get_pmd_stats("second", 0, "tx")
        self.verify(vf3_tx_stats[0] != 0, "no packet was sent by VF0")
        self.verify(vf2_rx_stats[0] != 0, "floating_VEB VFs cannot communicate with each other")
        self.verify(vf3_tx_stats[0] * 0.5 < vf2_rx_stats[0], "VF2 failed to receive packets from VF3")
    
    def test_floating_VEB_and_legacy_VEB_inter_pf_vf(self):
        """
        DPDK PF, then create 4VFs, VF0 and VF3 is in floating VEB, 
        VF1 and VF2 are in legacy VEB.
        1. Send traffic from VF0 to PF, then check PF will not see any traffic; 
        2. Send traffic from VF1 to PF, then check PF will receive all the 
           packets.
        3. send traffic from tester to VF0, check VF0 can't receive traffic 
           from tester.
        4. send traffic from tester to VF1, check VF1 can receive all the 
           traffic from tester.
        5. send traffic from VF1 to VF2, check VF2 can receive all the traffic
           from VF1.
        """
        self.setup_env(driver=self.drivername, vf_num=4)
        # VF0->PF
        self.dut.send_expect("./%s/app/testpmd -c 0xf -n 4 --socket-mem 1024,1024 \"-w %s,enable_floating_veb=1,floating_veb_list=0;3\" --file-prefix=test1 -- -i" % (self.target, self.pf_pci), "testpmd>", 120)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[0].pci, self.pf_mac_address), "testpmd>", 120)
        self.session_secondary.send_expect("set fwd txonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.dut.send_expect("stop", "testpmd>", 2)

        vf0_tx_stats = self.veb_get_pmd_stats("second", 0, "tx")
        pf_rx_stats = self.veb_get_pmd_stats("first", 0, "rx")
        self.verify(vf0_tx_stats[0] != 0, "no packet was sent by VF0")
        self.verify(pf_rx_stats[0] == 0, "PF can receive packet from VF0, the floating VEB doesn't work")
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)

        # VF1->PF
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[1].pci, self.pf_mac_address), "testpmd>", 120)
        self.session_secondary.send_expect("set fwd txonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        time.sleep(2)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.dut.send_expect("stop", "testpmd>", 2)

        vf1_tx_stats = self.veb_get_pmd_stats("second", 0, "tx")
        pf_rx_stats = self.veb_get_pmd_stats("first", 0, "rx")
        self.verify(vf1_tx_stats[0] != 0, "no packet was sent by VF1")
        self.verify(pf_rx_stats[0] != 0, "PF can't receive packet from VF1, the VEB doesn't work")
        self.verify(vf1_tx_stats[0] * 0.5 < pf_rx_stats[0], "PF failed to receive packets from VF1")
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)
     
        # tester->VF0
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[0].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf0_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd mac", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.send_packet(self.vf0_mac, self.tester_itf)
        time.sleep(2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.dut.send_expect("stop", "testpmd>", 2)

        vf0_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        self.verify(vf0_rx_stats[0] == 0, "VF0 can receive packet from outside world, the floating VEB doesn't work")
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)

        # tester->VF1
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[1].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf1_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd mac", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.send_packet(self.vf1_mac, self.tester_itf)
        time.sleep(2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)
        self.dut.send_expect("stop", "testpmd>", 2)

        vf1_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        self.verify(vf1_rx_stats[0] == 1, "VF1 can't receive packet from outside world, the VEB doesn't work")
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)

        # VF2->VF1
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[1].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf1_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd rxonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_third.send_expect("./%s/app/testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test3 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[2].pci, self.vf1_mac), "testpmd>", 120)
        self.session_third.send_expect("set fwd txonly", "testpmd>")
        self.session_third.send_expect("set promisc all off", "testpmd>")
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_third.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)

        vf1_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        vf2_tx_stats = self.veb_get_pmd_stats("third", 0, "tx")
        self.verify(vf2_tx_stats[0] != 0, "no packet was sent by VF2")
        self.verify(vf1_rx_stats[0] != 0, "VF1 can't receive packet from VF2, the VEB doesn't work")
        self.verify(vf2_tx_stats[0] * 0.5 < vf1_rx_stats[0], "VF1 failed to receive packets from VF2")
        self.session_third.send_expect("quit", "# ")
        time.sleep(2)
        self.session_secondary.send_expect("quit", "# ")
        time.sleep(2)

        # PF link down, VF2->VF1
        self.session_secondary.send_expect("./%s/app/testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test2 -- -i --crc-strip" % (self.target, self.sriov_vfs_port[1].pci), "testpmd>", 120)
        self.session_secondary.send_expect("mac_addr add 0 %s" % self.vf1_mac, "testpmd>")
        self.session_secondary.send_expect("set fwd rxonly", "testpmd>")
        self.session_secondary.send_expect("set promisc all off", "testpmd>")

        self.session_third.send_expect("./%s/app/testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w %s --file-prefix=test3 -- -i --crc-strip --eth-peer=0,%s" % (self.target, self.sriov_vfs_port[2].pci, self.vf1_mac), "testpmd>", 120)
        self.session_third.send_expect("set fwd txonly", "testpmd>")
        self.session_third.send_expect("set promisc all off", "testpmd>")
        
        self.dut.send_expect("port stop all", "testpmd>", 10)
        self.dut.send_expect("show port info 0", "Link status: down", 10)
        self.session_secondary.send_expect("start", "testpmd>")
        time.sleep(2) 
        self.session_third.send_expect("start", "testpmd>")
        time.sleep(2)

        self.session_third.send_expect("stop", "testpmd>", 2)
        self.session_secondary.send_expect("stop", "testpmd>", 2)

        vf1_rx_stats = self.veb_get_pmd_stats("second", 0, "rx")
        vf2_tx_stats = self.veb_get_pmd_stats("third", 0, "tx")
        self.verify(vf2_tx_stats[0] != 0, "no packet was sent by VF2")
        self.verify(vf1_rx_stats[0] != 0, "VF1 can't receive packet from VF2, the VEB doesn't work")
        self.verify(vf2_tx_stats[0] * 0.5 < vf1_rx_stats[0], "VF1 failed to receive packets from VF2")
 
    def tear_down(self):
        """
        Run after each test case.
        """
        if self.setup_1pf_ddriver_1vf_env_flag == 1:
            self.destroy_env(1)
        if self.setup_1pf_ddriver_2vf_env_flag == 1:
            self.destroy_env(2)
        if self.setup_1pf_ddriver_4vf_env_flag == 1:
            self.destroy_env(4)

        self.dut.kill_all()
    
    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
        self.dut.close_session(self.session_secondary)
        self.dut.close_session(self.session_third)
        # Marvin recommended that all the dut ports should be bound to igb_uio.
        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver(driver=self.drivername)

