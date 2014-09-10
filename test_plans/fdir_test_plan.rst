.. <COPYRIGHT_TAG>


==============================================
Testing of 82599 Flow Director Support in DPDK
==============================================


Description
===========

This document provides the plan for testing the Flow Director (FDir) feature of
the Intel 82599 10GbE Ethernet Controller. FDir allows an application to add
filters that identify specific flows (or sets of flows), by examining the VLAN
header, IP addresses, port numbers, protocol type (IPv4/IPv6, UDP/TCP, SCTP), or
a two-byte tuple within the first 64 bytes of the packet.

There are two types of filters:

1. Perfect match filters, where there must be a match between the fields of
   received packets and the programmed filters.
2. Signature filters, where there must be a match between a hash-based signature
   if the fields in the received packet.

There is also support for global masks that affect all filters by masking out
some fields, or parts of fields from the matching process.

Within DPDK, the FDir feature can be configured through the API in the
lib_ethdev library, and this API is used by the ``testpmd`` application.

Note that RSS features can not be enabled at the same time as FDir.


Prerequisites
=============

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

The DUT has a dual port Intel 82599 10GbE Ethernet Controller, with one of these
ports connected to a port on another device that is controlled by the Scapy
packet generator.

The Ethernet interface identifier of the port that Scapy will use must be known.
In all tests below, it is referred to as "eth9".

The following packets should be created in Scapy. Any reasonable MAC address can
be given but other fields must be as shown::

  p_udp=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/IP(src="192.168.0.1",
    dst="192.168.0.2")/UDP(sport=1024,dport=1024)
  p_udp1=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/IP(src="192.168.1.1",
    dst="192.168.1.2")/UDP(sport=0,dport=0)
  p_tcp=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/IP(src="192.168.0.1",
    dst="192.168.0.2")/TCP(sport=1024,dport=1024)
  p_ip=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/IP(src="192.168.0.1",
    dst="192.168.0.2")
  p_ipv6_udp=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IPv6(src="2001:0db8:85a3:0000:0000:8a2e:0370:7000",
    dst="2001:0db8:85a3:0000:0000:8a2e:0370:7338")/UDP(sport=1024,dport=1024)
  p_udp_1=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="192.168.0.1", dst="192.168.0.1")/UDP(sport=1024,dport=1024)
  p_udp_2=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")
    /IP(src="192.168.0.15", dst="192.168.0.15")/UDP(sport=1024,dport=1024)
  p_udp_3=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="192.168.0.1", dst="192.168.1.1")/UDP(sport=1024,dport=1024)
  p_udp_4=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4400,dport=0x4500)
  p_udp_5=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4411,dport=0x4517)
  p_udp_6=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="10.11.12.1", dst="10.11.12.2")/UDP(sport=0x4500,dport=0x5500)
  p_gre1=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0x1)/IP()/UDP()
  p_gre2=Ether(src=get_if_hwaddr("eth9"), dst="00:1B:21:91:3D:2C")/
    IP(src="192.168.0.1", dst="192.168.0.2")/GRE(proto=0xff)/IP()/UDP()

The test commands below assume that port 0 on the DUT is the port that is
connected to the traffic generator. If this is not the case, the following
``testpmd`` commands must be changed, and also the ``--portmask`` parameter.

  * ``show port fdir <port>``
  * ``add_perfect_filter <port>``
  * ``add_signature_filter <port>``
  * ``set_masks_filter <port>``
  * ``rx_vlan add all <port>``

Most of the tests below involve sending single packets from the generator and
checking if the packets match the configured filter, and go to a set queue. To
see this, there must be multiple queues, setup by passing the following command-
line arguments: ``--nb-cores=2 --rxq=2 --txq=2``. And at run-time, the
forwarding mode must be set to rxonly, and the verbosity level > 0 ::

  testpmd> set verbose 1
  testpmd> set fwd rxonly


Test case: Setting memory reserved for FDir filters
===================================================

Each FDir filter requires space in the Rx Packet Buffer (perfect filters require
32 B of space, and signature filters require 8 B of space). The total amount of
memory - and therefore the number of concurrent filters - can be set when
initialising FDir.


