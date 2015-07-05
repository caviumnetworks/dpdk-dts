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

Test queue start stop Feature

"""

import dts
import time
import re
import os
from test_case import TestCase
from pmd_output import PmdOutput

#
#
# Test class.
#


class TestQueueStartStop(TestCase):
    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.ports = self.dut.get_ports(self.nic)
        self.verify(len(self.ports) >= 2, "Insufficient number of ports.")

    def set_up(self):
        """
        Run before each test case.
        """
        pass

    def check_forwarding(self, ports, nic, testerports=[None, None], pktSize=64, received=True):
        self.send_packet(ports[0], ports[1], self.nic, testerports[1], pktSize, received)

    def send_packet(self, txPort, rxPort, nic, testerports=None, pktSize=64, received=True):
        """
        Send packages according to parameters.
        """

        if testerports is None:
            rxitf = self.tester.get_interface(self.tester.get_local_port(rxPort))
            txitf = self.tester.get_interface(self.tester.get_local_port(txPort))
        else:
            itf = testerports
        mac = self.dut.get_mac_address(txPort)

        self.tester.scapy_background()
        self.tester.scapy_append('p=sniff(iface="%s",count=1,timeout=5)' % rxitf)
        self.tester.scapy_append('RESULT=str(p)')

        self.tester.scapy_foreground()

        pktlen = pktSize - 14
        padding = pktlen - 20
        self.tester.scapy_append('sendp([Ether(dst="%s")/IP()/Raw(load="P"*%s)], iface="%s")' % (mac, padding, txitf))

        self.tester.scapy_execute()
        time.sleep(3)

        out = self.tester.scapy_get_result()
        if received:
            self.verify('PPP' in out, "start queue failed")
        else:
            self.verify('PPP' not in out, "stop queue failed")

    def add_code_to_dpdk(self, file_name, standard_row, add_rows, offset=0):
        """
        this function for add code in dpdk src code file.
        file: source code full path
        standard_row: standard row for find the place that add code
        offset: need offset row number
        add_rows:add source code

        return: source code lines
        """
        file_handel = open(file_name, "r+w")
        source_lines = file_handel.readlines()

        write_lines = source_lines

        # get the index that need add code
        index = -1
        for line in write_lines:
            if standard_row in line:
                index = write_lines.index(line) + offset
                break

        # add source code and re-write the file
        # print write_lines,index
        for line in add_rows:
            write_lines.insert(index, line)
            index += 1
        # print write_lines
        file_handel.seek(file_handel.tell() * -1, 2)
        file_handel.writelines(write_lines)
        file_handel.close()

        return source_lines

    def test_queue_start_stop(self):
        """
        queue start/stop test for fortville nic
        """
        self.dut.session.copy_file_from(r'%s/app/test-pmd/macfwd.c' % self.dut.base_dir)
        fwdmac_file = 'macfwd.c'
        printf_lines = ['printf("ports %u queue %u revice %u packages", fs->rx_port, fs->rx_queue, nb_rx);\n', r'printf("\n");',"\n"]
        sourcelines = self.add_code_to_dpdk(fwdmac_file, r'(unlikely(nb_rx == 0)', printf_lines, 2)
        self.dut.session.copy_file_to(fwdmac_file)
        self.dut.send_expect('scp  /root/macfwd.c %s/app/test-pmd/macfwd.c' % self.dut.base_dir, "#")
        self.dut.build_dpdk_apps('./app/test-pmd')

        self.dut.send_expect("./app/test-pmd/testpmd -c 0xf -n 4 -- -i --portmask=0x3", "testpmd>", 120)
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        self.check_forwarding([0, 1], self.nic)

        # stop rx queue test
        print "test stop rx queue"
        self.dut.send_expect("stop", "testpmd>")
        self.dut.send_expect("port 0 rxq 0 stop", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        self.check_forwarding([0, 1], self.nic, received=False)

        # start rx queue test
        print "test start rx queue stop tx queue"
        self.dut.send_expect("stop", "testpmd>")
        self.dut.send_expect("port 0 rxq 0 start", "testpmd>")
        self.dut.send_expect("port 1 txq 0 stop", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        self.check_forwarding([0, 1], self.nic, received=False)
        out = self.dut.send_expect("\n", "testpmd>")
        # print out
        self.verify("ports 0 queue 0 revice 1 packages" in out, "start queue revice package failed")

        # start tx queue test
        print "test start rx and tx queue"
        self.dut.send_expect("stop", "testpmd>")
        self.dut.send_expect("port 0 rxq 0 start", "testpmd>")
        self.dut.send_expect("port 1 txq 0 start", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        self.check_forwarding([0, 1], self.nic)
        self.dut.send_expect("quit", "testpmd>")

        # recover testpmd changed
        file_handel = open(fwdmac_file, "w")
        file_handel.writelines(sourcelines)
        file_handel.close()
        self.dut.session.copy_file_to(fwdmac_file)
        self.dut.send_expect('scp  /root/macfwd.c %s/app/test-pmd/macfwd.c' % self.dut.base_dir, "#")

    def tear_down(self):
        """
        Run after each test case.
        """
        self.dut.kill_all()

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
        #self.dut.send_expect("rm -rf ./app/test-pmd/testpmd", "#")
        #self.dut.send_expect("rm -rf ./app/test-pmd/*.o", "#")
        #self.dut.send_expect("rm -rf ./app/test-pmd/build", "#")
