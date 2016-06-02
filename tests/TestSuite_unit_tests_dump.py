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

import re

"""
DPDK Test suite.

Run Inter-VM share memory autotests
"""


from test_case import TestCase

#
#
# Test class.
#


class TestUnitTestsDump(TestCase):

    #
    #
    #
    # Test cases.
    #

    def set_up_all(self):
        """
        Run at the start of each test suite.
        Nothing to do here.
        """
        # Based on h/w type, choose how many ports to use
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= 1, "Insufficient ports for testing")
        self.start_test_time = 60
        self.run_cmd_time = 60

    def set_up(self):
        """
        Run before each test case.
        Nothing to do here.
        """
        pass

    def test_log_dump(self):
        """
        Run history log dump test case.
        """
        self.dut.send_expect("./%s/app/test -n 1 -c ffff" % (self.target), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_log_history", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")
        self.verify("EAL" in out, "Test failed")

    def test_ring_dump(self):
        """
        Run history log dump test case.
        """
        self.dut.send_expect("./%s/app/test -n 1 -c ffff" % (self.target), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_ring", "RTE>>", self.run_cmd_time)
        self.dut.send_expect("quit", "# ")
        elements = ['ring', 'address', 'flags', 'size', 'ct', 'ch', 'pt', 'ph', 'used', 'avail', 'watermark']
        match_regex = "ring <(.*?)>@0x(.*)\r\n"
        for element in elements[2:]:
            match_regex += "  %s=(\d*)\r\n" % element
        m = re.compile(r"%s" % match_regex, re.S)
        result = m.search(out)
        ring_info = dict(zip(elements, result.groups()))

        self.verify(ring_info['ring'] == 'MP_log_history', "Test failed")

    def test_mempool_dump(self):
        """
        Run mempool dump test case.
        """
        self.dut.send_expect("./%s/app/test -n 1 -c ffff" % (self.target), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_mempool", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")
        elements = ['mempool', 'flags', 'ring', 'phys_addr', 'nb_mem_chunks', 'size', 'populated_size', 'header_size', 'elt_size',
                    'trailer_size', 'total_obj_size', 'private_data_size', 'avg bytes/object',  'cache infos','cache_size', 'common_pool_count']
        match_regex = "mempool <(.*?)>@0x(.*?)\r\n"
        for element in elements[1:]:
            if element == 'cache_size':
                match_regex += "    %s=(.*?)\r\n" % element
            elif element == 'cache infos':
                match_regex += "  %s:\r\n" % element
            else:
                match_regex += "  %s=(.*?)\r\n" % element
        m = re.compile(r"%s" % match_regex, re.S)
        result = m.search(out)
        mempool_info = dict(zip(elements, result.groups()))

        self.verify(mempool_info['mempool'] == 'log_history', "Test failed")

    def test_physmem_dump(self):
        """
        Run physical memory dump test case.
        """
        self.dut.send_expect("./%s/app/test -n 1 -c ffff" % (self.target), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_physmem", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")
        elements = ['Segment', 'phys', 'len', 'virt', 'socket_id', 'hugepage_sz', 'nchannel', 'nrank']
        match_regex = "Segment (\d)+:"
        for element in elements[1:-1]:
            match_regex += " %s:(.*?)," % element
        match_regex += " %s:(.*?)" % elements[-1]
        m = re.compile(r"%s" % match_regex, re.DOTALL)
        results = m.findall(out)
        phy_info = []
        for result in results:
            phy_info.append(dict(zip(elements, result)))

        self.verify(len(phy_info) > 0, "Test failed")

    def test_memzone_dump(self):
        """
        Run memzone dump test case.
        """
        self.dut.send_expect("./%s/app/test -n 1 -c ffff" % (self.target), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_memzone", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")

        elements = ['Zone', 'name', 'phys', 'len', 'virt', 'socket_id', 'flags']
        match_regex = "Zone (\d):"
        for element in elements[1:-1]:
            match_regex += " %s:(.*?)," % element
        match_regex += " %s:(.*?)\n" % elements[-1]
        m = re.compile(r"%s" % match_regex, re.DOTALL)
        results = m.findall(out)

        memzone_info = []
        for result in results:
            memzone_info.append(dict(zip(elements, result)))

        self.verify(len(memzone_info) > 0, "Test failed")

    def test_dump_struct_size(self):
        """
        Run struct size dump test case.
        """
        self.dut.send_expect("./%s/app/test -n 1 -c ffff" % (self.target), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_struct_sizes", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")

        elements = ['struct rte_mbuf', 'struct rte_mempool', 'struct rte_ring']
        match_regex = ""
        for element in elements[:-1]:
            match_regex += "sizeof\(%s\) = (\d+)\r\n" % element
        match_regex += "sizeof\(%s\) = (\d+)" % elements[-1]
        m = re.compile(r"%s" % match_regex, re.S)
        result = m.search(out)
        struct_info = dict(zip(elements, result.groups()))

    def test_dump_devargs(self):
        """
        Run devargs dump test case.
        """
        test_port = self.dut_ports[0]
        self.dut.send_expect("./%s/app/test -n 1 -c ffff -b 0000:%s"
                             % (self.target, self.dut.ports_info[test_port]['pci']), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_devargs", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")
        black_str = "PCI blacklist 0000:%s" % self.dut.ports_info[test_port]['pci']
        self.verify(black_str in out, "Dump black list failed")

        self.dut.send_expect("./%s/app/test -n 1 -c ffff -w 0000:%s"
                             % (self.target, self.dut.ports_info[test_port]['pci']), "R.*T.*E.*>.*>", self.start_test_time)
        out = self.dut.send_expect("dump_devargs", "RTE>>", self.run_cmd_time * 2)
        self.dut.send_expect("quit", "# ")

        white_str = "PCI whitelist 0000:%s" % self.dut.ports_info[test_port]['pci']
        self.verify(white_str in out, "Dump white list failed")

    def tear_down(self):
        """
        Run after each test case.
        Stop application test after every case.
        """
        self.dut.kill_all()
        pass

    def tear_down_all(self):
        """
        Run after each test suite.
        Nothing to do here.
        """
        pass