Sub-case: Reserving 64 KB
-------------------------

Start the ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=0x1 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=64K

Check with the ``show port fdir`` command that the amount of FDIR filters that
are free to be used is equal to 2048 (2048 * 32B = 64KB).::
  
  testpmd> show port fdir 0
  
  ######################## FDIR infos for port 0  ########################
  collision: 0          free: 2048
  maxhash: 0          maxlen: 0
  add : 0            remove : 0
  f_add: 0          f_remove: 0
  ########################################################################


Sub-case: Reserving 128 KB
--------------------------

Start the ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=0x1 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=128K

Check with the ``show port fdir`` command that the amount of FDIR filters that
are free to be used is equal to 4096 (4096 * 32B = 128KB).::
  
  testpmd> show port fdir 0
  
  ######################## FDIR infos for port 0  ########################
  collision: 0          free: 4096
  maxhash: 0          maxlen: 0
  add : 0            remove : 0
  f_add: 0          f_remove: 0
  ########################################################################


Sub-case: Reserving 256 KB
--------------------------

Start the ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=0x1 --disable-rss --pkt-filter-mode=perfect --pkt-filter-size=256K

Check with the ``show port fdir`` command that the amount of FDIR filters that
are free to be used is equal to 8192 (8192 * 32B = 256KB).::
  
  testpmd> show port fdir 0
  
  ######################## FDIR infos for port 0  ########################
  collision: 0          free: 8192
  maxhash: 0          maxlen: 0
  add : 0            remove : 0
  f_add: 0          f_remove: 0
  ########################################################################


Test case: Control levels of FDir match reporting
=================================================

The status of FDir filter matching for each packet can be reported by the
hardware through the RX descriptor of each received packet, and this information
is copied into the packet mbuf, that can be examined by the application.

There are three different reporting modes, that can be set in testpmd using the
``--pkt-filter-report-hash`` command line argument:


Sub-case: ``--pkt-filter-report-hash=none`` mode
------------------------------------------------

In this mode FDir reporting mode, matches are never reported.
Start the ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=0x1 --nb-cores=2 --rxq=2 --txq=2
    --disable-rss --pkt-filter-mode=perfect --pkt-filter-report-hash=none
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Send the ``p_udp`` packet with Scapy on the traffic generator and check that no
FDir information is printed::

  testpmd> port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Add a perfect filter to match the ``p_udp`` packet, and send the packet again.
No Dir information is printed, but it can be seen that the packet went to queue
1 ::

  testpmd> add_perfect_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x800 vlan 0 queue 1 soft 0x14
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Sub-case: ``--pkt-filter-report-hash=match`` mode
-------------------------------------------------

In this mode FDir reporting mode, FDir information is printed for packets that
match a filter.
Start the ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=0x1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss
    --pkt-filter-mode=perfect --pkt-filter-report-hash=match
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Send the ``p_udp`` packet with Scapy on the traffic generator and check that no
FDir information is printed::

  testpmd> port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Add a perfect filter to match the ``p_udp`` packet, and send the packet again.
This time, the match is indicated (``PKT_RX_PKT_RX_FDIR``), and its details
(hash, id) printed ::

  testpmd> add_perfect_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x800 vlan 0 queue 1 soft 0x14
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60
    -nb_segs=1 - FDIR hash=0x43c - FDIR id=0x14
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Update the perfect filter to match the ``p_udp1`` packet, and send the packet again.
This time, the match is indicated (``PKT_RX_PKT_RX_FDIR``), and its details
(hash, id) printed ::

  testpmd> add_perfect_filter 0 udp src 192.168.1.1 1024 dst 192.168.1.2 0
     flexbytes 0x800 vlan 0 queue 1 soft 0x14
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60
    -nb_segs=1 - FDIR hash=0x43c - FDIR id=0x14
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
     
Remove the perfect filter match the ``p_udp1`` and ``p_udp`` packets, and send the packet again.
Check that no FDir information is printed::

  testpmd> port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Sub-case: ``--pkt-filter-report-hash=always`` mode
