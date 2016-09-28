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
Layer-3 forwarding exact-match test script.
"""

import utils
import string
import re
from test_case import TestCase
from exception import VerifyFailure
from settings import HEADER_SIZE
from etgen import IxiaPacketGenerator
from utils import *

class TestL3fwdEM(TestCase,IxiaPacketGenerator):

    path = "./examples/l3fwd/build/"

    test_cases_2_ports = {"1S/1C/1T": "%s -c %s -n %d -- -p %s -E --config '(P0,0,C{1.1.0}), (P1,0,C{1.1.0})' --hash-entry-num 0x400000",
                          "1S/2C/1T": "%s -c %s -n %d -- -p %s -E --config '(P0,0,C{1.1.0}), (P1,0,C{1.2.0})' --hash-entry-num 0x400000",
                          "1S/4C/1T": "%s -c %s -n %d -- -p %s -E --config '(P0,0,C{1.1.0}), (P1,0,C{1.2.0}),(P0,1,C{1.3.0}), (P1,1,C{1.4.0})' --hash-entry-num 0x400000"
                          }


    frame_sizes = [64, 65, 128, 256, 512, 1518]  # 65, 128
    methods = ['exact']

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

    def set_up_all(self):
        """
        Run at the start of each test suite.


        L3fwd Prerequisites
        """
        # Based on h/w type, choose how many ports to use
        ports = self.dut.get_ports(socket=1)
        if not ports:
            ports = self.dut.get_ports(socket=0)

        self.tester.extend_external_packet_generator(TestL3fwdEM, self)
        # Verify that enough ports are available
        self.verify(len(ports) >= 2, "Insufficient ports for speed testing")
        
        netdev = self.dut.ports_info[ports[0]]['port']
        
        self.port_socket = netdev.socket
        

        # Verify that enough threads are available
        cores = self.dut.get_core_list("1S/8C/2T")
        self.verify(cores is not None, "Insufficient cores for speed testing")

        global valports
        valports = [_ for _ in ports if self.tester.get_local_port(_) != -1]
        
        self.verify(len(valports) >= 2, "Insufficient active ports for speed testing")

        pat = re.compile("P([0123])")

        # Update config file and rebuild to get best perf on FVL
        self.dut.send_expect("sed -i -e 's/CONFIG_RTE_PCI_CONFIG=n/CONFIG_RTE_PCI_CONFIG=y/' ./config/common_linuxapp", "#", 20)
        self.dut.send_expect("sed -i -e 's/CONFIG_RTE_PCI_EXTENDED_TAG=.*$/CONFIG_RTE_PCI_EXTENDED_TAG=\"on\"/' ./config/common_linuxapp", "#", 20)
        self.dut.build_install_dpdk(self.target)


        
        out = self.dut.build_dpdk_apps("./examples/l3fwd")
        self.verify("Error" not in out, "compilation error 1")
        self.verify("No such file" not in out, "compilation error 2")


        self.l3fwd_test_results = {'header': [],
                                   'data': []}


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


    def test_perf_l3fwd_2ports(self):
        """
        L3fwd main 2 ports.
        """

        header_row = ["Frame", "mode", "S/C/T", "Mpps", "% linerate"]
        self.l3fwd_test_results['header'] = header_row
        self.result_table_create(header_row)
        self.l3fwd_test_results['data'] = []

        for frame_size in TestL3fwdEM.frame_sizes:

            # Prepare traffic flow
            payload_size = frame_size -  \
                HEADER_SIZE['ip'] - HEADER_SIZE['eth'] - HEADER_SIZE['tcp']
            
            # Traffic for port0
            dmac_port0 = self.dut.get_mac_address(valports[0])
            flow1 = '[Ether(dst="%s")/IP(src="200.20.0.1",dst="201.0.0.0")/TCP(sport=12,dport=102)/("X"*%d)]' %(dmac_port0,payload_size)
            self.tester.scapy_append('wrpcap("dst0.pcap",%s)' %flow1)

            # Traffic for port1
            dmac_port1 = self.dut.get_mac_address(valports[1])
            flow2 = '[Ether(dst="%s")/IP(src="100.10.0.1",dst="101.0.0.0")/TCP(sport=11,dport=101)/("X"*%d)]' %(dmac_port1,payload_size)
            self.tester.scapy_append('wrpcap("dst1.pcap",%s)' %flow2)
            self.tester.scapy_execute()



            # Prepare the command line
            global corelist
            pat = re.compile("P([0123]),([0123]),(C\{\d.\d.\d\})")
            
            pat2 = re.compile("C\{\d")
            repl1 = "C{" + str(self.port_socket)

            coreMask = {}
            rtCmdLines = dict(TestL3fwdEM.test_cases_2_ports)
            for key in rtCmdLines.keys():
                corelist = []
                while pat.search(rtCmdLines[key]):
                    # Change the socket to the NIC's socket
                    if key.find('1S')>=0:
                        rtCmdLines[key] = pat2.sub(repl1, rtCmdLines[key])
                    rtCmdLines[key] = pat.sub(self.repl, rtCmdLines[key])

                self.logger.info("%s\n" % str(corelist))
                coreMask[key] = utils.create_mask(set(corelist))

            # measure by two different mode
            for mode in TestL3fwdEM.methods:

                # start l3fwd
                index = 0
                subtitle = []
                for cores in rtCmdLines.keys():

                    info = "Executing l3fwd using %s mode, 2 ports, %s and %d frame size.\n" % (
                           mode, cores, frame_size)

                    self.logger.info(info)
                    self.rst_report(info, annex=True)

                    subtitle.append(cores)
                    cmdline = rtCmdLines[cores] % (TestL3fwdEM.path + "l3fwd", coreMask[cores],
                                                   self.dut.get_memory_channels(), utils.create_mask(valports[:2]))

                    self.rst_report(cmdline + "\n", frame=True, annex=True)

                    out = self.dut.send_expect(cmdline, "L3FWD: entering main loop", 120)
            
                    
                    print self.dut.get_session_output(timeout=3)           
                    

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
                    
                    _, pps = self.tester.traffic_generator_throughput(tgenInput,delay=20)
                    
                    self.verify(pps > 0, "No traffic detected")
                    pps /= 1000000.0
                    linerate = self.wirespeed(self.nic, frame_size, 2)
                    pct = pps * 100 / linerate

                    index += 1

                    # Stop l3fwd
                    self.dut.send_expect("^C", "#")
                    data_row = [frame_size, mode, cores, str(pps), str(pct)]
                    self.result_table_add(data_row)
                    self.l3fwd_test_results['data'].append(data_row)

        self.result_table_print()


    def ip(self, port, frag, src, proto, tos, dst, chksum, len, options, version, flags, ihl, ttl, id):
        self.add_tcl_cmd("protocol config -name ip")
        self.add_tcl_cmd("ip config -ipProtocol ipV4ProtocolTcp")
        self.add_tcl_cmd('ip config -sourceIpAddr "%s"' % src)
        self.add_tcl_cmd("ip config -sourceIpAddrMode ipIdle")
        self.add_tcl_cmd('ip config -destIpAddr "%s"' % dst)
        self.add_tcl_cmd("ip config -destIpAddrMode ipContIncrHost")
        self.add_tcl_cmd("ip config -destIpMask '255.240.0.0'")
        self.add_tcl_cmd("ip config -ttl %d" % ttl)
        self.add_tcl_cmd("ip config -totalLength %d" % len)
        self.add_tcl_cmd("ip config -fragment %d" % frag)
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
