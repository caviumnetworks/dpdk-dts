# BSD LICENSE
#
# Copyright(c) 2010-2017 Intel Corporation. All rights reserved.
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

vhost pmd xstats test suite.
"""
import os
import string
import re
import time
import utils
import datetime
import copy
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator
from qemu_kvm import QEMUKvm
from packet import Packet, sniff_packets, load_sniff_packets


class TestVhostPmdXstats(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.dut_ports = self.dut.get_ports(self.nic)
        self.unbind_ports = copy.deepcopy(self.dut_ports)
        self.unbind_ports.remove(0)
        self.dut.unbind_interfaces_linux(self.unbind_ports)
        cores = self.dut.get_core_list("1S/4C/1T")
        self.coremask = utils.create_mask(cores)

        self.scapy_num = 0
        self.dmac = self.dut.get_mac_address(self.dut_ports[0])
        self.virtio1_mac = "52:54:00:00:00:01"

        # build sample app
        out = self.dut.build_dpdk_apps("./examples/vhost")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def set_up(self):
        """ 
        Run before each test case.
        Launch vhost sample using default params
        """
        self.dut.send_expect("rm -rf ./vhost.out", "#")
        self.dut.send_expect("rm -rf ./vhost-net*", "#")
        self.dut.send_expect("killall vhost-switch", "#")
        self.dut.send_expect("killall qemu-system-x86_64", "#")

    def vm_testpmd_start(self):
        """
        Start testpmd in vm
        """
        self.vm_testpmd = "./%s/app/testpmd -c 0x3 -n 4 -- -i --txqflags=0xf01" % self.target
        if self.vm_dut is not None:
            self.vm_dut.send_expect(self.vm_testpmd, "testpmd>", 60)

    def vm_tx_first_start(self):
        """
        Start tx_first
        """
        if self.vm_dut is not None:
            # Start tx_first
            self.vm_dut.send_expect("set fwd mac", "testpmd>")
            self.vm_dut.send_expect("start tx_first", "testpmd>")

    def start_onevm(self):
        """
        Start One VM with one virtio device
        """
        self.vm_dut = None
        self.vm = QEMUKvm(self.dut, 'vm0', 'vhost_pmd_xstats')
        vm_params = {}
        vm_params['driver'] = 'vhost-user'
        vm_params['opt_path'] = './vhost-net'
        vm_params['opt_mac'] = self.virtio1_mac
        self.vm.set_vm_device(**vm_params)

        try:
            self.vm_dut = self.vm.start()
            if self.vm_dut is None:
                raise Exception("Set up VM ENV failed")
        except Exception as e:
            self.logger.error("Failure for %s" % str(e))
        return True

    def scapy_send_packet(self, pktsize, dmac, num=1):
        """
        Send a packet to port
        """
        self.scapy_num += 1
        txport = self.tester.get_local_port(self.dut_ports[0])
        self.txItf = self.tester.get_interface(txport)
        pkt = Packet(pkt_type='TCP', pkt_len=pktsize)
        pkt.config_layer('ether', {'dst': dmac, })
        pkt.send_pkt(tx_port=self.txItf, count=num)

    def send_verify(self, scope, mun):
        """
        according the scope to check results
        """
        out = self.dut.send_expect(
            "show port xstats %s" % self.dut_ports[0], "testpmd>", 60)
        packet = re.search("rx_%s_packets:\s*(\d*)" % scope, out)
        sum_packet = packet.group(1)
        self.verify(int(sum_packet) >= mun,
                    "Insufficient the received package")

    def prepare_start(self):
        """
        prepare all of the conditions for start
        """
        self.dut.send_expect("./%s/app/testpmd -c %s -n %s --socket-mem 1024,0 --vdev 'net_vhost0,iface=vhost-net,queues=1' -- -i --nb-cores=1" %
                             (self.target, self.coremask, self.dut.get_memory_channels()), "testpmd>", 60)
        self.start_onevm()
        self.vm_testpmd_start()
        self.dut.send_expect("set fwd mac", "testpmd>", 60)
        self.dut.send_expect("start tx_first", "testpmd>", 60)
        self.vm_tx_first_start()

    def test_based_size(self):
        """
        Verify receiving and transmitting packets correctly in the Vhsot PMD xstats
        """
        self.prepare_start()
        sizes = [64, 65, 128, 256, 513, 1025]
        scope = ''
        for pktsize in sizes:
            if pktsize == 64:
                scope = 'size_64'
            elif 65 <= pktsize <= 127:
                scope = 'size_65_to_127'
            elif 128 <= pktsize <= 255:
                scope = 'size_128_to_255'
            elif 256 <= pktsize <= 511:
                scope = 'size_256_to_511'
            elif 512 <= pktsize <= 1023:
                scope = 'size_512_to_1023'
            elif 1024 <= pktsize:
                scope = 'size_1024_to_max'

            self.scapy_send_packet(pktsize, self.dmac, 10000)
            self.send_verify(scope, 10000)
            self.clear_port_xstats(scope)

    def clear_port_xstats(self, scope):

        self.dut.send_expect("clear port xstats all", "testpmd>", 60)
        out = self.dut.send_expect(
            "show port xstats %s" % self.dut_ports[0], "testpmd>", 60)
        packet = re.search("rx_%s_packets:\s*(\d*)" % scope, out)
        sum_packet = packet.group(1)
        self.verify(int(sum_packet) == 0, "Insufficient the received package")

    def test_based_types(self):
        """
        Verify different type of packets receiving and transmitting packets correctly in the Vhsot PMD xstats
        """
        self.prepare_start()
        types = ['ff:ff:ff:ff:ff:ff', '01:00:00:33:00:01']
        scope = ''
        for p in types:
            if p == 'ff:ff:ff:ff:ff:ff':
                scope = 'broadcast'
                self.dmac = 'ff:ff:ff:ff:ff:ff'
            elif p == '01:00:00:33:00:01':
                scope = 'multicast'
                self.dmac = '01:00:00:33:00:01'
            self.scapy_send_packet(64, self.dmac, 10000)
            self.send_verify(scope, 10000)
            self.clear_port_xstats(scope)

    def test_stability(self):
        """
        Verify stability case with multiple queues for Vhsot PMD xstats 
        Send packets for 30 minutes, check the Xstatsa still can work correctly
        """
        self.scapy_num = 0
        self.prepare_start()
        date_old = datetime.datetime.now()
        date_new = date_old + datetime.timedelta(minutes=2)
        while(1):
            date_now = datetime.datetime.now()
            self.scapy_send_packet(64, self.dmac, 1)
            if date_now >= date_new:
                break
        out_0 = self.dut.send_expect(
            "show port xstats %s" % self.dut_ports[0], "testpmd>", 60)
        rx_packet = re.search("rx_size_64_packets:\s*(\d*)", out_0)
        rx_packets = rx_packet.group(1)
        self.verify(self.scapy_num == int(rx_packets), "Error for rx_package:%s != tx_package :%s" % (
            self.scapy_num, int(rx_packets)))

    def tear_down(self):
        """
        Run after each test case.
        """
        self.vm._stop_vm()
        self.dut.kill_all()
        time.sleep(2)

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.bind_interfaces_linux(nics_to_bind=self.unbind_ports)
