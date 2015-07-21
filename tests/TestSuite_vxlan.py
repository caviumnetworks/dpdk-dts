"""
DPDK Test suite.

Test IPv4 fragmentation features in DPDK.

"""

import dts
import string
import re
import time
import os
from pmd_output import PmdOutput

from socket import AF_INET6
from scapy.utils import struct, socket, wrpcap, rdpcap
from scapy.layers.inet import Ether, IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Dot1Q
from scapy.layers.vxlan import Vxlan
from scapy.layers.sctp import SCTP, SCTPChunkData
from scapy.sendrecv import sniff
from scapy.config import conf
from scapy.route import *

from test_case import TestCase
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator

#
#
# Test class.
#

VXLAN_PORT = 4789
PACKET_LEN = 128
BIDIRECT = True


class VxlanTestConfig(object):

    """
    Module for config/create/transmit vxlan packet
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
        Default vxlan packet format
        """
        self.pcap_file = 'vxlan.pcap'
        self.capture_file = 'capture.pcap'
        self.outer_mac_src = '00:00:10:00:00:00'
        self.outer_mac_dst = '11:22:33:44:55:66'
        self.outer_vlan = 'N/A'
        self.outer_ip_src = '192.168.1.1'
        self.outer_ip_dst = '192.168.1.2'
        self.outer_ip_invalid = 0
        self.outer_ip6_src = 'N/A'
        self.outer_ip6_dst = 'N/A'
        self.outer_ip6_invalid = 0
        self.outer_udp_src = 63
        self.outer_udp_dst = VXLAN_PORT
        self.outer_udp_invalid = 0
        self.vni = 1
        self.inner_mac_src = '00:00:20:00:00:00'
        self.inner_mac_dst = '00:00:20:00:00:01'
        self.inner_vlan = 'N/A'
        self.inner_ip_src = '192.168.2.1'
        self.inner_ip_dst = '192.168.2.2'
        self.inner_ip_invalid = 0
        self.inner_ip6_src = 'N/A'
        self.inner_ip6_dst = 'N/A'
        self.inner_ip6_invalid = 0
        self.payload_size = 18
        self.inner_l4_type = 'UDP'
        self.inner_l4_invalid = 0

    def packet_type(self):
        """
        Return vxlan packet type
        """
        if self.outer_udp_dst != VXLAN_PORT:
            if self.outer_ip6_src != 'N/A':
                return '(outer) L3 type: IPV6_EXT_UNKNOWN'
            else:
                return '(outer) L3 type: IPV4_EXT_UNKNOWN'
        else:
            if self.inner_ip6_src != 'N/A':
                return 'Inner L3 type: IPV6_EXT_UNKNOWN'
            else:
                return 'Inner L3 type: IPV4_EXT_UNKNOWN'

    def create_pcap(self, scp=True):
        """
        Create pcap file and copy it to tester if configured
        Return scapy packet object for later usage
        """
        if self.inner_l4_type == 'SCTP':
            self.inner_payload = SCTPChunkData(data='X' * 16)
        else:
            self.inner_payload = ("X" * self.payload_size)

        if self.inner_l4_type == 'TCP':
            l4_pro = TCP()
        elif self.inner_l4_type == 'SCTP':
            l4_pro = SCTP()
        else:
            l4_pro = UDP()

        if self.inner_ip6_src != 'N/A':
            inner_l3 = IPv6()
        else:
            inner_l3 = IP()

        if self.inner_vlan != 'N/A':
            inner = Ether() / Dot1Q() / inner_l3 / l4_pro / self.inner_payload
            inner[Dot1Q].vlan = self.inner_vlan
        else:
            inner = Ether() / inner_l3 / l4_pro / self.inner_payload

        if self.inner_ip6_src != 'N/A':
            inner[inner_l3.name].src = self.inner_ip6_src
            inner[inner_l3.name].dst = self.inner_ip6_dst
        else:
            inner[inner_l3.name].src = self.inner_ip_src
            inner[inner_l3.name].dst = self.inner_ip_dst

        if self.inner_ip_invalid == 1:
            inner[inner_l3.name].chksum = 0

        # when udp checksum is 0, will skip checksum
        if self.inner_l4_invalid == 1:
            if self.inner_l4_type == 'SCTP':
                inner[SCTP].chksum = 0
            else:
                inner[self.inner_l4_type].chksum = 1

        inner[Ether].src = self.inner_mac_src
        inner[Ether].dst = self.inner_mac_dst

        if self.outer_ip6_src != 'N/A':
            outer_l3 = IPv6()
        else:
            outer_l3 = IP()

        if self.outer_vlan != 'N/A':
            outer = Ether() / Dot1Q() / outer_l3 / UDP()
            outer[Dot1Q].vlan = self.outer_vlan
        else:
            outer = Ether() / outer_l3 / UDP()

        outer[Ether].src = self.outer_mac_src
        outer[Ether].dst = self.outer_mac_dst

        if self.outer_ip6_src != 'N/A':
            outer[outer_l3.name].src = self.outer_ip6_src
            outer[outer_l3.name].dst = self.outer_ip6_dst
        else:
            outer[outer_l3.name].src = self.outer_ip_src
            outer[outer_l3.name].dst = self.outer_ip_dst

        outer[UDP].src = self.outer_udp_src
        outer[UDP].dst = self.outer_udp_dst

        if self.outer_ip_invalid == 1:
            outer[outer_l3.name].chksum = 0
        # when udp checksum is 0, will skip checksum
        if self.outer_udp_invalid == 1:
            outer[UDP].chksum = 1

        if self.outer_udp_dst == VXLAN_PORT:
            self.pkt = outer / Vxlan(vni=self.vni) / inner
        else:
            self.pkt = outer / ("X" * self.payload_size)

        wrpcap(self.pcap_file, self.pkt)

        if scp is True:
            self.test_case.tester.session.copy_file_to(self.pcap_file)

        return self.pkt

    def get_chksums(self, pcap=None, tester=False):
        """
        get chksum values of Outer and Inner packet L3&L4
        Skip outer udp for it will be calculated by software
        """
        chk_sums = {}
        if pcap is None:
            if tester is True:
                self.test_case.tester.session.copy_file_from(self.pcap_file)
            pkts = rdpcap(self.pcap_file)
        else:
            if tester is True:
                self.test_case.tester.session.copy_file_from(pcap)
            pkts = rdpcap(pcap)

        time.sleep(1)

        if pkts[0].guess_payload_class(pkts[0]).name == "IP":
            chk_sums['outer_ip'] = hex(pkts[0][IP].chksum)

        if pkts[0].haslayer(Vxlan) == 1:
            inner = pkts[0][Vxlan]
            if inner.haslayer(IP) == 1:
                chk_sums['inner_ip'] = hex(inner[IP].chksum)
                if inner[IP].proto == 6:
                    chk_sums['inner_tcp'] = hex(inner[TCP].chksum)
                if inner[IP].proto == 17:
                    chk_sums['inner_udp'] = hex(inner[UDP].chksum)
                if inner[IP].proto == 132:
                    chk_sums['inner_sctp'] = hex(inner[SCTP].chksum)
            elif inner.haslayer(IPv6) == 1:
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

    def send_pcap(self, iface=""):
        """
        Send vxlan pcap file by iface
        """
        self.test_case.tester.scapy_append(
            'pcap = rdpcap("%s")' % self.pcap_file)
        self.test_case.tester.scapy_append(
            'sendp(pcap, iface="%s")' % iface)
        self.test_case.tester.scapy_execute()

    def pcap_len(self):
        """
        Return length of pcap packet, will plus 4 bytes crc
        """
        # add four bytes crc
        return len(self.pkt) + 4


