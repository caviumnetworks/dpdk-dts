.. Copyright (c) <2011>, Intel Corporation
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

==================================================================
Fortville RSS full support - Support configuring hash functions
==================================================================

This document provides test plan for testing the function of Fortville:
Support configuring hash functions.

Prerequisites
-------------

2x Intel® 82599 (Niantic) NICs (2x 10GbE full duplex optical ports per NIC)
1x Fortville_eagle NIC (4x 10G)
1x Fortville_spirit NIC (2x 40G) 
2x Fortville_spirit_single NIC (1x 40G)

The four ports of the 82599 connect to the Fortville_eagle;
The two ports of Fortville_spirit connect to Fortville_spirit_single.
The three kinds of NICs are the target NICs. the connected NICs can send packets
to these three NICs using scapy.

Network Traffic
---------------

The RSS feature is designed to improve networking performance by load balancing
the packets received from a NIC port to multiple NIC RX queues, with each queue
handled by a different logical core.

#1. The receive packet is parsed into the header fields used by the hash
operation (such as IP addresses, TCP port, etc.)

#2. A hash calculation is performed. The Fortville  supports four hash function:
Toeplitz, simple XOR and their Symmetric RSS.

#3. The seven LSBs of the hash result are used as an index into a 128/512 entry
'redirection table'. Each entry provides a 4-bit RSS output index.

#4. There are four cases to test the four hash function.

Test Case:  test_toeplitz
=========================

Testpmd configuration - 16 RX/TX queues per port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#1. set up testpmd woth fortville NICs::
  
  ./testpmd -c fffff -n %d -- -i --coremask=0xffffe --rxq=16 --txq=16

#2. Reta Configuration.  128 reta entries configuration::

  testpmd command: port config 0 rss reta (hash_index,queue_id)

#3. PMD fwd only receive the packets::

  testpmd command: set fwd rxonly

#4. rss recived package type configuration two received packet types configuration::

  testpmd command: port config 0 rss ip/udp

#5. verbose configuration::

  testpmd command: set verbose 8

#6. set hash functions, can choose symmetric or not, chosse port and packet type::

  set_hash_function 0 toeplitz

#7. start packet receive::

  testpmd command: start

tester Configuration
--------------------

#1. set up scapy

#2. send packets with different type ipv4/ipv4 with tcp/ipv4 with udp/
    ipv6/ipv6 with tcp/ipv6 with udp::

    sendp([Ether(dst="90:e2:ba:36:99:3c")/IP(src="192.168.0.4", dst="192.168.0.5")], iface="eth3")

test result
-----------

The testpmd will print the hash value and actual queue of every packet.

#1. Calaute the queue id: hash value%128or512, then refer to teh redirection table
    to get the theoretical queue id.

#2. Compare the theoretical queue id with the actual queue id.


Test Case:  test_toeplitz_symmetric
===================================

The same with the above steps, pay attention to "set hash function", should use::

  set_hash_function 0 toeplitz
  set_sym_hash_ena_per_port 0 enable
  set_sym_hash_ena_per_pctype 0 35 enable

And send packets with the same flow in different direction::

  sendp([Ether(dst="90:e2:ba:36:99:3c")/IP(src="192.168.0.4", dst="192.168.0.5")], iface="eth3")
  sendp([Ether(dst="90:e2:ba:36:99:3c")/IP(src="192.168.0.5", dst="192.168.0.4")], iface="eth3")

And the hash value and queue should be the same for these two flow .

Test Case:  test_simple
=======================

The same as the above two test cases. Just pay attention to set the hash function to "simple xor"

Test Case:  test_simple_symmetric
=================================

The same as the above two test cases. Just pay attention to set the hash function to "simple xor"


