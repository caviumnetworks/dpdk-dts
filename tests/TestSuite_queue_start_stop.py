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
from settings import FOLDERS

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
        try:
            patch_file = FOLDERS["Depends"] + r'/macfwd_log.patch'
        except:
            self.logger.warning(str(FOLDERS))
            patch_file = r'dep/macfwd_log.patch'
            FOLDERS["Depends"] = 'dep'
        patch_dst = "/tmp/"

        # dpdk patch and build
        try:
            self.dut.session.copy_file_to(patch_file, patch_dst)
            self.patch_hotfix_dpdk(patch_dst + "macfwd_log.patch", True)
            self.dut.build_dpdk_apps('./app/test-pmd')
        except Exception, e:
            raise IOError("dpdk setup failure: %s" % e)

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

        self.tester.scapy_background()
        self.tester.scapy_append('p=sniff(iface="%s",count=1,timeout=5)' % rxitf)
        self.tester.scapy_append('RESULT=str(p)')

        self.tester.scapy_foreground()

        pktlen = pktSize - 14
        padding = pktlen - 20
        self.tester.scapy_append('sendp([Ether(src="%s", dst="%s")/IP()/Raw(load="P"*%s)], iface="%s")' % (smac, dmac, padding, txitf))

        self.tester.scapy_execute()
        time.sleep(3)

        out = self.tester.scapy_get_result()
        if received:
            self.verify('PPP' in out, "start queue failed")
        else:
            self.verify('PPP' not in out, "stop queue failed")

    def patch_hotfix_dpdk(self, patch_dir, on = True):
        """
        This function is to apply or remove patch for dpdk.
        patch_dir: the abs path of the patch
        on: True for apply, False for remove
        """
        try:
            if on:
                self.dut.send_expect("patch -p0 < %s" % patch_dir, "#")
            else:
                self.dut.send_expect("patch -p0 -R < %s" % patch_dir, "#")
        except Exception, e:
            raise ValueError("patch_hotfix_dpdk failure: %s" % e)

    def test_queue_start_stop(self):
        """
        queue start/stop test
        """
        #dpdk start
        try:
            self.dut.send_expect("./app/test-pmd/testpmd -c 0xf -n 4 -- -i --portmask=0x1 --port-topology=loop", "testpmd>", 120)
            self.dut.send_expect("set fwd mac", "testpmd>")
            self.dut.send_expect("start", "testpmd>")
            self.check_forwarding([0, 0], self.nic)
        except Exception, e:
            raise IOError("dpdk start and first forward failure: %s" % e)

            # stop rx queue test
        try:
            print "test stop rx queue"
            self.dut.send_expect("stop", "testpmd>")
            self.dut.send_expect("port 0 rxq 0 stop", "testpmd>")
            self.dut.send_expect("start", "testpmd>")
            self.check_forwarding([0, 0], self.nic, received=False)

            # start rx queue test
            print "test start rx queue stop tx queue"
            self.dut.send_expect("stop", "testpmd>")
            self.dut.send_expect("port 0 rxq 0 start", "testpmd>")
            self.dut.send_expect("port 0 txq 0 stop", "testpmd>")
            self.dut.send_expect("start", "testpmd>")
            self.check_forwarding([0, 0], self.nic, received=False)
            out = self.dut.get_session_output()
        except Exception, e:
            raise IOError("queue start/stop forward failure: %s" % e)

        self.verify("ports 0 queue 0 receive 1 packages" in out, "start queue revice package failed, out = %s"%out)

        try:
            # start tx queue test
            print "test start rx and tx queue"
            self.dut.send_expect("stop", "testpmd>")
            self.dut.send_expect("port 0 txq 0 start", "testpmd>")
            self.dut.send_expect("start", "testpmd>")
            self.check_forwarding([0, 0], self.nic)
        except Exception, e:
            raise IOError("queue start/stop forward failure: %s" % e)

    def tear_down(self):
        """
        Run after each test case.
        """
        patch_dst = "/tmp/"

        try:
            self.dut.send_expect("stop", "testpmd>")
            self.dut.send_expect("quit", "testpmd>")
        except:
            print "Failed to quit testpmd"

        self.dut.kill_all()

        try:
            self.patch_hotfix_dpdk(patch_dst + "macfwd_log.patch", False)
        except Exception, e:
            print "patch_hotfix_dpdk remove failure :%s" %e

    def tear_down_all(self):
        """
        Run after each test suite.
        """
        self.dut.kill_all()
        self.dut.send_expect("rm -rf ./app/test-pmd/testpmd", "#")
        self.dut.send_expect("rm -rf ./app/test-pmd/*.o", "#")
        self.dut.send_expect("rm -rf ./app/test-pmd/build", "#")
