.. Copyright (c) <2010, 2011>, Intel Corporation
   All rights reserved.
   
   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions
   are met:
   
   - Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
   
   - Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in
     the documentation and/or other materials provided with the
     distribution.
   
   - Neither the name of Intel Corporation nor the names of its
     contributors may be used to endorse or promote products derived
     from this software without specific prior written permission.
   
   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
   FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
   COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
   INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
   SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
   HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
   STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
   OF THE POSSIBILITY OF SUCH DAMAGE.

=========================
Tespt PMD PCAP files test
=========================

This document provides tests for the userland Intel(R)
82599 Gigabit Ethernet Controller (Niantic) Poll Mode Driver (PMD) when using
pcap files as input and output.

The core configurations description is:

- 2C/1T: 2 Physical Cores, 1 Logical Core per physical core
- 4C/1T: 4 Physical Cores, 1 Logical Core per physical core

Prerequisites
=============

This test does not requires connections between DUT and tester as it is focused
in PCAP devices created by Test PMD.

It is Test PMD application itself which send and receibes traffic from and to
PCAP files, no traffic generator is involved.


Test Case: test_send_packets_with_one_device
============================================

It is necessary to generate the input pcap file for one interface test. The
pcap file can be created using scapy. Create a file with 1000 frames with the 
following structure::

  Ether(src='00:00:00:00:00:<last Eth>', dst='00:00:00:00:00:00')/IP(src='192.168.1.1', dst='192.168.1.2')/("X"*26))

<last Eth> goes from 0 to 255 and repeats.

The linuxapp is started with the following parameters:

::

  -c 0xffffff -n 3 --vdev 'eth_pcap0;rx_pcap=in.pcap;tx_pcap=out.pcap' --
  -i --port-topology=chained


Start the application and the forwarding, by typing `start` in the command line 
of the application. After a few seconds `stop` the forwarding and `quit` the 
application.

Check that the frames of in.pcap and out.pcap files are the same using scapy.

Test Case: test_send_packets_with_two_devices
=============================================

Create 2 pcap files with 1000 and 500 frames as explained in 
`test_send_packets_with_one_device` test case. 

The linuxapp is started with the following parameters:

::

  -c 0xffffff -n 3 --vdev 'eth_pcap0;rx_pcap=in1.pcap;tx_pcap=out1.pcap,"eth_pcap1;rx_pcap=in2.pcap;tx_pcap=out2.pcap'
  -- -i


Start the application and the forwarding, by typing `start` in the command line 
of the application. After a few seconds `stop` the forwarding and `quit` the 
application.

Check that the frames of the in1.pcap and out2.pcap, and in2.pcap and out1.pcap
file are the same using scapy.