--------------------------------------------------

In this mode FDir reporting mode, FDir information is printed for every received
packet.
Start the ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=0x1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss
    --pkt-filter-mode=perfect --pkt-filter-report-hash=always
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Send the ``p_udp`` packet with Scapy on the traffic generator and check the
output (FDIR id=0x0)::

  testpmd> port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60
    - nb_segs=1 - FDIR hash=0x43c - FDIR id=0x0
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Add a perfect filter to match the ``p_udp`` packet, and send the packet again.
This time, the filter ID is different, and the packet goes to queue 1 ::

  testpmd> add_perfect_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x800 vlan 0 queue 1 soft 0x14
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60
    - nb_segs=1 - FDIR hash=0x43c - FDIR id=0x14
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Test case: FDir signature matching mode
=======================================

This test adds signature filters to the hardware, and then checks whether sent
packets match those filters. In order to this, the packet should first be sent
from ``Scapy`` before the filter is created, to verify that it is not matched by
a FDir filter. The filter is then added from the ``testpmd`` command line and
the packet is sent again.

Launch the userland ``testpmd`` application as follows::
  
  ./testpmd -c 0xf -- -i --portmask=1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss
    --pkt-filter-mode=signature
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Send the ``p_udp`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_signature_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2
    1024 flexbytes 0x800 vlan 0 queue 1
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x143c - FDIR id=0xe230
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR



    
Send the ``p_tcp`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_signature_filter 0 tcp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x800 vlan 0 queue 1
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x1b47 - FDIR id=0xbd2b
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
    
Send the ``p_ip`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_signature_filter 0 ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x800 vlan 0 queue 1
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x1681 - FDIR id=0xf3ed
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Send the ``p_ipv6_udp`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_signature_filter 0 udp src 2001:0db8:85a3:0000:0000:8a2e:0370:7000 1024
    dst 2001:0db8:85a3:0000:0000:8a2e:0370:7338 1024 flexbytes 0x86dd vlan 0 queue 1
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x86dd - length=62 - nb_segs=1
    - FDIR hash=0x4aa - FDIR id=0xea83
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IPV6_HDR


Test case: FDir perfect matching mode
=====================================

