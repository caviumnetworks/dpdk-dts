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



=============
IP Reassembly
=============

This document provides a test plan for benchmarking of the IP Reassembly
sample application. This is a simple example app featuring packet processing
using Intel® Data Plane Development Kit (Intel® DPDK) that show-cases the use
of IP fragmented packets reassembly. 



Prerequisites
-------------

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

1x Intel® 82599 (Niantic) NICs (1x 10GbE full duplex optical ports per NIC) 
plugged into the available PCIe Gen2 8-lane slots.


Test Case: Send 1K packets, 4 fragments each and 1K maxflows
============================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=10s

Sends 1K packets split in 4 fragments each with a ``maxflows`` of 1K.

It expects:

  - 4K IP packets to be sent to the DUT.
  - 1K TCP packets being forwarded back to the TESTER.
  - 1K packets with a valid TCP checksum.


Test Case: Send 2K packets, 4 fragments each and 1K maxflows
============================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=10s

Sends 2K packets split in 4 fragments each with a ``maxflows`` of 1K.

It expects:

  - 8K IP packets to be sent to the DUT.
  - 1K TCP packets being forwarded back to the TESTER.
  - 1K packets with a valid TCP checksum.


Test Case: Send 4K packets, 7 fragments each and 4K maxflows
============================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=4096 --flowttl=10s

Modifies the sample app source code to enable up to 7 fragments per packet. 
Sends 4K packets split in 7 fragments each with a ``maxflows`` of 4K.

It expects:

  - 28K IP packets to be sent to the DUT.
  - 4K TCP packets being forwarded back to the TESTER.
  - 4K packets with a valid TCP checksum.


Test Case: Send +1K packets and ttl 3s; wait +ttl; send 1K packets
==================================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=3s

Sends 1100 packets split in 4 fragments each. 

It expects:

  - 4400 IP packets to be sent to the DUT.
  - 1K TCP packets being forwarded back to the TESTER.
  - 1K packets with a valid TCP checksum.


Then waits until the ``flowttl`` timeout and sends 1K packets.

It expects:

  - 4K IP packets to be sent to the DUT.
  - 1K TCP packets being forwarded back to the TESTER.
  - 1K packets with a valid TCP checksum.


Test Case: Send more packets than maxflows; only maxflows packets are forwarded back
====================================================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1023 --flowttl=5s

Sends 1K packets with ``maxflows`` equal to 1023.

It expects:

  - 4092 IP packets to be sent to the DUT.
  - 1023 TCP packets being forwarded back to the TESTER.
  - 1023 packets with a valid TCP checksum.

Then sends 1023 packets.

It expects:

  - 4092 IP packets to be sent to the DUT.
  - 1023 TCP packets being forwarded back to the TESTER.
  - 1023 packets with a valid TCP checksum.

Finally waits until the ``flowttl`` timeout and re-send 1K packets.

It expects:

  - 4092 IP packets to be sent to the DUT.
  - 1023 TCP packets being forwarded back to the TESTER.
  - 1023 packets with a valid TCP checksum.


Test Case: Send more fragments than supported
=============================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=10s

Sends 1 packet split in 5 fragments while the maximum number of supported 
fragments per packet is 4.

It expects:

  - 5 IP packets to be sent to the DUT.
  - 0 TCP packets being forwarded back to the TESTER.
  - 0 packets with a valid TCP checksum.



Test Case: Send 3 frames and delay the 4th; no frames are forwarded back
========================================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=3s

Creates 1 packet split in 4 fragments. Sends the first 3 fragments and waits 
until the ``flowttl`` timeout. Then sends the 4th fragment.

It expects:

  - 4 IP packets to be sent to the DUT.
  - 0 TCP packets being forwarded back to the TESTER.
  - 0 packets with a valid TCP checksum.



Test Case: Send jumbo frames
============================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=10s --enable-jumbo --max-pkt-len=9500

Sets the NIC MTU to 9000 and sends 1K packets of 8900B split in 4 fragments of
2500B at the most. The reassembled packet size will not be bigger than the 
MTU previously defined. 

It expects:

  - 4K IP packets to be sent to the DUT.
  - 1K TCP packets being forwarded back to the TESTER.
  - 1K packets with a valid TCP checksum.


Test Case: Send jumbo frames without enable them in the app
===========================================================

Sample command::

  ./examples/ip_reassembly/build/ip_reassembly -c 0x2 -n 4 -- -P -p 0x2 --config "(1,0,1)" --maxflows=1024 --flowttl=10s 

Sends jumbo packets in the same way the previous test case does but without
enabling support within the sample app. 

It expects:

  - 4K IP packets to be sent to the DUT.
  - 0 TCP packets being forwarded back to the TESTER.
  - 0 packets with a valid TCP checksum.


