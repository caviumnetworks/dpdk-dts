"""
DPDK Test suite.

Test NVGRE features in DPDK.

"""

import utils
import string
import re
import time
import os
from pmd_output import PmdOutput
from packet import IncreaseIP, IncreaseIPv6

from socket import AF_INET6
from scapy.utils import struct, socket, wrpcap, rdpcap
from scapy.layers.inet import Ether, IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Dot1Q
from scapy.layers.sctp import SCTP, SCTPChunkData
from nvgre import NVGRE
from scapy.sendrecv import sniff
from scapy.config import conf
from scapy.route import *

from test_case import TestCase
from settings import HEADER_SIZE

#
#
# Test class.
#


class NvgreTestConfig(object):

    """
    Module for config/create/transmit Nvgre packet
    """

    def __init__(self, test_case, **kwargs):
        self.test_case = test_case
        self.init()
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def init(self):
        self.packets_config()

    def packets_config(self):
        """
        Default nvgre packet format
        """
        self.pcap_file = '/root/nvgre.pcap'
        self.capture_file = '/root/capture.pcap'

        """
        outer info

        Outer Ethernet Header:             |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                (Outer) Destination MAC Address                |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |(Outer)Destination MAC Address |  (Outer)Source MAC Address    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                  (Outer) Source MAC Address                   |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |Optional Ethertype=C-Tag 802.1Q| Outer VLAN Tag Information    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |       Ethertype 0x0800        |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        Outer IPv4 Header:
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |Version|  IHL  |Type of Service|          Total Length         |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |         Identification        |Flags|      Fragment Offset    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |  Time to Live | Protocol 0x2F |         Header Checksum       |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                      (Outer) Source Address                   |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                  (Outer) Destination Address                  |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        """
        self.outer_mac_src = '00:00:10:00:00:00'
        self.outer_mac_dst = '11:22:33:44:55:66'
        self.outer_vlan = 'N/A'

        self.outer_ip_proto = 47
        self.outer_l3_type = "IPv4"
        self.outer_ip_src = '192.168.1.1'
        self.outer_ip_dst = '192.168.1.2'
        self.outer_ip_invalid = 0

        self.outer_ip6_src = 'N/A'
        self.outer_ip6_dst = 'N/A'
        self.outer_ip6_invalid = 0
        """
        gre info
        GRE Header:
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |0| |1|0| Reserved0       | Ver |   Protocol Type 0x6558        |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                        Tenant Network ID (TNI)|   Reserved    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        """
        self.tni = 1
        self.proto = 0x6558

        """
        inner info
        Inner Ethernet Header
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                (Inner) Destination MAC Address                |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |(Inner)Destination MAC Address |  (Inner)Source MAC Address    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                  (Inner) Source MAC Address                   |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |Optional Ethertype=C-Tag 802.1Q| PCP |0| VID set to 0          |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |       Ethertype 0x0800        |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        Inner IPv4 Header:
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |Version|  IHL  |Type of Service|          Total Length         |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |         Identification        |Flags|      Fragment Offset    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |  Time to Live |    Protocol   |         Header Checksum       |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                       Source Address                          |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                    Destination Address                        |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                    Options                    |    Padding    |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                      Original IP Payload                      |
        |                                                               |
        |                                                               |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        """
        self.inner_mac_src = '90:e2:ba:4a:34:88'
        self.inner_mac_dst = '90:e2:ba:4a:34:89'
        self.inner_vlan = 'N/A'

        self.inner_l3_type = "IPv4"
        self.inner_ip_src = '192.168.2.1'
        self.inner_ip_dst = '192.168.2.2'
        self.inner_ip_invalid = 0

        self.inner_ip6_src = 'N/A'
        self.inner_ip6_dst = 'N/A'
        self.inner_ip6_invalid = 0

        self.inner_l4_type = 'UDP'
        self.inner_l4_invalid = 0
        self.payload_size = 18

    def packet_type(self):
        """
        Return nvgre packet type
        """
        if self.outer_ip_proto != 47:
            if self.outer_l3_type == 'IPv4':
                return 'L3_IPV4_EXT_UNKNOWN'
            else:
                return 'L3_IPV6_EXT_UNKNOWN'
        else:
            if self.inner_l3_type == 'IPv4':
                return 'L3_IPV4_EXT_UNKNOWN'
            else:
                return 'L3_IPV6_EXT_UNKNOWN'

    def create_pcap(self):
        """
        Create pcap file in config.pcap_file
        Return scapy packet object for later usage
        """

        """
        inner package = L2/[Vlan]/L3/L4/Payload
        """
        if self.inner_l4_type == 'SCTP':
            self.inner_payload = SCTPChunkData(data='X' * 16)
        else:
            self.inner_payload = ("X" * self.payload_size)

        if self.inner_l4_type == 'TCP':
            inner_l4 = TCP()
        elif self.inner_l4_type == 'UDP':
            inner_l4 = UDP()
        elif self.inner_l4_type == 'SCTP':
            inner_l4 = SCTP()

        if self.inner_l3_type == 'IPv4':
            inner_l3 = IP()
        else:
            inner_l3 = IPv6()

        if self.inner_vlan != 'N/A':
            inner = Ether() / Dot1Q() / inner_l3 / inner_l4 / self.inner_payload
            inner[Dot1Q].vlan = self.inner_vlan
        else:
            if self.inner_l4_type == "None":
                inner = Ether() / inner_l3 / self.inner_payload
            else:
                inner = Ether() / inner_l3 / inner_l4 / self.inner_payload

        inner[Ether].src = self.inner_mac_src
        inner[Ether].dst = self.inner_mac_dst

        if self.inner_l3_type == 'IPv4':
            inner[inner_l3.name].src = self.inner_ip_src
            inner[inner_l3.name].dst = self.inner_ip_dst
        else:
            inner[inner_l3.name].src = self.inner_ip6_src
            inner[inner_l3.name].dst = self.inner_ip6_dst

        if self.inner_l4_type == "UDP" or self.inner_l4_type == "TCP":
            inner[inner_l4.name].dport = 1021
            inner[inner_l4.name].sport = 1021

        if self.inner_l3_type == 'IPv4' and self.inner_ip_invalid == 1:
            inner[inner_l3.name].chksum = 0x1234

        if self.inner_l4_invalid == 1:
            if self.inner_l4_type == 'SCTP':
                inner[SCTP].chksum = 0
            elif self.inner_l4_type == "UDP" or self.inner_l4_type == "TCP":
                inner[self.inner_l4_type].chksum = 0x1234

        """
        Outer package = L2/[Vlan]/L3
        """
        if self.outer_l3_type == 'IPv4':
            outer_l3 = IP()
        else:
            outer_l3 = IPv6()

        if self.outer_vlan != 'N/A':
            outer = Ether() / Dot1Q() / outer_l3
            outer[Dot1Q].vlan = self.outer_vlan
        else:
            outer = Ether() / outer_l3

        outer[Ether].src = self.outer_mac_src
        outer[Ether].dst = self.outer_mac_dst

        if self.outer_l3_type == 'IPv4':
            outer[outer_l3.name].src = self.outer_ip_src
            outer[outer_l3.name].dst = self.outer_ip_dst
            outer[outer_l3.name].proto = self.outer_ip_proto
        else:
            outer[outer_l3.name].src = self.outer_ip6_src
            outer[outer_l3.name].dst = self.outer_ip6_dst
            outer[outer_l3.name].nh = self.outer_ip_proto

        if self.outer_l3_type == 'IPv4' and self.outer_ip_invalid == 1:
            outer[outer_l3.name].chksum = 0x1234

        """
        GRE package: outer/GRE header/inner
        """
        if self.outer_ip_proto == 47:
            self.pkt = outer / NVGRE() / inner
        else:
            self.pkt = outer / ("X" * self.payload_size)

        wrpcap(self.pcap_file, self.pkt)

        return self.pkt

    def get_chksums(self, pcap=None):
        chk_sums = {}
        if pcap is None:
            pkts = rdpcap(self.pcap_file)
        else:
            pkts = rdpcap(pcap)

        time.sleep(1)

        if pkts[0].guess_payload_class(pkts[0]).name == "802.1Q":
            payload = pkts[0][Dot1Q]
        else:
            payload = pkts[0]

        if payload.guess_payload_class(payload).name == "IP":
            chk_sums['outer_ip'] = hex(payload[IP].chksum)

        if pkts[0].haslayer(NVGRE) == 1:
            inner = pkts[0][NVGRE]
            if inner.haslayer(IP) == 1:
                chk_sums['inner_ip'] = hex(inner[IP].chksum)
                if inner[IP].proto == 6:
                    chk_sums['inner_tcp'] = hex(inner[TCP].chksum)
                if inner[IP].proto == 17:
                    chk_sums['inner_udp'] = hex(inner[UDP].chksum)
                if inner[IP].proto == 132:
                    chk_sums['inner_sctp'] = hex(inner[SCTP].chksum)
            elif inner.haslayer(IPv6) is True:
                if inner[IPv6].nh == 6:
                    chk_sums['inner_tcp'] = hex(inner[TCP].chksum)
                if inner[IPv6].nh == 17:
                    chk_sums['inner_udp'] = hex(inner[UDP].chksum)
                # scapy can not get sctp checksum, so extracted manually
                if inner[IPv6].nh == 59:
                    load = str(inner[IPv6].payload)
                    chk_sums['inner_sctp'] = hex((ord(load[8]) << 24) |
                                                 (ord(load[9]) << 16) |
                                                 (ord(load[10]) << 8) |
                                                 (ord(load[11])))

        return chk_sums

    def send_pcap(self):
        """
        Send nvgre pcap file by tester_tx_iface
        """
        self.test_case.tester.scapy_append('pcap = rdpcap("%s")' % self.pcap_file)
        time.sleep(10)
        self.test_case.tester.scapy_append('sendp(pcap, iface="%s")' % self.test_case.tester_tx_iface)
        self.test_case.tester.scapy_execute()

    def pcap_len(self):
        """
        Return length of pcap packet, will plus 4 bytes crc
        """
        # add four bytes crc
        return len(self.pkt) + 4


