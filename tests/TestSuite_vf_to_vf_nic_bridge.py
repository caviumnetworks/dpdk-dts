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
DPDK Test suite
Test vf to vf nic bridge
"""

import re
import dts
import time
import pdb

from test_case import TestCase
from qemu_kvm import QEMUKvm
from pmd_output import PmdOutput

VF_NUMS_ON_ONE_PF = 2
VF_TEMP_MAC = "52:54:12:45:67:1%d"
SEND_PACKET = 100

class TestVF2VFBridge(TestCase):
    def set_up_all(self):
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports")
        self.vm0 = None
        self.vm1 = None

    def set_up(self):
        self.set_up_vf_to_vf_env()

    def set_up_vf_to_vf_env(self, driver='default'):
        self.pf_port_for_vfs = self.dut_ports[0]
        self.dut.restore_interfaces()
        self.dut.generate_sriov_vfs_by_port(self.pf_port_for_vfs, VF_NUMS_ON_ONE_PF, driver=driver)
        self.sriov_vfs_ports = self.dut.ports_info[self.pf_port_for_vfs]['vfs_port']
        self.host_port_intf = self.dut.ports_info[self.pf_port_for_vfs]['intf']
        for i in range(VF_NUMS_ON_ONE_PF):
            self.dut.send_expect('ip link set dev %s vf %d mac %s' % \
                                (self.host_port_intf, i, VF_TEMP_MAC % i), '#', 10)
        try:
            for port in self.sriov_vfs_ports:
                port.bind_driver('pci-stub')
            time.sleep(1)
        except Exception as e:
            raise Exception(e)
        
        vf0_prop = {'opt_host' : self.sriov_vfs_ports[0].pci}
        vf1_prop = {'opt_host' : self.sriov_vfs_ports[1].pci}
        time.sleep(1)
        self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_to_vf_bridge')
        self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
        try:
            self.vm0_dut = self.vm0.start()
            if self.vm0_dut is None:
                raise Exception('Set up VM0 failed')
        except Exception as e:
            print dts.RED(str(e))
        
        self.vm1 = QEMUKvm(self.dut, 'vm1', 'vf_to_vf_bridge')
        self.vm1.set_vm_device(driver='pci-assign', **vf1_prop)
        try:
            self.vm1_dut = self.vm1.start()
            if self.vm1_dut is None:
                raise Exception('Set up VM1 failed')
        except Exception as e:
            print dts.RED(str(e))
    
    def clear_vf_to_vf_env(self):
        if self.vm0 is not None:
            self.vm0.stop()
            self.vm0 = None
        if self.vm1 is not None:
            self.vm1.stop()
            self.vm1 = None
        if self.pf_port_for_vfs is not None:
            self.dut.destroy_sriov_vfs_by_port(self.pf_port_for_vfs)
            port = self.dut.ports_info[self.pf_port_for_vfs]['port']
            port.bind_driver()
            self.pf_port_for_vfs = 0
    
    def generate_pcap_pkt(self, dst, src, load, pktname='flow.pcap'):
        """
        dst:
            server: dst server object
             ether: dst mac
                ip: dst ip
               udp: dst udp protocol
               tcp: dst tcp protocal
        src:
            server: src server object
             ether: src mac
                ip: src ip
               udp: src udp protocol
               tcp: src tcp protocal
        load:
           content: pay load
            length: content length
        """
        context = '[Ether(dst="%s", src="%s")/IP()/Raw(load=%s)]' % \
                   (str(dst['ether']), str(src['ether']),load['content'])
        src['server'].send_expect('scapy', '>>> ', 10)
        src['server'].send_expect('wrpcap("%s", %s)'% (pktname, context), '>>> ', 10)
        src['server'].send_expect('quit()', '#', 10)
    
    def prepare_pktgen(self, vm):
        vm.session.copy_file_to('./dep/tgen.tgz')
        vm.send_expect("cd /root", "#", 10)
        vm.send_expect("tar xvf tgen.tgz", '#', 20)
        
    def send_stream_pktgen(self, vm, pktname='flow.pcap'):
        vm.send_expect("echo 2048 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages", "#", 10)
        vm.send_expect(" mount -t hugetlbfs nodedev /mnt/huge/", "#", 10)
        vm.send_expect("./pktgen -c 0xf -n 2 --proc-type auto -- -P -T -m '1.0' -s 0:%s" % pktname, "", 100)
        time.sleep(60)
        vm.send_expect("set 0 rate 50", "", 20)
        time.sleep(5)
        vm.send_expect("set 0 count %d" % SEND_PACKET, "", 20)
        time.sleep(5)
        vm.send_expect("start all", "", 20)
        time.sleep(20)

    def stop_stream_pktgen(self, vm):
        vm.send_expect("stop all", "", 20)
        time.sleep(5)
        vm.send_expect("quit", "#", 20)
    
    def test_2vf_d2d_pktgen_stream(self):
        self.vm0_ports = self.vm0_dut.get_ports('any')
        self.vm0_pmd = PmdOutput(self.vm0_dut)
        if self.kdriver == "i40e":
            self.vm0_pmd.start_testpmd('all', '--crc-strip')
        else:
            self.vm0_pmd.start_testpmd('all')
        self.vm0_pmd.execute_cmd('set fwd rxonly')
        self.vm0_pmd.execute_cmd('start')

        self.vm1_ports = self.vm1_dut.get_ports('any')
        self.prepare_pktgen(self.vm1_dut)

        dst = {}
        dst['server'] = self.vm0_dut
        dst['ether'] = self.vm0_dut.ports_info[self.vm0_ports[0]]['mac']
        src = {}
        src['server'] = self.vm1_dut
        src['ether'] = self.vm1_dut.ports_info[self.vm1_ports[0]]['mac']
        load = {}
        load['content'] = "'X'*46"
        self.generate_pcap_pkt(dst, src, load)
        self.send_stream_pktgen(self.vm1_dut)
        recv_num = self.vm0_pmd.get_pmd_stats(0)['RX-packets']
        time.sleep(1)
        self.stop_stream_pktgen(self.vm1_dut)
        self.vm0_pmd.execute_cmd('stop')
        self.vm0_pmd.execute_cmd('quit', '# ')
        
        self.verify(recv_num is SEND_PACKET,'Rx port recv error: %d' % recv_num)
    
    def test_2vf_d2k_pktgen_stream(self):
        self.vm0_dut.restore_interfaces()
        self.vm0_ports = self.vm0_dut.get_ports('any')
        vf0_intf = self.vm0_dut.ports_info[self.vm0_ports[0]]['intf']
        self.vm0_dut.send_expect('tcpdump -i %s -s 1000 ' % vf0_intf, 'tcpdump', 30)

        self.vm1_ports = self.vm1_dut.get_ports('any')
        self.prepare_pktgen(self.vm1_dut)

        dst = {}
        dst['server'] = self.vm0_dut
        dst['ether'] = self.vm0_dut.ports_info[self.vm0_ports[0]]['mac']
        src = {}
        src['server'] = self.vm1_dut
        src['ether'] = self.vm1_dut.ports_info[self.vm1_ports[0]]['mac']
        load = {}
        load['content'] = "'X'*46"
        self.generate_pcap_pkt(dst, src, load)
        self.send_stream_pktgen(self.vm1_dut)
        self.stop_stream_pktgen(self.vm1_dut)

        recv_tcpdump = self.vm0_dut.send_expect('^C', '#', 30)
        time.sleep(5)
        recv_pattern = re.compile("(\d+) packets captured")
        recv_info = recv_pattern.search(recv_tcpdump)
        recv_str = recv_info.group(0).split(' ')[0]
        recv_number = int(recv_str, 10)
        self.vm0_dut.bind_interfaces_linux(dts.drivername)
        
        self.verify(recv_number is SEND_PACKET, 'Rx port recv error: %d' % recv_number)
    
    def test_2vf_k2d_scapy_stream(self):
        self.vm0_ports = self.vm0_dut.get_ports('any')
        self.vm0_pmd = PmdOutput(self.vm0_dut)
        if self.kdriver == "i40e":
            self.vm0_pmd.start_testpmd('all', '--crc-strip')
        else:
            self.vm0_pmd.start_testpmd('all')
        self.vm0_pmd.execute_cmd('set fwd rxonly')
        self.vm0_pmd.execute_cmd('start')
        self.vm0_pmd.execute_cmd('clear port stats all')

        self.vm1_ports = self.vm1_dut.get_ports('any')
        self.vm1_dut.restore_interfaces()
        vf1_intf = self.vm1_dut.ports_info[self.vm1_ports[0]]['intf']

        dst_mac = self.vm0_dut.ports_info[self.vm0_ports[0]]['mac']
        src_mac = self.vm1_dut.ports_info[self.vm1_ports[0]]['mac']
        pkt_content = 'Ether(dst="%s", src="%s")/IP()/Raw(load="X"*46)' % \
                      (dst_mac, src_mac)
        self.vm1_dut.send_expect('scapy', '>>> ', 10)
        self.vm1_dut.send_expect('sendp([%s], iface="%s", count=%d)' % (pkt_content, vf1_intf, SEND_PACKET), '>>> ', 30)
        self.vm1_dut.send_expect('quit()', '# ', 10)
        self.vm1_dut.bind_interfaces_linux(dts.drivername)
        recv_num = self.vm0_pmd.get_pmd_stats(0)['RX-packets']
        self.vm0_pmd.execute_cmd('stop')
        self.vm0_pmd.execute_cmd('quit', '# ')

        self.verify(recv_num is SEND_PACKET, 'Rx port recv error: %d' % recv_num)
    
    def tear_down(self):
        self.clear_vf_to_vf_env()
    
    def tear_down_all(self):
        pass
