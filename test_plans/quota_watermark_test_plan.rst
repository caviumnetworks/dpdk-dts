.. Copyright (c) <2013>, Intel Corporation
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



====================
Quota and Water-mark
====================

This document provides test plan for benchmarking of the Quota and Water-mark 
sample application. This is a simple example app featuring packet processing 
using Intel® Data Plane Development Kit (Intel® DPDK) that show-cases the use 
of a quota as the maximum number of packets enqueue/dequeue at a time and low 
and high water-marks to signal low and high ring usage respectively. 
Additionally, it shows how ring water-marks can be used to feedback congestion 
notifications to data producers by temporarily stopping processing overloaded 
rings and sending Ethernet flow control frames.


Prerequisites
-------------

2x Intel® 82599 (Niantic) NICs (2x 10GbE full duplex optical ports per NIC) 
plugged into the available PCIe Gen2 8-lane slots in two different 
configurations: 
1. card0 and card1 attached to socket0.
2. card0 attached to socket0 and card1 to socket1. 

Test cases
----------

The idea behind the testing process is to send a fixed number of frames from 
the traffic generator to the DUT while these are being forwarded back by the 
app and measure some of statistics. Those configurable parameters exposed by 
the control app will be modified to see how these affect into the app's 
performance.Functional test is only used for checking packet transfer flow with
low watermark packets.

The statistics to be measured are explained below. 
A table will be presented showing all the different permutations.


- Ring size

  - Size of the rings that interconnect two adjacent cores within the 
    pipeline.

- Quota

  - Value controls how many packets are being moved through the pipeline per 
    en-queue and de-queue.

- Low water-mark

  - Global threshold that will resume en-queuing on a ring once its usage 
    goes below it.

- High water-mark

  - Threshold that will stop en-queuing on rings for which the usage has it.

- Frames sent

  - Number of frames sent from the traffic generator.

- Frames received

  - Number of frames received on the traffic generator once they were 
    forwarded back by the app.

- Control flow frames received
  
  - Number of Control flow frames (PAUSE frame defined by the IEEE 802.3x 
    standard) received on the traffic generator TX port.

- Transmit rate (Mpps)
  
  - Rate of transmission. It is calculated dividing the number of sent 
    packets over the time it took the traffic generator to send them.


  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | Ring size | Quota | Low water-mark | High water-mark | Frames sent | Frames received | Control flow frames received | Transmit rate (Mpps) |
  +===========+=======+================+=================+=============+=================+==============================+======================+
  | 64        | 5     | 1              | 5               | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | 64        | 5     | 10             | 20              | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | 64        | 5     | 10             | 99              | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | 64        | 5     | 60             | 99              | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | 64        | 5     | 90             | 99              | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | 64        | 5     | 10             | 80              | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  | 64        | 5     | 50             | 80              | 15000000    |                 |                              |                      |
  +-----------+-------+----------------+-----------------+-------------+-----------------+------------------------------+----------------------+
  
  
Test Case 1: Quota and Water-mark one socket (functional)
==========================================
Using No.1 card configuration.

This test case calls the application using cores and ports masks similar to 
the ones shown below. 

- Core mask ``0xFF00``
- Port mask ``0x280``

This core mask will make use of eight physical cores within the same socket. 
The used ports belong to different NIC’s attached to the same socket.

Sample command::
  
  ./examples/quota_watermark/qw/build/qw -c 0xFF00 -n 4 -- -p 0x280
  
After boot up qw and qwctl, send IP packets by scapy with low watermark value.
Command format::
   sendp([Ether()/IP()/("X"*26)]*<low watermark value>, iface="<port name>")
   
Sample command::
	sendp([Ether()/IP()/("X"*26)]*10, iface="p785p1")

Test Case 2: Quota and Water-mark one socket (performance)
==========================================

This test case calls the application using cores and ports masks similar to 
the ones shown below.

- Core mask ``0xFF00``
- Port mask ``0x280``

This core mask will make use of eight physical cores within the same socket. 
The used ports belong to different NIC’s attached to the same socket.

Sample command::
  
  ./examples/quota_watermark/qw/build/qw -c 0xFF00 -n 4 -- -p 0x280


Test Case 3: Quota and Water-mark two sockets (performance)
===========================================


This test case calls the application using a core and port mask similar to the 
ones shown below.

- Core mask ``0x0FF0``
- Port mask ``0x202``

This core mask will make use of eight physical cores; four within the first 
socket and four on the second one. The RX port will be attached to the first 
socket whereas the TX is to the second. This configuration will provoke the 
traffic going through the pipeline pass through the ``QPI`` channel.

Sample command::

  ./examples/quota_watermark/qw/build/qw -c 0x8180706 -n 4 -- -p 0x202


