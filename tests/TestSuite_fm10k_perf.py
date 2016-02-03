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
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator
from utils import *

class TestFM10kL3fwd(TestCase, IxiaPacketGenerator):

    path = "./examples/l3fwd/build/"

    test_cases_2_ports = {
                          "1S/1C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.1.0})'",
                          "1S/2C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.2.0})'",
                          "1S/4C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P1,0,C{1.2.0}), (P0,1,C{1.3.0}), (P1,1,C{1.4.0})'",
                          "1S/8C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P0,1,C{1.2.0}), (P0,2,C{1.3.0}), (P0,3,C{1.4.0})," +\
                                     "(P1,0,C{1.5.0}),(P1,1,C{1.6.0}), (P1,2,C{1.7.0}), (P1,3,C{1.8.0})'",
                          "1S/16C/1T": "%s -c %s -n %d -- -p %s  --config '(P0,0,C{1.1.0}), (P0,1,C{1.2.0}), (P0,2,C{1.3.0}), (P0,3,C{1.4.0})," +\
                                     "(P0,4,C{1.1.1}), (P0,5,C{1.2.1}), (P0,6,C{1.3.1}), (P0,7,C{1.4.1})," +\
                                     "(P1,0,C{1.5.0}), (P1,1,C{1.6.0}), (P1,2,C{1.7.0}), (P1,3,C{1.8.0})," +\
                                     "(P1,4,C{1.5.1}), (P1,5,C{1.6.1}), (P1,6,C{1.7.1}), (P1,7,C{1.8.1})'"
                          }

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

    frame_sizes = [64, 128, 256, 512, 2048]  # 65, 128
    methods = ['lpm']

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

    def set_up_all(self):
        """
        Run at the start of each test suite.
        L3fwd Prerequisites
        """
        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(socket=1)
        if not ports:
            ports = self.dut.get_ports(socket=0)

        self.tester.extend_external_packet_generator(TestFM10kL3fwd, self)
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

        self.main_file = "examples/l3fwd/main.c"
        self.pf_file = "drivers/net/fm10k/base/fm10k_pf.c"
        # Update config file and rebuild to get best perf on FVL
        if "redrockcanyou" in self.nic:
            self.dut.send_expect("sed -i -e 's/FM10K_TQDLOC_BASE_32_DESC/FM10K_TQDLOC_BASE_128_DESC/' %s" % self.pf_file, "# ")
            self.dut.send_expect("sed -i -e 's/FM10K_TQDLOC_SIZE_32_DESC/FM10K_TQDLOC_SIZE_128_DESC/' %s" % self.pf_file, "# ")
            self.dut.send_expect("sed -i -e 's/FM10K_TDLEN_ITR_SCALE_GEN3;$/FM10K_TDLEN_ITR_SCALE_GEN3 * 2;/' %s" % self.pf_file, "# ")
            
            self.dut.build_install_dpdk(self.target)

        self.l3fwd_test_results = {'header': [],
                                   'data': []}

        self.rebuild_l3fwd()

    def rebuild_l3fwd(self):
        pat = re.compile("P([0123])")
        # Prepare long prefix match table, replace P(x) port pattern
        lpmStr = "static struct ipv4_l3fwd_route ipv4_l3fwd_route_array[] = {\\\n"
        for idx in range(len(TestFM10kL3fwd.lpm_table)):
            TestFM10kL3fwd.lpm_table[idx] = pat.sub(self.portRepl, TestFM10kL3fwd.lpm_table[idx])
            lpmStr = lpmStr + ' ' * 4 + TestFM10kL3fwd.lpm_table[idx] + ",\\\n"
        lpmStr = lpmStr + "};"
        self.logger.debug(lpmStr)

        # Prepare host route table, replace P(x) port pattern
        exactStr = "static struct ipv4_l3fwd_route ipv4_l3fwd_route_array[] = {\\\n"
        for idx in range(len(TestFM10kL3fwd.host_table)):
            TestFM10kL3fwd.host_table[idx] = pat.sub(self.portRepl, TestFM10kL3fwd.host_table[idx])
            exactStr = exactStr + ' ' * 4 + TestFM10kL3fwd.host_table[idx] + ",\\\n"
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

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def fm10k_rxmode_set(self, mode="default"):
        """
        Change rxmode setting for RRC vector choice
        RRC rxmode choice will depend on rxmod
        """
        if mode == "scatter":
            # enable ip checkcsum
            self.dut.send_expect("sed -i -e 's/.hw_ip_checksum = .*$/.hw_ip_checksum = 1,/g' %s" % self.main_file, "# ")
            # enable scatter mode
            self.dut.send_expect("sed -i -e 's/.enable_scatter = .*$/.enable_scatter = 1,/g' %s" % self.main_file, "# ")
        elif mode == "scatter_vector":
            # disable ip checksum
            self.dut.send_expect("sed -i -e 's/.hw_ip_checksum = .*$/.hw_ip_checksum = 0,/g' %s" % self.main_file, "# ")
            # eanble scatter mode
            self.dut.send_expect("sed -i -e 's/.enable_scatter = .*$/.enable_scatter = 1,/g' %s" % self.main_file, "# ")
        elif mode == "vector":
            # disable ip checksum
            self.dut.send_expect("sed -i -e 's/.hw_ip_checksum = .*$/.hw_ip_checksum = 0,/g' %s" % self.main_file, "# ")
            # default l3fwd parameter, scatter will be disabled
            self.dut.send_expect("sed -i -e 's/.enable_scatter = .*$/.enable_scatter = 0,/g' %s" % self.main_file, "# ")
        elif mode == "default":
            # disable ip checksum
            self.dut.send_expect("sed -i -e 's/.hw_ip_checksum = .*$/.hw_ip_checksum = 1,/g' %s" % self.main_file, "# ")
            # default l3fwd parameter, scatter will be disabled
            self.dut.send_expect("sed -i -e 's/.enable_scatter = .*$/.enable_scatter = 0,' %s" % self.main_file, "# ")

        # rebuild l3fwd
        self.rebuild_l3fwd()

    def test_perf_fm10k_legacy_perf(self):
        # add setting for scatter
        #self.dut.send_expect("sed -i -e '/.hw_ip_checksum = .*$/a\\.enable_scatter = 0,' %s" % self.main_file, "# ")

