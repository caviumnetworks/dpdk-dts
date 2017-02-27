.. Copyright (c) <2010>, Intel Corporation
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

==========================
PMD RX/TX Checksum Offload
==========================

The support of RX/TX L3/L4 Checksum offload features by Poll Mode Drivers consists in:

On the RX side:
- Verify IPv4 checksum by hardware for received packets.
- Verify UDP/TCP/SCTP checksum by hardware for received packets.

On the TX side:

- IPv4 checksum insertion by hardware in transmitted packets.
- IPv4/UDP checksum insertion by hardware in transmitted packets.
- IPv4/TCP checksum insertion by hardware in transmitted packets.
- IPv4/SCTP checksum insertion by hardware in transmitted packets (sctp 
        length in 4 bytes).
- IPv6/UDP checksum insertion by hardware in transmitted packets.
- IPv6/TCP checksum insertion by hardware in transmitted packets.
- IPv6/SCTP checksum insertion by hardware in transmitted packets (sctp 
        length in 4 bytes).

RX side, the L3/L4 checksum offload by hardware can be enabled with the
following command of the ``testpmd`` application::

   enable-rx-checksum

TX side, the insertion of a L3/L4 checksum by hardware can be enabled with the
following command of the ``testpmd`` application and running in a dedicated
tx checksum mode::

   set fwd csum
   tx_checksum set mask port_id

The transmission of packet is done with the ``start`` command of the ``testpmd`` 
application that will receive packets and then transmit the packet out on all 
configured ports. ``mask`` is used to indicated what hardware checksum
offload is required on the ``port_id``. Please check the NIC datasheet for the 
corrresponding Hardware limits::

      bit 0 - insert ip checksum offload if set 
      bit 1 - insert udp checksum offload if set 
      bit 2 - insert tcp checksum offload if set
      bit 3 - insert sctp checksum offload if set


Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.
 
Assuming that ports ``0`` and ``2`` are connected to a traffic generator,
launch the ``testpmd`` with the following arguments::
  
  ./build/app/testpmd -cffffff -n 1 -- -i --burst=1 --txpt=32 \
  --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 --mbcache=250 --portmask=0x5
  enable-rx-checksum

Set the verbose level to 1 to display informations for each received packet::

  testpmd> set verbose 1 

Test Case: Validate checksum on the receive packet
==================================================

Setup the ``csum`` forwarding mode::

  testpmd> set fwd csum
  Set csum packet forwarding mode

Start the packet forwarding::
  
  testpmd> start
    csum packet forwarding - CRC stripping disabled - packets/burst=32
    nb forwarding cores=1 - nb forwarding ports=10
    RX queues=1 - RX desc=128 - RX free threshold=64
    RX threshold registers: pthresh=8 hthresh=8 wthresh=4
    TX queues=1 - TX desc=512 - TX free threshold=0
    TX threshold registers: pthresh=32 hthresh=8 wthresh=8

Configure the traffic generator to send the multiple packets with the following 
combination: good/bad ip checksum + good/bad udp/tcp checksum.

Except that SCTP header + payload length must be a multiple of 4 bytes.
IPv4 + UDP/TCP packet length can range from the minimum length to 1518 bytes.

Then verify that how many packets found with Bad-ipcsum or Bad-l4csum::

  testpmd> stop
  ---------------------- Forward statistics for port 0  ----------------------
  RX-packets: 0              RX-dropped: 0             RX-total: 0
  Bad-ipcsum: 0              Bad-l4csum: 0              
  TX-packets: 0              TX-dropped: 0             TX-total: 0
  ----------------------------------------------------------------------------


Test Case: Insert IPv4/IPv6 UDP/TCP/SCTP checksum on the transmit packet
========================================================================

Setup the ``csum`` forwarding mode::

  testpmd> set fwd csum
  Set csum packet forwarding mode

Enable the IPv4/UDP/TCP/SCTP checksum offload on port 0::
  
  testpmd> tx_checksum set 0xf 0
  testpmd> start
    csum packet forwarding - CRC stripping disabled - packets/burst=32
    nb forwarding cores=1 - nb forwarding ports=10
    RX queues=1 - RX desc=128 - RX free threshold=64
    RX threshold registers: pthresh=8 hthresh=8 wthresh=4
    TX queues=1 - TX desc=512 - TX free threshold=0
    TX threshold registers: pthresh=32 hthresh=8 wthresh=8

Configure the traffic generator to send the multiple packets for the following 
combination: IPv4/UDP, IPv4/TCP, IPv4/SCTP, IPv6/UDP, IPv6/TCP.

Except that SCTP header + payload length must be a multiple of 4 bytes.
IPv4 + UDP/TCP packet length can range from the minimum length to 1518 bytes.

Then verify that the same number of packet are correctly received on the traffic 
generator side. And IPv4 checksum, TCP checksum, UDP checksum, SCTP CRC32c need 
be validated as pass by the IXIA. 

The IPv4 source address will not be changed by testpmd.


Test Case: Do not insert IPv4/IPv6 UDP/TCP checksum on the transmit packet
==========================================================================

Setup the ``csum`` forwarding mode::

  testpmd> set fwd csum
  Set csum packet forwarding mode

Disable the IPv4/UDP/TCP/SCTP checksum offload on port 0::
  
  testpmd> tx_checksum set 0x0 0
  testpmd> start
    csum packet forwarding - CRC stripping disabled - packets/burst=32
    nb forwarding cores=1 - nb forwarding ports=10
    RX queues=1 - RX desc=128 - RX free threshold=64
    RX threshold registers: pthresh=8 hthresh=8 wthresh=4
    TX queues=1 - TX desc=512 - TX free threshold=0
    TX threshold registers: pthresh=32 hthresh=8 wthresh=8

Configure the traffic generator to send the multiple packets for the follwing
combination: IPv4/UDP, IPv4/TCP, IPv6/UDP, IPv6/TCP.

IPv4 + UDP/TCP packet length can range from the minimum length to 1518 bytes.

Then verify that the same number of packet are correctly received on the traffic
generator side. And IPv4 checksum, TCP checksum, UDP checksum need
be validated as pass by the IXIA. 

The first byte of source IPv4 address will be increment by testpmd. The checksum
is indeed recalculated by software algorithms.


Test Case: Validate RX checksum valid flags on the receive packet
=================================================================

Setup the ``csum`` forwarding mode::

  testpmd> set fwd csum
  Set csum packet forwarding mode

Start the packet forwarding::

  testpmd> start
    csum packet forwarding - CRC stripping disabled - packets/burst=32
    nb forwarding cores=1 - nb forwarding ports=10
    RX queues=1 - RX desc=128 - RX free threshold=64
    RX threshold registers: pthresh=8 hthresh=8 wthresh=4
    TX queues=1 - TX desc=512 - TX free threshold=0
    TX threshold registers: pthresh=32 hthresh=8 wthresh=8

Configure the traffic generator to send the multiple packets with the following
combination: good/bad ip checksum + good/bad udp/tcp checksum.

Check the Rx checksum flags consistent with expected flags.
