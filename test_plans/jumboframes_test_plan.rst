.. Copyright (c) <2010,2011>, Intel Corporation
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

============================================
Support of Jumbo Frames by Poll Mode Drivers
============================================

The support of jumbo frames by Poll Mode Drivers consists in enabling a port
to receive Jumbo Frames with a configurable maximum packet length that is
greater than the standard maximum Ethernet frame length (1518 bytes), up to
a maximum value imposed by the hardware.

Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Assuming that ports ``0`` and ``1`` of the test target are directly connected
to the traffic generator, launch the ``testpmd`` application with the following
arguments::

  ./build/app/testpmd -cffffff -n 3 -- -i --rxd=1024 --txd=1024 \
  --burst=144 --txpt=32 --txht=0 --txfreet=0 --rxfreet=64 \
  --mbcache=200 --portmask=0x3 --mbuf-size=2048 --max-pkt-len=9600

The -n command is used to select the number of memory channels. It should match the number of memory channels on that setup.

Setting the size of the mbuf data buffer to 2048 and the maximum packet length
to 9600 (CRC included) makes input Jumbo Frames to be stored in multiple
buffers by the hardware RX engine.

Start packet forwarding in the ``testpmd`` application with the ``start``
command. Then, make the Traffic Generator transmit to the target's port 0
packets of lengths (CRC included) 1517, 1518, 9599, and 9600 respectively.
Check that the same amount of frames and bytes are received back by the
Traffic Generator from its port connected to the target's port 1.

Then, make the Traffic Generator transmit to the target's port 0 packets of
length (CRC included) 9600 and check that no packet is received by the
Traffic Generator from its port connected to the target's port 1.

Configuring the Maximum Length of Jumbo Frames
==============================================

The maximum length of Jumbo Frames is configured with the parameter
``--max-pkt-len=N`` that is supplied in the set of parameters when launching
the ``testpmd`` application.

Functional Tests of Jumbo Frames
================================

Testing the support of Jumbo Frames in Poll Mode Drivers consists in
configuring the maximum packet length with a value greater than 1518, and in
sending to the test machine packets with the following lengths (CRC included):

#. packet length = 1518 - 1

#. packet length = 1518

#. packet length = 1518 + 1

#. packet length = maximum packet length - 1

#. packet length = maximum packet length

#. packet length = maximum packet length + 1

The cases 1) and 2) check that packets of standard lengths are still received
when enabling the receipt of Jumbo Frames.
The cases 3), 4) and 5) check that Jumbo Frames of lengths greater than the
standard maximum frame (1518) and lower or equal to the maximum frame length
can be received.
The case 6) checks that packets larger than the configured maximum packet length
are effectively dropped by the hardware.

Test Case: Normal frames with no jumbo frame support
====================================================

Send a packet with size 1517 bytes ::

  testpmd> show port stats 0
    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 1517
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 1517
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 1517


Send a packet with size 1518 bytes ::

  testpmd> show port stats 0

    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 1518
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 1518
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 1518


Test Case: Jumbo frames with no jumbo frame support
===================================================

Send a packet with size 1519 bytes ::

  testpmd> show port stats 0

   ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 0          RX-errors: 1         RX-bytes: 0
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 0


Test Case: Normal frames with jumbo frame support
=================================================

Start testpmd with jumbo frame support enabled ::

  ./testpmd -cffffff -n 3 -- -i --rxd=1024 --txd=1024 \
  --burst=144 --txpt=32 --txht=8 --txwt=8 --txfreet=0 --rxfreet=64 \
  --mbcache=200 --portmask=0x3 --mbuf-size=2048 --max-pkt-len=9600


Send a packet with size 1517 bytes ::

  testpmd> show port stats 0
    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 1517
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 1517
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 1517


Send a packet with size 1518 bytes ::

  testpmd> show port stats 0

    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 1518
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 1518
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 1518



Test Case: Jumbo frames with jumbo frame support
================================================

Send a packet with size 1519 bytes ::

  testpmd> show port stats 0

    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 1519
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 1519
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 1519


Send a packet with size 9599 bytes ::

  testpmd> show port stats 0

    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 9599
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 9599
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 9599.

Send a packet with size 9600 bytes ::

  testpmd> show port stats 0

    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 1          TX-errors: 0         TX-bytes: 9600
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 9600
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 9600.


Test Case: Frames bigger than jumbo frames, wwith jumbo frame support
=====================================================================

Send a packet with size 9601 bytes ::

  testpmd> show port stats 0

    ######################## NIC statistics for port 0  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 0
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################
  testpmd> show port stats 1

    ######################## NIC statistics for port 1  ########################
    RX-packets: 0          RX-errors: 1         RX-bytes: 0
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that TX-bytes on port 0 and RX-bytes on port 1 are 0.
