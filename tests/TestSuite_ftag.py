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

Test ftag feature

"""

import re
import os
import time
import dut
from config import PortConf
from test_case import TestCase
from pmd_output import PmdOutput
from settings import FOLDERS
from packet import Packet

#
#
# Test class.
#


class TestFtag(TestCase):
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        """
        self.verify(self.nic in ['redrockcanyou','atwood','boulderrapid'], 'ftag test can not support %s nic'%self.nic) 
        self.ports = self.dut.get_ports(self.nic)
        self.verify(len(self.ports) >= 2, "Insufficient number of ports.")
        patch_file = r'dep/fm10k-add-a-unit-test-for-FTAG-based-forwarding.patch'
        patch_dst = "/tmp/"
        self.dut.session.copy_file_to(patch_file, patch_dst)
        self.patch_hotfix_dpdk(patch_dst + "fm10k-add-a-unit-test-for-FTAG-based-forwarding.patch", True)
        self.dut.send_expect("sed -i -e '/CONFIG_RTE_VIRTIO_USER=y/a\CONFIG_RTE_LIBRTE_FM10K_FTAG_FWD=y' config/common_linuxapp", "# ")
        self.dut.send_expect("sed -i -e '/SRCS-y += test_pmd_perf.c/a\SRCS-y += test_fm10k_ftag.c' app/test/Makefile", "# ")
        self.dut.build_install_dpdk(self.dut.target)

         
    def set_up(self):
        """
        Run before each test case.
        """
        pass


    def check_forwarding(self, txPort, rxPort, nic, received=True):
        self.send_packet(txPort, rxPort, self.nic, received)
   
    def send_packet(self, txPort, rxPort, nic, received=True): 
        """
        Send packages according to parameters.
        """
        rxitf = self.tester.get_interface(self.tester.get_local_port(rxPort))
        txitf = self.tester.get_interface(self.tester.get_local_port(txPort))

        dmac_tx = self.dut.get_mac_address(txPort)
        dmac_rx = self.dut.get_mac_address(rxPort)

        pkg = 'Ether(dst="%s",src="52:00:00:00:00:00")/IP()/TCP()/("X"*46)' %dmac_rx 
        self.tester.scapy_foreground()
        self.tester.scapy_append('sendp(%s, iface="%s")' % (pkg, txitf))
        self.tester.scapy_execute()
        time.sleep(3)

    def patch_hotfix_dpdk(self, patch_dir, on = True):
        """
        This function is to apply or remove patch for dpdk.
        patch_dir: the abs path of the patch
        on: True for apply, False for remove
        """
        if on:
            self.dut.send_expect("patch -p1 < %s" % patch_dir, "#")
        else:
            self.dut.send_expect("patch -p1 -R < %s" % patch_dir, "#")


    def test_ftag_function(self):
        """
        ftag functional test
        """
        self.dut.send_expect("./%s/app/testpmd -c f -n 4 -- -i" %self.dut.target,"testpmd", 60)
        self.tx_port = self.ports[0]
        self.rx_port = self.ports[1]

        dmac_tx = self.dut.get_mac_address(self.tx_port)
        dmac_rx = self.dut.get_mac_address(self.rx_port)
        """
        get port glort id in the mac table of testpoint switch
        """
        if self.kdriver == "fm10k": 
            netobj = self.dut.ports_info[self.tx_port]['port']
            port0_glortid = netobj.get_glortid_bymac(dmac_tx)
            port1_glortid = netobj.get_glortid_bymac(dmac_rx)
        
        self.dut.send_expect("quit", "# ")
        """
        export port glort id
        """
        self.dut.send_expect("export PORT0_GLORT=%s" %port0_glortid, "#", 2)        
        self.dut.send_expect("export PORT1_GLORT=%s" %port1_glortid, "#", 2)   
        enable_ftag_ports = ''
        for port in range(0,len(self.ports)):
            pci_bus = self.dut.ports_info[port]['pci']
            enable_ftag_ports += '-w %s,enable_ftag=1 ' % pci_bus
        self.dut.send_expect("./%s/app/test -c f -n 4 %s" %(self.dut.target,enable_ftag_ports),"R.*T.*E.*>.*>", 60)

        #fm10k ftag auto test
        for txport in range(0,len(self.ports)):
            for rxport in range(0,len(self.ports)):
                self.dut.send_expect("fm10k_ftag_autotest", "Dump", 100)
                self.check_forwarding(txport, rxport, self.nic, received=False)
                out = self.dut.get_session_output()
                print "out:%s" %out
                self.verify("Test OK" in out, "Fail to do fm10k ftag test")
        self.dut.send_expect("quit", "# ")

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
        self.dut.send_expect("sed -i  '/CONFIG_RTE_LIBRTE_FM10K_FTAG_FWD=y/d' config/common_linuxapp", "# ")
        self.dut.send_expect("sed -i  '/SRCS-y += test_fm10k_ftag.c/d' app/test/Makefile", "# ")
        patch_dst = "/tmp/"
        self.patch_hotfix_dpdk(patch_dst + "fm10k-add-a-unit-test-for-FTAG-based-forwarding.patch", False)
        self.dut.build_install_dpdk(self.dut.target)
