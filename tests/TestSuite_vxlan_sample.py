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

Vxlan sample test suite.
"""

import os
import dts
import string
import re
import time
from plotting import Plotting
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator
from qemu_kvm import QEMUKvm
from TestSuite_vxlan import VxlanTestConfig
from pmd_output import PmdOutput

from scapy.utils import struct, socket, wrpcap, rdpcap
from scapy.layers.inet import Ether, IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Dot1Q
from scapy.layers.vxlan import Vxlan
from scapy.layers.sctp import SCTP, SCTPChunkData
from scapy.sendrecv import sniff
from scapy.config import conf
from scapy.route import *


PACKET_LEN = 128


class TestVxlanSample(TestCase):
    FEAT_ENABLE = 1
    FEAT_DISABLE = 0
    INNER_VLAN_VNI = 1
    INNER_VNI = 2
    OUTER_INNER_VNI = 3

    def set_up_all(self):
        """
        Run before each test suite.
        """
        # Change the config file to support vhost and recompile the package.
        self.dut.send_expect("sed -i -e 's/RTE_LIBRTE_VHOST=n$/"
                             + "RTE_LIBRTE_VHOST=y/' config/"
                             + "common_linuxapp", "# ", 30)
        # temporary disable skip_setup
        skip_setup = self.dut.skip_setup
        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.target)
        self.dut.skip_setup = skip_setup

        # this feature only enable in FVL now
        self.verify(self.nic in ["fortville_eagle", "fortville_spirit",
                                 "fortville_spirit_single"],
                    "Vxlan Only supported by Fortville")
        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports()

        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports for testing")

        # get pf socket
        self.pf = self.dut_ports[0]
        netdev = self.dut.ports_info[self.pf]['port']
        self.socket = netdev.get_nic_socket()
        self.pf_mac = self.dut.get_mac_address(self.pf)

        # build sample app
        out = self.dut.send_expect("make -C examples/tep_termination", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        # build for vhost user environment
        self.dut.send_expect("cd lib/librte_vhost/eventfd_link", "# ")
        self.dut.send_expect("make", "# ")
        self.dut.send_expect("insmod ./eventfd_link.ko", "# ")
        self.dut.send_expect("cd ../../..", "# ")
        out = self.dut.send_expect("lsmod |grep eventfd_link", "# ")
        self.verify("eventfd_link" in out,
                    "Failed to insmod eventfd_link driver")

        self.def_mac = "00:00:20:00:00:20"
        self.vm_dut = None
        self.tep_app = "./examples/tep_termination/build/tep_termination"
        self.vxlan_port = 4789
        self.vm_testpmd = "./x86_64-native-linuxapp-gcc/app/testpmd -c f -n 3" \
                          + " -- -i --txqflags=0xf00 --disable-hw-vlan"

        # params for tep_termination
        self.cores = self.dut.get_core_list("1S/4C/1T", socket=self.socket)
        self.capture_file = "/tmp/vxlan_cap.pcap"
        self.def_mss = 256

        # performance measurement, checksum based on encap
        self.perf_cfg = [{'Func': 'Decap', 'VirtIO': 'Single', 'Mpps': {},
                         'pct': {}},
                         {'Func': 'Encap', 'VirtIO': 'Single', 'Mpps': {},
                          'pct': {}},
                         {'Func': 'Decap&Encap', 'VirtIO': 'Single',
                          'Mpps': {}, 'pct': {}},
                         {'Func': 'Checksum', 'VirtIO': 'Single',
                          'Mpps': {}, 'pct': {}},
                         {'Func': 'Checksum&Decap', 'VirtIO': 'Single',
                          'Mpps': {}, 'pct': {}},
                         {'Func': 'Decap', 'VirtIO': 'Two Ports', 'Mpps': {},
                          'pct': {}},
                         {'Func': 'Encap', 'VirtIO': 'Two Ports', 'Mpps': {},
                          'pct': {}},
                         {'Func': 'Decap&Encap', 'VirtIO': 'Two Ports',
                          'Mpps': {}, 'pct': {}},
                         {'Func': 'Checksum', 'VirtIO': 'Two Ports',
                          'Mpps': {}, 'pct': {}},
                         {'Func': 'Checksum&Decap', 'VirtIO': 'Two Ports',
                          'Mpps': {}, 'pct': {}}]

    def set_up(self):
        """
        Run before each test case.
        """
        # create coremask
        self.coremask = dts.create_mask(self.cores)

        if "2VM" not in self.running_case:
            vm_num = 1
        else:
            vm_num = 2

        encap = self.FEAT_ENABLE
        decap = self.FEAT_ENABLE
        chksum = self.FEAT_DISABLE
        if self.running_case == "test_vxlan_sample_encap":
            encap = self.FEAT_ENABLE
            decap = self.FEAT_DISABLE
        elif self.running_case == "test_vxlan_sample_decap":
            encap = self.FEAT_DISABLE
            decap = self.FEAT_ENABLE
        elif self.running_case == "test_vxlan_sample_chksum":
            chksum = self.FEAT_ENABLE
        elif self.running_case == "test_vxlan_sample_tso":
            chksum = self.FEAT_ENABLE

        tep_cmd_temp = self.tep_app + " -c %(COREMASK)s -n %(CHANNELS)d " \
            + "--socket-mem 2048,2048 -- -p 0x1 " \
            + "--udp-port %(VXLAN_PORT)d --nb-devices %(NB_DEVS)d " \
            + "--filter-type %(FILTERS)d " \
            + "--tx-checksum %(TX_CHKS)d --encap %(ENCAP)d --decap %(DECAP)d"

        tep_cmd = tep_cmd_temp % {
            'COREMASK': self.coremask,
            'CHANNELS': self.dut.get_memory_channels(),
            'VXLAN_PORT': self.vxlan_port, 'NB_DEVS': vm_num * 2,
            'FILTERS': self.OUTER_INNER_VNI, 'TX_CHKS': chksum,
            'ENCAP': encap, 'DECAP': decap}

        if self.running_case == "test_vxlan_sample_tso":
            tep_cmd += " --tso-segsz=%d" % self.def_mss

        if self.running_case != "test_perf_vxlan_sample":
            self.prepare_vxlan_sample_env(tep_cmd, vm_num=vm_num)

        pass

    def prepare_vxlan_sample_env(self, tep_cmd, vm_num=1):
        # remove unexpected socke
        self.dut.send_expect("rm -rf vhost-net", "# ")

        # start tep_termination first
        self.dut.send_expect(tep_cmd, "VHOST_CONFIG: bind to vhost-net")

        # start one vm
        self.vm = QEMUKvm(self.dut, 'vm0', 'vxlan_sample')

        # add two virtio user netdevices
        vm_params = {}
        vm_params['driver'] = 'vhost-user'
        vm_params['opt_path'] = './vhost-net'
        vm_params['opt_mac'] = self.def_mac
        self.vm.set_vm_device(**vm_params)
        vm_params['opt_mac'] = self.mac_address_add(1)
        self.vm.set_vm_device(**vm_params)

        try:
            self.vm_dut = self.vm.start()
            if self.vm_dut is None:
                raise Exception("Set up VM ENV failed!")
        except Exception as e:
            print dts.RED("Failure for %s" % str(e))

        # create another vm
        if vm_num == 2:
            print "not implemented now"

        return True

    def clear_vxlan_sample_env(self):
        if self.vm_dut:
            self.vm_dut.kill_all()
            time.sleep(1)
            self.vm_dut.close()
            self.vm_dut.logger.logger_exit()
            self.vm_dut = None

        if self.vm:
            self.vm.stop()
            self.vm = None

    def mac_address_add(self, number):
        if number > 15:
            return ''
        mac = int(self.def_mac[-1]) + number
        return self.def_mac[:-1] + '%x' % mac

    def vm_testpmd_start(self, vm_id=0):
        """
        Start testpmd in virtual machine
        """
        if vm_id == 0 and self.vm_dut is not None:
            # start testpmd
            self.vm_dut.send_expect(self.vm_testpmd, "testpmd>", 20)
            # set fwd mac
            self.vm_dut.send_expect("set fwd io", "testpmd>")
            # start tx_first
            self.vm_dut.send_expect("start tx_first", "testpmd>")

    def test_vxlan_sample_encap(self):
        self.vm_testpmd_start(vm_id=0)
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="normal_udp")
        self.send_and_verify(vm_id=0, vf_id=1, pkt_type="normal_udp")

    def test_vxlan_sample_decap(self):
        self.vm_testpmd_start(vm_id=0)
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="vxlan_udp_decap")
        self.send_and_verify(vm_id=0, vf_id=1, pkt_type="vxlan_udp_decap")

    def test_vxlan_sample_encap_decap(self):
        self.vm_testpmd_start(vm_id=0)
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="vxlan_udp")
        self.send_and_verify(vm_id=0, vf_id=1, pkt_type="vxlan_udp")

    def test_vxlan_sample_chksum(self):
        self.vm_testpmd_start(vm_id=0)
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="vxlan_udp_chksum")
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="vxlan_tcp_chksum")
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="vxlan_sctp_chksum")

    def test_vxlan_sample_tso(self):
        self.vm_testpmd_start(vm_id=0)
        self.send_and_verify(vm_id=0, vf_id=0, pkt_type="vxlan_tcp_tso")

    def start_capture(self, itf, pkt_smac="", pkt_dmac="", count=1):
        self.tester.send_expect("rm -f %s" % self.capture_file, "# ")
        self.tester.scapy_background()
        if pkt_smac != "":
            self.tester.scapy_append(
                'p = sniff(filter="ether src %s",' % pkt_smac +
                'iface="%s", count=%d, timeout=5)' % (itf, count))
        if pkt_dmac != "":
            self.tester.scapy_append(
                'p = sniff(filter="ether dst %s",' % pkt_dmac +
                'iface="%s", count=%d, timeout=5)' % (itf, count))
        self.tester.scapy_append(
            'wrpcap(\"%s\", p)' % self.capture_file)
        self.tester.scapy_foreground()

    def transfer_capture_file(self):
        # copy capture file from tester
        if os.path.isfile('vxlan_cap.pcap'):
            os.remove('vxlan_cap.pcap')
        self.tester.session.copy_file_from(self.capture_file)

        if os.path.isfile('vxlan_cap.pcap'):
            pkts = rdpcap('vxlan_cap.pcap')
        else:
            pkts = []
        return pkts

    def send_and_verify(self, vm_id, vf_id, pkt_type):
        params = {}
        case_pass = True
        tester_recv_port = self.tester.get_local_port(self.pf)
        tester_iface = self.tester.get_interface(tester_recv_port)

        if pkt_type == "normal_udp":
            self.start_capture(tester_iface, pkt_smac=self.pf_mac)
            self.tester.scapy_append(
                'sendp([Ether(dst="%s")/IP()/UDP()/Raw("X"*18)], iface="%s")'
                % (self.pf_mac, tester_iface))
            self.tester.scapy_execute()
            time.sleep(5)

            pkts = self.transfer_capture_file()
            self.verify(len(pkts) >= 1, "Failed to capture packets")
            self.verify(pkts[0].haslayer(Vxlan) == 1,
                        "Packet not encapsulated")
            try:
                payload = str(pkts[0][UDP][Vxlan][UDP].payload)
                for i in range(18):
                    self.verify(ord(payload[i]) == 88, "Check udp data failed")
            except:
                case_pass = False
                print dts.RED("Failure in checking packet payload")

            if case_pass:
                print dts.GREEN("Check normal udp packet forward pass on "
                                "virtIO port %d" % vf_id)

        if pkt_type == "vxlan_udp_decap":
            # create vxlan packet pf mac + vni=1000 + inner virtIO port0 mac
            params['outer_mac_dst'] = self.pf_mac
            params['vni'] = 1000 + vm_id
            mac_incr = 2 * vm_id + vf_id
            params['inner_mac_dst'] = self.mac_address_add(mac_incr)

            # create vxlan pcap file and tranfer it to tester
            vxlan_pkt = VxlanTestConfig(self, **params)
            vxlan_pkt.create_pcap(scp=True)

            # start capture
            self.start_capture(tester_iface, pkt_dmac=params['inner_mac_dst'])
            vxlan_pkt.send_pcap(tester_iface)
            time.sleep(5)

            # transfer capture pcap to dts server
            pkts = self.transfer_capture_file()
            # check packet number and payload
            self.verify(len(pkts) >= 1, "Failed to capture packets")
            self.verify(pkts[0].haslayer(Vxlan) == 0,
                        "Packet not de-encapsulated")

            try:
                payload = str(pkts[0][UDP].payload)
                for i in range(18):
                    self.verify(ord(payload[i]) == 88, "Check udp data failed")
            except:
                case_pass = False
                print dts.RED("Failure in checking packet payload")

            if case_pass:
                print dts.GREEN("Check vxlan packet decap pass on virtIO port"
                                " %d" % vf_id)

        if pkt_type == "vxlan_udp":
            # create vxlan packet pf mac + vni=1000 + inner virtIO port0 mac
            params['outer_mac_dst'] = self.pf_mac
            params['vni'] = 1000 + vm_id
            mac_incr = 2 * vm_id + vf_id
            params['inner_mac_dst'] = self.mac_address_add(mac_incr)

            # create vxlan pcap file and tranfer it to tester
            vxlan_pkt = VxlanTestConfig(self, **params)
            vxlan_pkt.create_pcap(scp=True)

            # start capture
            self.start_capture(tester_iface, pkt_smac=self.pf_mac)
            vxlan_pkt.send_pcap(tester_iface)
            time.sleep(5)

            # transfer capture pcap to dts server
            pkts = self.transfer_capture_file()
            # check packet number and payload
            self.verify(len(pkts) >= 1, "Failed to capture packets")
            self.verify(pkts[0].haslayer(Vxlan) == 1,
                        "Packet not encapsulated")
            try:
                payload = str(pkts[0][UDP][Vxlan][UDP].payload)
                for i in range(18):
                    self.verify(ord(payload[i]) == 88, "Check udp data failed")
            except:
                case_pass = False
                print dts.RED("Failure in checking packet payload")

            if case_pass:
                print dts.GREEN("Check vxlan packet decap and encap pass on "
                                "virtIO port %d" % vf_id)

        if pkt_type == "vxlan_udp_chksum":
            params['inner_l4_type'] = 'UDP'
        if pkt_type == "vxlan_tcp_chksum":
            params['inner_l4_type'] = 'TCP'
        if pkt_type == "vxlan_sctp_chksum":
            params['inner_l4_type'] = 'SCTP'

        if 'chksum' in pkt_type:
            # create vxlan packet pf mac + vni=1000 + inner virtIO port0 mac
            params['outer_mac_dst'] = self.pf_mac
            params['vni'] = 1000 + vm_id
            mac_incr = 2 * vm_id + vf_id
            params['inner_mac_dst'] = self.mac_address_add(mac_incr)
            # extract reference chksum value
            vxlan_pkt = VxlanTestConfig(self, **params)
            vxlan_pkt.create_pcap()
            chksums_ref = vxlan_pkt.get_chksums()

            params['inner_ip_invalid'] = 1
            params['inner_l4_invalid'] = 1

            # create vxlan pcap file and tranfer it to tester
            vxlan_pkt = VxlanTestConfig(self, **params)
            vxlan_pkt.create_pcap(scp=True)

            # start capture
            self.start_capture(tester_iface, pkt_smac=self.pf_mac)
            vxlan_pkt.send_pcap(tester_iface)
            time.sleep(5)

            # transfer capture pcap to dts server
            pkts = self.transfer_capture_file()
            # check packet number and payload
            self.verify(len(pkts) >= 1, "Failed to capture packets")
            self.verify(pkts[0].haslayer(Vxlan) == 1,
                        "Packet not encapsulated")
            chksums = vxlan_pkt.get_chksums(pcap='vxlan_cap.pcap')
            for key in chksums_ref:
                if 'inner' in key:  # only check inner packet chksum
                    self.verify(chksums[key] == chksums_ref[key],
                                "%s not matched to %s"
                                % (key, chksums_ref[key]))

            print dts.GREEN("%s checksum pass" % params['inner_l4_type'])

        if pkt_type == "vxlan_tcp_tso":
            # create vxlan packet pf mac + vni=1000 + inner virtIO port0 mac +
            # tcp
            params['inner_l4_type'] = 'TCP'
            params['outer_mac_dst'] = self.pf_mac
            params['vni'] = 1000 + vm_id
            mac_incr = 2 * vm_id + vf_id
            params['inner_mac_dst'] = self.mac_address_add(mac_incr)
            params['payload_size'] = 892  # 256 + 256 + 256 + 124
            # extract reference chksum value
            vxlan_pkt = VxlanTestConfig(self, **params)
            vxlan_pkt.create_pcap()

            # start capture
            self.start_capture(tester_iface, pkt_smac=self.pf_mac, count=4)
            vxlan_pkt.send_pcap(tester_iface)
            time.sleep(5)

            # transfer capture pcap to dts server
            pkts = self.transfer_capture_file()
            # check packet number and payload
            self.verify(len(pkts) == 4, "Failed to capture tso packets")
            length = 0
            for pkt in pkts:
                self.verify(pkt.haslayer(Vxlan) == 1,
                            "Packet not encapsulated")
                try:
                    payload = str(pkt[UDP][Vxlan][TCP].payload)
                    self.verify(len(payload) <= self.def_mss,
                                "TCP payload oversized")
                    length += len(payload)
                except:
                    case_pass = False
                    print dts.RED("Failure in checking tso payload")

            self.verify(length == 892, "Total tcp payload size not match")
            if case_pass:
                print dts.GREEN("Vxlan packet tso pass on virtIO port %d"
                                % vf_id)

    def test_perf_vxlan_sample(self):
        # vxlan payload length for performance test
        # inner packet not contain crc, should need add four
        vxlan_payload = PACKET_LEN - HEADER_SIZE['eth'] - \
            HEADER_SIZE['ip'] - HEADER_SIZE['udp'] - \
            HEADER_SIZE['vxlan'] - HEADER_SIZE['eth'] - \
            HEADER_SIZE['ip'] - HEADER_SIZE['udp'] + 4

        vxlansample_header = ['Type', 'Queue', 'Mpps', '% linerate']
        dts.results_table_add_header(vxlansample_header)
        for perf_cfg in self.perf_cfg:
            func = perf_cfg['Func']
            if func is 'Decap':
                encap = self.FEAT_DISABLE
                decap = self.FEAT_ENABLE
                chksum = self.FEAT_DISABLE
            elif func is 'Encap':
                encap = self.FEAT_ENABLE
                decap = self.FEAT_DISABLE
                chksum = self.FEAT_DISABLE
            elif func is 'Decap&Encap':
                encap = self.FEAT_ENABLE
                decap = self.FEAT_ENABLE
                chksum = self.FEAT_DISABLE
            elif func is 'Checksum':
                encap = self.FEAT_ENABLE
                decap = self.FEAT_DISABLE
                chksum = self.FEAT_ENABLE
            elif func is 'Checksum&Decap':
                encap = self.FEAT_ENABLE
                decap = self.FEAT_ENABLE
                chksum = self.FEAT_ENABLE

            tep_cmd_temp = self.tep_app + " -c %(COREMASK)s -n %(CHANNELS)d " \
                + "--socket-mem 2048,2048 -- -p 0x1 --udp-port " \
                + "%(VXLAN_PORT)d  --nb-devices %(NB_DEVS)d --filter-type " \
                + "%(FILTERS)d --tx-checksum %(TX_CHKS)d --encap %(ENCAP)d " \
                + "--decap %(DECAP)d --rx-retry 1 --rx-retry-num 4 " \
                + "--rx-retry-delay 15"

            tep_cmd = tep_cmd_temp % {
                'COREMASK': self.coremask,
                'CHANNELS': self.dut.get_memory_channels(),
                'VXLAN_PORT': self.vxlan_port, 'NB_DEVS': 2,
                'FILTERS': self.OUTER_INNER_VNI, 'TX_CHKS': chksum,
                'ENCAP': encap, 'DECAP': decap}

            self.prepare_vxlan_sample_env(tep_cmd, vm_num=1)
            self.vm_testpmd_start(vm_id=0)

            # create vxlan packet pf mac + vni=1000 + inner virtIO port0 mac
            params = {}
            params['outer_mac_dst'] = self.pf_mac
            params['vni'] = 1000
            mac_incr = 0
            params['inner_mac_dst'] = self.mac_address_add(mac_incr)
            params['payload_size'] = vxlan_payload
            params['pcap_file'] = 'vxlan_sample.pcap'

            # create vxlan pcap file and tranfer it to tester
            vxlan_pkt = VxlanTestConfig(self, **params)
            vxlan_pkt.create_pcap(scp=False)

            if perf_cfg['VirtIO'] == "Two Ports":
                # create vxlan packet pf mac + vni=1000 + inner virtIO port0
                # mac
                params['outer_mac_dst'] = self.pf_mac
                params['vni'] = 1000
                mac_incr = 1
                params['inner_mac_dst'] = self.mac_address_add(mac_incr)
                params['pcap_file'] = 'vxlan_sample_1.pcap'

                # create vxlan pcap file and tranfer it to tester
                vxlan_pkt = VxlanTestConfig(self, **params)
                vxlan_pkt.create_pcap(scp=False)

                self.combine_pcap("vxlan_sample.pcap", "vxlan_sample_1.pcap")

            self.tester.session.copy_file_to("vxlan_sample.pcap")

            # config the flows
            tgen_input = []
            tgen_input.append((self.tester.get_local_port(self.pf),
                               self.tester.get_local_port(self.pf),
                               "vxlan_sample.pcap"))

            # run traffic generator
            _, pps = self.tester.traffic_generator_throughput(tgen_input)

            self.vm_dut.send_expect("stop", "testpmd>")
            self.vm_dut.send_expect("quit", "# ")

            pps /= 1000000.0
            perf_cfg['Mpps'] = pps
            wirespeed = self.wirespeed(self.nic, PACKET_LEN, 1)
            perf_cfg['pct'] = pps * 100 / wirespeed

            table_row = [perf_cfg['Func'], perf_cfg['VirtIO'],
                         perf_cfg['Mpps'], perf_cfg['pct']]

            dts.results_table_add_row(table_row)

            self.tear_down()

        dts.results_table_print()

    def combine_pcap(self, dest_pcap, src_pcap):
        pkts = rdpcap(dest_pcap)
        if len(pkts) != 1:
            return

        pkts_src = rdpcap(src_pcap)
        pkts += pkts_src

        wrpcap(dest_pcap, pkts)

    def tear_down(self):
        """
        Run after each test suite.
        """
        # send packet to pf, verify capture packet sent from virtIO port1
        self.clear_vxlan_sample_env()

        self.dut.kill_all()
        time.sleep(2)
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        # Restore the config file and recompile the package.
        self.dut.send_expect("sed -i -e 's/RTE_LIBRTE_VHOST=y$/"
                             + "RTE_LIBRTE_VHOST=n/' config/common_linuxapp",
                             "# ", 30)
        # temporary disable skip_setup
        skip_setup = self.dut.skip_setup
        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.target)
        self.dut.skip_setup = skip_setup
        # wait for build done
        time.sleep(20)
        pass
