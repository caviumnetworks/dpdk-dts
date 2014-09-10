.. Copyright (c) <2012>, Intel Corporation
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

==================================================
Support of Whitelist Features by Poll Mode Drivers
==================================================

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

The support of Whitelist offload features by Poll Mode Drivers consists in:


Prerequisites
=============

Assuming that at least a port is connected to a traffic generator,
launch the ``testpmd`` with the following arguments::
  
  ./x86_64-default-linuxapp-gcc/build/app/test-pmd/testpmd -c 0xc3 -n 3 -- -i \
  --burst=1 --rxpt=0     --rxht=0 --rxwt=0 --txpt=36 --txht=0 --txwt=0 \
  --txfreet=32 --rxfreet=64 --mbcache=250 --portmask=0x3
 
The -n command is used to select the number of memory channels. It should match the number of memory channels on that setup.
 
Set the verbose level to 1 to display informations for each received packet::

  testpmd> set verbose 1 
  
Show port infos for port 0 and store the default MAC address and the maximum 
number of MAC addresses::

  testpmd> show port info 0

    ********************* Infos for port 0  *********************
    MAC address: 00:1B:21:4D:D2:24
    Link status: up
    Link speed: 10000 Mbps
    Link duplex: full-duplex
    Promiscuous mode: enabled
    Allmulticast mode: disabled
    Maximum number of MAC addresses: 127


Test Case: add/remove mac addresses
===================================

Initialise first port without ``promiscuous mode``::

  testpmd> set promisc 0 off

Read the stats for port 0 before sending the packet::

  testpmd> show port stats 8

    ######################## NIC statistics for port 8  ########################
    RX-packets: 0          RX-errors: 0         RX-bytes: 64
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Send a packet with default destination MAC address for port 0::

  testpmd> show port stats 0

    ######################## NIC statistics for port 8  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 128
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).  

Send a packet with destination MAC address different than the port 0 address,
let's call it A.::

  testpmd> show port stats 0

    ######################## NIC statistics for port 8  ########################
    RX-packets: 1          RX-errors: 0         RX-bytes: 128
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was not received (RX-packets not incremented).

Add the MAC address A to the port 0::

  testpmd> mac_addr add 0 <A>
  testpmd> show port stats 0


    ######################## NIC statistics for port 8  ########################
    RX-packets: 2          RX-errors: 0         RX-bytes: 192
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was received (RX-packets incremented).

Remove the MAC address A to the port 0::

  testpmd> mac_addr remove 0 <A>
  testpmd> show port stats 0


    ######################## NIC statistics for port 8  ########################
    RX-packets: 2          RX-errors: 0         RX-bytes: 192
    TX-packets: 0          TX-errors: 0         TX-bytes: 0
    ############################################################################

Verify that the packet was not received (RX-packets not incremented).


Test Case: invalid addresses test
=================================

Add a MAC address of all zeroes to the port 0::

  testpmd> mac_addr add 0 00:00:00:00:00:00

Verify that the response is "Invalid argument" (-EINVAL)
  
Remove the default MAC address::

  testpmd> mac_addr remove 0 <default MAC address>

Verify that the response is "Address already in use" (-EADDRINUSE)
  
Add two times the same address::
  
  testpmd> mac_addr add 0 <A>
  testpmd> mac_addr add 0 <A>
  
Verify that there is no error

Add as many different addresses as maximum MAC addresses (n)::

   testpmd> mac_addr add 0 <A>
   ... n-times
   testpmd> mac_addr add 0 <A+n>

Add one more different address::

   testpmd> mac_addr add 0 <A+n+1>
   
Verify that the response is "No space left on device" (-ENOSPC)
