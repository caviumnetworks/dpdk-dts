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

Test short live dpdk app Feature

"""

import time
import re
import os
from test_case import TestCase
from pmd_output import PmdOutput
from settings import FOLDERS

from packet import Packet, sniff_packets, load_sniff_packets, strip_pktload
#
#
# Test class.
#


class TestShortLiveApp(TestCase):
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

    def compile_examples(self, example):
        # compile
        out = self.dut.build_dpdk_apps("./examples/%s"%example)
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")


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
        smac = self.tester.get_mac(self.tester.get_local_port(txPort))
        dmac = self.dut.get_mac_address(txPort)
        Dut_tx_mac = self.dut.get_mac_address(rxPort)

        count = 1
        # if only one port rx/tx, we should check count 2 so that both
        # rx and tx packet are list
        if (txPort == rxPort):
            count = 2


        inst = sniff_packets(intf=rxitf, count=count)

        pktlen = pktSize - 14
        padding = pktlen - 20
        self.tester.scapy_append('sendp([Ether(src="%s", dst="%s")/IP()/Raw(load="P"*%s)], iface="%s")' % (smac, dmac, padding, txitf))

        self.tester.scapy_execute()
        time.sleep(3)

	p = load_sniff_packets(inst)
	nr_packets=len(p)
	reslist = [p[i].pktgen.pkt for i in range(nr_packets)]
	out = str(reslist)

        if received:
            self.verify(('PPP' in out) and 'src=%s'% Dut_tx_mac in out, "Receive test failed")
        else:
            self.verify('PPP' not in out, "Receive test failed")

    def test_basic_forwarding(self):
        """
        Basic rx/tx forwarding test
        """
        #dpdk start
	cmd = "./%s/app/testpmd -c 0xf -n 4 -- -i --portmask=0x3"
	if "cavium" in self.dut.nic_type:
		cmd += " --disable-hw-vlan-filter"
        self.dut.send_expect(cmd % self.target, "testpmd>", 120)
        self.dut.send_expect("set fwd mac", "testpmd>")
        self.dut.send_expect("set promisc all off", "testpmd>")
        self.dut.send_expect("start", "testpmd>")
        self.check_forwarding([0, 1], self.nic)

    def test_start_up_time(self):
        """
        Using linux time to get start up time
        """
        time = []
        regex = re.compile(".* (\d+:\d{2}\.\d{2}).*")
        out = self.dut.send_expect("echo quit | time ./%s/app/testpmd -c 0x3 -n 4 --no-pci -- -i" % self.target, "#", 120)
        time = regex.findall(out)

        if time != []:
            print "start time: %s s"%time[0]
        else:
            self.verify(0, "start_up_time failed")
	    if "time: command not found" in out:
		print "Command time is not installed or is a shell keyword" 

    def test_clean_up_with_signal_testpmd(self):
        repeat_time = 5
	cmd = "./%s/app/testpmd -c 0xf -n 4 -- -i --portmask=0x3"
	if "cavium" in self.dut.nic_type:
		cmd += " --disable-hw-vlan-filter"
        for i in range(repeat_time):
            #dpdk start
            print "clean_up_with_signal_testpmd round %d" % (i + 1)
            self.dut.send_expect(cmd % self.target, "testpmd>", 120)
            self.dut.send_expect("set fwd mac", "testpmd>")
            self.dut.send_expect("set promisc all off", "testpmd>")
            self.dut.send_expect("start", "testpmd>")
            self.check_forwarding([0, 1], self.nic)

	    pid = self.dut.send_expect("ps -o pid -C testpmd | tail -n +2", "#", 60, True)
            # kill with differen Signal
            if i%2 == 0:
                self.dut.send_expect("pkill -2 testpmd", "#", 60, True)
            else:
                self.dut.send_expect("pkill -15 testpmd", "#", 60, True)
	    # waiting for the process to truly finish
	    while True:
	    	no_lines = int(self.dut.send_expect("ps -p %d | wc -l" % int(pid), "#", 60, True))
	    	if 1 == no_lines: break # only header is printed out

    def test_clean_up_with_signal_l2fwd(self):
        repeat_time = 5
        self.compile_examples("l2fwd")
        for i in range(repeat_time):
            #dpdk start
            print "clean_up_with_signal_l2fwd round %d" % (i + 1)
            self.dut.send_expect("./examples/l2fwd/build/app/l2fwd -n 4 -c 0xf -- -p 0x3 &", "L2FWD: entering main loop", 60)
            self.check_forwarding([0, 1], self.nic)

            # kill with differen Signal
	    pid = self.dut.send_expect("ps -o pid -C l2fwd | tail -n +2", "#", 60, True)
            if i%2 == 0:
                self.dut.send_expect("pkill -2 l2fwd", "#", 60, True)
            else:
                self.dut.send_expect("pkill -15 l2fwd", "#", 60, True)
	
	    while True:
	    	no_lines = int(self.dut.send_expect("ps -p %d | wc -l" % int(pid), "#", 60, True))
	    	if 1 == no_lines: break
	    

    def test_clean_up_with_signal_l3fwd(self):
        repeat_time = 5
        self.compile_examples("l3fwd")
        for i in range(repeat_time):
            #dpdk start
            print "clean_up_with_signal_l3fwd round %d" % (i + 1)
            self.dut.send_expect("./examples/l3fwd/build/app/l3fwd -n 4 -c 0xf -- -p 0x3 --config='(0,0,1),(1,0,2)' &", "L3FWD:", 120)
            self.check_forwarding([0, 0], self.nic)

	    pid = self.dut.send_expect("ps -o pid -C l3fwd | tail -n +2", "#", 60, True)
            # kill with differen Signal
            if i%2 == 0:
                self.dut.send_expect("pkill -2 l3fwd", "#", 60, True)
            else:
                self.dut.send_expect("pkill -15 l3fwd", "#", 60, True)
	
	    while True:
	    	no_lines = int(self.dut.send_expect("ps -p %d | wc -l" % int(pid), "#", 60, True))
	    	if 1 == no_lines: break
	    
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
        self.dut.send_expect("rm -rf ./app/test-pmd/testpmd", "#")
        self.dut.send_expect("rm -rf ./app/test-pmd/*.o", "#")
        self.dut.send_expect("rm -rf ./app/test-pmd/build", "#")
