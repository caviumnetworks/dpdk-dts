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

=======================================
Change driver configuration dynamically
=======================================

The purpose of this test is to check that it is possible to change the
configuration of a port dynamically. The following command can be used
to change the promiscuous mode of a specific port::
  
  set promisc PORTID on|off

A traffic generator sends traffic with a different destination mac
address than the one that is configured on the port. Once the
``testpmd`` application is started, it is possible to display the
statistics of a port using::
  
  show port stats PORTID

When promiscuous mode is disabled, packet must not be received. When
it is enabled, packets must be received. The change occurs without
stopping the device or restarting the application.


Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Connect the traffic generator to one of the ports (8 in this example).
The size of the packets is not important, in this example it was 64.

Start the testpmd application.

Use the 'show port' command to see the MAC address and promiscuous mode for port 8.
The default value for promosuous mode should be enabled::

  testpmd> show port info 8

  ********************* Infos for port 8  *********************
  MAC address: 00:1B:21:6D:A3:6E
  Link status: up
  Link speed: 1000 Mbps
  Link duplex: full-duplex
  Promiscuous mode: enabled
  Allmulticast mode: disabled


Test Case: Default Mode
=======================

The promiscuous mode should be enabled by default. 
In promiscuous mode all packets should be received.

Read the stats for port 8 before sending packets.::
  
  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 64
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Send a packet with destination MAC address different than the port 8 address.::

  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 2          RX-errors: 0         RX-bytes: 128
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).
Send a packet with with destination MAC address equal with the port 8 address.::

  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 3          RX-errors: 0         RX-bytes: 192
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).


Test Case: Disable Promiscuous Mode
===================================

Disable promiscuous mode and verify that the packets are received only for the
packet with destination address matching the port 8 address.::
  
  testpmd> set promisc 8 off

Send a packet with destination MAC address different than the port 8 address.::

  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 3          RX-errors: 0         RX-bytes: 192
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that no packet was received (RX-packets is the same).

Send a packet with destination MAC address equal to the port 8 address.::

    ######################## NIC statistics for port 8  ########################
    RX-packets: 4          RX-errors: 0         RX-bytes: 256
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).



Test Case: Enable Promiscuous Mode
==================================

Verify that promiscous mode is still disabled:::

  testpmd> show port info 8

  ********************* Infos for port 8  *********************
  MAC address: 00:1B:21:6D:A3:6E
  Link status: up
  Link speed: 1000 Mbps
  Link duplex: full-duplex
  Promiscuous mode: disabled
  Allmulticast mode: disabled

Enable promiscuous mode and verify that the packets are received for any 
destination MAC address.::

  testpmd> set promisc 8 on
  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 4          RX-errors: 0         RX-bytes: 256
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################
   testpmd> show port stats 8

Send a packet with destination MAC address different than the port 8 address.::

  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 5          RX-errors: 0         RX-bytes: 320
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).

Send a packet with with destination MAC address equal with the port 8 address.::

  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 6          RX-errors: 0         RX-bytes: 384
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).



 
