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
Test userland 10Gb PMD
"""

import dts
import re
import time
from test_case import TestCase
from plotting import Plotting
from time import sleep
from settings import HEADER_SIZE
from pmd_output import PmdOutput


class TestPmd(TestCase):

    def plot_results(self, number_ports):

        cores_configs = []
        percent_values = []

        # Append the percentage results for the all the cores configs
        for test_cycle in self.test_cycles:
            cores_configs.append(test_cycle['cores'])
            config_results = []
            for frame_size in self.frame_sizes:
                config_results.append(test_cycle['pct'][frame_size])

            percent_values.append(config_results)

        image_path = self.plotting.create_bars_plot(
            'test_perf_pmd_%sports' % number_ports,
            'PMD, %d ports' % number_ports,
            self.frame_sizes,
            percent_values,
            ylabel='% linerate',
            legend=cores_configs)

        dts.results_plot_print(image_path)

    def set_up_all(self):
        """
        Run at the start of each test suite.

        PMD prerequisites.
        """
        self.frame_sizes = [64, 65, 128, 256, 512, 1024, 1280, 1518]

        self.rxfreet_values = [0, 8, 16, 32, 64, 128]

        self.test_cycles = [{'cores': '1S/1C/1T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/1C/2T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/2C/1T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/2C/2T', 'Mpps': {}, 'pct': {}},
                            {'cores': '1S/4C/2T', 'Mpps': {}, 'pct': {}}
                            ]

        self.table_header = ['Frame Size']
        for test_cycle in self.test_cycles:
            self.table_header.append("%s Mpps" % test_cycle['cores'])
            self.table_header.append("% linerate")

        self.needed_ports = {"niantic": 2,
                             "kawela_2": 2,
                             "bartonhills": 4,
                             "82545EM": 2,
                             "82540EM": 2,
                             "I217V": 1,
                             "I217LM": 1,
                             "I218V": 1,
                             "I218LM": 1}

        self.blacklist = ""

        self.verify(self.nic in ["kawela_2", "niantic", "bartonhills", "82545EM", "82540EM", "I217V", "I217LM", "I218V", "I218LM"],
                    "NIC Unsupported: " + str(self.nic))

        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports(self.nic)

        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= self.needed_ports[self.nic],
                    "Insufficient ports for speed testing")

        self.headers_size = HEADER_SIZE['eth'] + HEADER_SIZE[
            'ip'] + HEADER_SIZE['udp']

        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.plotting = Plotting(self.dut.crb['name'], self.target, self.nic)

        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_perf_pmd_performance_4ports(self):
        """
        PMD Performance Benchmarking with 4 ports.
        """
        all_cores_mask = dts.create_mask(self.dut.get_core_list("all"))

        # prepare traffic generator input
        self.verify(len(self.dut_ports) >= 4,
                    "Insufficient ports for 4 ports performance")
        tgen_input = []

        tgen_input.append((self.tester.get_local_port(self.dut_ports[0]),
                           self.tester.get_local_port(self.dut_ports[1]),
                           "test.pcap"))
        tgen_input.append((self.tester.get_local_port(self.dut_ports[2]),
                           self.tester.get_local_port(self.dut_ports[3]),
                           "test.pcap"))
        tgen_input.append((self.tester.get_local_port(self.dut_ports[1]),
                           self.tester.get_local_port(self.dut_ports[0]),
                           "test.pcap"))
        tgen_input.append((self.tester.get_local_port(self.dut_ports[3]),
                           self.tester.get_local_port(self.dut_ports[2]),
                           "test.pcap"))

        # run testpmd for each core config
        for test_cycle in self.test_cycles:
            core_config = test_cycle['cores']

            core_list = self.dut.get_core_list(core_config,
                                               socket=self.ports_socket)

            if len(core_list) > 4:
                queues = len(core_list) / 4
            else:
                queues = 1

            core_mask = dts.create_mask(core_list)
            port_mask = dts.create_mask(self.dut.get_ports(self.nic))

            self.pmdout.start_testpmd("all", "--coremask=%s --rxq=%d --txq=%d --portmask=%s" % (core_mask, queues, queues, port_mask))

            info = "Executing PMD (mac fwd) using %s\n" % test_cycle['cores']
            dts.report(info, annex=True)
            self.logger.info(info)

            dts.report(commandLine + "\n\n", frame=True, annex=True)

            # self.dut.send_expect("set fwd mac", "testpmd> ", 100)
            self.dut.send_expect("start", "testpmd> ")

            for frame_size in self.frame_sizes:
                wirespeed = self.wirespeed(self.nic, frame_size, 4)

                # create pcap file
                self.logger.info("Running with frame size %d " % frame_size)
                payload_size = frame_size - self.headers_size
                self.tester.scapy_append(
                    'wrpcap("test.pcap", [Ether(src="52:00:00:00:00:00")/IP()/UDP()/("X"*%d)])' % payload_size)
                self.tester.scapy_execute()

                # run traffic generator
                _, pps = self.tester.traffic_generator_throughput(tgen_input)

                pps /= 1000000.0
                test_cycle['Mpps'][frame_size] = pps
                test_cycle['pct'][frame_size] = pps * 100 / wirespeed

            self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("quit", "# ", 30)
            sleep(5)

        for n in range(len(self.test_cycles)):
            for frame_size in self.frame_sizes:
                self.verify(self.test_cycles[n]['Mpps'][
                            frame_size] is not 0, "No traffic detected")

        # Print results
        dts.results_table_add_header(self.table_header)

        for frame_size in self.frame_sizes:
            table_row = [frame_size]

            for test_cycle in self.test_cycles:
                table_row.append(test_cycle['Mpps'][frame_size])
                table_row.append(test_cycle['pct'][frame_size])

            dts.results_table_add_row(table_row)

        self.plot_results(number_ports=4)
        dts.results_table_print()

    def test_perf_pmd_performance_2ports(self):
        """
        PMD Performance Benchmarking with 2 ports.
        """

        all_cores_mask = dts.create_mask(self.dut.get_core_list("all"))

        # prepare traffic generator input
        tgen_input = []
        tgen_input.append((self.tester.get_local_port(self.dut_ports[0]),
                           self.tester.get_local_port(self.dut_ports[1]),
                           "test.pcap"))
        tgen_input.append((self.tester.get_local_port(self.dut_ports[1]),
                           self.tester.get_local_port(self.dut_ports[0]),
                           "test.pcap"))

        # run testpmd for each core config
        for test_cycle in self.test_cycles:
            core_config = test_cycle['cores']

            core_list = self.dut.get_core_list(core_config,
                                               socket=self.ports_socket)

            if len(core_list) > 2:
                queues = len(core_list) / 2
            else:
                queues = 1

            core_mask = dts.create_mask(core_list)
            port_mask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])

            self.pmdout.start_testpmd("all", "--coremask=%s --rxq=%d --txq=%d --portmask=%s" % (core_mask, queues, queues, port_mask))
            command_line = self.pmdout.get_pmd_cmd()

            info = "Executing PMD using %s\n" % test_cycle['cores']
            self.logger.info(info)
            dts.report(info, annex=True)
            dts.report(command_line + "\n\n", frame=True, annex=True)

            self.dut.send_expect("start", "testpmd> ")
            for frame_size in self.frame_sizes:
                wirespeed = self.wirespeed(self.nic, frame_size, 2)

                # create pcap file
                self.logger.info("Running with frame size %d " % frame_size)
                payload_size = frame_size - self.headers_size
                self.tester.scapy_append(
                    'wrpcap("test.pcap", [Ether(src="52:00:00:00:00:00")/IP()/UDP()/("X"*%d)])' % payload_size)
                self.tester.scapy_execute()

                # run traffic generator
                _, pps = self.tester.traffic_generator_throughput(tgen_input)

                pps /= 1000000.0
                test_cycle['Mpps'][frame_size] = pps
                test_cycle['pct'][frame_size] = pps * 100 / wirespeed

            self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("quit", "# ", 30)
            sleep(5)

        for n in range(len(self.test_cycles)):
            for frame_size in self.frame_sizes:
                self.verify(self.test_cycles[n]['Mpps'][
                            frame_size] > 0, "No traffic detected")

        # Print results
        dts.results_table_add_header(self.table_header)
        for frame_size in self.frame_sizes:
            table_row = [frame_size]
            for test_cycle in self.test_cycles:
                table_row.append(test_cycle['Mpps'][frame_size])
                table_row.append(test_cycle['pct'][frame_size])

            dts.results_table_add_row(table_row)

        self.plot_results(number_ports=2)
        dts.results_table_print()

    def test_checksum_checking(self):
        """
        Packet forwarding checking test
        """

        self.dut.kill_all()

        all_cores_mask = dts.create_mask(self.dut.get_core_list("all"))
        core_mask = dts.create_mask(self.dut.get_core_list('1S/1C/1T',
                                                           socket=self.ports_socket))
        port_mask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])

        for rxfreet_value in self.rxfreet_values:

            self.pmdout.start_testpmd("all", "--coremask=%s --portmask=%s --nb-cores=2 --enable-rx-cksum --disable-hw-vlan --disable-rss --crc-strip --rxd=1024 --txd=1024 --rxfreet=%d" % (core_mask, port_mask, rxfreet_value))
            self.dut.send_expect("set fwd csum", "testpmd> ")
            self.dut.send_expect("start", "testpmd> ")

            self.send_packet(self.frame_sizes[0], checksum_test=True)

            l4csum_error = self.stop_and_get_l4csum_errors()

            # Check the l4 checksum errors reported for Rx port
            self.verify(1 == int(l4csum_error[1]),
                        "Wrong l4 checksum error count using rxfreet=%d (expected 1, reported %s)" %
                        (rxfreet_value, l4csum_error[1]))

            self.dut.send_expect("quit", "# ", 30)
            sleep(5)

    def test_packet_checking(self):
        """
        Packet forwarding checking test
        """

        self.dut.kill_all()

        all_cores_mask = dts.create_mask(self.dut.get_core_list("all"))
        core_mask = dts.create_mask(self.dut.get_core_list('1S/1C/1T',
                                                           socket=self.ports_socket))
        port_mask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])

        self.pmdout.start_testpmd("all", "--coremask=%s --portmask=%s" % (core_mask, port_mask))
        self.dut.send_expect("start", "testpmd> ")
        for size in self.frame_sizes:
            self.send_packet(size)

        self.dut.send_expect("stop", "testpmd> ")
        self.dut.send_expect("quit", "# ", 30)
        sleep(5)

    def stop_and_get_l4csum_errors(self):
        """
        Stop forwarding and get Bad-l4csum number from stop statistic
        """

        out = self.dut.send_expect("stop", "testpmd> ")
        result_scanner = r"Bad-l4csum: ([0-9]+) \s*"
        scanner = re.compile(result_scanner, re.DOTALL)
        m = scanner.findall(out)

        return m

    def get_stats(self, portid):
        """
        Get packets number from port statistic
        """

        stats = self.pmdout.get_pmd_stats(portid)
        return stats

    def send_packet(self, frame_size, checksum_test=False):
        """
        Send 1 packet to portid
        """

        port0_stats = self.get_stats(self.dut_ports[0])
        gp0tx_pkts, gp0tx_bytes = [port0_stats['TX-packets'], port0_stats['TX-bytes']]
        port1_stats = self.get_stats(self.dut_ports[1])
        gp1rx_pkts, gp1rx_err, gp1rx_bytes = [port1_stats['RX-packets'], port1_stats['RX-errors'], port1_stats['RX-bytes']]

        interface = self.tester.get_interface(
            self.tester.get_local_port(self.dut_ports[1]))
        mac = self.dut.get_mac_address(self.dut_ports[1])

        load_size = frame_size - HEADER_SIZE['eth']
        padding = frame_size - HEADER_SIZE['eth'] - HEADER_SIZE['ip'] - \
            HEADER_SIZE['udp']

        checksum = ''
        if checksum_test:
            checksum = 'chksum=0x0'

        self.tester.scapy_foreground()
        self.tester.scapy_append('nutmac="%s"' % mac)
        self.tester.scapy_append('sendp([Ether(dst=nutmac, src="52:00:00:00:00:00")/IP(len=%s)/UDP(%s)/Raw(load="\x50"*%s)], iface="%s")' % (
            load_size, checksum, padding, interface))

        out = self.tester.scapy_execute()
        time.sleep(.5)

        port0_stats = self.get_stats(self.dut_ports[0])
        p0tx_pkts, p0tx_bytes = [port0_stats['TX-packets'], port0_stats['TX-bytes']]
        port1_stats = self.get_stats(self.dut_ports[1])
        p1rx_pkts, p1rx_err, p1rx_bytes = [port1_stats['RX-packets'], port1_stats['RX-errors'], port1_stats['RX-bytes']]

        p0tx_pkts -= gp0tx_pkts
        p0tx_bytes -= gp0tx_bytes
        p1rx_pkts -= gp1rx_pkts
        p1rx_bytes -= gp1rx_bytes
        p1rx_err -= gp1rx_err

        time.sleep(5)

        self.verify(p0tx_pkts == p1rx_pkts,
                    "packet pass assert error, %d RX packets, %d TX packets" % (p1rx_pkts, p0tx_pkts))

        if checksum_test:
            self.verify(p1rx_bytes == frame_size - 4,
                        "packet pass assert error, expected %d RX bytes, actual %d" % (frame_size - 4, p1rx_bytes))
        else:
            self.verify(p1rx_bytes == frame_size,
                        "packet pass assert error, expected %d RX bytes, actual %d" % (frame_size, p1rx_bytes))

        self.verify(p0tx_bytes == frame_size,
                    "packet pass assert error, expected %d TX bytes, actual %d" % (frame_size, p0tx_bytes))

        return out

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
