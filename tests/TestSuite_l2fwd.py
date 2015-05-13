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
Test Layer-2 Forwarding support
"""

import dts
from test_case import TestCase
from plotting import Plotting
from settings import HEADER_SIZE


class TestL2fwd(TestCase):

    def plot_results(self):

        queues = []
        queues_results = []

        for test_queues in self.test_queues:
            queues.append(str(test_queues['queues']))
            results = []
            for frame_size in self.frame_sizes:
                results.append(test_queues['pct'][frame_size])
            queues_results.append(results)

        image_path = self.plotting.create_bars_plot(
            'test_perf_l2fwd',
            'L2fwd, %d ports' % self.number_of_ports,
            self.frame_sizes,
            queues_results,
            ylabel='% linerate',
            legend=queues)

        dts.results_plot_print(image_path)

    def set_up_all(self):
        """
        Run at the start of each test suite.

        L2fwd prerequisites.
        """
        self.frame_sizes = [64, 65, 128, 256, 512, 1024, 1280, 1518]

        self.test_queues = [{'queues': 1, 'Mpps': {}, 'pct': {}},
                            {'queues': 2, 'Mpps': {}, 'pct': {}},
                            {'queues': 4, 'Mpps': {}, 'pct': {}},
                            {'queues': 8, 'Mpps': {}, 'pct': {}}
                            ]

        self.core_config = "1S/4C/1T"
        self.number_of_ports = 2
        self.headers_size = HEADER_SIZE['eth'] + HEADER_SIZE['ip'] + \
            HEADER_SIZE['udp']

        self.dut_ports = self.dut.get_ports_performance()

        self.verify(len(self.dut_ports) >= self.number_of_ports,
                    "Not enough ports for " + self.nic)

        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        # compile
        out = self.dut.build_dpdk_apps("./examples/l2fwd")
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")

        self.table_header = ['Frame']
        for queue in self.test_queues:
            self.table_header.append("%d queues Mpps" % queue['queues'])
            self.table_header.append("% linerate")

        dts.results_table_add_header(self.table_header)
        self.plotting = Plotting(self.dut.crb['name'], self.target, self.nic)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def quit_l2fwd(self):
        self.dut.send_expect("fg", "l2fwd ", 5)
        self.dut.send_expect("^C", "# ", 5)

    def test_port_testing(self):
        """
        Check port forwarding.
        """
        # the cases use the first two ports
        port_mask = dts.create_mask([self.dut_ports[0], self.dut_ports[1]])

        self.dut.send_expect("./examples/l2fwd/build/app/l2fwd -n 1 -c f -- -q 8 -p %s  &" % port_mask, "L2FWD: entering main loop", 60)

        for i in [0, 1]:
            tx_port = self.tester.get_local_port(self.dut_ports[i])
            rx_port = self.tester.get_local_port(self.dut_ports[1 - i])

            tx_interface = self.tester.get_interface(tx_port)
            rx_interface = self.tester.get_interface(rx_port)

            self.tester.scapy_background()
            self.tester.scapy_append('p = sniff(iface="%s", count=1)' % rx_interface)
            self.tester.scapy_append('number_packets=len(p)')
            self.tester.scapy_append('RESULT = str(number_packets)')

            self.tester.scapy_foreground()
            self.tester.scapy_append('sendp([Ether()/IP()/UDP()/("X"*46)], iface="%s")' % tx_interface)

            self.tester.scapy_execute()
            number_packets = self.tester.scapy_get_result()
            self.verify(number_packets == "1", "Failed to switch L2 frame")

        self.quit_l2fwd()

    def test_perf_l2fwd_performance(self):
        """
        Benchmark performance for frame_sizes.
        """
        ports = []
        for port in xrange(self.number_of_ports):
            ports.append(self.dut_ports[port])

        port_mask = dts.create_mask(ports)
        core_mask = dts.create_mask(self.dut.get_core_list(self.core_config,
                                                           socket=self.ports_socket))

        for frame_size in self.frame_sizes:

            payload_size = frame_size - self.headers_size

            tgen_input = []
            for port in xrange(self.number_of_ports):
                rx_port = self.tester.get_local_port(self.dut_ports[port % self.number_of_ports])
                tx_port = self.tester.get_local_port(self.dut_ports[(port + 1) % self.number_of_ports])
                destination_mac = self.dut.get_mac_address(self.dut_ports[(port + 1) % self.number_of_ports])
                self.tester.scapy_append('wrpcap("l2fwd_%d.pcap", [Ether(dst="%s")/IP()/UDP()/("X"*%d)])' % (
                    port, destination_mac, payload_size))

                tgen_input.append((tx_port, rx_port, "l2fwd_%d.pcap" % port))

            self.tester.scapy_execute()

            for queues in self.test_queues:

                command_line = "./examples/l2fwd/build/app/l2fwd -n %d -c %s -- -q %s -p %s &" % \
                    (self.dut.get_memory_channels(), core_mask,
                     str(queues['queues']), port_mask)

                self.dut.send_expect(command_line, "memory mapped", 60)

                info = "Executing l2fwd using %s queues, frame size %d and %s setup.\n" % \
                       (queues['queues'], frame_size, self.core_config)

                self.logger.info(info)
                dts.report(info, annex=True)
                dts.report(command_line + "\n\n", frame=True, annex=True)
                _, pps = self.tester.traffic_generator_throughput(tgen_input)
                Mpps = pps / 1000000.0
                queues['Mpps'][frame_size] = Mpps
                queues['pct'][frame_size] = Mpps * 100 / float(self.wirespeed(
                                                               self.nic,
                                                               frame_size,
                                                               self.number_of_ports))

                self.quit_l2fwd()

        # Look for transmission error in the results
        for frame_size in self.frame_sizes:
            for n in range(len(self.test_queues)):
                self.verify(self.test_queues[n]['Mpps'][frame_size] > 0,
                            "No traffic detected")

        # Prepare the results for table and plot printing
        for frame_size in self.frame_sizes:
            results_row = []
            results_row.append(frame_size)
            for queue in self.test_queues:
                results_row.append(queue['Mpps'][frame_size])
                results_row.append(queue['pct'][frame_size])

            dts.results_table_add_row(results_row)

        self.plot_results()
        dts.results_table_print()

    def tear_down(self):
        """
        Run after each test case.
        """
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        pass