#        mode_settings = [{'rxmode': 'default', 'txmode': 'default'}, {'rxmode': 'vector', 'txmode': 'vector'}]
        mode_settings = [{'rxmode': 'default', 'txmode': 'default'}]
        for mode in mode_settings:
            self.fm10k_rxmode_set(mode = mode['rxmode'])
            if mode['txmode'] == 'default':
                # need --enable-jumbo parameter
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    if "--enable-jumbo" not in TestFM10kL3fwd.test_cases_2_ports[key]:
                        TestFM10kL3fwd.test_cases_2_ports[key] += " --enable-jumbo"
            else:
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    TestFM10kL3fwd.test_cases_2_ports[key].replace(" --enable-jumbo", "")

            print GREEN("Performance test for rxmode %s txmode %s" %(mode['rxmode'], mode['txmode']))
            self.perf_l3fwd_2ports()

        # remove setting for scatter
        self.dut.send_expect("sed -i -e '/.enable_scatter= .*$/d' %s" % self.main_file, "# ")

    def test_perf_fm10k_vec_perf(self):
        # add setting for scatter
        #self.dut.send_expect("sed -i -e '/.hw_ip_checksum = .*$/a\\.enable_scatter = 0,' %s" % self.main_file, "# ")

#        mode_settings = [{'rxmode': 'default', 'txmode': 'default'}, {'rxmode': 'vector', 'txmode': 'vector'}]
        mode_settings = [{'rxmode': 'vector', 'txmode': 'vector'}]
        for mode in mode_settings:
            self.fm10k_rxmode_set(mode = mode['rxmode'])
            if mode['txmode'] == 'default':
                # need --enable-jumbo parameter
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    if "--enable-jumbo" not in TestFM10kL3fwd.test_cases_2_ports[key]:
                        TestFM10kL3fwd.test_cases_2_ports[key] += " --enable-jumbo"
            else:
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    TestFM10kL3fwd.test_cases_2_ports[key].replace(" --enable-jumbo", "")

            print GREEN("Performance test for rxmode %s txmode %s" %(mode['rxmode'], mode['txmode']))
            self.perf_l3fwd_2ports()

        # remove setting for scatter
        self.dut.send_expect("sed -i -e '/.enable_scatter= .*$/d' %s" % self.main_file, "# ")


    def perf_l3fwd_2ports(self):
        """
        L3fwd main 2 ports.
        """

        header_row = ["Frame", "mode", "S/C/T", "Mpps", "% linerate", "latency_max(us)", "latency_min(us)", "latency_avg(us)"]
        self.l3fwd_test_results['header'] = header_row
        dts.results_table_add_header(header_row)
        self.l3fwd_test_results['data'] = []

	mac = ["02:00:00:00:00:00", "02:00:00:00:00:01"]
        for frame_size in TestFM10kL3fwd.frame_sizes:

            # Prepare traffic flow
            payload_size = frame_size -  \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth']
            for _port in range(2):
                dmac = self.dut.get_mac_address(valports[_port])
                flows = ['Ether(dst="%s", src="%s")/%s/("X"*%d)' % (dmac, mac[_port], flow, payload_size) for flow in self.flows()[_port *2:(_port +1)*2]]
                self.tester.scapy_append('wrpcap("dst%d.pcap", [%s])' %(valports[_port],string.join(flows,',')))
            self.tester.scapy_execute() 

            dts.report("Flows for 2 ports, %d frame size.\n" % (frame_size),
                       annex=True)
            dts.report("%s" % string.join(flows, '\n'),
                       frame=True, annex=True)


            # Prepare the command line
            global corelist
            pat = re.compile("P([0123]),([01234567]),(C\{\d.\d.\d\})")
            
            pat2 = re.compile("C\{\d")
            repl1 = "C{" + str(self.port_socket)

            coreMask = {}
            rtCmdLines = dict(TestFM10kL3fwd.test_cases_2_ports)
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
            #methods = TestFM10kL3fwd.methods

            for mode in TestFM10kL3fwd.methods:

                # start l3fwd
                index = 0
                subtitle = []
                for cores in rtCmdLines.keys():

                    info = "Executing l3fwd using %s mode, 2 ports, %s and %d frame size.\n" % (
                           mode, cores, frame_size)

                    self.logger.info(info)
                    dts.report(info, annex=True)

                    subtitle.append(cores)
                    cmdline = rtCmdLines[cores] % (TestFM10kL3fwd.path + "l3fwd_" + mode, coreMask[cores],
                                                   self.dut.get_memory_channels(), dts.create_mask(valports[:2]))

                    if frame_size > 1518:
                        cmdline = cmdline + " --max-pkt-len %d" % frame_size
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
                    latencys = self.tester.traffic_generator_latency(tgenInput)

                    index += 1

                    # Stop l3fwd
                    self.dut.send_expect("^C", "#")
                    print latencys

                    for latency in latencys:
                        if latency['max'] > 0:
                            data_row = [frame_size, mode, cores, str(pps), str(pct), str(latency['max']/1000), str(latency['min']/1000), str(latency['average']/1000)]
                    dts.results_table_add_row(data_row)
                    self.l3fwd_test_results['data'].append(data_row)

        dts.results_table_print()

    def perf_rfc2544(self):

        header_row = ["Frame", "mode", "S/C/T", "tx_pkts(1min)", "LR_rx_pkts(1min)", "LR_loss_pkts(1min)", "% zero_loss_rate(0.01%loss)"]
        self.l3fwd_test_results['header'] = header_row
        dts.results_table_add_header(header_row)
        self.l3fwd_test_results['data'] = []

        for frame_size in TestFM10kL3fwd.frame_sizes:

            # Prepare traffic flow
            payload_size = frame_size -  \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth']
            for _port in range(2):
                dmac = self.dut.get_mac_address(valports[_port])
                flows = ['Ether(dst="%s")/%s/("X"*%d)' % (dmac, flow, payload_size) for flow in self.flows()[_port *2:(_port +1)*2]]
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
            rtCmdLines = dict(TestFM10kL3fwd.test_cases_2_ports)
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
            for mode in TestFM10kL3fwd.methods:

                # start l3fwd
                index = 0
                subtitle = []
                for cores in rtCmdLines.keys():

                    #in order to save time, only some of the cases will be run.
                    if mode == "lpm" and (cores == "1S/1C/1T" or cores == "1S/4C/1T"):
                        info = "Executing l3fwd using %s mode, 2 ports, %s and %d frame size.\n" % (
                               mode, cores, frame_size)

                        self.logger.info(info)
                        dts.report(info, annex=True)


                        subtitle.append(cores)
                        cmdline = rtCmdLines[cores] % (TestFM10kL3fwd.path + "l3fwd_" + mode, coreMask[cores],
                                                       self.dut.get_memory_channels(), dts.create_mask(valports[:2]))

                        if frame_size > 1518:
                            cmdline = cmdline + "  --max-pkt-len %d" % frame_size
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

                        zero_loss_rate, tx_pkts, rx_pkts = self.tester.run_rfc2544(tgenInput, delay=5, permit_loss_rate=0.01)
                        loss_pkts = tx_pkts - rx_pkts
                        self.dut.send_expect("^C", "#")

                        tx_pkts = human_read_number(tx_pkts)
                        rx_pkts = human_read_number(rx_pkts)
                        loss_pkts = human_read_number(loss_pkts)

                        data_row = [frame_size, mode, cores, str(tx_pkts), str(rx_pkts), loss_pkts, zero_loss_rate]
                        dts.results_table_add_row(data_row)
                        self.l3fwd_test_results['data'].append(data_row)
                    else:
                        pass

                    index += 1

        dts.results_table_print()

    def test_perf_rfc2544_vec(self):
        # add setting for scatter

        #mode_settings = [{'rxmode': 'default', 'txmode': 'default'}, {'rxmode': 'vector', 'txmode': 'vector'}]
        mode_settings = [{'rxmode': 'vector', 'txmode': 'vector'}]
        for mode in mode_settings:
            self.fm10k_rxmode_set(mode = mode['rxmode'])
            if mode['txmode'] == 'default':
                # need --enable-jumbo parameter
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    if "--enable-jumbo" not in TestFM10kL3fwd.test_cases_2_ports[key]:
                        TestFM10kL3fwd.test_cases_2_ports[key] += " --enable-jumbo"
            else:
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    TestFM10kL3fwd.test_cases_2_ports[key].replace(" --enable-jumbo", "")

            print GREEN("Performance test for rxmode %s txmode %s" %(mode['rxmode'], mode['txmode']))
            self.perf_rfc2544()

        # remove setting for scatter
        self.dut.send_expect("sed -i -e '/.enable_scatter= .*$/d' %s" % self.main_file, "# ")

    def test_perf_rfc2544_legacy(self):
        # add setting for scatter

        #mode_settings = [{'rxmode': 'default', 'txmode': 'default'}, {'rxmode': 'vector', 'txmode': 'vector'}]
        mode_settings = [{'rxmode': 'default', 'txmode': 'default'}]
        for mode in mode_settings:
            self.fm10k_rxmode_set(mode = mode['rxmode'])
            if mode['txmode'] == 'default':
                # need --enable-jumbo parameter
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    if "--enable-jumbo" not in TestFM10kL3fwd.test_cases_2_ports[key]:
                        TestFM10kL3fwd.test_cases_2_ports[key] += " --enable-jumbo"
            else:
                for key in TestFM10kL3fwd.test_cases_2_ports.keys():
                    TestFM10kL3fwd.test_cases_2_ports[key].replace(" --enable-jumbo", "")

            print GREEN("Performance test for rxmode %s txmode %s" %(mode['rxmode'], mode['txmode']))
            self.perf_rfc2544()

        # remove setting for scatter
        self.dut.send_expect("sed -i -e '/.enable_scatter= .*$/d' %s" % self.main_file, "# ")


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
        # remove setting for scatter
        self.dut.send_expect("sed -i -e '/.enable_scatter= .*$/d' %s" % self.main_file, "# ")
        pass