class TestNvgre(TestCase):

    #
    #
    # Utility methods and other non-test code.
    #
    # Insert or move non-test functions here.
    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        nvgre Prerequisites
        """
        # this feature only enable in FVL now
        if self.nic in ["fortville_eagle", "fortville_spirit", "fortville_spirit_single", "fortpark_TLV"]:
            self.compile_switch = 'CONFIG_RTE_LIBRTE_I40E_INC_VECTOR'
        elif self.nic in ["sageville", "sagepond"]:
            self.compile_switch = 'CONFIG_RTE_IXGBE_INC_VECTOR'
        else:
            self.verify(False, "%s not support NVGRE case" % self.nic)
        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(self.nic)
        self.portmask = utils.create_mask(self.dut.get_ports(self.nic))

        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports for testing")

        # Verify that enough threads are available
        self.all_cores_mask = utils.create_mask(self.dut.get_core_list("all"))
        cores = self.dut.get_core_list("1S/5C/1T")
        self.verify(cores is not None, "Insufficient cores for speed testing")
        self.coremask = utils.create_mask(cores)

        # start testpmd
        self.pmdout = PmdOutput(self.dut)

        # init port
        self.dut_rx_port = ports[0]
        self.dut_tx_port = ports[1]
        self.dut_rx_port_mac = self.dut.get_mac_address(self.dut_rx_port)
        self.dut_tx_port_mac = self.dut.get_mac_address(self.dut_tx_port)

        self.tester_tx_port = self.tester.get_local_port(self.dut_rx_port)
        self.tester_tx_iface = self.tester.get_interface(self.tester_tx_port)
        self.tester_rx_port = self.tester.get_local_port(self.dut_tx_port)
        self.tester_rx_iface = self.tester.get_interface(self.tester_rx_port)

        # invalid parameter
        self.invalid_mac = "00:00:00:00:01"
        self.invalid_ip = "192.168.1.256"
        self.invalid_vlan = 4097
        self.invalid_queue = 64

        # performance test cycle
        self.test_cycles = [
            {'cores': '1S/1C/1T', 'Mpps': {}, 'pct': {}},
            {'cores': '1S/1C/2T', 'Mpps': {}, 'pct': {}},
            {'cores': '1S/2C/1T', 'Mpps': {}, 'pct': {}}
        ]

        """
        self.cal_type = [
            {'Type': 'SOFTWARE ALL', 'tx_checksum': '0x0'},
            {'Type': 'HW OUTER L3', 'tx_checksum': '0x1'},
            {'Type': 'HW OUTER L4', 'tx_checksum': '0x2'},
            {'Type': 'HW OUTER L3&L4', 'tx_checksum': '0x3'},
            {'Type': 'HW INNER L3', 'tx_checksum': '0x10'},
            {'Type': 'HW INNER L4', 'tx_checksum': '0x20'},
            {'Type': 'HW INNER L3&L4', 'tx_checksum': '0x30'},
            {'Type': 'HARDWARE ALL', 'tx_checksum': '0xff'}
        ]
        """

        self.table_header = ['Calculate Type']
        for test_cycle in self.test_cycles:
            self.table_header.append("%s Mpps" % test_cycle['cores'])
            self.table_header.append("% linerate")

        # tunnel filter performance test
        self.default_vlan = 1
        self.tunnel_multiqueue = 2
        self.tunnel_header = ['Packet', 'Filter', 'Queue', 'Mpps', '% linerate']
        self.tunnel_perf = [
            {'Packet': 'Normal', 'tunnel_filter': 'None', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'None', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac-ivlan', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac-ivlan-tenid', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac-tenid', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'omac-imac-tenid', 'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac-ivlan', 'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac-ivlan-tenid', 'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac-tenid', 'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'imac', 'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'NVGRE', 'tunnel_filter': 'omac-imac-tenid', 'recvqueue': 'Multi'}
        ]

        self.ports_socket = self.dut.get_numa_id(self.dut_rx_port)

    def nvgre_detect(self, **kwargs):
        """
        send nvgre packet and check whether testpmd detect the correct packet type
        """
        out = self.dut.send_expect("./%s/app/testpmd -c %s -n %d -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=4 --portmask=%s --txqflags=0"
                                   % (self.target, self.coremask, self.dut.get_memory_channels(), self.portmask), "testpmd>", 30)
        out = self.dut.send_expect("set fwd rxonly", "testpmd>", 10)
        self.dut.send_expect("set verbose 1", "testpmd>", 10)

        arg_str = ""
        for arg in kwargs:
            arg_str += "[%s = %s]" % (arg, kwargs[arg])

        # create pcap file with supplied arguments
        self.logger.info("send nvgre pkts %s" % arg_str)
        config = NvgreTestConfig(self, **kwargs)
        # now cloud filter will default enable L2 mac filter, so dst mac must be same
        config.outer_mac_dst = self.dut_rx_port_mac
        config.create_pcap()
        self.dut.send_expect("start", "testpmd>", 10)
        config.send_pcap()
        # check whether detect nvgre type
        out = self.dut.get_session_output()
        print out
        self.verify(config.packet_type() in out, "Nvgre Packet not detected")
        self.dut.send_expect("show port stats all", "testpmd>", 10)
        self.dut.send_expect("stop", "testpmd>", 10)
        self.dut.send_expect("quit", "#", 10)
        
    def nvgre_filter(self, filter_type="omac-imac-tenid", queue_id=3, vlan=False, remove=False):
        """
        send nvgre packet and check whether receive packet in assigned queue
        """
        self.dut.send_expect("./%s/app/testpmd -c %s -n %d -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=4 --portmask=%s --txqflags=0"
                             % (self.target, self.coremask, self.dut.get_memory_channels(), self.portmask), "testpmd>", 30)
        self.dut.send_expect("set fwd rxonly", "testpmd>", 10)
        self.dut.send_expect("set verbose 1", "testpmd>", 10)

        if vlan is not False:
            config = NvgreTestConfig(self, inner_vlan=vlan)
            vlan_id = vlan
        else:
            config = NvgreTestConfig(self)
            vlan_id = 1

        # now cloud filter will default enable L2 mac filter, so dst mac must be same
        config.outer_mac_dst = self.dut_rx_port_mac

        # tunnel_filter add port_id outer_mac inner_mac ip_addr inner_vlan tunnel_type(vxlan|nvgre)
        #       filter_type (imac-ivlan|imac-ivlan-tenid|imac-tenid|imac|omac-imac-tenid|iip) tenant_id queue_num

        out = self.dut.send_expect("tunnel_filter add %d %s %s %s %d nvgre %s %d %d"
                                   % (self.dut_rx_port, config.outer_mac_dst, config.inner_mac_dst, config.inner_ip_dst, vlan_id, filter_type, config.tni, queue_id),
                                   "testpmd>", 10)
        print out
        # invalid case request to remove tunnel filter
        if remove is True:
            queue_id = 0
            self.dut.send_expect("tunnel_filter rm %d %s %s %s %d nvgre %s %d %d"
                                 % (self.dut_rx_port, config.outer_mac_dst, config.inner_mac_dst, config.inner_ip_dst, vlan_id,
                                    filter_type, config.tni, queue_id), "testpmd>", 10)

        # send nvgre packet
        config.create_pcap()
        self.dut.send_expect("start", "testpmd>", 10)
        config.send_pcap()
        out = self.dut.get_session_output()
        print out
        queue = -1
        pattern = re.compile("- Receive queue=0x(\d)")
        m = pattern.search(out)
        if m is not None:
            queue = m.group(1)

        # verify received in expected queue
        self.verify(queue_id == int(queue), "invalid receive queue")

        self.dut.send_expect("stop", "testpmd>", 10)
        self.dut.send_expect("quit", "#", 10)

    def nvgre_checksum(self, **kwargs):

        # create pcap file with correct arguments
        args = {}
        for arg in kwargs:
            if "invalid" not in arg:
                args[arg] = kwargs[arg]

        config = NvgreTestConfig(self, **args)
        # now cloud filter will default enable L2 mac filter, so dst mac must be same
        config.outer_mac_dst = self.dut_rx_port_mac
        # csum function will not change outer ipv src address already
        if config.outer_ip6_src != "N/A":
            config.outer_ip6_src = config.outer_ip6_src
        else:
            config.outer_ip_src = config.outer_ip_src

        # csum function will not auto change nvgre inner ipv src address already
        if config.inner_ip6_src != "N/A":
            config.inner_ip6_src = config.inner_ip6_src
        else:
            config.inner_ip_src = config.inner_ip_src

        # create abnormal package with wrong checksum
        config.create_pcap()
        chksums_default = config.get_chksums()
        self.logger.info("chksums_ref:" + str(chksums_default))

        # start testpmd with 2queue/1port
        out = self.dut.send_expect("./%s/app/testpmd -c %s -n %d -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=4 --portmask=%s --enable-rx-cksum --txqflags=0"
                                   % (self.target, self.coremask, self.dut.get_memory_channels(), self.portmask), "testpmd>", 30)
        # disable vlan filter
        self.dut.send_expect('vlan set filter off %d' % self.dut_rx_port, "testpmd")

        # enable tx checksum offload
        self.dut.send_expect("set verbose 1", "testpmd>", 10)
        self.dut.send_expect("set fwd csum", "testpmd>", 10)
        self.dut.send_expect("csum set ip hw %d" % (self.dut_tx_port), "testpmd>", 10)
        self.dut.send_expect("csum set udp hw %d" % (self.dut_tx_port), "testpmd>", 10)
        self.dut.send_expect("csum set tcp hw %d" % (self.dut_tx_port), "testpmd>", 10)
        self.dut.send_expect("csum set sctp hw %d" % (self.dut_tx_port), "testpmd>", 10)
        self.dut.send_expect("csum set outer-ip hw %d" % (self.dut_tx_port), "testpmd>", 10)
        self.dut.send_expect("csum parse_tunnel on %d" % (self.dut_tx_port), "testpmd>", 10)

        # log the nvgre format
        arg_str = ""
        for arg in kwargs:
            arg_str += "[%s = %s]" % (arg, kwargs[arg])
        self.logger.info("nvgre packet %s" % arg_str)

        out = self.dut.send_expect("start", "testpmd>", 10)

        # create pcap file with supplied arguments
        config = NvgreTestConfig(self, **kwargs)
        config.outer_mac_dst = self.dut_rx_port_mac
        config.create_pcap()

        # remove tempory files
        self.tester.send_expect("rm -rf %s" % config.capture_file, "# ")
        # save the capture packet into pcap format
        self.tester.scapy_background()
        self.tester.scapy_append('p=sniff(iface="%s",count=1,timeout=5)' % self.tester_rx_iface)
        self.tester.scapy_append('wrpcap(\"%s\", p)' % config.capture_file)
        self.tester.scapy_foreground()

        config.send_pcap()
        time.sleep(5)

        # extract the checksum offload from saved pcap file
        chksums = config.get_chksums(pcap=config.capture_file)
        os.remove(config.capture_file)
        self.logger.info("chksums_tx:" + str(chksums))

        out = self.dut.send_expect("stop", "testpmd>", 10)

        # verify detected l4 invalid checksum
        if "inner_l4_invalid" in kwargs and config.inner_l4_type is not 'UDP':
            self.verify(self.pmdout.get_pmd_value("Bad-l4csum:", out) == 1, "Failed to count inner l4 chksum error")

        # verify detected l3 invalid checksum
        if "inner_ip_invalid" in kwargs:
            self.verify(self.pmdout.get_pmd_value("Bad-ipcsum:", out) == 1, "Failed to count inner ip chksum error")

        self.dut.send_expect("quit", "#", 10)

        # verify saved pcap checksum same to expected checksum
        for key in chksums_default:
            self.verify(chksums[key] == chksums_default[key], "%s not matched to %s" % (key, chksums_default[key]))

    def test_nvgre_ipv4(self):
        """
        verify nvgre packet with ipv4
        """
        # packet type detect must used without VECTOR pmd
        out = self.dut.send_expect("cat config/common_base", "]# ", 10)
        src_vec_model = re.findall("%s=." % self.compile_switch, out)[0][-1]
        if src_vec_model == 'y':
            self.dut.send_expect("sed -i -e 's/%s=.*$/" % self.compile_switch
                                + "%s=n/' config/common_base" % self.compile_switch, "# ", 30)
            self.dut.skip_setup = False
            self.dut.build_install_dpdk(self.target)

        # check no nvgre packet
        self.nvgre_detect(outer_ip_proto=0xFF)
        # check nvgre + IP inner packet
        self.nvgre_detect(inner_l3_type="IPv4", inner_l4_type='None')
        # check nvgre + udp inner packet
        self.nvgre_detect(inner_l4_type='TCP')
        # check nvgre + SCTP inner packet
        # self.nvgre_detect(inner_l4_type='SCTP')
        # check nvgre + vlan inner packet
        self.nvgre_detect(outer_vlan=1)
        # check vlan nvgre + vlan inner packet
        self.nvgre_detect(outer_vlan=1, inner_vlan=1)
        out = self.dut.send_expect("cat config/common_base", "]# ", 10)
        dst_vec_model = re.findall("%s=." % self.compile_switch, out)[0][-1]
        if src_vec_model != dst_vec_model:
            self.dut.send_expect("sed -i -e 's/%s=.*$/" % self.compile_switch
                                + "%s=%s/' config/common_base" % (self.compile_switch, src_vec_model), "# ", 30)
            self.dut.skip_setup = False
            self.dut.build_install_dpdk(self.target)
    def test_tunnel_filter(self):

        # verify tunnel filter feature
        # check outer mac
        self.nvgre_filter(filter_type="omac-imac-tenid")
        # check inner mac + inner vlan filter can work
        self.nvgre_filter(filter_type="imac-ivlan", vlan=1)
        # check inner mac + inner vlan + tunnel id filter can work
        self.nvgre_filter(filter_type="imac-ivlan-tenid", vlan=1)
        # check inner mac + tunnel id filter can work
        self.nvgre_filter(filter_type="imac-tenid")
        # check inner mac filter can work
        self.nvgre_filter(filter_type="imac")
        # check outer mac + inner mac + tunnel id filter can work
        self.nvgre_filter(filter_type="omac-imac-tenid")
        # check iip filter can work
        # self.nvgre_filter(filter_type="iip")

    def test_tunnel_filter_invalid(self):
        # verify tunnel filter parameter check function

        # invalid parameter
        vlan_id = 1
        filter_type = 'omac-imac-tenid'
        queue_id = 3

        self.nvgre_filter(filter_type="imac", remove=True)
        config = NvgreTestConfig(self)
        # config.outer_mac_dst = self.dut_port_mac
        self.dut.send_expect("./%s/app/testpmd -c %s -n %d -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=4 --portmask=%s --txqflags=0"
                             % (self.target, self.coremask, self.dut.get_memory_channels(), self.portmask), "testpmd>", 30)
        out = self.dut.send_expect("tunnel_filter add %d %s %s %s %d nvgre %s %d %d"
                                   % (self.dut_rx_port, config.outer_mac_dst, self.invalid_mac, config.inner_ip_dst, vlan_id,
                                      filter_type, config.tni, queue_id), "testpmd>", 10)
        self.verify("Bad arguments" in out, "Failed to detect invalid mac")
        out = self.dut.send_expect("tunnel_filter add %d %s %s %s %d nvgre %s %d %d"
                                   % (self.dut_rx_port, config.outer_mac_dst, config.inner_mac_dst, self.invalid_ip, vlan_id,
                                      filter_type, config.tni, queue_id), "testpmd>", 10)
        self.verify("Bad arguments" in out, "Failed to detect invalid ip")
        out = self.dut.send_expect("tunnel_filter add %d %s %s %s %d nvgre %s %d %d"
                                   % (self.dut_rx_port, config.outer_mac_dst, config.inner_mac_dst, config.inner_ip_dst, self.invalid_vlan,
                                      filter_type, config.tni, queue_id), "testpmd>", 10)
        self.verify("Input/output error" in out, "Failed to detect invalid vlan")
        out = self.dut.send_expect("tunnel_filter add %d %s %s %s %d nvgre %s %d %d"
                                   % (self.dut_rx_port, config.outer_mac_dst, config.inner_mac_dst, config.inner_ip_dst, vlan_id,
                                      filter_type, config.tni, self.invalid_queue), "testpmd>", 10)
        self.verify("Input/output error" in out, "Failed to detect invalid queue")

        self.dut.send_expect("stop", "testpmd>", 10)
        self.dut.send_expect("quit", "#", 10)

    def test_nvgre_ipv4_checksum_offload(self):
        # check normal packet
        self.nvgre_checksum()
        # check normal packet + ip checksum invalid
        self.nvgre_checksum(outer_ip_invalid=1)
        # check nvgre packet + inner ip checksum invalid
        self.nvgre_checksum(inner_ip_invalid=1)
        # check nvgre packet + outer ip checksum invalid
        self.nvgre_checksum(outer_ip_invalid=1)
        # check nvgre packet + outer ip + inner ip checksum invalid
        self.nvgre_checksum(outer_ip_invalid=1, inner_ip_invalid=1)
        # check nvgre packet + inner udp checksum invalid
        self.nvgre_checksum(inner_l4_invalid=1)
        # check nvgre packet + inner tcp checksum invalid
        self.nvgre_checksum(inner_l4_invalid=1, inner_l4_type='TCP')
        # check nvgre packet + inner sctp checksum invalid
        self.nvgre_checksum(inner_l4_invalid=1, inner_l4_type='SCTP')
        # check vlan nvgre packet + outer ip checksum invalid
        self.nvgre_checksum(outer_vlan=1, outer_ip_invalid=1)
        # check vlan nvgre packet + inner ip checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_ip_invalid=1)
        # check vlan nvgre packet + outer&inner ip checksum invalid
        self.nvgre_checksum(outer_vlan=1, outer_ip_invalid=1, inner_ip_invalid=1)
        # check vlan nvgre packet + inner vlan + outer ip checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_vlan=1, outer_ip_invalid=1)
        # check vlan nvgre packet + inner vlan + inner ip checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_vlan=1, inner_ip_invalid=1)
        # check vlan nvgre packet + inner vlan + outer&inner ip checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_vlan=1, outer_ip_invalid=1, inner_ip_invalid=1)
        # check vlan nvgre packet + inner vlan + inner udp checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_l4_invalid=1, inner_l4_type='UDP')
        # check vlan nvgre packet + inner vlan + inner tcp checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_l4_invalid=1, inner_l4_type='TCP')
        # check vlan nvgre packet + inner vlan + inner sctp checksum invalid
        self.nvgre_checksum(outer_vlan=1, inner_l4_invalid=1, inner_l4_type='SCTP')

    def test_perf_nvgre_tunnelfilter_performance_2ports(self):
        self.result_table_create(self.tunnel_header)
        core_list = self.dut.get_core_list('1S/%dC/1T' % (self.tunnel_multiqueue * 2), socket=self.ports_socket)
        core_mask = utils.create_mask(core_list)

        command_line = "./%s/app/testpmd -c %s -n %d -- -i --disable-rss --coremask=%s --rxq=4 --txq=4 --portmask=%s" % (self.target,
                                                                                                                         self.all_cores_mask,
                                                                                                                         self.dut.get_memory_channels(),
                                                                                                                         core_mask, self.portmask)
        for perf_config in self.tunnel_perf:
            pkts = []
            config = NvgreTestConfig(self)
            config.inner_vlan = self.default_vlan
            config.outer_mac_dst = self.dut.get_mac_address(self.dut_port)
            # get frame size
            config.create_pcap()
            frame_size = config.pcap_len()

            # restart testpmd in each performance config
            self.dut.send_expect(command_line, "testpmd> ", 100)
            if perf_config['tunnel_filter'] != 'None':
                self.dut.send_expect("tunnel_filter add %d %s %s %s %d vxlan %s %d %d"
                                     % (self.dut_port, config.outer_mac_dst, config.inner_mac_dst, config.inner_ip_dst, config.inner_vlan,
                                        perf_config['tunnel_filter'], config.tni, 0), "testpmd>", 10)

            if perf_config['Packet'] == 'Normal':
                config.outer_udp_dst = 63
                config.outer_mac_dst = self.dut.get_mac_address(self.dut_port)
                config.payload_size = frame_size - HEADER_SIZE['eth'] - HEADER_SIZE['ip'] - HEADER_SIZE['udp']

            # add default pkt into pkt list
            pkt = config.create_pcap()
            pkts.append(pkt)

            # add other pkts into pkt list when enable multi receive queues
            if perf_config['recvqueue'] == 'Multi':
                for queue in range(self.tunnel_multiqueue - 1):
                    if 'imac' in perf_config['tunnel_filter']:
                        config.inner_mac_dst = "00:00:20:00:00:0%d" % (queue + 2)
                    if 'ivlan' in perf_config['tunnel_filter']:
                        config.inner_vlan = (queue + 2)
                    if 'tenid' in perf_config['tunnel_filter']:
                        config.vni = (queue + 2)

                    # add tunnel filter the same as pkt
                    pkt = config.create_pcap()
                    pkts.append(pkt)
                    out = self.dut.send_expect("tunnel_filter add %d %s %s %s %d vxlan %s %d %d"
                                               % (self.dut_port, config.outer_mac_dst, config.inner_mac_dst, config.inner_ip_dst, config.inner_vlan,
                                                  perf_config['tunnel_filter'], config.vni, (queue + 1)), "testpmd>", 10)

            # save pkt list into pcap file
            wrpcap(config.pcap_file, pkts)
            self.tester.session.copy_file_to(config.pcap_file)

            # config the flows
            tgen_input = []
            tgen_input.append((self.tester.get_local_port(self.dut_port),
                               self.tester.get_local_port(self.recv_port),
                               config.pcap_file))

            self.dut.send_expect("set fwd mac", "testpmd>", 10)
            self.dut.send_expect("start", "testpmd>", 10)

            frame_size = config.pcap_len()
            wirespeed = self.wirespeed(self.nic, frame_size, 2)
            # run traffic generator
            _, pps = self.tester.traffic_generator_throughput(tgen_input)

            pps /= 1000000.0
            perf_config['Mpps'] = pps
            perf_config['pct'] = pps * 100 / wirespeed

            out = self.dut.send_expect("stop", "testpmd>", 10)
            self.dut.send_expect("quit", "# ", 10)

            # verify every queue work fine
            if perf_config['recvqueue'] == 'Multi':
                for queue in range(self.tunnel_multiqueue):
                    self.verify("RX Port= 0/Queue= %d -> TX Port= 1/Queue= %d" % (queue, queue) in out, "Queue %d no traffic" % queue)

            table_row = [perf_config['Packet'], perf_config['tunnel_filter'],
                         perf_config['recvqueue'], perf_config['Mpps'],
                         perf_config['pct']]

            self.result_table_add(table_row)

        self.result_table_print()

    def test_perf_nvgre_checksum_performance_2ports(self):
        config = NvgreTestConfig(self)
        config.outer_mac_dst = self.dut.get_mac_address(self.dut_port)
        config.pcap_file = "nvgre1.pcap"
        config.create_pcap()
        config.outer_mac_dst = self.dut.get_mac_address(self.recv_port)
        config.pcap_file = "nvgre.pcap"
        config.create_pcap()

        # configure flows
        tgen_input = []
        tgen_input.append((self.tester.get_local_port(self.dut_port),
                          self.tester.get_local_port(self.recv_port),
                          "nvgre.pcap"))
        tgen_input.append((self.tester.get_local_port(self.recv_port),
                          self.tester.get_local_port(self.dut_port),
                          "nvgre.pcap"))

        all_cores_mask = utils.create_mask(self.dut.get_core_list("all"))

        # socket/core/thread
        for test_cycle in self.test_cycles:
            core_config = test_cycle['cores']

            # take care the corelist when enable numa
            if '2S' not in core_config:
                core_list = self.dut.get_core_list(core_config,
                                                   socket=self.ports_socket)
            else:
                core_list = self.dut.get_core_list(core_config)

            core_mask = utils.create_mask(core_list)

            command_line = "./%s/app/testpmd -c %s -n %d -- -i \
 --disable-rss --coremask=%s --portmask=%s" % (self.target,
                                               all_cores_mask,
                                               self.dut.get_memory_channels(),
                                               core_mask, self.portmask)

            self.dut.send_expect(command_line, "testpmd> ", 100)
            self.dut.send_expect("set fwd csum", "testpmd>", 10)

            # different calculate type
            for cal in self.cal_type:
                self.dut.send_expect("tx_checksum set %s %d" % (cal['tx_checksum'], self.dut_port), "testpmd>", 10)
                self.dut.send_expect("tx_checksum set %s %d" % (cal['tx_checksum'], self.recv_port), "testpmd>", 10)
                self.dut.send_expect("start", "testpmd>", 10)

                frame_size = config.pcap_len()
                wirespeed = self.wirespeed(self.nic, frame_size, 2)
                # run traffic generator
                _, pps = self.tester.traffic_generator_throughput(tgen_input)

                pps /= 1000000.0
                test_cycle['Mpps'][cal['Type']] = pps
                test_cycle['pct'][cal['Type']] = pps * 100 / wirespeed

                self.dut.send_expect("stop", "testpmd>", 10)

            self.dut.send_expect("quit", "# ", 10)

        self.result_table_create(self.table_header)

        # save the results
        for cal in self.cal_type:
            table_row = [cal['Type']]
            for test_cycle in self.test_cycles:
                table_row.append(test_cycle['Mpps'][cal['Type']])
                table_row.append(test_cycle['pct'][cal['Type']])

            self.result_table_add(table_row)

        self.result_table_print()

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
