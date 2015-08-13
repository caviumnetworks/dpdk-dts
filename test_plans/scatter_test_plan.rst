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

=================================================
Support of Scattered Packets by Poll Mode Drivers
=================================================

The support of scattered packets by Poll Mode Drivers consists in making
it possible to receive and to transmit scattered multi-segments packets
composed of multiple non-contiguous memory buffers.
To enforce the receipt of scattered packets, the DMA rings of port RX queues
must be configured with mbuf data buffers whose size is lower than the maximum
frame length.
The forwarding of scattered input packets naturally enforces the transmission
of scattered packets by PMD transmit functions.

Configuring the size of mbuf data buffers
=========================================

The size of mbuf data buffers is configured with the parameter ``--mbuf-size``
that is supplied in the set of parameters when launching the ``testpmd``
application.
The default size of the mbuf data buffer is 2048 so that a full 1518-byte
(CRC included) Ethernet frame can be stored in a mono-segment packet.

Functional Tests of Scattered Packets
=====================================

Testing the support of scattered packets in Poll Mode Drivers consists in
sending to the test machine packets whose length is greater than the size
of mbuf data buffers used to populate the DMA rings of port RX queues.

First, the receipt and the transmission of scattered packets must be tested
with the ``CRC stripping`` option enabled, which guarantees that scattered
packets only contain packet data.

In addition, the support of scattered packets must also be performed with
the ``CRC stripping`` option disabled, to check the special cases of scattered
input packets whose last buffer only contains the whole CRC or part of it.
In such cases, PMD receive functions must free the last buffer when removing
the CRC from the packet before returning it.

As a whole, the following packet lengths (CRC included) must be tested to
check all packet memory configurations:

#. packet length < mbuf data buffer size

#. packet length = mbuf data buffer size

#. packet length = mbuf data buffer size + 1

#. packet length = mbuf data buffer size + 4

#. packet length = mbuf data buffer size + 5

In cases 1) and 2), the hardware RX engine stores the packet data and the CRC
in a single buffer.
In case 3), the hardware RX engine stores the packet data and the 3 first bytes
of the CRC in the first buffer, and the last byte of the CRC in a second buffer.
In case 4), the hardware RX engine stores all the packet data in the first
buffer, and the CRC in a second buffer.
In case 5), the hardware RX engine stores part of the packet data in the first
buffer, and the last data byte plus the CRC in a second buffer.

Prerequisites
=============

Assuming that ports ``0`` and ``1`` of the test target are directly connected
to a Traffic Generator, launch the ``testpmd`` application with the following
arguments::
  
  ./build/app/testpmd -cffffff -n 3 -- -i --rxd=1024 --txd=1024 \
  --burst=144 --txpt=32 --txht=8 --txwt=8 --txfreet=0 --rxfreet=64 \
  --mbcache=200 --portmask=0x3 --mbuf-size=1024

The -n command is used to select the number of memory channels. It should match 
the number of memory channels on that setup.

Setting the size of the mbuf data buffer to 1024 makes 1025-bytes input packets
(CRC included) and larger packets to be stored in two buffers by the hardware
RX engine.

Test Case: Mbuf 1024 traffic
============================

Start packet forwarding in the ``testpmd`` application with the ``start`` command.
Send 5 packets of lengths (CRC included) 1023, 1024, 1025, 1028, and 1029.
Check that the same amount of frames and bytes are received back by the Traffic 
Generator from its port connected to the target's port 1.

