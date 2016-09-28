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

Generic Routing Encapsulation (GRE) is a tunneling protocol developed by 
Cisco Systems that can encapsulate a wide variety of network layer protocols 
inside virtual point-to-point links over an Internet Protocol network.

Fortville support GRE packet detecting, checksum computing and filtering.
"""

import utils
import re
import time
import os

from packet import Packet, sniff_packets, load_sniff_packets, NVGRE, IPPROTO_NVGRE

from scapy.utils import wrpcap, rdpcap
from packet import IncreaseIP
from scapy.packet import split_layers,bind_layers
from scapy.layers.inet import Ether, IP, TCP, UDP
from scapy.layers.sctp import SCTP
from scapy.layers.l2 import GRE

from test_case import TestCase
from exception import VerifyFailure

class TestIpgre(TestCase):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.printFlag = self._enable_debug
        ports = self.dut.get_ports()
        self.verify(self.nic.startswith("fortville"),
                    "GRE tunnel packet type only support by Fortville")
        self.verify(len(ports) >= 1, "Insufficient ports for testing")
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        # start testpmd
        self.dut_port = valports[0]
        tester_port = self.tester.get_local_port(self.dut_port)
        self.tester_iface = self.tester.get_interface(tester_port)
        self.tester_iface_mac =  self.tester.get_mac(tester_port)
        self.initialize_port_config()
        self.re_bind_nvgre_to_gre()

    def initialize_port_config(self):
        self.outer_mac_src = '00:00:10:00:00:00'
        self.outer_mac_dst = '11:22:33:44:55:66'
        self.outer_ip_src = '192.168.1.1'
        self.outer_ip_dst = '192.168.1.2'
        self.inner_ip_src = '192.168.2.1'
        self.inner_ip_dst = '192.168.2.2'

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def check_packet_transmission(self, pkt_types, layer_configs=None):
        time.sleep(1)
        for pkt_type in pkt_types.keys():
            pkt_names = pkt_types[pkt_type]
            pkt = Packet(pkt_type=pkt_type)
            if layer_configs:
                for layer in layer_configs.keys():
                    pkt.config_layer(layer, layer_configs[layer])
            inst = sniff_packets(self.tester_iface, count=1, timeout=8)
            pkt.send_pkt(tx_port=self.tester_iface)
            out = self.dut.get_session_output(timeout=2)
            time.sleep(1)
            load_sniff_packets(inst)
            if self.printFlag: # debug output
                print out
            for pkt_layer_name in pkt_names:
                if self.printFlag:# debug output
                    print pkt_layer_name
                if pkt_layer_name not in out:
                    print utils.RED("Fail to detect %s" % pkt_layer_name)
                    if not self.printFlag:
                        raise VerifyFailure("Failed to detect %s" % pkt_layer_name)
            else:
                print utils.GREEN("Detected %s successfully" % pkt_type)
	        time.sleep(1)

    def save_ref_packet(self, pkt_types, layer_configs=None):
        for pkt_type in pkt_types.keys():
            pkt_names = pkt_types[pkt_type]
            pkt = Packet(pkt_type=pkt_type)
            if layer_configs:
                for layer in layer_configs.keys():
                    pkt.config_layer(layer, layer_configs[layer])
            wrpcap("/tmp/ref_pkt.pcap", pkt.pktgen.pkt)
            time.sleep(1)

    def re_bind_nvgre_to_gre(self):
        split_layers(IP, NVGRE, frag=0, proto=IPPROTO_NVGRE)
        bind_layers(IP, GRE, frag=0, proto=IPPROTO_NVGRE)

    def get_chksums(self, pcap=None):
        """
        get chksum values of Outer and Inner packet L3&L4
        Skip outer udp for it will be calculated by software
        """
        chk_sums = {}
        pkts = rdpcap(pcap)
        for number in range(len(pkts)):
            if pkts[number].guess_payload_class(pkts[number]).name == "gre":
                payload = pkts[number][GRE]
            else:
                payload = pkts[number]
    
            if payload.guess_payload_class(payload).name == "IP":
                chk_sums['outer_ip'] = hex(payload[IP].chksum)

            if pkts[number].haslayer(GRE) == 1:
                inner = pkts[number][GRE]
                if inner.haslayer(IP) == 1:
                    chk_sums['inner_ip'] = hex(inner[IP].chksum)
                    if inner[IP].proto == 6:
                        chk_sums['inner_tcp'] = hex(inner[TCP].chksum)
                    if inner[IP].proto == 17:
                        chk_sums['inner_udp'] = hex(inner[UDP].chksum)
                    if inner[IP].proto == 132:
                        chk_sums['inner_sctp'] = hex(inner[SCTP].chksum)
                break

        return chk_sums

    def compare_checksum(self):
        chksums_ref =  self.get_chksums('/tmp/ref_pkt.pcap')
        chksums =  self.get_chksums('/tmp/sniff_{0}.pcap'.format(self.tester_iface))
        self.logger.info("chksums_ref :: %s"%chksums_ref)
        self.logger.info("chksums :: %s"%chksums)
        # verify saved pcap checksum same to expected checksum
        for key in chksums_ref:
            self.verify(int(chksums[key], 16) == int(chksums_ref[key], 16), "%s not matched to %s" % (key, chksums_ref[key]))
        print utils.GREEN("Checksum is ok")

    def test_GRE_ipv4_packet_detect(self):
        """
        Start testpmd and enable rxonly forwarding mode
        Send packet as table listed and packet type match each layer
        """
        pkt_types = {
            "MAC_IP_GRE_IPv4-TUNNEL_UDP_PKT":        ["Tunnel type: GRENAT", "Inner L4 type: UDP"],
            "MAC_IP_GRE_IPv4-TUNNEL_TCP_PKT":        ["Tunnel type: GRENAT", "Inner L4 type: TCP"],
            "MAC_IP_GRE_IPv4-TUNNEL_SCTP_PKT":       ["Tunnel type: GRENAT", "Inner L4 type: SCTP"],
            "MAC_VLAN_IP_GRE_IPv4-TUNNEL_UDP_PKT":   ["Tunnel type: GRENAT", "Inner L4 type: UDP"],
            "MAC_VLAN_IP_GRE_IPv4-TUNNEL_TCP_PKT":   ["Tunnel type: GRENAT", "Inner L4 type: TCP"],
            "MAC_VLAN_IP_GRE_IPv4-TUNNEL_SCTP_PKT":  ["Tunnel type: GRENAT", "Inner L4 type: SCTP"]
        }
        config_layers =  {'ether': {'src': self.outer_mac_src},
                          'ipv4': {'proto': 'gre'}}
        # Start testpmd and enable rxonly forwarding mode
        testpmd_cmd = "./%s/app/testpmd -c ffff -n 4 -- -i --enable-rx-cksum --enable-rx-cksum" % self.target
        self.dut.send_expect( testpmd_cmd, 
                              "testpmd>", 
                              20)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        self.check_packet_transmission(pkt_types, config_layers)

        self.dut.send_expect("quit", "#")

    def test_GRE_ipv6_packet_detect(self):
        """
        Start testpmd and enable rxonly forwarding mode
        Send packet as table listed and packet type match each layer
        """
        pkt_types_ipv6_ip = {
            "MAC_IPv6_GRE_IPv4-TUNNEL_UDP_PKT":           ["Tunnel type: GRENAT", "Inner L4 type: UDP"],
            "MAC_IPv6_GRE_IPv4-TUNNEL_TCP_PKT":           ["Tunnel type: GRENAT", "Inner L4 type: TCP"],
            "MAC_IPv6_GRE_IPv4-TUNNEL_SCTP_PKT":          ["Tunnel type: GRENAT", "Inner L4 type: SCTP"],
            "MAC_VLAN_IPv6_GRE_IPv4-TUNNEL_UDP_PKT":      ["Tunnel type: GRENAT", "Inner L4 type: UDP", "PKT_RX_VLAN_PKT"],
            "MAC_VLAN_IPv6_GRE_IPv4-TUNNEL_TCP_PKT":      ["Tunnel type: GRENAT", "Inner L4 type: TCP", "PKT_RX_VLAN_PKT"],
            "MAC_VLAN_IPv6_GRE_IPv4-TUNNEL_SCTP_PKT":     ["Tunnel type: GRENAT", "Inner L4 type: SCTP", "PKT_RX_VLAN_PKT"]
        }

        pkt_types_ipv6_ipv6 = {
            "MAC_IPv6_GRE_IPv6-TUNNEL_UDP_PKT":         ["Tunnel type: GRENAT", "Inner L4 type: UDP"],
            "MAC_IPv6_GRE_IPv6-TUNNEL_TCP_PKT":         ["Tunnel type: GRENAT", "Inner L4 type: TCP"],
            "MAC_VLAN_IPv6_GRE_IPv6-TUNNEL_UDP_PKT":    ["Tunnel type: GRENAT", "Inner L4 type: UDP", "PKT_RX_VLAN_PKT"],
            "MAC_VLAN_IPv6_GRE_IPv6-TUNNEL_TCP_PKT":    ["Tunnel type: GRENAT", "Inner L4 type: TCP", "PKT_RX_VLAN_PKT"]
        }

        pkt_types_ipv6_ipv6_SCTP = {
            "MAC_IPv6_GRE_IPv6-TUNNEL_SCTP_PKT":        ["Tunnel type: GRENAT", "Inner L4 type: SCTP"],
            "MAC_VLAN_IPv6_GRE_IPv6-TUNNEL_SCTP_PKT":   ["Tunnel type: GRENAT", "Inner L4 type: SCTP", "PKT_RX_VLAN_PKT"]
        }
        
        # Start testpmd and enable rxonly forwarding mode
        testpmd_cmd = "./%s/app/testpmd -c ffff -n 4 -- -i --enable-rx-cksum" % self.target
        self.dut.send_expect(testpmd_cmd, "testpmd>", 20)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        # inner ipv4
        config_layers =  {'ether': {'src': self.outer_mac_src},
                          'ipv6': {'nh': 47},
                          'raw':  {'payload':['78']*40}}
        self.check_packet_transmission(pkt_types_ipv6_ip, config_layers)

        # inner ipv6
        config_layers =  {'ether': {'src': self.outer_mac_src},
                          'ipv6': {'nh': 47},
                          'gre':  {'proto': 0x86dd},
                          'raw':  {'payload':['78']*40}}
        self.check_packet_transmission(pkt_types_ipv6_ipv6, config_layers)

        # inner ipv6 SCTP
        config_layers =  {'ether': {'src': self.outer_mac_src},
                          'ipv6': {'nh': 47},
                          'gre':  {'proto': 0x86dd},
                          'inner_ipv6': {'nh': 132}, 
                          'raw':  {'payload':['78']*40}}
        self.check_packet_transmission(pkt_types_ipv6_ipv6_SCTP, config_layers)
        self.dut.send_expect("quit", "#")

    def test_GRE_packet_filter(self):
        """
        Start testpmd with multi queues, add GRE filter that forward 
        inner/outer ip address 0.0.0.0 to queue 3, Send packet inner 
        ip address matched and check packet recevied by queue 3
        """
        outer_mac = self.tester_iface_mac
        inner_mac = "10:00:00:00:00:00"
        
        # Start testpmd with multi queues
        #testpmd_cmd = "./%s/app/testpmd -c ff -n 3 -- -i  --rxq=4 --txq=4 --txqflags=0x0" % self.target
        testpmd_cmd = "./%s/app/testpmd -c ff -n 3 -- -i --enable-rx-cksum  --rxq=4 --txq=4" % self.target
        self.dut.send_expect(testpmd_cmd, "testpmd>", 20)
        self.dut.send_expect("set fwd rxonly", "testpmd>")
        self.dut.send_expect("set nbcore 4", "testpmd>")
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        # Add GRE filter that forward inner ip address 0.0.0.0 to queue 3
        cmd = "tunnel_filter add 0 %s %s 0.0.0.0 1 ipingre iip 0 3"%(outer_mac, inner_mac)
        self.dut.send_expect( cmd, "testpmd>")
        
        # Send packet inner ip address matched and check packet recevied by queue 3
        pkt_types = {"MAC_IP_GRE_IPv4-TUNNEL_UDP_PKT":  ["Tunnel type: GRENAT",  "Inner L4 type: UDP"]}
        config_layers = {'ether': {'src': self.outer_mac_src},
                         'ipv4': {'dst': "0.0.0.0", 'proto': 'gre'}}
        self.check_packet_transmission(pkt_types, config_layers)

        # Remove tunnel filter and check same packet recevied by queue 0
        cmd = "tunnel_filter rm 0 %s %s 0.0.0.0 1 ipingre iip 0 3"%(outer_mac, inner_mac)
        self.dut.send_expect( cmd, "testpmd>")
        
        # Add GRE filter that forward outer ip address 0.0.0.0 to queue 3
        cmd = "tunnel_filter add 0 %s %s 0.0.0.0 1 ipingre oip 0 3"%(outer_mac, inner_mac)
        self.dut.send_expect( cmd, "testpmd>")

        # Send packet outer ip address matched and check packet recevied by queue 3.
        pkt_types = {"MAC_IP_GRE_IPv4-TUNNEL_UDP_PKT": ["Tunnel type: GRENAT", "Inner L4 type: UDP"]}
        config_layers = {'ether': {'src': self.outer_mac_src},
                         'ipv4': {'dst': "0.0.0.0", 'proto': 'gre'}}
        self.check_packet_transmission(pkt_types, config_layers)

        # Add GRE filter that forward outer ip address 0.0.0.0 to queue 3
        cmd = "tunnel_filter rm 0 %s %s 0.0.0.0 1 ipingre iip 0 3"%(outer_mac, inner_mac)
        self.dut.send_expect( cmd, "testpmd>")
        time.sleep(2)
        self.dut.send_expect("quit", "#")

    def test_GRE_packet_chksum_offload(self):
        """
        Start testpmd with hardware checksum offload enabled,
        Send packet with wrong IP/TCP/UDP/SCTP checksum and check forwarded packet checksum 
        """
        # Start testpmd and enable rxonly forwarding mode
        testpmd_cmd = "./%s/app/testpmd -c ff -n 3 -- -i --enable-rx-cksum --txqflags=0x0 --port-topology=loop" % self.target
        self.dut.send_expect(testpmd_cmd, "testpmd>", 20)
        self.dut.send_expect("set verbose 1", "testpmd>")
        self.dut.send_expect("set fwd csum", "testpmd>")
        self.dut.send_expect("csum set ip hw 0", "testpmd>")
        self.dut.send_expect("csum set udp hw 0", "testpmd>")
        self.dut.send_expect("csum set sctp hw 0", "testpmd>")
        self.dut.send_expect("csum set outer-ip hw 0", "testpmd>")
        self.dut.send_expect("csum set tcp hw 0", "testpmd>")
        self.dut.send_expect("csum parse_tunnel on 0", "testpmd>")
        self.dut.send_expect("start", "testpmd>")

        # Send packet with wrong outer IP checksum and check forwarded packet IP checksum is correct
        pkt_types = { "MAC_IP_GRE_IPv4-TUNNEL_TCP_PKT": ["PKT_TX_IP_CKSUM"]}
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': IncreaseIP(self.outer_ip_src),
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':IncreaseIP(self.inner_ip_src),
                                       'dst':self.inner_ip_dst}}
        self.save_ref_packet(pkt_types, config_layers)
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': self.outer_ip_src,
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':self.inner_ip_src,
                                       'dst':self.inner_ip_dst,
                                        'chksum': 0x0}}
        self.check_packet_transmission(pkt_types, config_layers)
        self.compare_checksum()

        # Send packet with wrong inner IP checksum and check forwarded packet IP checksum is correct
        pkt_types = { "MAC_IP_GRE_IPv4-TUNNEL_TCP_PKT": ["PKT_TX_IP_CKSUM"]}
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': IncreaseIP(self.outer_ip_src),
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':IncreaseIP(self.inner_ip_src),
                                       'dst':self.inner_ip_dst}}
        self.save_ref_packet(pkt_types, config_layers)
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': self.outer_ip_src,
                                  'dst': self.outer_ip_dst,
                                  'chksum': 0x0},
                         'inner_ipv4':{'src':self.inner_ip_src,
                                       'dst':self.inner_ip_dst}}
        self.check_packet_transmission(pkt_types, config_layers)
        self.compare_checksum()
        
        # Send packet with wrong inner TCP checksum and check forwarded packet TCP checksum is correct
        pkt_types = { "MAC_IP_GRE_IPv4-TUNNEL_TCP_PKT": ["PKT_TX_TCP_CKSUM"]}
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': IncreaseIP(self.outer_ip_src),
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':IncreaseIP(self.inner_ip_src),
                                       'dst':self.inner_ip_dst},
                         'tcp': {'src': 53, 
                                  'dst': 53}}
        self.save_ref_packet(pkt_types, config_layers)
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': self.outer_ip_src,
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':self.inner_ip_src,
                                       'dst':self.inner_ip_dst},
                         'tcp': {'chksum': 0x0}}
        self.check_packet_transmission(pkt_types, config_layers)
        self.compare_checksum()

        # Send packet with wrong inner UDP checksum and check forwarded packet UDP checksum is correct
        pkt_types = { "MAC_IP_GRE_IPv4-TUNNEL_UDP_PKT": ["PKT_TX_UDP_CKSUM"]}
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': IncreaseIP(self.outer_ip_src),
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':IncreaseIP(self.inner_ip_src),
                                       'dst':self.inner_ip_dst}}
        self.save_ref_packet(pkt_types, config_layers)
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': self.outer_ip_src,
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':self.inner_ip_src,
                                       'dst':self.inner_ip_dst},
                         'udp': {'chksum': 0xffff}}
        self.check_packet_transmission(pkt_types, config_layers)
        self.compare_checksum()
    
        # Send packet with wrong inner SCTP checksum and check forwarded packet SCTP checksum is correct
        pkt_types = { "MAC_IP_GRE_IPv4-TUNNEL_SCTP_PKT": ["PKT_TX_SCTP_CKSUM"]}
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': IncreaseIP(self.outer_ip_src),
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':IncreaseIP(self.inner_ip_src),
                                       'dst':self.inner_ip_dst},
                         'sctp': {'src': 53,
                                  'dst': 53}}
        self.save_ref_packet(pkt_types, config_layers)
        config_layers = {'ether': {'src': self.outer_mac_src, 
                                   'dst': self.outer_mac_dst},
                         'ipv4': {'proto': 'gre',
                                  'src': self.outer_ip_src,
                                  'dst': self.outer_ip_dst},
                         'inner_ipv4':{'src':self.inner_ip_src,
                                       'dst':self.inner_ip_dst},
                         'sctp': {'chksum': 0x0}}
        self.check_packet_transmission(pkt_types, config_layers)
        self.compare_checksum()

        self.dut.send_expect("quit", "#")

    def tear_down(self):
        """
        Run after each test case.
        Nothing to do.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        Nothing to do.
        """
        self.dut.kill_all()
        pass
