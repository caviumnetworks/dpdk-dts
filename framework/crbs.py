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
Static configuration data for any CRBs that can be used.
"""
from settings import IXIA

crbs = [
    {'IP': '10.239.128.117',
     'name': 'CrownPassCRB1',
     'user': 'root',
     'pass': 'tester',
     'tester IP': '10.239.128.116',
     IXIA: None,
     'memory channels': 4,
     'bypass core0': True},
]


crbs_desc = {
    'CrownPassCRB1':

    """
    - Intel Grizzly Pass Server Board populated with:

      - 2x Intel Xeon CPU E5-2680 @ 2.7GHz with 64 KB L1 D-cache (per
        physical core), 256 KB L2 D-cache (per physical core) and 25 MB of
        L3 D-cache (shared across physical cores).
      - 8x DDR3 DIMMs @ 1333 MHz of 4GB each. Each of the 4 memory channels of each
        CPU is populated with 2 DIMMs.
      - 4x Intel 82599 (Niantic) NICs (2x 10GbE full duplex optical ports per NIC)
        plugged into the available PCIe Gen2 8-lane slots. To avoid PCIe bandwidth
        bottlenecks at high packet rates, a single optical port from each NIC is
        connected to the traffic  generator.

    - BIOS version R02.01.0002 with the following settings:

      - Intel Turbo Boost Technology [Disabled]
      - Enhanced Intel SpeedStep Technology (EIST) [Disabled]
      - Intel Hyper-Threading Technology  [Enabled]
      - Direct Cache Access [Disabled]

      - Execute DisableBit [Enabled]
      - MLC Streamer [Enabled]
      - MLC Spatial Prefetcher [Disabled]
      - DCU Data Prefetcher [Disabled]
      - DCU Instruction Prefetcher [Enabled]

    - Software configuration:

      - Linux operating system: Fedora 20 64-bit
      - Linux kernel version: 3.6.10
    """
}
