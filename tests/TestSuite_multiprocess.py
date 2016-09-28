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
Multi-process Test.
"""

import utils
import time
from etgen import IxiaPacketGenerator
executions = []
from test_case import TestCase


class TestMultiprocess(TestCase, IxiaPacketGenerator):

    def set_up_all(self):
        """
        Run at the start of each test suite.

        Multiprocess prerequisites.
        Requirements:
            OS is not freeBSD
            DUT core number >= 4
            multi_process build pass
        """
        #self.verify('bsdapp' not in self.target, "Multiprocess not support freebsd")

        self.verify(len(self.dut.get_all_cores()) >= 4, "Not enough Cores")
        self.tester.extend_external_packet_generator(TestMultiprocess, self)

        out = self.dut.build_dpdk_apps("./examples/multi_process/")
        self.verify('Error' not in out, "Compilation failed")

        executions.append({'nprocs': 1, 'cores': '1S/1C/1T', 'pps': 0})
        executions.append({'nprocs': 2, 'cores': '1S/1C/2T', 'pps': 0})
        executions.append({'nprocs': 2, 'cores': '1S/2C/1T', 'pps': 0})
        executions.append({'nprocs': 4, 'cores': '1S/2C/2T', 'pps': 0})
        executions.append({'nprocs': 4, 'cores': '1S/4C/1T', 'pps': 0})
        executions.append({'nprocs': 8, 'cores': '1S/4C/2T', 'pps': 0})
        self.dut.alt_session.send_expect("cd dpdk","# ",5)

       # start new session to run secondary
        self.session_secondary = self.dut.new_session()

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def test_multiprocess_simple_mpbasicoperation(self):
        """
        Basic operation.
        """
        # Send message from secondary to primary
        cores = self.dut.get_core_list('1S/2C/1T')
        coremask = utils.create_mask(cores)
        self.dut.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=primary" % (self.target, coremask), "Finished Process Init", 100)
        time.sleep(20)
        coremask = hex(int(coremask, 16) * 0x10000).rstrip("L")
        self.session_secondary.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=secondary" % (self.target, coremask), "Finished Process Init", 100)

        self.session_secondary.send_expect("send hello_primary", ">")
        out = self.dut.get_session_output()
        self.session_secondary.send_expect("quit", "# ")
        self.dut.send_expect("quit","# ")
        self.verify("Received 'hello_primary'" in out, "Message not received on primary process")
        # Send message from primary to secondary
        cores = self.dut.get_core_list('1S/2C/1T')
        coremask = utils.create_mask(cores)
        self.session_secondary.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=primary " % (self.target, coremask), "Finished Process Init", 100)
        time.sleep(20)
        coremask = hex(int(coremask, 16) * 0x10000).rstrip("L")
        self.dut.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=secondary" % (self.target, coremask), "Finished Process Init", 100)
        self.session_secondary.send_expect("send hello_secondary", ">")
        out = self.dut.get_session_output()
        self.session_secondary.send_expect("quit", "# ")
        self.dut.send_expect("quit", "# ")

        self.verify("Received 'hello_secondary'" in out,
                    "Message not received on primary process")

    def test_multiprocess_simple_mploadtest(self):
        """
        Load test of Simple MP application.
        """

        cores = self.dut.get_core_list('1S/2C/1T')
        coremask = utils.create_mask(cores)
        self.session_secondary.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=primary" % (self.target, coremask), "Finished Process Init", 100)
        time.sleep(20)
        coremask = hex(int(coremask, 16) * 0x10000).rstrip("L")
        self.dut.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=secondary" % (self.target, coremask), "Finished Process Init", 100)
        stringsSent = 0
        for line in open('/usr/share/dict/words', 'r').readlines():
            line = line.split('\n')[0]
            self.dut.send_expect("send %s" % line, ">")
            stringsSent += 1
            if stringsSent == 3:
                break

        time.sleep(5)
        self.dut.send_expect("quit", "# ")
        self.session_secondary.send_expect("quit", "# ")

    def test_multiprocess_simple_mpapplicationstartup(self):
        """
        Test use of Auto for Application Startup.
        """

        # Send message from secondary to primary (auto process type)
        cores = self.dut.get_core_list('1S/2C/1T')
        coremask = utils.create_mask(cores)
        out = self.dut.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=auto " % (self.target, coremask), "Finished Process Init", 100)
        self.verify("EAL: Auto-detected process type: PRIMARY" in out, "The type of process (PRIMARY) was not detected properly")
        time.sleep(20)
        coremask = hex(int(coremask, 16) * 0x10000).rstrip("L")
        out = self.session_secondary.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=auto" % (self.target, coremask), "Finished Process Init", 100)
        self.verify("EAL: Auto-detected process type: SECONDARY" in out,
                    "The type of process (SECONDARY) was not detected properly")

        self.session_secondary.send_expect("send hello_primary", ">")
        out = self.dut.get_session_output()
        self.session_secondary.send_expect("quit", "# ")
        self.dut.send_expect("quit", "# ")
        self.verify("Received 'hello_primary'" in out, "Message not received on primary process")

        # Send message from primary to secondary (auto process type)
        cores = self.dut.get_core_list('1S/2C/1T')
        coremask = utils.create_mask(cores)
        out = self.session_secondary.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=auto" % (self.target, coremask), "Finished Process Init", 100)
        self.verify("EAL: Auto-detected process type: PRIMARY" in out, "The type of process (PRIMARY) was not detected properly")
        time.sleep(20)
        coremask = hex(int(coremask, 16) * 0x10000).rstrip("L")
        out = self.dut.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s --proc-type=auto" % (self.target, coremask), "Finished Process Init", 100)
        self.verify("EAL: Auto-detected process type: SECONDARY" in out, "The type of process (SECONDARY) was not detected properly")
        self.session_secondary.send_expect("send hello_secondary", ">",100)
        out = self.dut.get_session_output()
        self.session_secondary.send_expect("quit", "# ")
        self.dut.send_expect("quit", "# ")

        self.verify("Received 'hello_secondary'" in out,
                    "Message not received on primary process")

    def test_multiprocess_simple_mpnoflag(self):
        """
        Multiple processes without "--proc-type" flag.
        """

        cores = self.dut.get_core_list('1S/2C/1T')
        coremask = utils.create_mask(cores)
        self.session_secondary.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s -m 64" % (self.target, coremask), "Finished Process Init", 100)
        coremask = hex(int(coremask, 16) * 0x10000).rstrip("L")
        out = self.dut.send_expect("./examples/multi_process/simple_mp/simple_mp/%s/simple_mp -n 1 -c %s" % (self.target, coremask), "# ", 100)

        self.verify("Is another primary process running" in out,
                    "No other primary process detected")

        self.session_secondary.send_expect("quit", "# ")

    def test_perf_multiprocess_client_serverperformance(self):
        """
        Benchmark Multiprocess client-server performance.
        """
        self.dut.kill_all()
        self.dut.send_expect("fg", "# ")
        dutPorts = self.dut.get_ports()
        txPort = self.tester.get_local_port(dutPorts[0])
        rxPort = self.tester.get_local_port(dutPorts[1])
        mac = self.tester.get_mac(txPort)

        self.tester.scapy_append('dmac="%s"' % self.dut.get_mac_address(dutPorts[0]))
        self.tester.scapy_append('smac="%s"' % mac)
        if not self.dut.want_perf_tests:
            self.tester.scapy_append('flows = [Ether(src=smac, dst=dmac)/IP(src="192.168.1.%s" % src, dst="192.168.1.%s" % dst)/("X"*26) for src in range(64) for dst in range(64)]')
        else:
            self.tester.scapy_append('flows = [Ether(src=smac, dst=dmac)/IP(src="192.168.1.1", dst="192.168.1.1")/("X"*26)]')
        self.tester.scapy_append('wrpcap("test.pcap", flows)')
        self.tester.scapy_execute()

        validExecutions = []
        for execution in executions:
            if len(self.dut.get_core_list(execution['cores'])) == execution['nprocs']:
                validExecutions.append(execution)

        for execution in validExecutions:
            coreList = self.dut.get_core_list(execution['cores'])

            coreMask = utils.create_mask(self.dut.get_core_list('1S/1C/1T'))
            portMask = utils.create_mask([dutPorts[0], dutPorts[1]])
            self.dut.send_expect("./examples/multi_process/client_server_mp/mp_server/client_server_mp/mp_server/%s/mp_server -n %d -c %s -- -p %s -n %d" % (self.target, self.dut.get_memory_channels(), "0xA0", portMask, execution['nprocs']), "Finished Process Init", 20)
            self.dut.send_expect("^Z", "\r\n")
            self.dut.send_expect("bg", "# ")

            for n in range(execution['nprocs']):
                time.sleep(5)
                coreMask = utils.create_mask([coreList[n]])
                self.dut.send_expect("./examples/multi_process/client_server_mp/mp_client/client_server_mp/mp_client/%s/mp_client -n %d -c %s --proc-type=secondary -- -n %d" % (self.target, self.dut.get_memory_channels(), coreMask, n), "Finished Process Init")
                self.dut.send_expect("^Z", "\r\n")
                self.dut.send_expect("bg", "# ")

            tgenInput = []
            tgenInput.append([txPort, rxPort, "test.pcap"])
            _, pps = self.tester.traffic_generator_throughput(tgenInput)
            execution['pps'] = pps
            self.dut.kill_all()
            time.sleep(5)

        for n in range(len(executions)):
            self.verify(executions[n]['pps'] is not 0, "No traffic detected")

        self.result_table_create(['Server threads', 'Server Cores/Threads', 'Num-procs', 'Sockets/Cores/Threads', 'Num Ports', 'Frame Size', '%-age Line Rate', 'Packet Rate(mpps)'])

        for execution in validExecutions:
            self.result_table_add([1, '1S/1C/1T', execution['nprocs'], execution['cores'], 2, 64, execution['pps'] / float(100000000 / (8 * 84)), execution['pps'] / float(1000000)])

        self.result_table_print()

    def ip(self, port, frag, src, proto, tos, dst, chksum, len, options, version, flags, ihl, ttl, id):
        self.add_tcl_cmd("protocol config -name ip")
        self.add_tcl_cmd('ip config -sourceIpAddr "%s"' % src)
        self.add_tcl_cmd('ip config -sourceIpAddrMode ipIncrHost')
        self.add_tcl_cmd('ip config -sourceIpAddrRepeatCount %d' % 64)
        self.add_tcl_cmd('ip config -destIpAddr "%s"' % dst)
        self.add_tcl_cmd('ip config -destIpAddrMode ipIncrHost')
        self.add_tcl_cmd('ip config -destIpAddrRepeatCount %d' % 64)
        self.add_tcl_cmd("ip config -ttl %d" % ttl)
        self.add_tcl_cmd("ip config -totalLength %d" % len)
        self.add_tcl_cmd("ip config -fragment %d" % frag)
        self.add_tcl_cmd("ip config -ipProtocol %d" % proto)
        self.add_tcl_cmd("ip config -identifier %d" % id)
        self.add_tcl_cmd("stream config -framesize %d" % (len + 18))
        self.add_tcl_cmd("ip set %d %d %d" % (self.chasId, port['card'], port['port']))

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
        self.dut.close_session(self.session_secondary)

        pass