class TestVxlan(TestCase, IxiaPacketGenerator):

    def set_up_all(self):
        """
        vxlan Prerequisites
        """
        # this feature only enable in FVL now
        self.verify(self.nic in ["fortville_eagle", "fortville_spirit",
                                 "fortville_spirit_single"],
                    "Vxlan Only supported by Fortville")
        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports()

        # update IxiaPacketGenerator function by local
        self.tester.extend_external_packet_generator(TestVxlan, self)

        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports for testing")
        global valports
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]

        self.portMask = dts.create_mask(valports[:2])

        # Verify that enough threads are available
        netdev = self.dut.ports_info[ports[0]]['port']
        self.ports_socket = netdev.socket
        cores = self.dut.get_core_list("1S/5C/2T", socket=self.ports_socket)
        self.verify(cores is not None, "Insufficient cores for speed testing")
        self.coremask = dts.create_mask(cores)

        # start testpmd
        self.pmdout = PmdOutput(self.dut)

        # init port config
        self.dut_port = valports[0]
        self.dut_port_mac = self.dut.get_mac_address(self.dut_port)
        tester_port = self.tester.get_local_port(self.dut_port)
        self.tester_iface = self.tester.get_interface(tester_port)
        self.recv_port = valports[1]
        tester_recv_port = self.tester.get_local_port(self.recv_port)
        self.recv_iface = self.tester.get_interface(tester_recv_port)

        # invalid parameter
        self.invalid_mac = "00:00:00:00:01"
        self.invalid_ip = "192.168.1.256"
        self.invalid_vlan = 4097
        self.invalid_queue = 64

        # vxlan payload length for performance test
        # inner packet not contain crc, should need add four
        self.vxlan_payload = PACKET_LEN - HEADER_SIZE['eth'] - \
            HEADER_SIZE['ip'] - HEADER_SIZE['udp'] - \
            HEADER_SIZE['vxlan'] - HEADER_SIZE['eth'] - \
            HEADER_SIZE['ip'] - HEADER_SIZE['udp'] + 4

        self.cal_type = [
            {'Type': 'SOFTWARE ALL', 'csum': [], 'recvqueue': 'Single',
                'Mpps': {}, 'pct': {}},
            {'Type': 'HW L4', 'csum': ['udp'], 'recvqueue': 'Single',
                'Mpps': {}, 'pct': {}},
            {'Type': 'HW L3&L4', 'csum': ['ip', 'udp', 'outer-ip'],
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Type': 'SOFTWARE ALL', 'csum': [], 'recvqueue': 'Multi',
                'Mpps': {}, 'pct': {}},
            {'Type': 'HW L4', 'csum': ['udp'], 'recvqueue': 'Multi',
                'Mpps': {}, 'pct': {}},
            {'Type': 'HW L3&L4', 'csum': ['ip', 'udp', 'outer-ip'],
                'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
        ]

        self.chksum_header = ['Calculate Type']
        self.chksum_header.append("Queues")
        self.chksum_header.append("Mpps")
        self.chksum_header.append("% linerate")

        # tunnel filter performance test
        self.default_vlan = 1
        self.tunnel_multiqueue = 2
        self.tunnel_header = [
            'Packet', 'Filter', 'Queue', 'Mpps', '% linerate']
        self.tunnel_perf = [
            {'Packet': 'Normal', 'tunnel_filter': 'None',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'None',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac-ivlan',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac-ivlan-tenid',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac-tenid',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'omac-imac-tenid',
                'recvqueue': 'Single', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'None',
                'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac-ivlan',
                'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac-ivlan-tenid',
                'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac-tenid',
                'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter': 'imac',
                'recvqueue': 'Multi', 'Mpps': {}, 'pct': {}},
            {'Packet': 'Vxlan', 'tunnel_filter':
                'omac-imac-tenid', 'recvqueue': 'Multi'}
        ]

    def send_and_detect(self, **kwargs):
        """
        send vxlan packet and check whether testpmd detect the correct
        packet type
        """
        pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
            "%(CHANNEL)d -- -i --disable-rss --rxq=4 --txq=4" + \
            " --nb-cores=8 --portmask=%(PORT)s --txqflags=0x0"
        pmd_cmd = pmd_temp % {'TARGET': self.target,
                              'COREMASK': self.coremask,
                              'CHANNEL': self.dut.get_memory_channels(),
                              'PORT': self.portMask}
        self.dut.send_expect(pmd_cmd, "testpmd>", 30)

        self.dut.send_expect("set fwd rxonly", "testpmd>", 10)
        self.dut.send_expect("set verbose 1", "testpmd>", 10)
        self.enable_vxlan(self.dut_port)
        self.enable_vxlan(self.recv_port)

        arg_str = ""
        for arg in kwargs:
            arg_str += "[%s = %s]" % (arg, kwargs[arg])

        # create pcap file with supplied arguments
        self.logger.info("send vxlan pkts %s" % arg_str)
        config = VxlanTestConfig(self, **kwargs)
        # now cloud filter will default enable L2 mac filter, so dst mac must
        # be same
        config.outer_mac_dst = self.dut_port_mac
        config.create_pcap()
        config.send_pcap(self.tester_iface)

        # check whether detect vxlan type
        out = self.dut.send_expect("start", "testpmd>", 10)
        self.verify(config.packet_type() in out, "Vxlan Packet not detected")
        out = self.dut.send_expect("stop", "testpmd>", 10)
        self.dut.send_expect("quit", "#", 10)

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
            '!8H', addr[0], addr[1], addr[2], addr[3], addr[4], addr[5],
            addr[6], addr[7]))
        return ipv6

    def send_and_check(self, **kwargs):
        """
        send vxlan packet and check whether receive packet with correct
        checksum
        """
        # create pcap file with supplied arguments
        outer_ipv6 = False
        args = {}
        for arg in kwargs:
            if "invalid" not in arg:
                args[arg] = kwargs[arg]
                if "outer_ip6" in arg:
                    outer_ipv6 = True

        config = VxlanTestConfig(self, **args)
        # now cloud filter will default enable L2 mac filter, so dst mac must
        # be same
        config.outer_mac_dst = self.dut_port_mac
        # csum function will auto add outer ipv src address
        if config.outer_ip6_src != "N/A":
            config.outer_ip6_src = self.increment_ipv6_address(
                config.outer_ip6_src)
        else:
            config.outer_ip_src = self.increment_ip_address(
                config.outer_ip_src)

        # csum function will auto add vxlan inner ipv src address
        if config.outer_udp_dst == VXLAN_PORT:
            if config.inner_ip6_src != "N/A":
                config.inner_ip6_src = self.increment_ipv6_address(
                    config.inner_ip6_src)
            else:
                config.inner_ip_src = self.increment_ip_address(
                    config.inner_ip_src)

        # extract the checksum value of vxlan packet
        config.create_pcap()
        chksums_ref = config.get_chksums()
        self.logger.info("chksums_ref" + str(chksums_ref))

        # start testpmd with 2queue/1port
        pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
            "%(CHANNEL)d -- -i --disable-rss --rxq=4 --txq=4" + \
            " --nb-cores=8 --portmask=%(PORT)s --txqflags=0x0"
        pmd_cmd = pmd_temp % {'TARGET': self.target,
                              'COREMASK': self.coremask,
                              'CHANNEL': self.dut.get_memory_channels(),
                              'PORT': self.portMask}
        self.dut.send_expect(pmd_cmd, "testpmd>", 30)

        # enable tx checksum offload
        self.dut.send_expect("set fwd csum", "testpmd>", 10)
        self.csum_set_type('ip', self.dut_port)
        # if packet outer L3 is ipv6, should not enable hardware checksum
        if not outer_ipv6:
            self.csum_set_type('outer-ip', self.dut_port)
        self.csum_set_type('udp', self.dut_port)
        self.csum_set_type('tcp', self.dut_port)
        self.csum_set_type('sctp', self.dut_port)
        self.csum_set_type('ip', self.recv_port)
        # if packet outer L3 is ipv6, should not enable hardware checksum
        if not outer_ipv6:
            self.csum_set_type('outer-ip', self.recv_port)
        self.csum_set_type('udp', self.recv_port)
        self.csum_set_type('tcp', self.recv_port)
        self.csum_set_type('sctp', self.recv_port)
        self.dut.send_expect("csum parse_tunnel on %d" %
                             self.dut_port, "testpmd>", 10)
        self.dut.send_expect("csum parse_tunnel on %d" %
                             self.recv_port, "testpmd>", 10)

        self.enable_vxlan(self.dut_port)
        self.enable_vxlan(self.recv_port)

        # log the vxlan format
        arg_str = ""
        for arg in kwargs:
            arg_str += "[%s = %s]" % (arg, kwargs[arg])

        self.logger.info("vxlan packet %s" % arg_str)

        out = self.dut.send_expect("start", "testpmd>", 10)

        # create pcap file with supplied arguments
        config = VxlanTestConfig(self, **kwargs)
        config.outer_mac_dst = self.dut_port_mac
        config.create_pcap()

        # remove tempory files
        self.tester.send_expect("rm -rf /root/%s" % config.capture_file, "# ")
        # save the capture packet into pcap format
        self.tester.scapy_background()
        self.tester.scapy_append(
            'p=sniff(iface="%s",count=1,timeout=5)' % self.recv_iface)
        self.tester.scapy_append(
            'wrpcap(\"/root/%s\", p)' % config.capture_file)
        self.tester.scapy_foreground()

        config.send_pcap(self.tester_iface)
        time.sleep(5)

        # extract the checksum offload from saved pcap file
        chksums = config.get_chksums(pcap=config.capture_file, tester=True)
        os.remove(config.capture_file)
        self.logger.info("chksums" + str(chksums))

        out = self.dut.send_expect("stop", "testpmd>", 10)

        # verify detected l4 invalid checksum
        if "inner_l4_invalid" in kwargs and config.inner_l4_type is not 'UDP':
            self.verify(self.pmdout.get_pmd_value("Bad-l4csum:", out)
                        == 1, "Failed to count inner l4 chksum error")

        # verify detected l3 invalid checksum
        if "inner_ip_invalid" in kwargs:
            self.verify(self.pmdout.get_pmd_value("Bad-ipcsum:", out)
                        == 1, "Failed to count inner ip chksum error")

        self.dut.send_expect("quit", "#", 10)

        # verify saved pcap checksum same to expected checksum
        for key in chksums_ref:
            self.verify(chksums[key] == chksums_ref[
                        key], "%s not matched to %s" % (key, chksums_ref[key]))

    def filter_and_check(self, filter_type="imac-ivlan", queue_id=3,
                         vlan=False, remove=False):
        """
        send vxlan packet and check whether receive packet in assigned queue
        """
        pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
            "%(CHANNEL)d -- -i --disable-rss --rxq=4 --txq=4" + \
            " --nb-cores=8 --portmask=%(PORT)s --txqflags=0x0"
        pmd_cmd = pmd_temp % {'TARGET': self.target,
                              'COREMASK': self.coremask,
                              'CHANNEL': self.dut.get_memory_channels(),
                              'PORT': self.portMask}
        self.dut.send_expect(pmd_cmd, "testpmd>", 30)

        self.dut.send_expect("set fwd rxonly", "testpmd>", 10)
        self.dut.send_expect("set verbose 1", "testpmd>", 10)
        self.enable_vxlan(self.dut_port)
        self.enable_vxlan(self.recv_port)

        if vlan is not False:
            config = VxlanTestConfig(self, inner_vlan=vlan)
            vlan_id = vlan
        else:
            config = VxlanTestConfig(self)
            vlan_id = 1

        # now cloud filter will default enable L2 mac filter, so dst mac must
        # be same
        config.outer_mac_dst = self.dut_port_mac

        args = [self.dut_port, config.outer_mac_dst, config.inner_mac_dst,
                config.inner_ip_dst, vlan_id, filter_type, config.vni,
                queue_id]

        self.tunnel_filter_add(*args)

        # invalid case request to remove tunnel filter
        if remove is True:
            queue_id = 0
            args = [self.dut_port, config.outer_mac_dst, config.inner_mac_dst,
                    config.inner_ip_dst, vlan_id, filter_type, config.vni,
                    queue_id]
            self.tunnel_filter_del(*args)

        # send vxlan packet
        config.create_pcap()
        config.send_pcap(self.tester_iface)
        out = self.dut.send_expect("start", "testpmd>", 10)

        queue = -1
        pattern = re.compile("VNI = (\d) - Receive queue=0x(\d)")
        m = pattern.search(out)
        if m is not None:
            queue = m.group(2)

        # verify received in expected queue
        self.verify(queue_id == int(queue), "invalid receive queue")

        self.dut.send_expect("stop", "testpmd>", 10)
        self.dut.send_expect("quit", "#", 10)

    def test_vxlan_ipv4_detect(self):
        """
        verify vxlan packet detection
        """
        # check normal packet
        self.send_and_detect(outer_udp_dst=1234)
        # check vxlan + UDP inner packet
        self.send_and_detect(inner_l4_type='UDP')
        # check vxlan + TCP inner packet
        self.send_and_detect(inner_l4_type='TCP')
        # check vxlan + SCTP inner packet
        self.send_and_detect(inner_l4_type='SCTP')
        # check vxlan + vlan inner packet
        self.send_and_detect(outer_vlan=1)
        # check vlan vxlan + vlan inner packet
        self.send_and_detect(outer_vlan=1, inner_vlan=1)

    def test_vxlan_ipv6_detect(self):
        """
        verify vxlan packet detection with ipv6 header
        """
        # check normal ipv6 packet
        self.send_and_detect(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                             outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                             outer_udp_dst=1234)
        # check ipv6 vxlan + UDP inner packet
        self.send_and_detect(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                             outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                             inner_l4_type='UDP')
        # check ipv6 vxlan + TCP inner packet
        self.send_and_detect(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                             outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                             inner_l4_type='TCP')
        # check ipv6 vxlan + SCTP inner packet
        self.send_and_detect(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                             outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                             inner_l4_type='SCTP')

    def test_vxlan_ipv4_checksum_offload(self):
        """
        verify vxlan packet checksum offload
        """
        # check normal packet + ip checksum invalid
        self.send_and_check(outer_ip_invalid=1, outer_udp_dst=1234)
        # check vxlan packet + inner ip checksum invalid
        self.send_and_check(inner_ip_invalid=1)
        # check vxlan packet + outer ip checksum invalid
        self.send_and_check(outer_ip_invalid=1)
        # check vxlan packet + outer ip + inner ip checksum invalid
        self.send_and_check(outer_ip_invalid=1, inner_ip_invalid=1)
        # check vxlan packet + inner udp checksum invalid
        self.send_and_check(inner_l4_invalid=1)
        # check vxlan packet + inner tcp checksum invalid
        self.send_and_check(inner_l4_invalid=1, inner_l4_type='TCP')
        # check vxlan packet + inner sctp checksum invalid
        self.send_and_check(inner_l4_invalid=1, inner_l4_type='SCTP')
        # check vlan vxlan packet + outer ip checksum invalid
        self.send_and_check(outer_vlan=1, outer_ip_invalid=1)
        # check vlan vxlan packet + inner ip checksum invalid
        self.send_and_check(outer_vlan=1, inner_ip_invalid=1)
        # check vlan vxlan packet + outer&inner ip checksum invalid
        self.send_and_check(
            outer_vlan=1, outer_ip_invalid=1, inner_ip_invalid=1)
        # check vlan vxlan packet + inner vlan + outer ip checksum invalid
        self.send_and_check(outer_vlan=1, inner_vlan=1, outer_ip_invalid=1)
        # check vlan vxlan packet + inner vlan + inner ip checksum invalid
        self.send_and_check(outer_vlan=1, inner_vlan=1, inner_ip_invalid=1)
        # check vlan vxlan packet + inner vlan + outer&inner ip checksum
        # invalid
        self.send_and_check(
            outer_vlan=1, inner_vlan=1, outer_ip_invalid=1, inner_ip_invalid=1)
        # check vlan vxlan packet + inner vlan + inner udp checksum invalid
        self.send_and_check(
            outer_vlan=1, inner_l4_invalid=1, inner_l4_type='UDP')
        # check vlan vxlan packet + inner vlan + inner tcp checksum invalid
        self.send_and_check(
            outer_vlan=1, inner_l4_invalid=1, inner_l4_type='TCP')
        # check vlan vxlan packet + inner vlan + inner sctp checksum invalid
        self.send_and_check(
            outer_vlan=1, inner_l4_invalid=1, inner_l4_type='SCTP')

    def test_vxlan_ipv6_checksum_offload(self):
        """
        verify vxlan packet checksum offload with ipv6 header
        not support ipv6 + sctp
        """
        # check normal ipv6 packet
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1")
        # check normal ipv6 packet + ip checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            outer_udp_dst=1234)
        # check ipv6 vxlan packet + inner ip checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_ip_invalid=1)
        # check ipv6 vxlan packet + inner udp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='UDP')
        # check ipv6 vxlan packet + inner udp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='UDP')
        # check ipv6 vxlan packet + inner tcp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='TCP')
        # check ipv6 vlan vxlan packet + inner udp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='UDP',
                            outer_vlan=1)
        # check ipv6 vlan vxlan packet + inner tcp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='TCP',
                            outer_vlan=1)
        # check ipv6 vlan vxlan packet + vlan + inner udp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='UDP',
                            outer_vlan=1, inner_vlan=1)
        # check ipv6 vlan vxlan packet + vlan + inner tcp checksum invalid
        self.send_and_check(outer_ip6_src="FE80:0:0:0:0:0:0:0",
                            outer_ip6_dst="FE80:0:0:0:0:0:0:1",
                            inner_l4_invalid=1, inner_l4_type='TCP',
                            outer_vlan=1, inner_vlan=1)

    def test_tunnel_filter(self):
        """
        verify tunnel filter feature
        """
        # check inner mac + inner vlan filter can work
        self.filter_and_check(filter_type="imac-ivlan", vlan=1)
        # check inner mac + inner vlan + tunnel id filter can work
        self.filter_and_check(filter_type="imac-ivlan-tenid", vlan=1)
        # check inner mac + tunnel id filter can work
        self.filter_and_check(filter_type="imac-tenid")
        # check inner mac filter can work
        self.filter_and_check(filter_type="imac")
        # check outer mac + inner mac + tunnel id filter can work
        self.filter_and_check(filter_type="omac-imac-tenid")
        # iip not supported by now
        # self.filter_and_check(filter_type="iip")

    def test_tunnel_filter_invalid(self):
        """
        verify tunnel filter parameter check function
        """
        # invalid parameter
        vlan_id = 1
        filter_type = 'omac-imac-tenid'
        queue_id = 3

        config = VxlanTestConfig(self)
        config.outer_mac_dst = self.dut_port_mac

        pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
            "%(CHANNEL)d -- -i --disable-rss --rxq=4 --txq=4" + \
            " --nb-cores=8 --portmask=%(PORT)s --txqflags=0x0"
        pmd_cmd = pmd_temp % {'TARGET': self.target,
                              'COREMASK': self.coremask,
                              'CHANNEL': self.dut.get_memory_channels(),
                              'PORT': self.portMask}
        self.dut.send_expect(pmd_cmd, "testpmd>", 30)

        self.enable_vxlan(self.dut_port)
        self.enable_vxlan(self.recv_port)
        args = [self.dut_port, config.outer_mac_dst, self.invalid_mac,
                config.inner_ip_dst, vlan_id, filter_type, config.vni,
                queue_id]
        out = self.tunnel_filter_add_nocheck(*args)
        self.verify("Bad arguments" in out, "Failed to detect invalid mac")
        args = [self.dut_port, config.outer_mac_dst, config.inner_mac_dst,
                self.invalid_ip, vlan_id, filter_type, config.vni, queue_id]
        out = self.tunnel_filter_add_nocheck(*args)
        self.verify("Bad arguments" in out, "Failed to detect invalid ip")
        args = [self.dut_port, config.outer_mac_dst, config.inner_mac_dst,
                config.inner_ip_dst, self.invalid_vlan, filter_type,
                config.vni, queue_id]
        out = self.tunnel_filter_add_nocheck(*args)
        self.verify("Input/output error" in out,
                    "Failed to detect invalid vlan")
        args = [self.dut_port, config.outer_mac_dst, config.inner_mac_dst,
                config.inner_ip_dst, vlan_id, filter_type, config.vni,
                self.invalid_queue]
        out = self.tunnel_filter_add_nocheck(*args)
        self.verify("Input/output error" in out,
                    "Failed to detect invalid queue")

        self.dut.send_expect("stop", "testpmd>", 10)
        self.dut.send_expect("quit", "#", 10)

    def config_tunnelfilter(self, dut_port, recv_port, perf_config, pcapfile):
        pkts = []
        config = VxlanTestConfig(self, payload_size=self.vxlan_payload - 4)
        config.inner_vlan = self.default_vlan
        config.outer_mac_dst = self.dut.get_mac_address(dut_port)
        config.pcap_file = pcapfile

        tun_filter = perf_config['tunnel_filter']
        recv_queue = perf_config['recvqueue']
        # there's known bug that if enable vxlan, rss will be disabled
        if tun_filter == "None" and recv_queue == 'Multi':
            print dts.RED("RSS and Tunel filter can't enable in the same time")
        else:
            self.enable_vxlan(dut_port)

        if tun_filter != 'None':
            args = [self.dut_port, config.outer_mac_dst,
                    config.inner_mac_dst, config.inner_ip_dst,
                    config.inner_vlan, tun_filter,
                    config.vni, 0]
            self.tunnel_filter_add(*args)

        if perf_config['Packet'] == 'Normal':
            config.outer_udp_dst = 63
            config.outer_mac_dst = self.dut.get_mac_address(dut_port)
            config.payload_size = PACKET_LEN - \
                HEADER_SIZE['eth'] - HEADER_SIZE['ip'] - HEADER_SIZE['udp']

        # add default pkt into pkt list
        pkt = config.create_pcap(scp=False)
        pkts.append(pkt)

        # add other pkts into pkt list when enable multi receive queues
        if recv_queue == 'Multi' and tun_filter != 'None':
            for queue in range(self.tunnel_multiqueue - 1):
                if 'imac' in tun_filter:
                    config.inner_mac_dst = "00:00:20:00:00:0%d" % (
                        queue + 2)
                if 'ivlan' in tun_filter:
                    config.inner_vlan = (queue + 2)
                if 'tenid' in tun_filter:
                    config.vni = (queue + 2)

                # add tunnel filter the same as pkt
                pkt = config.create_pcap(scp=False)
                pkts.append(pkt)

                args = [dut_port, config.outer_mac_dst,
                        config.inner_mac_dst, config.inner_ip_dst,
                        config.inner_vlan, tun_filter,
                        config.vni, (queue + 1)]
                self.tunnel_filter_add(*args)

        # save pkt list into pcap file
        wrpcap(config.pcap_file, pkts)
        self.tester.session.copy_file_to(config.pcap_file)

    def ip_random(self, port, frag, src, proto, tos, dst, chksum, len,
                  options, version, flags, ihl, ttl, id):
        self.add_tcl_cmd("protocol config -name ip")
        self.add_tcl_cmd('ip config -sourceIpAddr "%s"' % src)
        self.add_tcl_cmd('ip config -sourceIpAddrMode ipIncrHost')
        self.add_tcl_cmd('ip config -sourceIpAddrRepeatCount %d' % 64)
        self.add_tcl_cmd('ip config -destIpAddr "%s"' % dst)
        self.add_tcl_cmd('ip config -destIpMask "255.255.0.0" ')
        self.add_tcl_cmd('ip config -destIpAddrMode ipRandom')
        self.add_tcl_cmd('ip config -destIpAddrRepeatCount 65536')
        self.add_tcl_cmd("ip config -ttl %d" % ttl)
        self.add_tcl_cmd("ip config -totalLength %d" % len)
        self.add_tcl_cmd("ip config -fragment %d" % frag)
        self.add_tcl_cmd("ip config -ipProtocol %d" % proto)
        self.add_tcl_cmd("ip config -identifier %d" % id)
        self.add_tcl_cmd("stream config -framesize %d" % (len + 18))
        self.add_tcl_cmd("ip set %d %d %d" %
                         (self.chasId, port['card'], port['port']))

    def combine_pcap(self, dest_pcap, src_pcap):
        pkts = rdpcap(dest_pcap)
        if len(pkts) != 1:
            return

        pkts_src = rdpcap(src_pcap)
        pkts += pkts_src

        wrpcap(dest_pcap, pkts)

    def test_perf_vxlan_tunnelfilter_performance_2ports(self):
        dts.results_table_add_header(self.tunnel_header)
        core_list = self.dut.get_core_list(
            '1S/%dC/1T' % (self.tunnel_multiqueue * 2 + 1),
            socket=self.ports_socket)
        core_mask = dts.create_mask(core_list)

        pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
            "%(CHANNEL)d -- -i --disable-rss --rxq=2 --txq=2" + \
            " --nb-cores=4 --portmask=%(PORT)s --txqflags=0x0"

        for perf_config in self.tunnel_perf:
            tun_filter = perf_config['tunnel_filter']
            recv_queue = perf_config['recvqueue']
            print dts.GREEN("Measure tunnel performance of [%s %s %s]"
                            % (perf_config['Packet'], tun_filter, recv_queue))

            if tun_filter == "None" and recv_queue == "Multi":
                pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
                    "%(CHANNEL)d -- -i --rss-udp --rxq=2 --txq=2" + \
                    " --nb-cores=4 --portmask=%(PORT)s --txqflags=0x0"

            pmd_cmd = pmd_temp % {'TARGET': self.target,
                                  'COREMASK': core_mask,
                                  'CHANNEL': self.dut.get_memory_channels(),
                                  'PORT': self.portMask}
            self.dut.send_expect(pmd_cmd, "testpmd> ", 100)

            # config flow
            self.config_tunnelfilter(
                self.dut_port, self.recv_port, perf_config, "flow1.pcap")
            # config the flows
            tgen_input = []
            tgen_input.append((self.tester.get_local_port(self.dut_port),
                               self.tester.get_local_port(self.recv_port),
                               "flow1.pcap"))

            if BIDIRECT:
                self.config_tunnelfilter(
                    self.recv_port, self.dut_port, perf_config, "flow2.pcap")
                tgen_input.append((self.tester.get_local_port(self.recv_port),
                                   self.tester.get_local_port(self.dut_port),
                                   "flow2.pcap"))

            self.dut.send_expect("set fwd io", "testpmd>", 10)
            self.dut.send_expect("start", "testpmd>", 10)

            if BIDIRECT:
                wirespeed = self.wirespeed(self.nic, PACKET_LEN, 2)
            else:
                wirespeed = self.wirespeed(self.nic, PACKET_LEN, 1)

            if recv_queue == 'Multi' and tun_filter == "None":
                ip_ori = self.ip
                self.ip = self.ip_random

            # run traffic generator
            _, pps = self.tester.traffic_generator_throughput(tgen_input)

            if recv_queue == 'Multi' and tun_filter == "None":
                self.ip = ip_ori

            pps /= 1000000.0
            perf_config['Mpps'] = pps
            perf_config['pct'] = pps * 100 / wirespeed

            out = self.dut.send_expect("stop", "testpmd>", 10)
            self.dut.send_expect("quit", "# ", 10)

            # verify every queue work fine
            if recv_queue == 'Multi':
                for queue in range(self.tunnel_multiqueue):
                    self.verify("Queue= %d -> TX Port"
                                % (queue) in out,
                                "Queue %d no traffic" % queue)

            table_row = [perf_config['Packet'], tun_filter, recv_queue,
                         perf_config['Mpps'], perf_config['pct']]

            dts.results_table_add_row(table_row)

        dts.results_table_print()

    def test_perf_vxlan_checksum_performance_2ports(self):
        dts.results_table_add_header(self.chksum_header)
        vxlan = VxlanTestConfig(self, payload_size=self.vxlan_payload)
        vxlan.outer_mac_dst = self.dut.get_mac_address(self.dut_port)
        vxlan.pcap_file = "vxlan1.pcap"
        vxlan.inner_mac_dst = "00:00:20:00:00:01"
        vxlan.create_pcap(scp=False)

        vxlan_queue = VxlanTestConfig(self, payload_size=self.vxlan_payload)
        vxlan_queue.outer_mac_dst = self.dut.get_mac_address(self.dut_port)
        vxlan_queue.pcap_file = "vxlan1_1.pcap"
        vxlan_queue.inner_mac_dst = "00:00:20:00:00:02"
        vxlan_queue.create_pcap(scp=False)

        # socket/core/thread
        core_list = self.dut.get_core_list(
            '1S/%dC/1T' % (self.tunnel_multiqueue * 2 + 1),
            socket=self.ports_socket)
        core_mask = dts.create_mask(core_list)

        tgen_dut = self.tester.get_local_port(self.dut_port)
        tgen_tester = self.tester.get_local_port(self.recv_port)
        for cal in self.cal_type:
            recv_queue = cal['recvqueue']
            print dts.GREEN("Measure checksum performance of [%s %s %s]"
                            % (cal['Type'], recv_queue, cal['csum']))

            # configure flows
            tgen_input = []
            if recv_queue == 'Multi':
                self.combine_pcap("vxlan1.pcap", "vxlan1_1.pcap")
            self.tester.session.copy_file_to("vxlan1.pcap")
            tgen_input.append((tgen_dut, tgen_tester, "vxlan1.pcap"))

            # multi queue and signle queue commands
            if recv_queue == 'Multi':
                pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
                    "%(CHANNEL)d -- -i --disable-rss --rxq=2 --txq=2" + \
                    " --nb-cores=4 --portmask=%(PORT)s --txqflags=0x0"
            else:
                pmd_temp = "./%(TARGET)s/app/testpmd -c %(COREMASK)s -n " + \
                    "%(CHANNEL)d -- -i --nb-cores=2 --portmask=%(PORT)s" + \
                    " --txqflags=0x0"

            pmd_cmd = pmd_temp % {'TARGET': self.target,
                                  'COREMASK': core_mask,
                                  'CHANNEL': self.dut.get_memory_channels(),
                                  'PORT': self.portMask}

            self.dut.send_expect(pmd_cmd, "testpmd> ", 100)
            self.dut.send_expect("set fwd csum", "testpmd>", 10)
            self.dut.send_expect("csum parse_tunnel on %d" %
                                 self.dut_port, "testpmd>", 10)
            self.dut.send_expect("csum parse_tunnel on %d" %
                                 self.recv_port, "testpmd>", 10)
            self.enable_vxlan(self.dut_port)
            self.enable_vxlan(self.recv_port)

            # redirect flow to another queue by tunnel filter
            args = [self.dut_port, vxlan.outer_mac_dst,
                    vxlan.inner_mac_dst, vxlan.inner_ip_dst,
                    0, 'imac', vxlan.vni, 0]
            self.tunnel_filter_add(*args)

            if recv_queue == 'Multi':
                args = [self.dut_port, vxlan_queue.outer_mac_dst,
                        vxlan_queue.inner_mac_dst, vxlan_queue.inner_ip_dst,
                        0, 'imac', vxlan_queue.vni, 1]
                self.tunnel_filter_add(*args)

            for pro in cal['csum']:
                self.csum_set_type(pro, self.dut_port)
                self.csum_set_type(pro, self.recv_port)

            self.dut.send_expect("start", "testpmd>", 10)

            wirespeed = self.wirespeed(self.nic, PACKET_LEN, 1)

            # run traffic generator
            _, pps = self.tester.traffic_generator_throughput(tgen_input)

            pps /= 1000000.0
            cal['Mpps'] = pps
            cal['pct'] = pps * 100 / wirespeed

            out = self.dut.send_expect("stop", "testpmd>", 10)
            self.dut.send_expect("quit", "# ", 10)

            # verify every queue work fine
            if recv_queue == 'Multi':
                for queue in range(self.tunnel_multiqueue):
                    self.verify("Queue= %d -> TX Port"
                                % (queue) in out,
                                "Queue %d no traffic" % queue)

            table_row = [cal['Type'], recv_queue, cal['Mpps'], cal['pct']]
            dts.results_table_add_row(table_row)

        dts.results_table_print()

    def enable_vxlan(self, port):
        self.dut.send_expect("rx_vxlan_port add %d %d"
                             % (VXLAN_PORT, port),
                             "testpmd>", 10)

    def csum_set_type(self, proto, port):
        out = self.dut.send_expect("csum set %s hw %d" % (proto, port),
                                   "testpmd>", 10)
        self.verify("Bad arguments" not in out, "Failed to set vxlan csum")
        self.verify("error" not in out, "Failed to set vxlan csum")

    def tunnel_filter_add(self, *args):
        # tunnel_filter add port_id outer_mac inner_mac ip inner_vlan
        # tunnel_type(vxlan)
        # filter_type
        # (imac-ivlan|imac-ivlan-tenid|imac-tenid|imac|omac-imac-tenid|iip)
        # tenant_id queue_num
        out = self.dut.send_expect("tunnel_filter add %d " % args[0] +
                                   "%s %s %s " % (args[1], args[2], args[3]) +
                                   "%d vxlan %s " % (args[4], args[5]) +
                                   "%d %d" % (args[6], args[7]),
                                   "testpmd>", 10)
        self.verify("Bad arguments" not in out, "Failed to add tunnel filter")
        self.verify("error" not in out, "Failed to add tunnel filter")
        return out

    def tunnel_filter_add_nocheck(self, *args):
        out = self.dut.send_expect("tunnel_filter add %d " % args[0] +
                                   "%s %s %s " % (args[1], args[2], args[3]) +
                                   "%d vxlan %s " % (args[4], args[5]) +
                                   "%d %d" % (args[6], args[7]),
                                   "testpmd>", 10)
        return out

    def tunnel_filter_del(self, *args):
        out = self.dut.send_expect("tunnel_filter rm %d " % args[0] +
                                   "%s %s %s " % (args[1], args[2], args[3]) +
                                   "%d vxlan %s " % (args[4], args[5]) +
                                   "%d %d" % (args[6], args[7]),
                                   "testpmd>", 10)
        self.verify("Bad arguments" not in out,
                    "Failed to remove tunnel filter")
        self.verify("error" not in out, "Failed to remove tunnel filter")
        return out

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
