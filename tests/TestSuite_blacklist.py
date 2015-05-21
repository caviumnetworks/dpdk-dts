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
Test device blacklisting.
"""
import dts
from test_case import TestCase
from pmd_output import PmdOutput

class TestBlackList(TestCase):
    def set_up_all(self):
        """
        Run at the start of each test suite.
        Blacklist Prerequisites.
        Requirements:
            Two Ports
        """
        self.ports = self.dut.get_ports()
        self.verify(len(self.ports) >= 2, "Insufficient ports for testing")
        [arch, machine, self.env, toolchain] = self.target.split('-')

        if self.env == 'bsdapp':
            self.regexp_blacklisted_port = "EAL: PCI device 0000:%02x:%s on NUMA socket [-0-9]+[^\n]*\nEAL:   probe driver[^\n]*\nEAL:   Device is blacklisted, not initializing"
        else:
            self.regexp_blacklisted_port = "EAL: PCI device 0000:%s on NUMA socket [-0-9]+[^\n]*\nEAL:   probe driver[^\n]*\nEAL:   Device is blacklisted, not initializing"
        self.pmdout = PmdOutput(self.dut)

    def set_up(self):
        """
        Run before each test case.
        Nothing to do.
        """
        pass

    def check_blacklisted_ports(self, output, ports, blacklisted=False):
        """
        Check if any of the ports in `ports` have been blacklisted, if so, raise
        exception.
        If `blacklisted` is True, then raise an exception if any of the ports
        in `ports` have not been blacklisted.
        """
        for port in ports:
            # Look for the PCI ID of each card followed by
            # "Device is blacklisted, not initializing" but avoid to consume more
            # than one device.
            if self.env == 'bsdapp':
                pci = self.dut.ports_info[port]['pci']
                regexp_blacklisted_port = self.regexp_blacklisted_port % (int(pci.split(':')[0], 16), pci.split(':')[1])
            else:
                regexp_blacklisted_port = self.regexp_blacklisted_port % self.dut.ports_info[port]['pci']
            matching_ports = dts.regexp(output, regexp_blacklisted_port, True)
            if blacklisted:
                self.verify(len(matching_ports) == 1,
                            "Blacklisted port is being initialized")
            else:
                self.verify(len(matching_ports) == 0,
                            "Not blacklisted port is being blacklisted")

    def test_bl_noblacklisted(self):
        """
        Run testpmd with no blacklisted device.
        """
        out = self.pmdout.start_testpmd("Default")
        rexp = r"Link"
        match_status = dts.regexp(out, rexp, True)

        self.check_blacklisted_ports(out, self.ports)

    def test_bl_oneportblacklisted(self):
        """
        Run testpmd with one port blacklisted.
        """
        self.dut.kill_all()
        out = self.pmdout.start_testpmd("Default", eal_param="-b 0000:%s -- -i" % self.dut.ports_info[0]['pci'])
        self.check_blacklisted_ports(out, self.ports[1:])

    def test_bl_allbutoneportblacklisted(self):
        """
        Run testpmd with all but one port blacklisted.
        """
        self.dut.kill_all()
        ports_to_blacklist = self.ports[:-1]
        cmdline = ""
        for port in ports_to_blacklist:
            cmdline += " -b 0000:%s" % self.dut.ports_info[port]['pci']
        out = self.pmdout.start_testpmd("Default", eal_param=cmdline)
        blacklisted_ports = self.check_blacklisted_ports(out,
                                              ports_to_blacklist, True)

    def tear_down(self):
        """
        Run after each test case.
        Quit testpmd.
        """
        self.dut.send_expect("quit", "# ", 10)
    def tear_down_all(self):
        """
        Run after each test suite.
        Nothing to do.
        """
        pass
