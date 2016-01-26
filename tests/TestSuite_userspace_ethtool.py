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
Test support of userspace ethtool feature
"""

import dts
import time
import re
from test_case import TestCase
from pmd_output import PmdOutput
from packet import Packet, sniff_packets, load_sniff_packets
import random
from etgen import IxiaPacketGenerator
from settings import HEADER_SIZE
from settings import SCAPY2IXIA


class TestUserspaceEthtool(TestCase, IxiaPacketGenerator):

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.ports = self.dut.get_ports()
        self.verify(len(self.ports) >= 2, "No ports found for " + self.nic)

        # build sample app
        out = self.dut.send_expect("make -C examples/ethtool", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        path = "./examples/ethtool/ethtool-app/ethtool-app/%s/ethtool" % self.target
        self.cmd = "%s -c f -n %d" % (path, self.dut.get_memory_channels())

        # pause frame basic configuration
        self.pause_time = 65535
        self.frame_size = 64
        self.pause_rate = 0.50

        # update IxiaPacketGenerator function from local
        self.tester.extend_external_packet_generator(TestUserspaceEthtool, self)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def build_ethtool(self):
        out = self.dut.send_expect("make -C examples/ethtool", "# ")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

    def strip_portstats(self, portid):
        out = self.dut.send_expect("portstats %d " % portid, "EthApp>")
        stats_pattern = r"portstats (\d)(\s+)Port (\d+) stats(\s+)In: (\d+)" \
            " \((\d+) bytes\)(\s+)Out: (\d+) \((\d+) bytes\)" \
            "(\s+)Err: (\d+)"

        m = re.match(stats_pattern, out)
        if m:
            return (int(m.group(5)), int(m.group(8)))
        else:
            return (0, 0)

    def strip_ringparam(self, portid):
        out = self.dut.send_expect("ringparam %d" % portid, "EthApp>")
        ring_pattern = r"ringparam (\d)(\s+)Port (\d+) ring parameters(\s+)" \
            "Rx Pending: (\d+) \((\d+) max\)(\s+)Tx Pending: " \
            "(\d+) \((\d+) max\)"
        m = re.match(ring_pattern, out)
        if m:
            return (int(m.group(5)), int(m.group(6)), int(m.group(8)),
                    int(m.group(9)))
        else:
            return (0, 0, 0, 0)

    def strip_mac(self, portid):
        out = self.dut.send_expect("macaddr %d" % portid, "EthApp>")
        mac_pattern = r"macaddr (\d+)(\s+)Port (\d+) MAC Address: (.*)"
        m = re.match(mac_pattern, out)
        if m:
            return m.group(4)
        else:
            return "00:00:00:00:00:00"

    def strip_mtu(self, intf):
        """
        Strip tester port mtu
        """
        link_info = self.tester.send_expect("ip link show %s" % intf, "# ")
        mtu_pattern = r".* mtu (\d+) .*"
        m = re.match(mtu_pattern, link_info)
        if m:
            return int(m.group(1))
        else:
            return 1518

    def strip_md5(self, filename):
        md5_info = self.dut.send_expect("md5sum %s" % filename, "# ")
        md5_pattern = r"(\w+)  (\w+)"
        m = re.match(md5_pattern, md5_info)
        if m:
            return m.group(1)
        else:
            return ""

    def test_dump_driver_info(self):
        """
        Test ethtool can dump basic information
        """
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        out = self.dut.send_expect("drvinfo", "EthApp>")
        driver_pattern = r"Port (\d+) driver: rte_(.*)_pmd \(ver: RTE (.*)\)"
        driver_infos = out.split("\r\n")
        self.verify(len(driver_infos) > 1, "Userspace tool failed to dump driver infor")

        # check dump driver info function
        for driver_info in driver_infos:
            m = re.match(driver_pattern, driver_info)
            if m:
                port = m.group(1)
                driver = m.group(2)
                version = m.group(3)
                print dts.GREEN("Detect port %s with %s driver\n" % (port, driver))

        # check link status dump function
        for port in self.ports:
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            self.tester.send_expect("ip link set dev %s down" % intf, "# ")
        # wait for link stable
        time.sleep(5)

        out = self.dut.send_expect("link", "EthApp>", 60)
        link_pattern = r"Port (\d+): (.*)"
        link_infos = out.split("\r\n")
        for link_info in link_infos:
            m = re.match(link_pattern, link_info)
            if m:
                port = m.group(1)
                status = m.group(2)
                self.verify(status == "Down", "Userspace tool failed to detect link down")

        for port in self.ports:
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            self.tester.send_expect("ip link set dev %s up" % intf, "# ")
        # wait for link stable
        time.sleep(5)

        # check port stats function
        pkt = Packet(pkt_type='UDP')
        for port in self.ports:
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            ori_rx_pkts, ori_tx_pkts = self.strip_portstats(port)
            pkt.send_pkt(tx_port=intf)
            time.sleep(1)
            rx_pkts, tx_pkts = self.strip_portstats(port)
            self.verify((rx_pkts == (ori_rx_pkts + 1)), "Failed to record Rx/Tx packets")

        self.dut.send_expect("quit", "# ")

    def test_retrieve_reg(self):
        """
        Test ethtool app can retrieve port register
        """
        self.dut.send_expect(self.cmd, "EthApp>", 60)

        portsinfo = []
        ori_drivers = []

        for portid in range(len(self.ports)):
            self.dut.send_expect("regs %d regs_%d.bin" % (portid, portid), "EthApp>")
            portinfo = {'portid': portid, 'reg_file': 'regs_%d.bin' % portid}
            portsinfo.append(portinfo)

        self.dut.send_expect("quit", "# ")

        for index in range(len(self.ports)):
            port = self.ports[index]
            netdev = self.dut.ports_info[port]['port']
            portinfo = portsinfo[index]
            # strip orignal driver
            portinfo['ori_driver'] = netdev.get_nic_driver()
            portinfo['net_dev'] = netdev
            # bind to default driver
            netdev.bind_driver()
            # get linux interface
            intf = netdev.get_interface_name()
            out = self.dut.send_expect("ethtool -d %s raw off file %s" % (intf, portinfo['reg_file']), "# ")
            self.verify(("LINKS" in out and "FCTRL" in out), "Failed to dump %s registers" % intf)

        for index in range(len(self.ports)):
            # bind to original driver
            portinfo = portsinfo[index]
            portinfo['net_dev'].bind_driver(portinfo['ori_driver'])

    def test_retrieve_eeprom(self):
        """
        Test ethtool app dump eeprom function
        """
        # require md5sum to check file
        out = self.dut.send_expect("whereis md5sum", "# ")
        self.verify("/usr/bin/md5sum" in out, "This case required md5sum installed on DUT")

        self.dut.send_expect(self.cmd, "EthApp>", 60)

        portsinfo = []
        ori_drivers = []

        for portid in range(len(self.ports)):
            # dump eemprom by userspace ethtool
            self.dut.send_expect("eeprom %d eeprom_%d.bin" % (portid, portid), "EthApp>")
            portinfo = {'portid': portid, 'eeprom_file': 'eeprom_%d.bin' % portid}
            portsinfo.append(portinfo)

        self.dut.send_expect("quit", "# ")

        for index in range(len(self.ports)):
            port = self.ports[index]
            netdev = self.dut.ports_info[port]['port']
            portinfo = portsinfo[index]
            # strip orignal driver
            portinfo['ori_driver'] = netdev.get_nic_driver()
            portinfo['net_dev'] = netdev
            # bind to default driver
            netdev.bind_driver()
            # get linux interface
            intf = netdev.get_interface_name()
            ethtool_eeprom = "ethtool_eeprom_%d.bin" % index
            # dump eemprom by linux ethtool
            self.dut.send_expect("ethtool --eeprom-dump %s raw on > %s" % (intf, ethtool_eeprom), "# ")
            # wait for file ready
            time.sleep(2)
            portinfo['ethtool_eeprom'] = ethtool_eeprom
            # bind to original driver
            portinfo['net_dev'].bind_driver(portinfo['ori_driver'])

        for index in range(len(self.ports)):
            md5 = self.strip_md5(portsinfo[index]['eeprom_file'])
            md5_ref = self.strip_md5(portsinfo[index]['ethtool_eeprom'])
            print dts.GREEN("Reference eeprom md5 %s" % md5_ref)
            self.verify(md5 == md5_ref, "Dumped eeprom not same as linux dumped")

    def test_ring_parameter(self):
        """
        Test ethtool app ring parameter getting and setting
        """
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        for index in range(len(self.ports)):
            port = self.ports[index]
            ori_rx_pkts, ori_tx_pkts = self.strip_portstats(port)
            _, rx_max, _, tx_max = self.strip_ringparam(index)
            self.dut.send_expect("ringparam %d %d %d" % (index, rx_max, tx_max), "EthApp>")
            rx_ring, _, tx_ring, _ = self.strip_ringparam(index)
            self.verify(rx_ring == rx_max, "Userspace tool failed to set Rx ring parameter")
            self.verify(tx_ring == tx_max, "Userspace tool failed to set Tx ring parameter")
            pkt = Packet()
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            pkt.send_pkt(tx_port=intf)
            rx_pkts, tx_pkts = self.strip_portstats(index)
            self.verify(rx_pkts == ori_rx_pkts + 1, "Failed to forward after ring parameter changed")

        self.dut.send_expect("quit", "# ")

    def test_ethtool_vlan(self):
        """
        Test ethtool app vlan add and delete
        """
        main_file = "examples/ethtool/ethtool-app/main.c"
        # enable vlan filter
        self.dut.send_expect("sed -i -e '/cfg_port.txmode.mq_mode = ETH_MQ_TX_NONE;$/a\\cfg_port.rxmode.hw_vlan_filter=1;' %s" % main_file, "# ")

        # build sample app
        self.build_ethtool()

        self.dut.send_expect(self.cmd, "EthApp>", 60)
        for index in range(len(self.ports)):
            port = self.ports[index]
            # generate random vlan
            vlan = random.randrange(0, 4095)
            # add vlan on port, record original statistic
            self.dut.send_expect("vlan %d add %d" % (index, vlan), "EthApp>")
            ori_rx_pkts, ori_tx_pkts = self.strip_portstats(port)

            # send correct vlan packet to port
            pkt = Packet(pkt_type='VLAN_UDP')
            pkt.config_layer('dot1q', {'vlan': vlan})
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            pkt.send_pkt(tx_port=intf)
            time.sleep(2)
            rx_pkts, tx_pkts = self.strip_portstats(port)
            self.verify(rx_pkts == ori_rx_pkts + 1, "Failed to Rx vlan packet")
            self.verify(tx_pkts == ori_tx_pkts + 1, "Failed to Tx vlan packet")

            # send incorrect vlan packet to port
            wrong_vlan = (vlan + 1) % 4096
            pkt.config_layer('dot1q', {'vlan': wrong_vlan})
            pkt.send_pkt(tx_port=intf)
            time.sleep(2)
            rx_pkts_wrong, _ = self.strip_portstats(port)
            self.verify(rx_pkts_wrong == rx_pkts, "Failed to filter Rx vlan packet")

            # remove vlan
            self.dut.send_expect("vlan %d del %d" % (index, vlan), "EthApp>")
            # send same packet and make sure not received
            pkt.config_layer('dot1q', {'vlan': vlan})
            pkt.send_pkt(tx_port=intf)
            time.sleep(2)
            rx_pkts_del, _ = self.strip_portstats(port)
            self.verify(rx_pkts_del == rx_pkts, "Failed to remove Rx vlan filter")

        self.dut.send_expect("quit", "# ")
        self.dut.send_expect("sed -i -e '/hw_vlan_filter=1;$/d' %s" % main_file, "# ")
        # build sample app
        self.build_ethtool()

    def test_mac_address(self):
        """
        Test ethtool app mac function
        """
        valid_mac = "00:10:00:00:00:00"
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        for index in range(len(self.ports)):
            port = self.ports[index]
            mac = self.dut.ports_info[port]['mac']
            dump_mac = self.strip_mac(index)
            self.verify(mac == dump_mac, "Userspace tool failed to dump mac")
            self.dut.send_expect("macaddr %d %s" % (port, valid_mac), "EthApp>")
            dump_mac = self.strip_mac(index)
            self.verify(dump_mac == valid_mac, "Userspace tool failed to set mac")
            # check forwarded mac has been changed
            pkt = Packet()
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            # send and sniff packet
            inst = sniff_packets(intf, timeout=5)
            pkt.send_pkt(tx_port=intf)
            pkts = load_sniff_packets(inst)
            self.verify(len(pkts) == 2, "Packet not forwarded as expected")
            src_mac = pkts[1].strip_layer_element("layer2", "src")
            self.verify(src_mac == valid_mac, "Forwarded packet not match default mac")

        # check multicase will not be valid mac
        invalid_mac = "01:00:00:00:00:00"
        out = self.dut.send_expect("validate %s" % invalid_mac, "EthApp>")
        self.verify("not unicast" in out, "Failed to detect incorrect unicast mac")
        invalid_mac = "00:00:00:00:00:00"
        out = self.dut.send_expect("validate %s" % invalid_mac, "EthApp>")
        self.verify("not unicast" in out, "Failed to detect incorrect unicast mac")
        out = self.dut.send_expect("validate %s" % valid_mac, "EthApp>")
        self.verify("is unicast" in out, "Failed to detect correct unicast mac")
        self.dut.send_expect("quit", "# ")

    def test_port_config(self):
        """
        Test ethtool app port configure
        """
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        for index in range(len(self.ports)):
            port = self.ports[index]
            ori_rx_pkts, _ = self.strip_portstats(index)
            # stop port
            self.dut.send_expect("stop %d" % index, "EthApp>")
            # check packet not forwarded when port is stop
            pkt = Packet()
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            pkt.send_pkt(tx_port=intf)
            rx_pkts, tx_pkts = self.strip_portstats(index)
            self.verify(rx_pkts == ori_rx_pkts, "Failed to stop port")
            # restart port and check packet can normally forwarded
            self.dut.send_expect("open %d" % index, "EthApp>")
            # wait few time for port ready
            time.sleep(0.5)
            pkt.send_pkt(tx_port=intf)
            rx_pkts_open, tx_pkts_open = self.strip_portstats(index)
            self.verify(rx_pkts_open == rx_pkts + 1, "Failed to reopen port rx")
            self.verify(tx_pkts_open == tx_pkts + 1, "Failed to reopen port tx")

        self.dut.send_expect("quit", "# ")

    def test_port_mtu(self):
        """
        Test ethtool app port mtu configure
        """
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        mtus = [1519, 2048]
        for index in range(len(self.ports)):
            port = self.ports[index]
            # change mtu
            tester_port = self.tester.get_local_port(port)
            intf = self.tester.get_interface(tester_port)
            ori_mtu = self.strip_mtu(intf)
            self.tester.send_expect("ifconfig %s mtu 9000" % (intf), "# ")
            for mtu in mtus:
                self.dut.send_expect("mtu %d %d" % (index, mtu), "EthApp>")
                pkt_size = mtu + HEADER_SIZE['eth']
                pkt = Packet(pkt_len=pkt_size)
                pkt.send_pkt(tx_port=intf)
                rx_pkts, _ = self.strip_portstats(index)
                self.verify(rx_pkts == 1, "Packet match mtu not forwarded as expected")
                pkt = Packet(pkt_len=mtu + 1)
                pkt.send_pkt(tx_port=intf)
                rx_pkts_over, _ = self.strip_portstats(index)
                self.verify(rx_pkts == rx_pkts_over, "Packet over mtu should not be forwarded")

            self.tester.send_expect("ifconfig %s mtu %d" % (intf, ori_mtu), "# ")

        self.dut.send_expect("quit", "# ")

    def test_perf_port_rx_pause(self):
        """
        Test ethtool app flow control configure
        """
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        # enable pause rx
        self.dut.send_expect("pause 0 rx", "EthApp")

        # calculate number of packets
        pps = self.wirespeed(self.nic, self.frame_size, 1) * 1000000.0
        # get line rate
        linerate = pps * (self.frame_size + 20) * 8
        # calculate default sleep time for one pause frame
        sleep = (1 / linerate) * self.pause_time * 512
        # calculate packets dropped in sleep time
        self.n_pkts = int((sleep / (1 / pps)) * (1 / self.pause_rate))

        tgen_input = []
        headers_size = HEADER_SIZE['eth'] + HEADER_SIZE['ip'] + \
            HEADER_SIZE['udp']
        payload_size = self.frame_size - headers_size
        self.tester.scapy_append('wrpcap("pause_rx.pcap", [Ether()/IP()/UDP()/("X"*%d)])' % payload_size)
        self.tester.scapy_execute()
        # rx and tx is the same port
        tester_port = self.tester.get_local_port(self.ports[0])
        tgen_input.append((tester_port, tester_port, "pause_rx.pcap"))

        ori_func = self.config_stream
        self.config_stream = self.config_stream_pause_rx
        _, rx_pps = self.tester.traffic_generator_throughput(tgen_input)
        self.config_stream = ori_func

        rate = rx_pps / pps
        # rate should same as expected rate
        self.verify(rate > (self.pause_rate - 0.01) and
                    rate < (self.pause_rate + 0.01), "Failed to handle Rx pause frame")

        self.dut.send_expect("quit", "# ")

    def test_perf_port_tx_pause(self):
        """
        Test ethtool app flow control configure
        """
        # sleep a while when receive packets
        main_file = "examples/ethtool/ethtool-app/main.c"
        self.dut.send_expect("sed -i -e '/if (cnt_recv_frames > 0) {$/i\usleep(10);' %s" % main_file, "# ")
        # build sample app
        self.build_ethtool()
        self.dut.send_expect(self.cmd, "EthApp>", 60)
        # enable pause tx
        self.dut.send_expect("pause 0 tx", "EthApp")

        tgen_input = []
        headers_size = HEADER_SIZE['eth'] + HEADER_SIZE['ip'] + \
            HEADER_SIZE['udp']
        payload_size = self.frame_size - headers_size
        self.tester.scapy_append('wrpcap("pause_tx.pcap", [Ether()/IP()/UDP()/("X"*%d)])' % payload_size)
        self.tester.scapy_execute()
        # rx and tx is the same port
        tester_port = self.tester.get_local_port(self.ports[0])
        tgen_input.append((tester_port, tester_port, "pause_tx.pcap"))

        self.wirespeed(self.nic, self.frame_size, 1) * 1000000.0
        _, tx_pps = self.tester.traffic_generator_throughput(tgen_input)

        # verify ixia transmit line rate dropped
        pps = self.wirespeed(self.nic, self.frame_size, 1) * 1000000.0
        rate = tx_pps / pps
        self.verify(rate < 0.1, "Failed to slow down transmit speed")

        # verify received packets more than sent
        self.stat_get_stat_all_stats(tester_port)
        sent_pkts = self.get_frames_sent()
        recv_pkts = self.get_frames_received()
        self.verify((float(recv_pkts) / float(sent_pkts)) > 1.05, "Failed to transmit pause frame")

        self.dut.send_expect("quit", "# ")
        self.dut.send_expect("sed -i -e '/usleep(10);$/d' %s" % main_file, "# ")
        # rebuild sample app
        self.build_ethtool()

    def config_stream_pause_rx(self, fpcap, txport, rate_percent, stream_id=1, latency=False):
        """
        Configure IXIA stream with pause frame and normal packet
        """
        # enable flow control on port
        self.add_tcl_cmd("port config -flowControl true")
        self.add_tcl_cmd("port config -flowControlType ieee8023x")
        self.add_tcl_cmd("port set %d %d %d" % (self.chasId, txport['card'], txport['port']))

        flows = self.parse_pcap(fpcap)

        self.add_tcl_cmd("ixGlobalSetDefault")
        self.add_tcl_cmd("stream config -rateMode usePercentRate")
        self.add_tcl_cmd("stream config -percentPacketRate 100")
        self.add_tcl_cmd("stream config -numBursts 1")
        self.add_tcl_cmd("stream config -numFrames %d" % self.n_pkts)
        self.add_tcl_cmd("stream config -dma advance")

        pat = re.compile(r"(\w+)\((.*)\)")
        for header in flows[0].split('/'):
            match = pat.match(header)
            params = eval('dict(%s)' % match.group(2))
            method_name = match.group(1)
            if method_name in SCAPY2IXIA:
                method = getattr(self, method_name.lower())
                method(txport, **params)

        # stream id start from 1
        self.add_tcl_cmd("stream set %d %d %d %d" % (self.chasId, txport['card'], txport['port'], 1))

        # pause frame stream
        self.add_tcl_cmd("stream config -rateMode usePercentRate")
        self.add_tcl_cmd("stream config -percentPacketRate 100")
        self.add_tcl_cmd("stream config -numBursts 1")
        self.add_tcl_cmd("stream config -numFrames 1")
        self.add_tcl_cmd("stream config -dma gotoFirst")

        self.add_tcl_cmd("protocol setDefault")
        self.add_tcl_cmd("protocol config -name pauseControl")
        self.add_tcl_cmd("pauseControl setDefault")
        self.add_tcl_cmd("pauseControl config -da \"01 80 C2 00 00 01\"")
        self.add_tcl_cmd("pauseControl config -pauseTime %d" % self.pause_time)
        self.add_tcl_cmd("pauseControl config -pauseControlType ieee8023x")
        self.add_tcl_cmd("pauseControl set %d %d %d" % (self.chasId, txport['card'], txport['port']))
        self.add_tcl_cmd("stream set %d %d %d %d" %
                         (self.chasId, txport['card'], txport['port'], 2))

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
