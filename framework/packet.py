#!/usr/bin/python
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
Generic packet create, transmit and analyze module
Base on scapy(python program for packet manipulation)
"""

import os
import time
import signal
import sys
import re
import signal
import random
import subprocess
from uuid import uuid4
from settings import FOLDERS

from scapy.config import conf
conf.use_pcap = True

from scapy.all import conf
from scapy.utils import struct, socket, wrpcap, rdpcap
from scapy.layers.inet import Ether, IP, TCP, UDP, ICMP
from scapy.layers.inet6 import IPv6, IPv6ExtHdrRouting, IPv6ExtHdrFragment
from scapy.layers.l2 import Dot1Q, ARP, GRE
from scapy.layers.sctp import SCTP, SCTPChunkData
from scapy.sendrecv import sniff
from scapy.route import *
from scapy.packet import bind_layers, Raw
from scapy.sendrecv import sendp


sys.path.append(FOLDERS['Depends'])
# load extension layers
from vxlan import Vxlan
bind_layers(UDP, Vxlan, dport=4789)
bind_layers(Vxlan, Ether)
from nvgre import NVGRE, IPPROTO_NVGRE
bind_layers(IP, NVGRE, proto=IPPROTO_NVGRE)
bind_layers(NVGRE, Ether)
from lldp import LLDP, LLDPManagementAddress
bind_layers(Ether, LLDP, type=0x88cc)

# packet generator type should be configured later
PACKETGEN = "scapy"

LayersTypes = {
    "L2": ['ether', 'dot1q', '1588', 'arp', 'lldp'],
    # ipv4_ext_unknown, ipv6_ext_unknown
    "L3": ['ipv4','ipv4ihl', 'ipv6', 'ipv4_ext', 'ipv6_ext','ipv6_ext2', 'ipv6_frag'],
    "L4": ['tcp', 'udp', 'frag', 'sctp', 'icmp', 'nofrag'],
    "TUNNEL": ['ip', 'gre', 'vxlan', 'nvgre', 'geneve', 'grenat'],
    "INNER L2": ['inner_mac', 'inner_mac&vlan'],
    # inner_ipv4_unknown, inner_ipv6_unknown
    "INNER L3": ['inner_ipv4', 'inner_ipv4_ext', 'inner_ipv6', 'inner_ipv6_ext'],
    "INNER L4": ['inner_tcp', 'inner_udp', 'inner_frag', 'inner_sctp', 'inner_icmp', 'inner_nofrag'],
    "PAYLOAD": ['raw']
}

# Saved back groud sniff process id
SNIFF_PIDS = {}

# Saved packet generator process id
# used in pktgen or tgen
PKTGEN_PIDS = {}


class scapy(object):
    SCAPY_LAYERS = {
        'ether': Ether(dst="ff:ff:ff:ff:ff:ff"),
        'dot1q': Dot1Q(),
        '1588': Ether(type=0x88f7),
        'arp': ARP(),
        'ipv4': IP(),
        'ipv4ihl': IP(ihl=10),
        'ipv4_ext': IP(frag=5),
        'ipv6': IPv6(src="::1"),
        'ipv6_ext': IPv6(src="::1", nh=43)/IPv6ExtHdrRouting(),
        'ipv6_ext2': IPv6()/IPv6ExtHdrRouting(),
        'udp': UDP(),
        'tcp': TCP(),
        'sctp': SCTP(),
        'icmp': ICMP(),
        'gre': GRE(),
        'raw': Raw(),
        'vxlan': Vxlan(),

        'inner_mac': Ether(),
        'inner_mac&vlan': Ether() / Dot1Q(),
        'inner_ipv4': IP(),
        'inner_ipv4_ext': IP(),
        'inner_ipv6': IPv6(src="::1"),
        'inner_ipv6_ext': IPv6(src="::1"),

        'inner_tcp': TCP(),
        'inner_udp': UDP(),
        'inner_sctp': SCTP(),
        'inner_icmp': ICMP(),

        'lldp': LLDP()/LLDPManagementAddress(),
        'ip_frag': IP(frag=5),
        'ipv6_frag': IPv6(src="::1")/IPv6ExtHdrFragment(),
        'ip_in_ip': IP()/IP(),
        'ip_in_ip_frag': IP()/IP(frag=5),
        'ipv6_in_ip': IP()/IPv6(src="::1"),
        'ipv6_frag_in_ip': IP()/IPv6(src="::1", nh=44)/IPv6ExtHdrFragment(),
        'nvgre': NVGRE(),
        'geneve': "Not Implement",
    }

    def __init__(self):
        self.pkt = None
        pass

    def assign_pkt(self, pkt):
        self.pkt = pkt

    def add_layers(self, layers):
        self.pkt = None
        for layer in layers:
            if self.pkt is not None:
                self.pkt = self.pkt / self.SCAPY_LAYERS[layer]
            else:
                self.pkt = self.SCAPY_LAYERS[layer]

    def ether(self, dst="ff:ff:ff:ff:ff:ff", src="00:00:20:00:00:00", type=None):
        self.pkt[Ether].dst = dst
        self.pkt[Ether].src = src
        if type is not None:
            self.pkt[Ether].type = type

    def dot1q(self, vlan, prio=0, type=None):
        self.pkt[Dot1Q].vlan = int(vlan)
        self.pkt[Dot1Q].prio = prio
        if type is not None:
            self.pkt[Dot1Q].type = type

    def strip_dot1q(self, element):
        value = None

        if self.pkt.haslayer('Dot1Q') is 0:
            return None

        if element == 'vlan':
            value = int(str(self.pkt[Dot1Q].vlan))
        return value

    def ipv4(self, frag=0, src="127.0.0.1", proto=None, tos=0, dst="127.0.0.1", chksum=None, len=None, version=4, flags=None, ihl=None, ttl=64, id=1, options=None):
        self.pkt[IP].frag = frag
        self.pkt[IP].src = src
        if proto is not None:
            self.pkt[IP].proto = proto
        self.pkt[IP].tos = tos
        self.pkt[IP].dst = dst
        if chksum is not None:
            self.pkt[IP].chksum = chksum
        if len is not None:
            self.pkt[IP].len = len
        self.pkt[IP].version = version
        if flags is not None:
            self.pkt[IP].flags = flags
        if ihl is not None:
            self.pkt[IP].ihl = ihl
        self.pkt[IP].ttl = ttl
        self.pkt[IP].id = id
        if options is not None:
            self.pkt[IP].options = options

    def ipv6(self, version=6, tc=0, fl=0, plen=0, nh=0, hlim=64, src="::1", dst="::1"):
        """
        Configure IPv6 protocal.
        """
        self.pkt[IPv6].version = version
        self.pkt[IPv6].tc = tc
        self.pkt[IPv6].fl = fl
        if plen:
            self.pkt[IPv6].plen = plen
        if nh:
            self.pkt[IPv6].nh = nh
        self.pkt[IPv6].src = src
        self.pkt[IPv6].dst = dst

    def inner_ipv6(self, version=6, tc=0, fl=0, plen=0, nh=0, hlim=64, src="::1", dst="::1"):
        """
        Configure IPv6 protocal.
        """
        self.pkt[IPv6][Ether][IPv6].version = version
        self.pkt[IPv6][Ether][IPv6].tc = tc
        self.pkt[IPv6][Ether][IPv6].fl = fl
        if plen:
            self.pkt[IPv6][Ether][IPv6].plen = plen
        if nh:
            self.pkt[IPv6][Ether][IPv6].nh = nh
        self.pkt[IPv6][Ether][IPv6].src = src
        self.pkt[IPv6][Ether][IPv6].dst = dst

    def udp(self, src=53, dst=53, len=None, chksum=None):
        self.pkt[UDP].sport = src
        self.pkt[UDP].dport = dst
        if len is not None:
            self.pkt[UDP].len = len
        if chksum is not None:
            self.pkt[UDP].chksum = chksum

    def raw(self, payload=None):
        if payload is not None:
            self.pkt[Raw].load = ''
            for load in payload:
                self.pkt[Raw].load += '%c' % int(load, 16)

    def vxlan(self, vni=0):
        self.pkt[Vxlan].vni = vni

    def read_pcap(self, file):
        pcap_pkts = []
        try:
            pcap_pkts = rdpcap(file)
        except:
            pass

        return pcap_pkts

    def write_pcap(self, file):
        try:
            wrpcap(file, self.pkt)
        except:
            pass

    def send_pcap_pkt(self, crb=None, file='', intf=''):
        if intf == '' or file == '' or crb is None:
            print "Invalid option for send packet by scapy"
            return

        content = 'pkts=rdpcap(\"%s\");sendp(pkts, iface=\"%s\");exit()' % (file, intf)
        cmd_file = '/tmp/scapy_%s.cmd' % intf

        crb.create_file(content, cmd_file)
        crb.send_expect("scapy -c scapy_%s.cmd &" % intf, "# ")

    def print_summary(self):
        print "Send out pkt %s" % self.pkt.summary()

    def send_pkt(self, intf=''):
        self.print_summary()
        if intf != '':
            sendp(self.pkt, iface=intf)


class Packet(object):
    """
    Module for config/create packet
    Based on scapy module
    Usage: assign_layers([layers list])
           config_layer('layername', {layer config})
           ...
    """
    def_packet = {
        'TIMESYNC': {'layers': ['ether', 'raw'], 'cfgload': False},
        'ARP': {'layers': ['ether', 'arp'], 'cfgload': False},
        'LLDP': {'layers': ['ether', 'lldp'], 'cfgload': False},
        'TCP': {'layers': ['ether', 'ipv4', 'tcp', 'raw'], 'cfgload': True},
        'UDP': {'layers': ['ether', 'ipv4', 'udp', 'raw'], 'cfgload': True},
        'SCTP': {'layers': ['ether', 'ipv4', 'sctp', 'raw'], 'cfgload': True},
        'IPv6_TCP': {'layers': ['ether', 'ipv6', 'tcp', 'raw'], 'cfgload': True},
        'IPv6_UDP': {'layers': ['ether', 'ipv6', 'udp', 'raw'], 'cfgload': True},
        'IPv6_SCTP': {'layers': ['ether', 'ipv6', 'sctp', 'raw'], 'cfgload': True},
    }

    def __init__(self, **options):
        """
        pkt_type: description of packet type
                  defined in def_packet
        options: special option for Packet module
                 pkt_len: length of network packet
                 ran_payload: whether payload of packet is random
                 pkt_file:
                 pkt_gen: packet generator type
                          now only support scapy
        """
        self.pkt_layers = []
        self.pkt_len = 64
        self.pkt_opts = options

        self.pkt_type = "UDP"

        if 'pkt_type' in self.pkt_opts.keys():
            self.pkt_type = self.pkt_opts['pkt_type']

        if self.pkt_type in self.def_packet.keys():
            self.pkt_layers = self.def_packet[self.pkt_type]['layers']
            self.pkt_cfgload = self.def_packet[self.pkt_type]['cfgload']
            if "IPv6" in self.pkt_type:
                self.pkt_len = 128
        else:
            self._load_pkt_layers()
            
        if 'pkt_len' in self.pkt_opts.keys():
            self.pkt_len = self.pkt_opts['pkt_len']

        if 'pkt_file' in self.pkt_opts.keys():
            self.uni_name = self.pkt_opts['pkt_file']
        else:
            self.uni_name = '/tmp/' + str(uuid4()) + '.pcap'

        if 'pkt_gen' in self.pkt_opts.keys():
            if self.pkt_opts['pkt_gen'] == 'scapy':
                self.pktgen = scapy()
            else:
                print "Not support other pktgen yet!!!"
        else:
            self.pktgen = scapy()

    def send_pkt(self, crb=None, tx_port='', auto_cfg=True):
        if tx_port == '':
            print "Invalid Tx interface"
            return

        self.tx_port = tx_port

        # assign layer
        self.assign_layers()

        # config special layer
        if auto_cfg is True:
            self.config_def_layers()

        # handle packet options
        payload_len = self.pkt_len - len(self.pktgen.pkt) - 4

        # if raw data has not been configured and payload should configured
        if hasattr(self, 'configured_layer_raw') is False and self.pkt_cfgload is True:
            payload = []
            raw_confs = {}
            if 'ran_payload' in self.pkt_opts.keys():
                for loop in range(payload_len):
                    payload.append("%02x" % random.randrange(0, 255))
            else:
                for loop in range(payload_len):
                    payload.append('58')  # 'X'

            raw_confs['payload'] = payload
            self._config_layer_raw(raw_confs)

        # check with port type
        if 'ixia' in self.tx_port:
            print "Not Support Yet"

        if crb is not None:
            self.pktgen.write_pcap(self.uni_name)
            crb.session.copy_file_to(self.uni_name)
            pcap_file = self.uni_name.split('/')[2]
            self.pktgen.send_pcap_pkt(crb=crb, file=pcap_file, intf=self.tx_port)
        else:
            self.pktgen.send_pkt(intf=self.tx_port)

    def check_layer_config(self, layer, config):
        """
        check the format of layer configuration
        every layer should has different check function
        """
        pass

    def assign_layers(self, layers=None):
        """
        assign layer for this packet
        maybe need add check layer function
        """
        if layers is not None:
            self.pkt_layers = layers

        for layer in self.pkt_layers:
            found = False
            l_type = layer.lower()

            for types in LayersTypes.values():
                if l_type in types:
                    found = True
                    break

            if found is False:
                self.pkt_layers.remove(l_type)
                print "INVAILD LAYER TYPE [%s]" % l_type.upper()

        self.pktgen.add_layers(self.pkt_layers)

    def _load_pkt_layers(self):
        name2type = {
            'MAC': 'ether',
            'VLAN': 'dot1q',
            'IP': 'ipv4',
            'IPihl': 'ipv4ihl',
            'IPFRAG': 'ipv4_ext',
            'IPv6': 'ipv6',
            'IPv6FRAG': 'ipv6_frag',
            'IPv6EXT': 'ipv6_ext',
            'IPv6EXT2': 'ipv6_ext2',
            'TCP': 'tcp',
            'UDP': 'udp',
            'SCTP': 'sctp',
            'ICMP': 'icmp',
            'NVGRE': 'nvgre',
            'GRE': 'gre',
            'VXLAN': 'vxlan',
            'PKT': 'raw',
        }

        layers = self.pkt_type.split('_')
        self.pkt_layers = []
        self.pkt_cfgload = True
        for layer in layers:
            if layer in name2type.keys():
                self.pkt_layers.append(name2type[layer])
        
    def config_def_layers(self):
        """
        Handel config packet layers by default
        """
        if self.pkt_type == "TIMESYNC":
            self.config_layer('ether', {'dst': 'FF:FF:FF:FF:FF:FF',
                                        'type': 0x88f7})
            self.config_layer('raw', {'payload': ['00', '02']})

        if self.pkt_type == "ARP":
            self.config_layer('ether', {'dst': 'FF:FF:FF:FF:FF:FF'})

        if self.pkt_type == "IPv6_SCTP":
            self.config_layer('ipv6', {'nh': 132})

        if "IPv6_NVGRE" in self.pkt_type:
            self.config_layer('ipv6', {'nh': 47})
            if "IPv6_SCTP" in self.pkt_type:
                self.config_layer('inner_ipv6', {'nh': 132})
            if "IPv6_ICMP" in self.pkt_type:
                self.config_layer('inner_ipv6', {'nh': 58})
            if "IPFRAG" in self.pkt_type:
                self.config_layer('raw', {'payload': ['00'] * 40})
            else:
                self.config_layer('raw', {'payload': ['00'] * 18})

        if "MAC_IP_IPv6" in self.pkt_type or\
           "MAC_IP_NVGRE" in self.pkt_type or \
           "MAC_IP_UDP_VXLAN" in self.pkt_type:
            if "IPv6_SCTP" in self.pkt_type:
                self.config_layer('ipv6', {'nh': 132})
            if "IPv6_ICMP" in self.pkt_type:
                self.config_layer('ipv6', {'nh': 58})
            if "IPFRAG" in self.pkt_type:
                self.config_layer('raw', {'payload': ['00'] * 40})
            else:
                self.config_layer('raw', {'payload': ['00'] * 18})
        
    def config_layer(self, layer, config={}):
        """
        Configure packet assgined layer
        return the status of configure result
        """
        try:
            # if inner in layer mean same layer in outer
            if 'inner' in layer:
                dup_layer = layer[6:]
                if self.pkt_layers.count(dup_layer) != 2:
                    raise
            else:
                idx = self.pkt_layers.index(layer)
        except Exception as e:
            print "INVALID LAYER ID %s" % layer
            return -1

        if self.check_layer_config(layer, config) is False:
            return -1

        layer_conf = getattr(self, "_config_layer_%s" % layer)
        setattr(self, 'configured_layer_%s' % layer, True)

        return layer_conf(config)

    def _config_layer_ether(self, config):
        return self.pktgen.ether(**config)

    def _config_layer_dot1q(self, config):
        return self.pktgen.dot1q(**config)

    def _config_layer_ipv4(self, config):
        return self.pktgen.ipv4(**config)

    def _config_layer_ipv6(self, config):
        return self.pktgen.ipv6(**config)

    def _config_layer_inner_ipv6(self, config):
        return self.pktgen.inner_ipv6(**config)

    def _config_layer_udp(self, config):
        return self.pktgen.udp(**config)

    def _config_layer_raw(self, config):
        return self.pktgen.raw(**config)

    def _config_layer_vxlan(self, config):
        return self.pktgen.vxlan(**config)

    def strip_layer_element(self, layer, element):
        """
        Strip packet layer elements
        return the status of configure result
        """
        strip_element = getattr(self, "strip_element_%s" % layer)

        return strip_element(element)

    def strip_element_dot1q(self, element):
        return self.pktgen.strip_dot1q(element)


def increment_ip_address(self, addr):
    """
    Returns the IP address from a given one, like
    192.168.1.1 ->192.168.1.2
    If disable ip hw chksum, csum routine will increase ip
    """
    ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
    x = ip2int(addr)
    int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
    return int2ip(x + 1)


def increment_ipv6_address(self, addr):
    """
    Returns the IP address from a given one, like
    FE80:0:0:0:0:0:0:0 -> FE80::1
    csum routine will increase ip
    """
    ipv6addr = struct.unpack('!8H', socket.inet_pton(AF_INET6, addr))
    addr = list(ipv6addr)
    addr[7] += 1
    ipv6 = socket.inet_ntop(AF_INET6, struct.pack(
        '!8H', addr[0], addr[1], addr[2], addr[3], addr[4], addr[5], addr[6], addr[7]))
    return ipv6


def sniff_packets(intf, count=0, timeout=5):
    """
    sniff all packets for certain port in certain seconds
    """
    sniff_cmd = 'tcpdump -i %(INTF)s -w %(FILE)s'
    options = {'INTF': intf, 'COUNT': count,
               'FILE': '/tmp/sniff_%s.pcap' % intf}
    if count:
        sniff_cmd += ' -c %(COUNT)d'
        cmd = sniff_cmd % options
    else:
        cmd = sniff_cmd % options

    args = cmd.split()
    pipe = subprocess.Popen(args)
    index = str(time.time())
    SNIFF_PIDS[index] = (pipe, intf, timeout)
    return index


def load_sniff_packets(index=''):
    pkts = []
    child_exit = False
    if index in SNIFF_PIDS.keys():
        pipe, intf, timeout = SNIFF_PIDS[index]
        time_elapse = int(time.time() - float(index))
        while time_elapse < timeout:
            if pipe.poll() is not None:
                child_exit = True
                break

            time.sleep(1)
            time_elapse += 1

        if not child_exit:
            pipe.kill()

        # wait pcap file ready
        time.sleep(0.5)
        try:
            cap_pkts = rdpcap("/tmp/sniff_%s.pcap" % intf)
            for pkt in cap_pkts:
                # packet gen should be scapy
                packet = Packet(tx_port=intf)
                packet.pktgen.assign_pkt(pkt)
                pkts.append(packet)
        except:
            pass

    return pkts

############################################################################################################
############################################################################################################
if __name__ == "__main__":
    inst = sniff_packets("lo", timeout=5)
    time.sleep(3)
    pkts = load_sniff_packets(inst)

    pkt = Packet(pkt_type='UDP', pkt_len=1500, ran_payload=True)
    pkt.send_pkt(tx_port='lo')
    pkt = Packet(pkt_type='IPv6_TCP')
    pkt.send_pkt(tx_port='lo')
    pkt = Packet(pkt_type='IPv6_SCTP')
    pkt.send_pkt(tx_port='lo')

    pkt = Packet()
    pkt.assign_layers(['ether', 'dot1q', 'ipv4', 'udp', 'vxlan', 'inner_mac', 'inner_ipv4', 'inner_udp', 'raw'])
    pkt.config_layer('ether', {'dst': '00:11:22:33:44:55'})
    pkt.config_layer('dot1q', {'vlan': 2})
    pkt.config_layer('ipv4', {'dst': '1.1.1.1'})
    pkt.config_layer('udp', {'src': 4789, 'dst': 4789, 'chksum': 0x1111})
    pkt.config_layer('vxlan', {'vni': 2})
    pkt.config_layer('raw', {'payload': ['58']*18})
