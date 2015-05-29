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

================================================================
reta(Redirection table) benchmark Results of the 82599 10GbE PMD
================================================================

This document provides test plan for benchmarking of Rss reta(Redirection
table) updating for the Intel® 82599 10 Gigabit Ethernet Controller
(Niantic) Poll Mode Driver (PMD) in userland runtime configurations.
The content of Rss Redirection table are not defined following reset
of the Memory Configuration registers. System software must initialize
the table prior to enabling multiple receive queues .It can also update
the redirection table during run time. Such updates of the table are
not synchronized with the arrival time of received packets.

Prerequisites
-------------

2x Intel® 82599 (Niantic) NICs (2x 10GbE full duplex optical ports per NIC)
plugged into the available PCIe Gen2 8-lane slots. To avoid PCIe bandwidth
bottlenecks at high packet rates, a single optical port from each NIC is
connected to the traffic  generator.


Network Traffic
---------------

The RSS feature is designed to improve networking performance by load balancing
the packets received from a NIC port to multiple NIC RX queues, with each queue
handled by a different logical core.

#1. The receive packet is parsed into the header fields used by the hash
operation (such as IP addresses, TCP port, etc.)

#2. A hash calculation is performed. The 82599 supports a single hash function,
as defined by MSFT RSS. The 82599 therefore does not indicate to the device
driver which hash function is used. The 32-bit result is fed into the packet
receive descriptor.

#3. The seven LSBs of the hash result are used as an index into a 128-entry
'redirection table'. Each entry provides a 4-bit RSS output index.

The RSS RETA update feature is designed to make RSS more flexible by allowing
users to define the correspondence between the seven LSBs of hash result and
the queue id(RSS output index) by themself.


Test Case:  Results - IO Forwarding Mode
========================================

The following RX Ports/Queues configurations have to be benchmarked:

- 1 RX port / 2 RX queues (1P/2Q)

- 1 RX port / 9 RX queues (1P/9Q)

- 1 RX ports / 16 RX queues (1P/16Q)


Testpmd configuration - 2 RX/TX queues per port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  
  testpmd -cffffff -n 3 -b 0000:05:00.1 -- -i --rxd=512 --txd=512 --burst=32 \
  --txpt=36 --txht=0 --txwt=0 --txfreet=32 --rxfreet=64 --txrst=32 --mbcache=128 \
  --rxq=2 --txq=2

Testpmd configuration - 9 RX/TX queues per port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  
  testpmd -cffffff -n 3 -b 0000:05:00.1 -- -i --rxd=512 --txd=512 --burst=32 \
  --txpt=36 --txht=0 --txwt=0 --txfreet=32 --rxfreet=64 --txrst=32 --mbcache=128 \
  --rxq=9 --txq=9

Testpmd configuration - 16 RX/TX queues per port
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  
  testpmd -cffffff -n 3 -b 0000:05:00.1 -- -i --rxd=512 --txd=512 --burst=32 \
  --txpt=36 --txht=0 --txwt=0 --txfreet=32 --rxfreet=64 --txrst=32 --mbcache=128 \
  --rxq=16 --txq=16

The -n command is used to select the number of memory channels. It should match the number of memory channels on that setup.
The -b command is used to prevent the use of pic port to receive packets. It should match the pci number of the pci device.

Testpmd Configuration Options
-----------------------------

By default, a single logical core runs the test.
The CPU IDs and the number of logical cores running the test in parallel can
be manually set with the ``set corelist X,Y`` and the ``set nbcore N``
interactive commands of the ``testpmd`` application.

#1. Reta Configuration.  128 reta entries configuration::

  testpmd command: port config 0 rss reta (hash_index,queue_id)

#2. PMD fwd only receive the packets::

  testpmd command: set fwd rxonly

#3. rss recived package type configuration two received packet types configuration::

  testpmd command: port config 0 rss ip/udp

#4. verbose configuration::

  testpmd command: set verbose 8

#5. start packet receive::

  testpmd command: start

tester Configuration
--------------------

#1. In order to make most entries of the reta to be tested,the traffic generator
has to be configured to randomize the value of the 5-tuple fields of the
transmitted IP/UDP packets so that RSS hash function output of 5-tuple fileds covers
most of reta index.

#2. set the package numbers of one burst to a centain value.


Example output (1P/2Q)  received by the dut):::
-----------------------------------------------

+--------------+-------------+------------+-----------------+------+
| packet index | hash output | rss output | actual queue id | pass |
+--------------+-------------+------------+-----------------+------+
| 0            |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
| 1            |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
| 2            |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
| etc.         |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
| 125          |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
| 126          |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
| 127          |             |            |                 |      |
+--------------+-------------+------------+-----------------+------+
