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
A base class for creating DTF test cases.
"""

from exception import VerifyFailure
from settings import DRIVERS


class TestCase(object):

    def __init__(self, dut, tester, target, nic):
        self.dut = dut
        self.tester = tester
        self.target = target
        self.nic = nic

    def set_up_all(self):
        pass

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def tear_down_all(self):
        pass

    def verify(self, passed, description):
        if not passed:
            raise VerifyFailure(description)

    def get_nic_driver(self, nic_name):
        if nic_name in DRIVERS.keys():
            return DRIVERS[nic_name]

        raise ValueError(nic_name)

    def wirespeed(self, nic, frame_size, num_ports):
        """
        Calculate bit rate. It is depended for NICs
        """
        bitrate = 1000.0  # 1Gb ('.0' forces to operate as float)
        if self.get_nic_driver(self.nic) == "ixgbe":
            bitrate *= 10  # 10 Gb NICs
        elif self.nic == "avoton2c5":
            bitrate *= 2.5  # 2.5 Gb NICs
        elif self.nic in ["fortville_spirit", "fortville_spirit_single"]:
            bitrate *= 40
        elif self.nic == 'fortville_eagle':
           bitrate *= 10

        return bitrate * num_ports / 8 / (frame_size + 20)