This test adds perfect-match filters to the hardware, and then checks whether
sent packets match those filters. In order to this, the packet should first be
sent from ``Scapy`` before the filter is created, to verify that it is not
matched by a FDir filter. The filter is then added from the ``testpmd`` command
line and the packet is sent again.::

  ./testpmd -c 0xf -- -i --portmask=1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss
    --pkt-filter-mode=perfect
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Send the ``p_udp`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_perfect_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x800 vlan 0 queue 1 soft 0x14
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x43c - FDIR id=0x14
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Update the perfect filter match the ``p_udp1`` packet and send the packet and check
that there is a match::

  testpmd> add_perfect_filter 0 udp src 192.168.1.1 1024 dst 192.168.1.2 0
     flexbytes 0x800 vlan 0 queue 1 soft 0x14
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60
    -nb_segs=1 - FDIR hash=0x43c - FDIR id=0x14
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
     
Remove the perfect filter match the ``p_udp1`` and ``p_udp`` packets, and send the packet again.
Check that no FDir information is printed::

  testpmd> port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Send the ``p_tcp`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_perfect_filter 0 tcp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x800 vlan 0 queue 1 soft 0x15
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x347 - FDIR id=0x15
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Send the ``p_ip`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_perfect_filter 0 ip src 192.168.0.1 0 dst 192.168.0.2 0
    flexbytes 0x800 vlan 0 queue 1 soft 0x17
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x681 - FDIR id=0x17
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Test case: FDir filter masks
============================

This section tests the functionality of the setting FDir masks to to affect
which fields, or parts of fields are used in the matching process. Note that 
setting up a mask resets all the FDir filters, so the ``testpmd`` application
does not have to be relaunched for each sub-case.

Launch the userland ``testpmd`` application::
  
  ./testpmd -c 0xf -- -i --portmask=1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss
    --pkt-filter-mode=perfect
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Sub-case: IP address masking
----------------------------

Create the following IPv4 mask on port 0. This mask means the lower byte of the 
source and destination IP addresses will not be considered in the matching
process::
  
  testpmd> set_masks_filter 0 only_ip_flow 0 src_mask 0xffffff00 0xffff
    dst_mask 0xffffff00 0xffff flexbytes 1 vlan_id 1 vlan_prio 1

Then, add the following perfect IPv4 filter::
  
  testpmd> add_perfect_filter 0 udp src 192.168.0.0 1024 dst 192.168.0.0 1024
    flexbytes 0x800 vlan 0 queue 1 soft 0x17

Then send the ``p_udp_1``, ``p_udp_2``, and ``p_udp_3`` packets from Scapy. The
first two packets should match the masked filter, but the third packet will not,
as it differs in the second lowest IP address byte.::

  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x6cf - FDIR id=0x17
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
  port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x6cf - FDIR id=0x17
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
  port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Sub-case: Port masking
----------------------

Create the following mask on port 0. This mask means the lower byte of the 
source and destination ports will not be considered in the matching process::
  
  testpmd> set_masks_filter 0 only_ip_flow 0 src_mask 0xffffffff 0xff00
    dst_mask 0xffffffff 0xff00 flexbytes 1 vlan_id 1 vlan_prio 1

Then, add the following perfect IPv4 filter::
  
  testpmd> add_perfect_filter 0 udp src 10.11.12.1 0x4400 dst 10.11.12.2 0x4500
    flexbytes 0x800 vlan 0 queue 1 soft 0x4

Then send the ``p_udp_4``, ``p_udp_5``, and ``p_udp_6`` packets from Scapy. The
first two packets should match the masked filter, but the third packet will not,
as it differs in higher byte of the port numbers.::

  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x41d - FDIR id=0x4
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
  port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x41d - FDIR id=0x4
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
  port 0/queue 0: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Sub-case: L4Type field masking
------------------------------

Create the following mask on port 0. This mask means that the L4type field of
packets will not be considered. Note that in this case, the source and the
destination port masks are irrelevant and must be set to zero::
  
  testpmd> set_masks_filter 0 only_ip_flow 1 src_mask 0xffffffff 0x0
    dst_mask 0xffffffff 0x0 flexbytes 1 vlan_id 1 vlan_prio 1

Then, add the following perfect IPv4 filter::
  
  testpmd> add_perfect_filter 0 ip src 192.168.0.1 0 dst 192.168.0.2 0
    flexbytes 0x800 vlan 0 queue 1 soft 0x42

Then send the ``p_udp`` and ``p_tcp`` packets from Scapy. Both packets will
match the filter::

  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x681 - FDIR id=0x42
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
  port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=60 - nb_segs=1
    - FDIR hash=0x681 - FDIR id=0x42
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Test case: FDir ``flexbytes`` filtering
=======================================

The FDir feature supports setting up filters that can match on any two byte
field within the first 64 bytes of a packet. Which byte offset to use is
set by passing command line arguments to ``testpmd``. In this test a value of 
``18`` corresponds to the bytes at offset 36 and 37, as the offset is in 2-byte
units::

  ./testpmd -c 0xf -- -i --portmask=1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss
    --pkt-filter-mode=perfect --pkt-filter-flexbytes-offset=18
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> start

Send the ``p_gre1`` packet and verify that there is not a match. Then add the
filter and check that there is a match::

  testpmd> add_perfect_filter 0 ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x1 vlan 0 queue 1 soft 0x1
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=66 - nb_segs=1
    - FDIR hash=0x18b - FDIR id=0x1
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR

Send the ``p_gre2`` packet and verify that there is not a match. Then add a
second filter and check that there is a match::

  testpmd> add_perfect_filter 0 ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0xff vlan 0 queue 1 soft 0xff
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=66 - nb_segs=1 - FDIR hash=0x3a1 - FDIR id=0xff
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Sub-case: ``flexbytes`` FDir masking
------------------------------------

A mask can also be applied to the ``flexbytes`` filter::
    
  testpmd> set_masks_filter 0 only_ip_flow 0 src_mask 0xffffffff 0xffff
    dst_mask 0xffffffff 0xffff flexbytes 0 vlan_id 1 vlan_prio 1

Then, add the following perfect filter (same as first filter in prev. test), and
check that this time both packets match (``p_gre1`` and ``p_gre2``)::
  
  testpmd> add_perfect_filter 0 ip src 192.168.0.1 0 dst 192.168.0.2 0 flexbytes 0x0 vlan 0 queue 1 soft 0x42
  testpmd> port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=66 - nb_segs=1 - FDIR hash=0x2f3 - FDIR id=0x42
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
  port 0/queue 1: received 1 packets
    src=00:1B:21:53:1F:14 - dst=00:1B:21:91:3D:2C - type=0x0800 - length=66 - nb_segs=1 - FDIR hash=0x2f3 - FDIR id=0x42
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR
    

Test case: FDir VLAN field filtering
====================================

Connect port 0 of the DUT to a traffic generator capable of sending packets with
VLAN headers.

Then launch the ``testpmd`` application, and enable VLAN packet reception::
  
  ./testpmd -c 0xf -- -i --portmask=1 --nb-cores=2 --rxq=2 --txq=2 --disable-rss --pkt-filter-mode=perfect
  testpmd> set verbose 1
  testpmd> set fwd rxonly
  testpmd> rx_vlan add all 0
  testpmd> start

From the traffic generator, transmit a packet with the following details, and 
verify that it does not match any FDir filters.:

* VLAN ID = 0x0FFF
* IP source address = 192.168.0.1
* IP destination address = 192.168.0.2
* UDP source port = 1024
* UDP destination port = 1024

Then, add the following perfect VLAN filter, resend the packet and verify that
it matches the filter::
  
  testpmd> add_perfect_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x8100 vlan 0xfff queue 1 soft 0x47
  testpmd> port 0/queue 1: received 1 packets
    src=00:00:03:00:03:00 - dst=00:00:03:00:02:00 - type=0x0800 - length=64 - nb_segs=1
    - FDIR hash=0x7e9 - FDIR id=0x47  - VLAN tci=0xfff
    PKT_RX_VLAN_PKT
    PKT_RX_PKT_RX_FDIR
    PKT_RX_IP_CKSUM
    PKT_RX_IPV4_HDR


Sub-case: VLAN field masking
----------------------------

First, set the following mask to disable the matching of the VLAN field, and add
a perfect filter to match any VLAN identifier::
  
  testpmd> set_masks_filter 0 only_ip_flow 0 src_mask 0xffffffff 0xffff 
    dst_mask 0xffffffff 0xffff flexbytes 1 vlan_id 0 vlan_prio 0
  testpmd> add_perfect_filter 0 udp src 192.168.0.1 1024 dst 192.168.0.2 1024
    flexbytes 0x8100 vlan 0 queue 1 soft 0x47

Then send the same packet above, but with the VLAN field change first to 0x001,
and then to 0x0017. The packets should still match the filter:::

  testpmd> port 0/queue 1: received 1 packets
  src=00:00:03:00:03:00 - dst=00:00:03:00:02:00 - type=0x0800 - length=64 - nb_segs=1
    - FDIR hash=0x7e8 - FDIR id=0x47  - VLAN tci=0x1
  PKT_RX_VLAN_PKT
  PKT_RX_PKT_RX_FDIR
  PKT_RX_IP_CKSUM
  PKT_RX_IPV4_HDR
  port 0/queue 1: received 1 packets
  src=00:00:03:00:03:00 - dst=00:00:03:00:02:00 - type=0x0800 - length=64 - nb_segs=1
    - FDIR hash=0x7e8 - FDIR id=0x47  - VLAN tci=0x17
  PKT_RX_VLAN_PKT
  PKT_RX_PKT_RX_FDIR
  PKT_RX_IP_CKSUM
  PKT_RX_IPV4_HDR
