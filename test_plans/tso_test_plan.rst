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



==============================================
Testing of TSO Support in DPDK
==============================================


Description
===========

This document provides the plan for testing the TSO(Transmit Segmentation 
Offload, also called Large Send offload - LSO) feature of
Intel Ethernet Controller, including Intel 82599 10GbE Ethernet Controller and
Fortville 40GbE Ethernet Controller. TSO enables the TCP/IP stack to
pass to the network device a larger ULP datagram than the Maximum Transmit 
Unit Size (MTU). NIC divides the large ULP datagram to multiple segments 
according to the MTU size. 


Prerequisites
=============

The DUT must take one of the Ethernet controller ports connected to a port on another 
device that is controlled by the Scapy packet generator.

The Ethernet interface identifier of the port that Scapy will use must be known.                
On tester, all offload feature should be disabled on tx port, and start rx port capture:
  ethtool -K <tx port> rx off tx off tso off gso off gro off lro off
  ip l set <tx port> up
  tcpdump -n -e -i <rx port> -s 0 -w /tmp/cap


On DUT, run pmd with parameter "--enable-rx-cksum". Then enable TSO on tx port 
and checksum on rx port. The test commands is below:
  #enable hw checksum on rx port
  tx_checksum set ip hw 0
  tx_checksum set udp hw 0
  tx_checksum set tcp hw 0
  tx_checksum set sctp hw 0
  set fwd csum

  # enable TSO on tx port
  *tso set 800 1 


Test case: csum fwd engine, use TSO
====================================================

This test uses ``Scapy`` to send out one large TCP package. The dut forwards package 
with TSO enable on tx port while rx port turns checksum on. After package send out 
by TSO on tx port, the tester receives multiple small TCP package.

Turn off tx port by ethtool on tester::
  ethtool -K <tx port> rx off tx off tso off gso off gro off lro off
  ip l set <tx port> up
capture package rx port on tester::
  tcpdump -n -e -i <rx port> -s 0 -w /tmp/cap
  
Launch the userland ``testpmd`` application on DUT as follows::
./x86_64-native-linuxapp-gcc/app/testpmd -c 0xffffffff -n 2 -- -i --rxd=512 --txd=512 
--burst=32 --rxfreet=64 --mbcache=128 --portmask=0x3 --txpt=36 --txht=0 --txwt=0 
--txfreet=32 --txrst=32 --enable-rx-cksum
  testpmd> set verbose 1

  # enable hw checksum on rx port
  testpmd> tx_checksum set ip hw 0
  testpmd> tx_checksum set udp hw 0
  testpmd> tx_checksum set tcp hw 0
  testpmd> tx_checksum set sctp hw 0
  # enable TSO on tx port
  testpmd> tso set 800 1
  # set fwd engine and start
  testpmd> set fwd csum
  testpmd> start 

Test IPv4() in scapy:
    sendp([Ether(dst="%s", src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/UDP(sport=1021,dport=1021)/Raw(load="\x50"*%s)], iface="%s")

Test IPv6() in scapy:
    sendp([Ether(dst="%s", src="52:00:00:00:00:00")/IPv6(src="FE80:0:0:0:200:1FF:FE00:200", dst="3555:5555:6666:6666:7777:7777:8888:8888")/UDP(sport=1021,dport=1021)/Raw(load="\x50"*%s)], iface="%s"

Test case: csum fwd engine, use TSO tunneling
====================================================

This test uses ``Scapy`` to send out one large TCP package. The dut forwards package 
with TSO enable on tx port while rx port turns checksum on. After package send out 
by TSO on tx port, the tester receives multiple small TCP package.

Turn off tx port by ethtool on tester::
  ethtool -K <tx port> rx off tx off tso off gso off gro off lro off
  ip l set <tx port> up
capture package rx port on tester::
  tcpdump -n -e -i <rx port> -s 0 -w /tmp/cap
  
Launch the userland ``testpmd`` application on DUT as follows::
./x86_64-native-linuxapp-gcc/app/testpmd -c 0xffffffff -n 2 -- -i --rxd=512 --txd=512 
--burst=32 --rxfreet=64 --mbcache=128 --portmask=0x3 --txpt=36 --txht=0 --txwt=0 
--txfreet=32 --txrst=32 --enable-rx-cksum
  testpmd> set verbose 1

  # enable hw checksum on rx port
  testpmd> tx_checksum set ip hw 0
  testpmd> tx_checksum set udp hw 0
  testpmd> tx_checksum set tcp hw 0
  testpmd> tx_checksum set sctp hw 0
  testpmd> tx_checksum set vxlan hw 0
  testpmd> tx_checksum set nvgre hw 0
  # enable TSO on tx port
  testpmd> tso set 800 1
  # set fwd engine and start
  testpmd> set fwd csum
  testpmd> start 

Test vxlan() in scapy:
    sendp([Ether(dst="%s",src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/UDP(sport=1021,dport=4789)/VXLAN(vni=1234)/Ether(dst=%s,src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/UDP(sport=1021,dport=1021)/Raw(load="\x50"*%s)], iface="%s"

Test nvgre() in scapy:
    sendp([Ether(dst="%s",src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2",proto=47)/NVGRE()/Ether(dst=%s,src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/TCP(sport="1021",dport="1021")/("X"*%s)], iface="%s")

Test case: TSO performance
====================================================
Set the packet stream to be sent out from packet generater before testing as 
below.

+-------+---------+---------+---------+----------+----------+ 
| Frame | 1S/1C/1T| 1S/1C/1T| 1S/2C/1T| 1S/2C/2T | 1S/2C/2T | 
| Size  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  64   |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  65   |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  128  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  256  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  512  |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  1024 |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  1280 |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+ 
|  1518 |         |         |         |          |          | 
+-------+---------+---------+---------+----------+----------+

Then run the test application as below:: 
./x86_64-native-linuxapp-gcc/app/testpmd -c 0xffffffff -n 2 -- -i --rxd=512 --txd=512 
--burst=32 --rxfreet=64 --mbcache=128 --portmask=0x3 --txpt=36 --txht=0 --txwt=0 
--txfreet=32 --txrst=32 --enable-rx-cksum
The -n command is used to select the number of memory channels. It should match the 
number of memory channels on that setup.


