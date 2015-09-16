.. Copyright (c) 2010,2011 Intel Corporation
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
      
=========================================================================
Support of RX/TX Packet Filtering using VMDQ Features of 40G&10G&1G  NIC
=========================================================================

The 1G, 10G 82599 and 40G FVL Network Interface Card (NIC), supports a number of packet
filtering functions which can be used to distribute incoming packets into a
number of reception (RX) queues. VMDQ is a  filtering
functions which operate on VLAN-tagged packets to distribute those packets
among up to 512 RX queues.

The feature itself works by:

- splitting the incoming packets up into different "pools" - each with its own 
  set of RX queues - based upon the MAC address and VLAN ID within the VLAN tag of the packet.
- assigning each packet to a specific queue within the pool, based upon the
  user priority field within the VLAN tag and MAC address.

The VMDQ features are enabled in the ``vmdq`` example application
contained in the Intel DPDK, and this application should be used to validate
the feature.

Prerequisites
=============
- All tests assume a linuxapp setup.
- The port ids of the two 10G or 40G ports to be used for the testing are specified
  in the commandline. it use a portmask.
- The Intel DPDK is compiled for the appropriate target type in each case, and 
  the VMDQ  example application is compiled and linked with that DPDK
  instance
- Two ports are connected to the test system, one to be used for packet
  reception, the other for transmission
- The traffic generator being used is configured to send to the application RX
  port a stream of packets with VLAN tags, where the VLAN IDs increment from 0
  to the pools numbers(e.g: for FVL spirit, it's 63, inclusive) as well as the MAC address from 
  52:54:00:12:[port_index]:00 to 52:54:00:12:[port_index]:3e and the VLAN user priority field increments from 0 to 7
  (inclusive) for each VLAN ID. In our case port_index = 0 or 1. 


Test Case: Measure VMDQ pools queues
------------------------------------
1. Put different number of pools: in the case of 10G 82599 Nic is 64, in the case
   of FVL spirit is 63,in case of FVL eagle is 34. 
2. Start traffic transmission using approx 10% of line rate.
3. After a number of seconds, e.g. 15, stop traffic, and ensure no traffic 
   loss (<0.001%) has occurred.
4. Send a hangup signal (SIGHUP) to the application to have it print out the
   statistics of how many packets were received per RX queue
   
Expected Result:

- No packet loss is expected
- Every RX queue should have received approximately (+/-15%) the same number of
  incoming packets

Test Case: Measure VMDQ Performance
-----------------------------------

1. Compile VMDQ  example application as in first test above.
2. Run application using a core mask for the appropriate thread and core
   settings given in the following list: 

  * 1S/1C/1T
  * 1S/2C/1T
  * 1S/2C/2T
  * 1S/4C/1T

3. Measure maximum RFC2544 performance throughput for bi-directional traffic for
   all standard packet sizes.

Output Format:
The output format should be as below, or any similar table-type, with figures
given in mpps:

+------------+----------+----------+----------+----------+
| Frame size | 1S/1C/1T | 1S/2C/1T | 1S/2C/2T | 1S/4C/1T |
+============+==========+==========+==========+==========+
| 64         | 19.582   | 42.222   | 53.204   | 73.768   |
+------------+----------+----------+----------+----------+
| 128        | 20.607   | 42.126   | 52.964   | 67.527   |
+------------+----------+----------+----------+----------+
| 256        | 15.614   | 33.849   | 36.232   | 36.232   |
+------------+----------+----------+----------+----------+
| 512        | 11.794   | 18.797   | 18.797   | 18.797   |
+------------+----------+----------+----------+----------+
| 1024       | 9.568    | 9.579    | 9.579    | 9.579    |
+------------+----------+----------+----------+----------+
| 1280       | 7.692    | 7.692    | 7.692    | 7.692    |
+------------+----------+----------+----------+----------+
| 1518       | 6.395    | 6.502    | 6.502    | 6.502    |
+------------+----------+----------+----------+----------+

