# BSD LICENSE
#
# Copyright(c) 2010-2016 Intel Corporation. All rights reserved.
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
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
DPDK Test suite.

'''

import re
import time
import sys

import utils
from qemu_kvm import QEMUKvm
from test_case import TestCase
from pmd_output import PmdOutput
from exception import VerifyFailure

from scapy.utils import rdpcap

from packet import Packet, sniff_packets, load_sniff_packets

VM_CORES_MASK = 'all'

class TestEtag(TestCase):
    def set_up_all(self):
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(self.nic in ['sagepond'], '802.1BR only support by sagepond')
        self.verify(len(self.dut_ports) >= 1, 'Insufficient ports')
        self.src_intf = self.tester.get_interface(self.tester.get_local_port(0))
        self.src_mac =  self.tester.get_mac(self.tester.get_local_port(0))
        self.dst_mac = self.dut.get_mac_address(0)
        self.vm0 = None
        self.printFlag = self._enable_debug
        self.dut.send_expect('ls', '#')
        self.setup_vm_env_flag = 0
        self.preset_host_cmds = list()

    def set_up(self):
        pass

    def setup_vm_env(self, driver='default'):
        '''
        setup qemu virtual environment
        '''
        if self.setup_vm_env_flag == 1:
            return

        self.used_dut_port_0 = self.dut_ports[0]
        self.dut.generate_sriov_vfs_by_port(self.used_dut_port_0, 2, driver=driver)
        self.sriov_vfs_port_0 = self.dut.ports_info[self.used_dut_port_0]['vfs_port']

        try:
            for port in self.sriov_vfs_port_0:
                port.bind_driver('pci-stub')

            time.sleep(1)
            vf0_prop = {'opt_host': self.sriov_vfs_port_0[0].pci}
            vf1_prop = {'opt_host': self.sriov_vfs_port_0[1].pci}
            
            # start testpmd without the two VFs on the host
            self.host_testpmd = PmdOutput(self.dut)
            eal_param = '-b %(vf0)s -b %(vf1)s' % {'vf0': self.sriov_vfs_port_0[0].pci,
                                                   'vf1': self.sriov_vfs_port_0[1].pci}

            self.preset_host_testpmd('1S/2C/2T', eal_param)

            # set up VM0 ENV
            self.vm0 = QEMUKvm(self.dut, 'vm0', 'vf_etag')
            self.vm0.set_vm_device(driver='pci-assign', **vf0_prop)
            self.vm0.set_vm_device(driver='pci-assign', **vf1_prop)
            self.vm_dut_0 = self.vm0.start()
            if self.vm_dut_0 is None:
                raise Exception('Set up VM0 ENV failed!')

        except Exception as e:
            print e
            self.destroy_vm_env()
            raise Exception(e)

    def destroy_vm_env(self):
        #destroy testpmd in vm0
        if getattr(self, 'vm0_testpmd', None) and self.vm0_testpmd:
            self.vm0_testpmd.execute_cmd('stop')
            self.vm0_testpmd.execute_cmd('quit', '# ')
            self.vm0_testpmd = None

        #destroy vm0
        if getattr(self, 'vm0', None) and self.vm0:
            self.vm0_dut_ports = None
            self.vm0.stop()
            self.vm0 = None
        
        #destroy host testpmd
        if getattr(self, 'host_testpmd', None):
            self.host_testpmd.execute_cmd('quit', '# ')
            self.host_testpmd = None

        # reset used port's sriov 
        if getattr(self, 'used_dut_port_0', None):
            self.dut.destroy_sriov_vfs_by_port(self.used_dut_port_0)
            port = self.dut.ports_info[self.used_dut_port_0]['port']
            port.bind_driver()
            self.used_dut_port_0 = None

        # bind used ports with default driver 
        for port_id in self.dut_ports:
            port = self.dut.ports_info[port_id]['port']
            port.bind_driver()
        self.setup_vm_env_flag = 0

    def check_packet_transmission(self, pkt_types):
        time.sleep(1)
        for pkt_type in pkt_types.keys():
            intf = self.src_intf
            pkt = Packet(pkt_type=pkt_type)
            # set packet every layer's input parameters
            if 'layer_configs' in pkt_types[pkt_type].keys():
                pkt_configs = pkt_types[pkt_type]['layer_configs']
                if pkt_configs:
                    for layer in pkt_configs.keys():
                        pkt.config_layer(layer, pkt_configs[layer])
            pkt.send_pkt(tx_port=self.src_intf)
            
            # check vm testpmd packet received information
            if 'vm' in pkt_types[pkt_type].keys():
                out = self.vm0_testpmd.get_output(timeout=2)
                if self.printFlag: # debug output
                    print out
                for pkt_attribute in pkt_types[pkt_type]['vm']:
                    if self.printFlag:# debug output
                        print pkt_attribute
                    if pkt_attribute not in out:
                        print utils.RED('Fail to detect %s' % pkt_attribute)
                        if not self.printFlag:# print out all info in debug mode
                            raise VerifyFailure('Failed to detect %s' % pkt_attribute)
                print utils.GREEN('VM detected %s successfully' % pkt_type)

            # check dut testpmd packet received information
            if 'dut' in pkt_types[pkt_type].keys():
                out = self.host_testpmd.get_output(timeout=2)
                if self.printFlag: # debug output
                    print out
                for pkt_attribute in pkt_types[pkt_type]['dut']:
                    if self.printFlag:# debug output
                        print pkt_attribute
                    if pkt_attribute not in out:
                        print utils.RED('Fail to detect %s' % pkt_attribute)
                        if not self.printFlag:# print out all info in debug mode
                            raise VerifyFailure('Failed to detect %s' % pkt_attribute)
                print utils.GREEN('DUT detected %s successfully' % pkt_type)
            time.sleep(1)

    def preset_host_testpmd(self, core_mask, eal_param):
        if self.setup_vm_env_flag == 0:
            self.host_testpmd.start_testpmd(core_mask, 
                                            param='--port-topology=loop', 
                                            eal_param=eal_param)
            self.execute_host_testpmd_cmd(self.preset_host_cmds)
            self.preset_host_cmds = list()
            time.sleep(2)

    def execute_host_testpmd_cmd(self, cmds):
        if len(cmds) == 0:
            return
        for item in cmds:
            if len(item) == 2:
                self.host_testpmd.execute_cmd(item[0], int(item[1]))
            else:
                self.host_testpmd.execute_cmd(item[0])

        time.sleep(2)

    def preset_guest_testpmd(self):
        if self.setup_vm_env_flag == 0:
            self.vm0_testpmd = PmdOutput(self.vm_dut_0)
            self.vm0_testpmd.start_testpmd(VM_CORES_MASK, param='--port-topology=loop')
            time.sleep(1)
        elif self.vm0_testpmd:
            self.vm0_testpmd.quit()
            self.vm0_testpmd.start_testpmd(VM_CORES_MASK, param='--port-topology=loop')
            time.sleep(1)

    def execute_guest_testpmd_cmd(self, cmds):
        if len(cmds) == 0:
            return
        for item in cmds:
            if len(item) == 2:
                self.vm0_testpmd.execute_cmd(item[0], int(item[1]))
            else:
                self.vm0_testpmd.execute_cmd(item[0])

    def preset_test_enviroment(self):
        self.setup_vm_env(driver='igb_uio')
        self.preset_guest_testpmd()
        self.setup_vm_env_flag = 1
        time.sleep(2)

    def test_l2_tunnel_filter(self):
        '''
        Enable E-tag l2 tunnel support means enabling ability of parsing E-tag packet.
        This ability should be enabled before we enable filtering, forwarding,
        offloading for this specific type of tunnel.
        '''
        host_cmds =[['port config 0 l2-tunnel E-tag enable'],
                    ['set fwd rxonly'],
                    ['set verbose 1'],
                    ['start']]
        guest_cmds = [['set fwd rxonly'],
                      ['set verbose 1'],
                      ['start']]
        config_layers =  {'ether': {'src': self.src_mac},
                          'etag':  {'ECIDbase': 1000}}
        pkt_types = {'ETAG_UDP': {'dut':['type=0x893f'],
                                  'vm':['type=0x893f'],
                                  'layer_configs': config_layers}}

        self.preset_test_enviroment()
        self.execute_host_testpmd_cmd(host_cmds)
        self.execute_guest_testpmd_cmd(guest_cmds)
        self.check_packet_transmission(pkt_types)

    def test_etag_filter(self):
        '''
        when E-tag packet forwarding and add E-tag on VF0
        '''
        test_types = ['etag_pf', 'etag_remove', 'etag_vf_0', 'etag_vf_1']
        host_cmds = [['port config 0 l2-tunnel E-tag enable'],
                     ['E-tag set forwarding on port 0']]
        self.preset_test_enviroment()
        self.execute_host_testpmd_cmd(host_cmds)
        for test_type in test_types:
            host_cmds = list()
            guest_cmds = [['set fwd rxonly'],
                          ['set verbose 1'],
                          ['start']]
            if test_type == 'etag_pf':
                # Same E-tag forwarding to PF0, Send 802.1BR packet with broardcast mac and
                # check packet only recevied on PF
                
                host_cmds = [['E-tag set filter add e-tag-id 1000 dst-pool 2 port 0'],
                             ['set fwd mac'],
                             ['set verbose 1'],
                             ['start']]
                # set packet type and its expecting result
                config_layers =  {'ether': {'src': self.src_mac, 'dst': self.dst_mac},
                                  'etag':  {'ECIDbase': 1000}}
                pkt_types = {'ETAG_UDP': {'dut':['type=0x893f'],
                                          'layer_configs': config_layers}}
            elif test_type == 'etag_remove':
                # Remove E-tag, Send 802.1BR packet with broardcast mac and check packet not
                # recevied
                host_cmds = [ ['E-tag set filter del e-tag-id 1000 port 0'],
                              ['set fwd rxonly'],
                              ['set verbose 1'],
                              ['start']]
                config_layers =  {'ether': {'src': self.src_mac},
                                  'etag':  {'ECIDbase': 1000}}
                pkt_types = {'ETAG_UDP': {'vm':[''],
                                          'dut':[''],
                                          'layer_configs': config_layers}}
            else:
                # Same E-tag forwarding to VF0, Send 802.1BR packet with broardcast mac and
                # check packet only recevied on VF0 or VF1
                host_cmds = [['E-tag set filter add e-tag-id 1000 dst-pool %d port 0'%test_type[-1:]],
                             ['set fwd rxonly'],
                             ['set verbose 1'],
                             ['start']]
                config_layers =  {'ether': {'src': self.src_mac},
                                  'etag':  {'ECIDbase': 1000}}
                pkt_types = {'ETAG_UDP': {'vm':['type=0x893f'],
                                          'layer_configs': config_layers}}

            self.execute_host_testpmd_cmd(host_cmds)
            self.execute_guest_testpmd_cmd(guest_cmds)
            self.check_packet_transmission(pkt_types)
        self.host_testpmd.execute_cmd('E-tag set forwarding off port 0')

    def test_etag_insertion(self):
        '''
        When E-tag insertion enable in VF0
        '''
        host_cmds =[['port config 0 l2-tunnel E-tag enable'],
                    ['E-tag set insertion on port-tag-id 1000 port 0 vf 0'],
                    ['set fwd mac'],
                    ['set verbose 1'],
                    ['start']]
        guest_cmds = [['set fwd mac'],
                      ['set verbose 1'],
                      ['start']]
        self.preset_test_enviroment()
        self.execute_host_testpmd_cmd(host_cmds)
        self.execute_guest_testpmd_cmd(guest_cmds)

        self.vm0_dut_ports = self.vm_dut_0.get_ports('any')
        config_layers =  {'ether': {'src': self.src_mac}}
        pkt_types = {'IP_RAW': {'layer_configs': config_layers}}

        intf = self.src_intf
        inst = sniff_packets(intf)

        self.check_packet_transmission(pkt_types)
        time.sleep(1)
        pkts = load_sniff_packets(inst)
        self.host_testpmd.execute_cmd('E-tag set insertion off port-tag-id 1000 port 0 vf 0')

        # load sniff pcap file, check received packet's content
        packetContentFile = "/tmp/packetContent.log"
        pcap_file = "/tmp/sniff_%s.pcap"%intf
        fp=open(packetContentFile,'w')
        backup_out=sys.stdout
        sys.stdout=fp
        pkts=rdpcap(pcap_file)
        pkts.show()
        fp.close()
        sys.stdout=backup_out
        fp=open(packetContentFile,'r')
        out = fp.read()
        fp.close()
        if self.printFlag:# debug output
            print out
        self.verify( "Dot1BR" in out, "tester %s hasn't receiver etag packet"% intf)

    def test_etag_strip(self):
        '''
        When E-tag strip enable on PF
        '''
        host_cmds =[['port config 0 l2-tunnel E-tag enable'],
                    ['set fwd rxonly'],
                    ['set verbose 1'],
                    ['start']]
        guest_cmds = [['set fwd rxonly'],
                      ['set verbose 1'],
                      ['start']]
        config_layers =  {'ether': {'src': self.src_mac},
                          'etag':  {'ECIDbase': 1000}}
        pkt_types_on = {'ETAG_UDP': {'vm':['type=0x0800', 'type=0x893f'],
                                     'layer_configs': config_layers}}
        pkt_types_off = {'ETAG_UDP': {'vm':['type=0x893f', 'type=0x893f'],
                                      'layer_configs': config_layers}}        

        self.preset_test_enviroment()
        self.execute_host_testpmd_cmd(host_cmds)
        self.execute_guest_testpmd_cmd(guest_cmds)
        # Enable E-tag strip on PF, Send 802.1BR packet to VF and check forwarded packet without E-tag
        self.host_testpmd.execute_cmd('E-tag set stripping on port 0')
        self.check_packet_transmission(pkt_types_on)

        # Disable E-tag strip on PF, Send 802.1BR packet and check forwarded packet with E-tag
        self.host_testpmd.execute_cmd('E-tag set stripping off port 0')
        self.check_packet_transmission(pkt_types_off)

    def tear_down(self):
        pass

    def tear_down_all(self):
        if self.setup_vm_env_flag == 1:
            self.destroy_vm_env()

        if getattr(self, 'vm0', None):
            self.vm0.stop()

        for port_id in self.dut_ports:
            self.dut.destroy_sriov_vfs_by_port(port_id)

        self.tester.send_expect("kill -9 $(ps aux | grep -i qemu | grep -v grep  | awk  {'print $2'})", '# ', 5)

