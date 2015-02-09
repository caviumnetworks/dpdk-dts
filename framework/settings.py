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
Folders for framework running enviornment.
"""
FOLDERS = {
    'Framework'     : 'framework',
    'Testscripts'   : 'tests',
    'Configuration' : 'conf',
}

"""
Nics and its identifiers supported by the framework.
"""
NICS = {
    'kawela': '8086:10e8',
    'kawela_2': '8086:10c9',
    'kawela_4': '8086:1526',
    'bartonhills': '8086:150e',
    'powerville': '8086:1521',
    'ophir': '8086:105e',
    'niantic': '8086:10fb',
    'ironpond': '8086:151c',
    'twinpond': '8086:1528',
    'twinville': '8086:1512',
    'hartwell': '8086:10d3',
    '82545EM': '8086:100f',
    '82540EM': '8086:100e',
    'springville': '8086:1533',
    'springfountain': '8086:154a',
    'virtio': '1af4:1000',
    'avoton': '8086:1f41',
    'avoton2c5': '8086:1f45',
    'I217V': '8086:153b',
    'I217LM': '8086:153a',
    'I218V': '8086:1559',
    'I218LM': '8086:155a',
    'fortville_eagle': '8086:1572',
    'fortville_spirit': '8086:1583',
    'fortville_spirit_single': '8086:1584',
}

DRIVERS = {
    'kawela': 'igb',
    'kawela_2': 'igb',
    'kawela_4': 'igb',
    'bartonhills': 'igb',
    'powerville': 'igb',
    'ophir': 'igb',
    'niantic': 'ixgbe',
    'ironpond': 'ixgbe',
    'twinpond': 'ixgbe',
    'twinville': 'ixgbe',
    'hartwell': 'igb',
    '82545EM': 'igb',
    '82540EM': 'igb',
    'springville': 'igb',
    'springfountain': 'ixgbe',
    'virtio': 'igb',
    'avoton': 'igb',
    'avoton2c5': 'igb',
    'I217V': 'igb',
    'I217LM': 'igb',
    'I218V': 'igb',
    'I218LM': 'igb',
    'fortville_eagle': 'i40e',
    'fortville_spirit': 'i40e',
    'fortville_spirit_single':'i40e'
}

"""
List used to translate scapy packets into Ixia TCL commands.
"""
SCAPY2IXIA = [
    'Ether',
    'Dot1Q',
    'IP',
    'IPv6',
    'TCP',
    'UDP',
    'SCTP'
]

USERNAME = 'root'


"""
Helpful header sizes.
"""
HEADER_SIZE = {
    'eth': 18,
    'ip': 20,
    'ipv6': 40,
    'udp': 8,
    'tcp': 20
}


"""
Default session timeout.
"""
TIMEOUT = 15


"""
Global macro for dts.
"""
IXIA = "ixia"
