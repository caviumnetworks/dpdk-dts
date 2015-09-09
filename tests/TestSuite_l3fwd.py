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
Layer-3 forwarding test script.
"""

import dts
import string
import re
from plotting import Plotting
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator

class TestL3fwd(TestCase,IxiaPacketGenerator):

    path = "./examples/l3fwd/build/"

    test_cases_2_ports = {"1S/1C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.1.0})'",
                          "1S/1C/2T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.1.1})'",
                          "1S/2C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.2.0})'",
                          "1S/4C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.2.0}),(P0,1,C{1.3.0}), (P1,1,C{1.4.0})'",
                          "2S/2C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{0.1.0}), (P1,0,C{0.2.0}),(P0,1,C{1.3.0}), (P1,1,C{1.4.0})'",
                          }

    test_cases_4_ports = [(1, "1S/1C/1T",
                           "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}),(P1,0,C{1.1.0}),(P2,0,C{1.1.0}),(P3,0,C{1.1.0})'"),
                          (1, "1S/2C/2T",
                           "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}),(P1,0,C{1.1.1}),(P2,0,C{1.2.0}),(P3,0,C{1.2.1})'"),
                          (1, "1S/4C/1T",
                           "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}),(P1,0,C{1.2.0}),(P2,0,C{1.3.0}),(P3,0,C{1.4.0})'"),
                          (2, "1S/8C/1T",
                           "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}),(P0,1,C{1.2.0}),(P1,0,C{1.3.0}),(P1,1,C{1.4.0}),(P2,0,C{1.5.0}),(P2,1,C{1.6.0}),(P3,0,C{1.7.0}),(P3,1,C{1.8.0})'"),
                          (2, "2S/2C/1T",
                           "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}),(P1,0,C{1.2.0}),(P2,0,C{0.3.0}),(P3,0,C{0.4.0})'"),
                          ]

    queues_4_ports = []

    for case in test_cases_4_ports:
        if case[0] * 4 not in queues_4_ports:
            queues_4_ports.append(case[0] * 4)

    host_table = [
        "{{IPv4(10,100,0,1), IPv4(1,2,3,4), 1, 10, IPPROTO_UDP}, P0}",
        "{{IPv4(10,101,0,1), IPv4(1,2,3,4), 1, 10, IPPROTO_UDP}, P0}",
        "{{IPv4(11,100,0,1), IPv4(1,2,3,4), 1, 11, IPPROTO_UDP}, P1}",
        "{{IPv4(11,101,0,1), IPv4(1,2,3,4), 1, 11, IPPROTO_UDP}, P1}",
        "{{IPv4(12,100,0,1), IPv4(1,2,3,4), 1, 12, IPPROTO_UDP}, P2}",
        "{{IPv4(12,101,0,1), IPv4(1,2,3,4), 1, 12, IPPROTO_UDP}, P2}",
        "{{IPv4(13,100,0,1), IPv4(1,2,3,4), 1, 13, IPPROTO_UDP}, P3}",
        "{{IPv4(13,101,0,1), IPv4(1,2,3,4), 1, 13, IPPROTO_UDP}, P3}",
    ]

    lpm_table = [
        "{IPv4(10,100,0,0), 24, P0}",
        "{IPv4(10,101,0,0), 24, P0}",
        "{IPv4(11,100,0,0), 24, P1}",
        "{IPv4(11,101,0,0), 24, P1}",
        "{IPv4(12,100,0,0), 24, P2}",
        "{IPv4(12,101,0,0), 24, P2}",
        "{IPv4(13,100,0,0), 24, P3}",
        "{IPv4(13,101,0,0), 24, P3}",
    ]

    frame_sizes = [64,128]  # 65, 128
    methods = ['lpm', 'exact']

    #
    #
    # Utility methods and other non-test code.
    #
    # Insert or move non-test functions here.
    def portRepl(self, match):
        """
        Function to replace P([0123]) pattern in tables
        """

        portid = match.group(1)
        self.verify(int(portid) in range(4), "invalid port id")
        if int(portid) >= len(valports):
            return '0'
        else:
            return '%s' % valports[int(portid)]

    #
    #
    #
    # Test cases.
    #

    def plot_4_ports(self):

        data = self.l3fwd_test_results['data']

        # Create a plot for each number of queues for frame size and mode comparison
        cores = '1S/1C/1T'
        for queues in TestL3fwd.queues_4_ports:
            ydata = []
            lpm_ydata = []
            exact_ydata = []
            for frame_size in TestL3fwd.frame_sizes:
                for row in data:
                    if row[1] * 4 == queues and row[2] == cores and \
                            row[0] == frame_size:
                        if len(TestL3fwd.methods) == 2:
                            lpm_ydata.append(row[4])
                            exact_ydata.append(row[6])
                        else:
                            if 'lpm' in TestL3fwd.methods:
                                lpm_ydata.append(row[4])
                            if 'exact' in TestL3fwd.methods:
                                exact_ydata.append(row[4])

            if 'lpm' in TestL3fwd.methods:
                ydata.append(lpm_ydata)
            if 'exact' in TestL3fwd.methods:
                ydata.append(exact_ydata)

            if len(ydata[0]) == 0:
                self.logger.warning('No data for plotting 1S/1C/1T')
                break
            else:
                try:
                    image_path = self.plotting.create_bars_plot(
                        'test_perf_l3fwd_4ports_1S_1C_1T_%dRxQ' % queues,
                        'LPM & Exact modes, 1S/1C/1T, %d Rx Queues, 4 ports' % queues,
                        TestL3fwd.frame_sizes,
                        ydata,
                        ylabel='% linerate',
                        legend=TestL3fwd.methods)

                    dts.results_plot_print(image_path, 50)
                except VerifyFailure as e:
                    self.logger.error(str(e))

        # Create a plot for each number of queues for core config and mode comparison
        frame_size = TestL3fwd.frame_sizes[0]   # Frame size fixed to the first selected
        for queues in TestL3fwd.queues_4_ports:

            cores = []
            for row in data:
                if row[2] not in cores and \
                   row[1] * 4 == queues:
                    cores.append(row[2])

            ydata = []
            lpm_ydata = []
            exact_ydata = []

            for core in cores:
                for row in data:
                    if row[1] * 4 == queues and \
                       row[2] == core and \
                       row[0] == frame_size:
                        if len(TestL3fwd.methods) == 2:
                            lpm_ydata.append(row[4])
                            exact_ydata.append(row[6])
                        else:
                            if 'lpm' in TestL3fwd.methods:
                                lpm_ydata.append(row[4])
                            if 'exact' in TestL3fwd.methods:
                                exact_ydata.append(row[4])

            if 'lpm' in TestL3fwd.methods:
                ydata.append(lpm_ydata)
            if 'exact' in TestL3fwd.methods:
                ydata.append(exact_ydata)

            try:
                image_path = self.plotting.create_bars_plot(
                    'test_perf_l3fwd_4ports_%d_%dRxQ' % (frame_size, queues),
                    'LPM & Exact modes, %dB, %d Rx Queues, 4 ports' % (frame_size, queues),
                    cores,
                    ydata,
                    ylabel='% linerate',
                    legend=TestL3fwd.methods)

                dts.results_plot_print(image_path)
            except VerifyFailure as e:
                self.logger.error(str(e))

    def plot_2_ports(self):

        data = self.l3fwd_test_results['data']

        cores = []
        for row in data:
            if row[2] not in cores:
                cores.append(row[2])

        # Create a plot for each mode for frame size and cores comparison
        for mode in TestL3fwd.methods:
            mode_ydata = []

            for core in cores:
                core_ydata = []
                for row in data:
                    if row[5] == mode and row[2] == core:
                        core_ydata.append(float(row[4]))

                mode_ydata.append(core_ydata)

            image_path = self.plotting.create_bars_plot(
                'test_perf_l3fwd_2ports_%s' % mode,
                'L3fwd %s mode, 2 ports' % mode,
                TestL3fwd.frame_sizes,
                mode_ydata,
                ylabel='% linerate',
                legend=cores)

            dts.results_plot_print(image_path, 50)

        # If testing only one mode, do nothing else.
        if len(TestL3fwd.methods) == 1:
            return

        # Create a plot for 1st core config for mode and frame size comparison
        core = '1S/1C/1T'

        ydata = []
        for mode in TestL3fwd.methods:
            mode_ydata = []
            for frame_size in TestL3fwd.frame_sizes:
                for row in data:
                    if row[2] == core and row[0] == frame_size and \
                            row[5] == mode:
                        mode_ydata.append(float(row[4]))

            ydata.append(mode_ydata)

        str_frame_sizes = []
        for frame_size in TestL3fwd.frame_sizes:
            str_frame_sizes.append(str(frame_size))

        image_path = self.plotting.create_bars_plot(
            'test_perf_l3fwd_2ports_1S_1C_1T',
            'L3fwd 1S/1C/1T cores, 2 ports',
            TestL3fwd.frame_sizes,
            ydata,
            ylabel='% linerate',
            legend=TestL3fwd.methods)

        dts.results_plot_print(image_path)

    def set_up_all(self):
        """
        Run at the start of each test suite.


        L3fwd Prerequisites
        """
        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(socket=1)
        if not ports:
            ports = self.dut.get_ports(socket=0)

        self.tester.extend_external_packet_generator(TestL3fwd, self)
        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports for speed testing")
        
        netdev = self.dut.ports_info[ports[0]]['port']
        
        self.port_socket = netdev.socket
        

        # Verify that enough threads are available
        cores = self.dut.get_core_list("2S/8C/2T")
        self.verify(cores is not None, "Insufficient cores for speed testing")

        global valports
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        
        self.verify(len(valports) >= 2, "Insufficient active ports for speed testing")

        pat = re.compile("P([0123])")
        # Update config file and rebuild to get best perf on FVL
        self.dut.send_expect("sed -i -e 's/CONFIG_RTE_PCI_CONFIG=n/CONFIG_RTE_PCI_CONFIG=y/' ./config/common_linuxapp", "#", 20)
        self.dut.send_expect("sed -i -e 's/CONFIG_RTE_PCI_EXTENDED_TAG=.*$/CONFIG_RTE_PCI_EXTENDED_TAG=\"on\"/' ./config/common_linuxapp", "#", 20)
        self.dut.build_install_dpdk(self.target)


        # Prepare long prefix match table, replace P(x) port pattern
        lpmStr = "static struct ipv4_l3fwd_route ipv4_l3fwd_route_array[] = {\\\n"
        for idx in range(len(TestL3fwd.lpm_table)):
            TestL3fwd.lpm_table[idx] = pat.sub(self.portRepl, TestL3fwd.lpm_table[idx])
            lpmStr = lpmStr + ' ' * 4 + TestL3fwd.lpm_table[idx] + ",\\\n"
        lpmStr = lpmStr + "};"
        self.logger.debug(lpmStr)

        # Prepare host route table, replace P(x) port pattern
        exactStr = "static struct ipv4_l3fwd_route ipv4_l3fwd_route_array[] = {\\\n"
        for idx in range(len(TestL3fwd.host_table)):
            TestL3fwd.host_table[idx] = pat.sub(self.portRepl, TestL3fwd.host_table[idx])
            exactStr = exactStr + ' ' * 4 + TestL3fwd.host_table[idx] + ",\\\n"
        exactStr = exactStr + "};"
        self.logger.debug(exactStr)

        # Compile l3fwd with LPM lookup.
        self.dut.send_expect(r"sed -i '/ipv4_l3fwd_route_array\[\].*{/,/^\}\;/c\\%s' examples/l3fwd/main.c" % lpmStr, "# ")
        out = self.dut.build_dpdk_apps("./examples/l3fwd", "USER_FLAGS=-DAPP_LOOKUP_METHOD=1")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        # Backup the LPM exe and clean up the build.
        self.dut.send_expect("mv -f examples/l3fwd/build/l3fwd examples/l3fwd/build/l3fwd_lpm", "# ")
        out = self.dut.send_expect("make clean -C examples/l3fwd", "# ")

        # Compile l3fwd with hash/exact lookup.
        self.dut.send_expect(r"sed -i -e '/ipv4_l3fwd_route_array\[\].*{/,/^\}\;/c\\%s' examples/l3fwd/main.c" % exactStr, "# ")
        out = self.dut.build_dpdk_apps("./examples/l3fwd", "USER_FLAGS=-DAPP_LOOKUP_METHOD=0")

        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")

        # Backup the Hash/Exact exe.
        self.dut.send_expect("mv -f examples/l3fwd/build/l3fwd examples/l3fwd/build/l3fwd_exact", "# ")

        self.l3fwd_test_results = {'header': [],
                                   'data': []}

        self.plotting = Plotting(self.dut.crb['name'], self.target, self.nic)

    def flows(self):
        """
        Return a list of packets that implements the flows described in the
        l3fwd test plan.

        """   
        return [
            'IP(src="1.2.3.4",dst="11.100.0.1")',
            'IP(src="1.2.3.4",dst="11.101.0.1")',
            'IP(src="1.2.3.4",dst="10.100.0.1")',
            'IP(src="1.2.3.4",dst="10.101.0.1")',
            'IP(src="1.2.3.4",dst="13.100.0.1")',
            'IP(src="1.2.3.4",dst="13.101.0.1")',
            'IP(src="1.2.3.4",dst="12.100.0.1")',
            'IP(src="1.2.3.4",dst="12.101.0.1")']

    def repl(self, match):
        pid = match.group(1)
        qid = match.group(2)
        self.logger.debug("%s\n" % match.group(3))
        lcid = self.dut.get_lcore_id(match.group(3))
        self.logger.debug("%s\n" % lcid)

        global corelist
        corelist.append(int(lcid))

        self.verify(int(pid) in range(4), "invalid port id")
        self.verify(lcid, "invalid thread id")

        return '%s,%s,%s' % (str(valports[int(pid)]), qid, lcid)

    def get_throughput(self, frame_size, rx_queues_per_port, cores_config, command_line):
        """
        Get the throughput for a test case from test_cases_4_ports.
        """

        output_pattern = re.compile("P([0123]),([0123]),(C\{\d.\d.\d\})")
        pat2 = re.compile("C\{\d")
        repl1 = "C{" + str(self.port_socket)
 

        bps = dict()
        pps = dict()
        pct = dict()

        global corelist
        corelist = []
        
        
        while output_pattern.search(command_line):
        # If one socket case, we update the socket to ensure the core used by l3fwd is on the same socket of the NIC.
            if cores_config.find('1S')>=0:
                command_line = pat2.sub(repl1,command_line)
            command_line = output_pattern.sub(self.repl, command_line)
            

        self.logger.debug("%s\n" % str(corelist))
        core_mask = dts.create_mask(set(corelist))

        # First, measure by two different methods
        for method in TestL3fwd.methods:
            # start l3fwd
            method_command_line = command_line % (TestL3fwd.path + "l3fwd_" + method,
                                                  core_mask,
                                                  self.dut.get_memory_channels(),
                                                  dts.create_mask(valports[:4]))

            dts.report(method_command_line + "\n", frame=True, annex=True)

            out = self.dut.send_expect(method_command_line, "L3FWD:", 120)

            # measure test
            tgen_input = []
            for rxPort in range(4):
                if rxPort % 2 == 0:
                    tx_interface = self.tester.get_local_port(valports[rxPort + 1])
                else:
                    tx_interface = self.tester.get_local_port(valports[rxPort - 1])

                rx_interface = self.tester.get_local_port(valports[rxPort])
                # Make sure the traffic send to the correct MAC address
                if rxPort % 2 == 0: 
                    tgen_input.append((tx_interface, rx_interface, "dst%d.pcap" % valports[rxPort+1]))
                else:
                    tgen_input.append((tx_interface, rx_interface, "dst%d.pcap" % valports[rxPort-1]))

            # FIX ME
            bps[method], pps[method] = self.tester.traffic_generator_throughput(tgen_input)
            self.verify(pps[method] > 0, "No traffic detected")
            pps[method] /= 1000000.0
            pct[method] = pps[method] * 100 / float(self.wirespeed(self.nic,
                                                                   frame_size,
                                                                   4))

            # stop l3fwd
            self.dut.send_expect("^C", "#")

        data_row = [frame_size, rx_queues_per_port, cores_config]
        for method in TestL3fwd.methods:
            data_row.append(pps[method])
            data_row.append(pct[method])

        # generate report table
        dts.results_table_add_row(data_row)
        self.l3fwd_test_results['data'].append(data_row)

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_perf_l3fwd_4ports(self):
        """
        L3fwd main 4 ports.
        """

        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports()
        # Verify that enough ports are available
        self.verify(len(ports) >= 4, "Insufficient ports for speed testing")

        header_row = ["Frame size", "RX Queues/NIC Port", "S/C/T"]

        for method in TestL3fwd.methods:
            header_row.append('%s Mpps' % method)
            header_row.append('% linerate')

        dts.results_table_add_header(header_row)
        self.l3fwd_test_results['header'] = header_row
        self.l3fwd_test_results['data'] = []

        for frame_size in TestL3fwd.frame_sizes:

            # Prepare traffic flow
            payload_size = frame_size - \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth']

            for _port in range(4):
                dmac = self.dut.get_mac_address(valports[_port])
                flows = ['Ether(dst="%s")/%s/("X"*%d)' % (dmac, flow, payload_size) for flow in self.flows()[_port * 2:(_port + 1) * 2]]
                self.tester.scapy_append('wrpcap("dst%d.pcap", [%s])' % (valports[_port], string.join(flows, ',')))

            self.tester.scapy_execute()

            dts.report("Flows for 4 ports, %d frame size.\n" % (frame_size),
                       annex=True)
            dts.report("%s" % string.join(flows, '\n'),
                       frame=True, annex=True)

            # Get the number of sockets of the board
            number_sockets = self.dut.send_expect("grep \"processor\|physical id\|core id\|^$\" /proc/cpuinfo | grep physical | sort -u | wc -l", "# ")
            number_sockets = int(number_sockets.split('\r\n')[0])

            # Run case by case
            for test_case in TestL3fwd.test_cases_4_ports:

                # Check if the board has sockets enough for the test case
                if number_sockets >= int(test_case[1].split('/')[0][0]):
                    self.get_throughput(frame_size, *test_case)

        self.plot_4_ports()
        dts.results_table_print()

    def test_perf_l3fwd_2ports(self):
        """
        L3fwd main 2 ports.
        """

        header_row = ["Frame", "Ports", "S/C/T", "Mpps", "% linerate", "mode"]
        self.l3fwd_test_results['header'] = header_row
        dts.results_table_add_header(header_row)
        self.l3fwd_test_results['data'] = []

        for frame_size in TestL3fwd.frame_sizes:

            # Prepare traffic flow
            payload_size = frame_size -  \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth']
            for _port in range(2):
                dmac = self.dut.get_mac_address(valports[_port])
                flows = ['Ether(dst=%s)/%s/("X"*%d)' % (dmac, flow, payload_size) for flow in self.flows()[_port *2:(_port +1)*2]]
                self.tester.scapy_append('wrpcap("dst%d.pcap", [%s])' %(valports[_port],string.join(flows,',')))
            self.tester.scapy_execute() 

            dts.report("Flows for 2 ports, %d frame size.\n" % (frame_size),
                       annex=True)
            dts.report("%s" % string.join(flows, '\n'),
                       frame=True, annex=True)


            # Prepare the command line
            global corelist
            pat = re.compile("P([0123]),([0123]),(C\{\d.\d.\d\})")
            
            pat2 = re.compile("C\{\d")
            repl1 = "C{" + str(self.port_socket)

            coreMask = {}
            rtCmdLines = dict(TestL3fwd.test_cases_2_ports)
            for key in rtCmdLines.keys():
                corelist = []
                while pat.search(rtCmdLines[key]):
                    # Change the socket to the NIC's socket
                    if key.find('1S')>=0:
                        rtCmdLines[key] = pat2.sub(repl1, rtCmdLines[key])
                    rtCmdLines[key] = pat.sub(self.repl, rtCmdLines[key])

                self.logger.info("%s\n" % str(corelist))
                coreMask[key] = dts.create_mask(set(corelist))

            # measure by two different mode
            for mode in TestL3fwd.methods:

                # start l3fwd
                index = 0
                subtitle = []
                for cores in rtCmdLines.keys():

                    info = "Executing l3fwd using %s mode, 2 ports, %s and %d frame size.\n" % (
                           mode, cores, frame_size)

                    self.logger.info(info)
                    dts.report(info, annex=True)

                    subtitle.append(cores)
                    cmdline = rtCmdLines[cores] % (TestL3fwd.path + "l3fwd_" + mode, coreMask[cores],
                                                   self.dut.get_memory_channels(), dts.create_mask(valports[:2]))

                    dts.report(cmdline + "\n", frame=True, annex=True)

                    out = self.dut.send_expect(cmdline, "L3FWD:", 120)

                    # Measure test
                    tgenInput = []
                    for rxPort in range(2):
                        # No use on rx/tx limitation
                        if rxPort % 2 == 0:
                            txIntf = self.tester.get_local_port(valports[rxPort + 1])
                        else:
                            txIntf = self.tester.get_local_port(valports[rxPort - 1])

                        rxIntf = self.tester.get_local_port(valports[rxPort])
                        if rxPort % 2 == 0: 
                            tgenInput.append((txIntf, rxIntf, "dst%d.pcap" %valports[rxPort+1]))
                        else: 
                            tgenInput.append((txIntf, rxIntf, "dst%d.pcap" %valports[rxPort-1]))

                    _, pps = self.tester.traffic_generator_throughput(tgenInput)
                    self.verify(pps > 0, "No traffic detected")
                    pps /= 1000000.0
                    linerate = self.wirespeed(self.nic, frame_size, 2)
                    pct = pps * 100 / linerate

                    index += 1

                    # Stop l3fwd
                    self.dut.send_expect("^C", "#")

                    data_row = [frame_size, 2, cores, str(pps), str(pct), mode]
                    dts.results_table_add_row(data_row)
                    self.l3fwd_test_results['data'].append(data_row)

        self.plot_2_ports()
        dts.results_table_print()

    def ip(self, port, frag, src, proto, tos, dst, chksum, len, options, version, flags, ihl, ttl, id):
        self.add_tcl_cmd("protocol config -name ip")
        self.add_tcl_cmd('ip config -sourceIpAddr "%s"' % src)
        self.add_tcl_cmd("ip config -sourceIpAddrMode ipRandom")
        self.add_tcl_cmd('ip config -destIpAddr "%s"' % dst)
        self.add_tcl_cmd("ip config -destIpAddrMode ipIdle")
        self.add_tcl_cmd("ip config -ttl %d" % ttl)
        self.add_tcl_cmd("ip config -totalLength %d" % len)
        self.add_tcl_cmd("ip config -fragment %d" % frag)
        self.add_tcl_cmd("ip config -ipProtocol ipV4ProtocolReserved255")
        self.add_tcl_cmd("ip config -identifier %d" % id)
        self.add_tcl_cmd("stream config -framesize %d" % (len + 18))
        self.add_tcl_cmd("ip set %d %d %d" % (self.chasId, port['card'], port['port']))

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
