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

import os
import re
import dts


class PmdOutput():

    """
    Module for get all statics value by port in testpmd
    """

    def __init__(self, dut):
        self.dut = dut
        self.rx_pkts_prefix = "RX-packets:"
        self.rx_missed_prefix = "RX-missed:"
        self.rx_bytes_prefix = "RX-bytes:"
        self.rx_badcrc_prefix = "RX-badcrc:"
        self.rx_badlen_prefix = "RX-badlen:"
        self.rx_error_prefix = "RX-errors:"
        self.rx_nombuf_prefix = "RX-nombuf:"
        self.tx_pkts_prefix = "TX-packets:"
        self.tx_error_prefix = "TX-errors:"
        self.tx_bytes_prefix = "TX-bytes:"
        self.bad_ipcsum_prefix = "Bad-ipcsum:"
        self.bad_l4csum_prefix = "Bad-l4csum:"

    def get_pmd_value(self, prefix, out):
        pattern = re.compile(prefix + "(\s+)([0-9]+)")
        m = pattern.search(out)
        if m is None:
            return None
        else:
            return int(m.group(2))

    def get_pmd_stats(self, portid):
        stats = {}
        out = self.dut.send_expect("show port stats %d" % portid, "testpmd> ")
        stats["RX-packets"] = self.get_pmd_value(self.rx_pkts_prefix, out)
        stats["RX-missed"] = self.get_pmd_value(self.rx_missed_prefix, out)
        stats["RX-bytes"] = self.get_pmd_value(self.rx_bytes_prefix, out)

        stats["RX-badcrc"] = self.get_pmd_value(self.rx_badcrc_prefix, out)
        stats["RX-badlen"] = self.get_pmd_value(self.rx_badlen_prefix, out)
        stats["RX-errors"] = self.get_pmd_value(self.rx_error_prefix, out)
        stats["RX-nombuf"] = self.get_pmd_value(self.rx_nombuf_prefix, out)
        stats["TX-packets"] = self.get_pmd_value(self.tx_pkts_prefix, out)
        stats["TX-errors"] = self.get_pmd_value(self.tx_error_prefix, out)
        stats["TX-bytes"] = self.get_pmd_value(self.tx_bytes_prefix, out)

        # display when testpmd config forward engine to csum
        stats["Bad-ipcsum"] = self.get_pmd_value(self.bad_ipcsum_prefix, out)
        stats["Bad-l4csum"] = self.get_pmd_value(self.bad_l4csum_prefix, out)
        return stats

    def get_pmd_cmd(self):
        return self.command

    def start_testpmd(self, cores, param='', eal_param='', socket=0):
        core_list = self.dut.get_core_list(cores, socket)
        self.coremask = dts.create_mask(core_list)
        command = "./%s/app/testpmd -c %s -n %d %s -- -i %s" \
            % (self.dut.target, self.coremask, self.dut.get_memory_channels(), eal_param, param)
        out = self.dut.send_expect(command, "testpmd> ", 120)
        self.command = command
        return out
