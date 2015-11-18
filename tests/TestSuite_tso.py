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

Tests for TSO.

"""

import dts
import time
import re
from test_case import TestCase
from plotting import Plotting
from settings import HEADER_SIZE


class TestTSO(TestCase):
    dut_ports = []
    #
    #
    # Utility methods and other non-test code.
    #

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
        """
        # this feature support Fortville, Niantic
        self.verify(self.nic in ["kawela_2", "niantic", "bartonhills", "82545EM",
                                 "82540EM", "springfountain", "fortville_eagle",
                                 "fortville_spirit", "fortville_spirit_single"],
                    "NIC Unsupported: " + str(self.nic))

        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports(self.nic)

        # Verify that enough ports are available
        self.verify(len(self.dut_ports) >= 2, "Insufficient ports for testing")

        # Verify that enough threads are available
        self.all_cores_mask = dts.create_mask(self.dut.get_core_list("all"))
        self.portMask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])
        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.frame_sizes = [128, 1458]
        self.rxfreet_values = [0, 8, 16, 32, 64, 128]

        # self.test_cycles = [{'cores': '1S/1C/1T', 'Mpps': {}, 'pct': {}},
        #                     {'cores': '1S/1C/2T', 'Mpps': {}, 'pct': {}},
        #                     {'cores': '1S/2C/1T', 'Mpps': {}, 'pct': {}},
        #                     {'cores': '1S/2C/2T', 'Mpps': {}, 'pct': {}},
        #                     {'cores': '1S/4C/2T', 'Mpps': {}, 'pct': {}}
        #                     ]
        self.test_cycles = [{'cores': '1S/1C/2T', 'Mpps': {}, 'pct': {}}]

        self.table_header = ['Frame Size']
        for test_cycle in self.test_cycles:
            self.table_header.append("%s Mpps" % test_cycle['cores'])
            self.table_header.append("% linerate")

        self.blacklist = ""

        # self.coreMask = dts.create_mask(cores)

        self.headers_size = HEADER_SIZE['eth'] + HEADER_SIZE[
            'ip'] + HEADER_SIZE['tcp']

        self.plotting = Plotting(self.dut.crb['name'], self.target, self.nic)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def tcpdump_start_sniffing(self, ifaces=[]):
        """
        Starts tcpdump in the background to sniff the tester interface where
        the packets are transmitted to and from the self.dut.
        All the captured packets are going to be stored in a file for a
        post-analysis.
        """

        for iface in ifaces:
            command = ('tcpdump -w tcpdump_{0}.pcap -i {0} 2>tcpdump_{0}.out &').format(iface)
            self.tester.send_expect('rm -f tcpdump_{0}.pcap', '#').format(iface)
            self.tester.send_expect(command, '#')

    def tcpdump_stop_sniff(self):
        """
        Stops the tcpdump process running in the background.
        """
        self.tester.send_expect('killall tcpdump', '#')
        time.sleep(1)
        self.tester.send_expect('echo "Cleaning buffer"', '#')
        time.sleep(1)

    def tcpdump_command(self, command):
        """
        Sends a tcpdump related command and returns an integer from the output
        """

        result = self.tester.send_expect(command, '#')
        print result
        return int(result.strip())

    def number_of_packets(self, iface):
        """
        By reading the file generated by tcpdump it counts how many packets were
        forwarded by the sample app and received in the self.tester. The sample app
        will add a known MAC address for the test to look for.
        """

        command = ('tcpdump -A -nn -e -v -r tcpdump_{iface}.pcap 2>/dev/null | ' +
                   'grep -c "seq"')
        return self.tcpdump_command(command.format(**locals()))

    def test_tso(self):
        """
        TSO IPv4 TCP, IPv6 TCP, VXLan testing
        """
        tx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))
        rx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1]))

        mac = self.dut.get_mac_address(self.dut_ports[0])
        cores = self.dut.get_core_list("1S/2C/2T")
        self.verify(cores is not None, "Insufficient cores for speed testing")
        self.coreMask = dts.create_mask(cores)

        padding = self.frame_sizes[0] - self.headers_size

        self.tester.send_expect("ethtool -K %s rx off tx off tso off gso off gro off lro off" % tx_interface, "# ")
        self.tester.send_expect("ip l set %s up" % tx_interface, "# ")

        cmd = "./%s/app/testpmd -c %s -n %d %s -- -i --rxd=512 --txd=512 --burst=32 --rxfreet=64 --mbcache=128 --portmask=%s --txpt=36 --txht=0 --txwt=0 --txfreet=32 --txrst=32 --txqflags=0 " % (self.target, self.coreMask, self.dut.get_memory_channels(), self.blacklist, self.portMask)
        self.dut.send_expect(cmd, "testpmd> ", 120)
        self.dut.send_expect("set verbose 1", "testpmd> ", 120)
        self.dut.send_expect("csum set ip hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set udp hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set tcp hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set sctp hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set outer-ip hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum parse_tunnel on %d" % self.dut_ports[0], "testpmd> ", 120)

        self.dut.send_expect("csum set ip hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set udp hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set tcp hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set sctp hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set outer-ip hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum parse_tunnel on %d" % self.dut_ports[1], "testpmd> ", 120)

        self.dut.send_expect("tso set 800 %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("set fwd csum", "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        self.tester.scapy_foreground()
        time.sleep(5)

        # IPv4 tcp test

        self.tcpdump_start_sniffing([tx_interface, rx_interface])
        self.tester.scapy_append('sendp([Ether(dst="%s",src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/TCP(sport=1021,dport=1021)/("X"*%s)], iface="%s")' % (mac, padding, tx_interface))
        out = self.tester.scapy_execute()
        out = self.dut.send_expect("show port stats all", "testpmd> ", 120)
        print out
        self.tcpdump_stop_sniff()
        rx_stats = self.number_of_packets(rx_interface)
        if (rx_stats == 2):
            self.verify(1, "Pass")

        # IPv6 tcp test

        self.tcpdump_start_sniffing([tx_interface, rx_interface])
        self.tester.scapy_append('sendp([Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/TCP(sport=1021,dport=1021)/("X"*%s)], iface="%s")' % (mac, padding, tx_interface))
        out = self.tester.scapy_execute()
        out = self.dut.send_expect("show port stats all", "testpmd> ", 120)
        print out
        self.tcpdump_stop_sniff()
        rx_stats = self.number_of_packets(rx_interface)
        if (rx_stats == 2):
            self.verify(1, "Pass")

    def test_tso_tunneling(self):
        """
        TSO IPv4 TCP, IPv6 TCP, VXLan testing
        """
        tx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[0]))
        rx_interface = self.tester.get_interface(self.tester.get_local_port(self.dut_ports[1]))

        mac = self.dut.get_mac_address(self.dut_ports[0])

        cores = self.dut.get_core_list("1S/2C/2T")
        self.verify(cores is not None, "Insufficient cores for speed testing")
        self.coreMask = dts.create_mask(cores)

        padding = self.frame_sizes[0] - self.headers_size

        self.tester.send_expect("ethtool -K %s rx off tx off tso off gso off gro off lro off" % tx_interface, "# ")
        self.tester.send_expect("ip l set %s up" % tx_interface, "# ")

        cmd = "./%s/app/testpmd -c %s -n %d %s -- -i --rxd=512 --txd=512 --burst=32 --rxfreet=64 --mbcache=128 --portmask=%s --txpt=36 --txht=0 --txwt=0 --txfreet=32 --txrst=32 --txqflags=0 " % (self.target, self.coreMask, self.dut.get_memory_channels(), self.blacklist, self.portMask)
        self.dut.send_expect(cmd, "testpmd> ", 120)
        self.dut.send_expect("set verbose 1", "testpmd> ", 120)
        self.dut.send_expect("csum set ip hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set udp hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set tcp hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set sctp hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum set outer-ip hw %d" % self.dut_ports[0], "testpmd> ", 120)
        self.dut.send_expect("csum parse_tunnel on %d" % self.dut_ports[0], "testpmd> ", 120)

        self.dut.send_expect("csum set ip hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set udp hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set tcp hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set sctp hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum set outer-ip hw %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("csum parse_tunnel on %d" % self.dut_ports[1], "testpmd> ", 120)

        self.dut.send_expect("tso set 800 %d" % self.dut_ports[1], "testpmd> ", 120)
        self.dut.send_expect("set fwd csum", "testpmd> ", 120)
        self.dut.send_expect("start", "testpmd> ")

        self.tester.scapy_foreground()
        time.sleep(5)

        # Vxlan test
        self.tcpdump_start_sniffing([tx_interface, rx_interface])
        self.tester.scapy_append('sendp([Ether(dst="%s",src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/UDP(sport="1021",dport="4789")/VXLAN()/Ether(dst=%s,src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/TCP(sport="1021",dport="1021")/("X"*%s)], iface="%s")' % (mac, mac, padding, tx_interface))
        out = self.tester.scapy_execute()
        out = self.dut.send_expect("show port stats all", "testpmd> ", 120)
        print out
        self.tcpdump_stop_sniff()
        rx_stats = self.number_of_packets(rx_interface)
        if (rx_stats == 2):
            self.verify(1, "Pass")

        # Nvgre test
        self.tcpdump_start_sniffing([tx_interface, rx_interface])
        self.tester.scapy_append('sendp([Ether(dst="%s",src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2",proto=47)/NVGRE()/Ether(dst=%s,src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/TCP(sport="1021",dport="1021")/("X"*%s)], iface="%s")' % (mac, mac, padding, tx_interface))
        out = self.tester.scapy_execute()
        out = self.dut.send_expect("show port stats all", "testpmd> ", 120)
        print out
        self.tcpdump_stop_sniff()
        rx_stats = self.number_of_packets(rx_interface)
        if (rx_stats == 2):
            self.verify(1, "Pass")

    def test_perf_TSO_2ports(self):
        """
        TSO Performance Benchmarking with 2 ports.
        """

        # prepare traffic generator input
        tgen_input = []

        # run testpmd for each core config
        for test_cycle in self.test_cycles:
            core_config = test_cycle['cores']
            cores = self.dut.get_core_list(core_config, socket=self.ports_socket)
            self.coreMask = dts.create_mask(cores)
            if len(cores) > 2:
                queues = len(cores) / 2
            else:
                queues = 1

            command_line = "./%s/app/testpmd -c %s -n %d %s -- -i --coremask=%s --rxd=512 --txd=512 --burst=32 --rxfreet=64 --mbcache=128 --portmask=%s --txpt=36 --txht=0 --txwt=0 --txfreet=32 --txrst=32 --txqflags=0 " % (self.target, self.all_cores_mask, self.dut.get_memory_channels(), self.blacklist, self.coreMask, self.portMask)

            info = "Executing PMD using %s\n" % test_cycle['cores']
            self.logger.info(info)
            dts.report(info, annex=True)
            dts.report(command_line + "\n\n", frame=True, annex=True)

            self.dut.send_expect(command_line, "testpmd> ", 120)
            self.dut.send_expect("csum set ip hw %d" % self.dut_ports[0], "testpmd> ", 120)
            self.dut.send_expect("csum set udp hw %d" % self.dut_ports[0], "testpmd> ", 120)
            self.dut.send_expect("csum set tcp hw %d" % self.dut_ports[0], "testpmd> ", 120)
            self.dut.send_expect("csum set sctp hw %d" % self.dut_ports[0], "testpmd> ", 120)
            self.dut.send_expect("csum set outer-ip hw %d" % self.dut_ports[0], "testpmd> ", 120)
            self.dut.send_expect("csum parse_tunnel on %d" % self.dut_ports[0], "testpmd> ", 120)
            self.dut.send_expect("csum set ip hw %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("csum set udp hw %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("csum set tcp hw %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("csum set sctp hw %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("csum set outer-ip hw %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("csum parse_tunnel on %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("tso set 800 %d" % self.dut_ports[1], "testpmd> ", 120)
            self.dut.send_expect("set fwd csum", "testpmd> ", 120)
            self.dut.send_expect("start", "testpmd> ")
            for frame_size in self.frame_sizes:
                wirespeed = self.wirespeed(self.nic, frame_size, 2)

                # create pcap file
                self.logger.info("Running with frame size %d " % frame_size)
                payload_size = frame_size - self.headers_size
		for _port in range(2):
			mac = self.dut.get_mac_address(self.dut_ports[_port])
                	self.tester.scapy_append('wrpcap("dst%d.pcap", [Ether(dst="%s",src="52:00:00:00:00:01")/IP(src="192.168.1.1",dst="192.168.1.2")/TCP(sport=1021,dport=1021)/("X"*%d)])' % (_port, mac, payload_size))
        		tgen_input.append((self.tester.get_local_port(self.dut_ports[_port]),
                           self.tester.get_local_port(self.dut_ports[1-_port]), "dst%d.pcap") % _port)
                self.tester.scapy_execute()

                # run traffic generator
                _, pps = self.tester.traffic_generator_throughput(tgen_input)

                pps /= 1000000.0
                test_cycle['Mpps'][frame_size] = pps
                test_cycle['pct'][frame_size] = pps * 100 / wirespeed

            self.dut.send_expect("stop", "testpmd> ")
            self.dut.send_expect("quit", "# ", 30)
            time.sleep(5)

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
