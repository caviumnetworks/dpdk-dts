.. Copyright (c) <2014>, Intel Corporation
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
   "AS IS" AND ANY EXPR   ESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
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

================
 Fortville Vxlan
================
Cloud providers build virtual network overlays over existing network 
infrastructure that provide tenant isolation and scaling. Tunneling 
layers added to the packets carry the virtual networking frames over
existing Layer 2 and IP networks. Conceptually, this is similar to 
creating virtual private networks over the Internet. Fortville will 
process these tunneling layers by the hardware.

This document provides test plan for Fortville vxlan packet detecting,
checksum computing and filtering.

Prerequisites
=============
1x Intel® X710 (Fortville) NICs (2x 40GbE full duplex optical ports per NIC)
plugged into the available PCIe Gen3 8-lane slot.

1x Intel® XL710-DA4 (Eagle Fountain) (1x 10GbE full duplex optical ports per NIC)
plugged into the avaiable PCIe Gen3 8-lane slot.

DUT board must be two sockets system and each cpu have more than 8 lcores.

Test Case: Vxlan ipv4 packet detect
===================================
Start testpmd with tunneling packet type to vxlan::

	testpmd -c ffff -n 4 -- -i --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2 --txqflags=0x0
	
Set rxonly packet forwarding mode and enable verbose log::

	set fwd rxonly
	set verbose 1
    rx_vxlan_port add 4789 0

Send packet as table listed and check dumped packet type the same as column 
"Rx packet type".

+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Inner L4  | Rx packet type      | Pkt Error |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv4     | None      | None       | None     | None      | PKT_RX_IPV4_HDR     | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv4     | Vxlan     | None       | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv4     | Vxlan     | None       | Ipv4     | Tcp       | PKT_RX_IPV4_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv4     | Vxlan     | None       | Ipv4     | Sctp      | PKT_RX_IPV4_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| Yes        | Ipv4     | Vxlan     | None       | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| Yes        | Ipv4     | Vxlan     | Yes        | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+



Test Case: Vxlan ipv6 packet detect
===================================
Start testpmd with tunneling packet type to vxlan::

	testpmd -c ffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2 --txqflags=0x0
	
Set rxonly packet forwarding mode and enable verbose log::

	set fwd rxonly
	set verbose 1
    rx_vxlan_port add 4789 0

Send ipv6 packet as table listed and check dumped packet type the same as 
column "Rx packet type".

+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 | Rx packet type      | Pkt Error |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv6     | None      | None       | None     | None      | PKT_RX_IPV6_HDR     | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv6     | Vxlan     | None       | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv6     | Vxlan     | None       | Ipv6     | Tcp       | PKT_RX_IPV6_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| No         | Ipv6     | Vxlan     | None       | Ipv6     | Sctp      | PKT_RX_IPV6_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| Yes        | Ipv6     | Vxlan     | None       | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+
| Yes        | Ipv6     | Vxlan     | Yes        | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+------------+----------+-----------+------------+----------+-----------+---------------------+-----------+


Test Case: Vxlan ipv4 checksum offload
======================================

Start testpmd with tunneling packet type to vxlan::

	testpmd -c ffff -n 4 -- -i --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2 --txqflags=0x0
	
Set csum packet forwarding mode and enable verbose log::

	set fwd csum
	set verbose 1
    rx_vxlan_port add 4789 0

Enable VXLAN protocal on ports::

    rx_vxlan_port add 4789 0
    rx_vxlan_port add 4789 1

Enable IP,UDP,TCP,SCTP,OUTER-IP checksum offload::
	
    csum parse_tunnel on 0
    csum parse_tunnel on 1
    csum set ip hw 0
    csum set udp hw 0
    csum set tcp hw 0
    csum set stcp hw 0
    csum set outer-ip hw 0

Send packet with valid checksum and check there's no chksum error counter 
increased.

+------------+----------+-----------+------------+----------+-----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 | Pkt Error |
+------------+----------+-----------+------------+----------+-----------+-----------+
| No         | Ipv4     | None      | None       | None     | None      | None      |
+------------+----------+-----------+------------+----------+-----------+-----------+

Send packet with invalid l3 checksum first. Then check forwarded packet checksum 
corrected and there's correct l3 chksum error counter increased.

+------------+----------+-----------+------------+----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 |
+------------+----------+-----------+------------+----------+-----------+
| No         | Bad Ipv4 | None      | None       | None     | None      |
+------------+----------+-----------+------------+----------+-----------+
| No         | Ipv4     | Vxlan     | None       | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| No         | Bad Ipv4 | Vxlan     | None       | Ipv4     | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| No         | Bad Ipv4 | Vxlan     | None       | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+

Send packet with invalid l4 checksum first. Then check forwarded packet checksum 
corrected and there's correct l4 chksum error counter increased.

+------------+----------+-----------+------------+----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 |
+------------+----------+-----------+------------+----------+-----------+
| No         | Ipv4     | Vxlan     | None       | Ipv4     | Bad Udp   |
+------------+----------+-----------+------------+----------+-----------+
| No         | Ipv4     | Vxlan     | None       | Ipv4     | Bad Tcp   |
+------------+----------+-----------+------------+----------+-----------+
| No         | Ipv4     | Vxlan     | None       | Ipv4     | Bad Sctp  |
+------------+----------+-----------+------------+----------+-----------+

Send vlan packet with invalid l3 checksum first. Then check forwarded packet 
checksum corrected and there's correct l3 chksum error counter increased.

+------------+----------+-----------+------------+----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Bad Ipv4 | Vxlan     | None       | Ipv4     | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv4     | Vxlan     | None       | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Bad Ipv4 | Vxlan     | None       | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Bad Ipv4 | Vxlan     | Yes        | Ipv4     | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv4     | Vxlan     | Yes        | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Bad Ipv4 | Vxlan     | Yes        | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+

Send vlan packet with invalid l4 checksum first. Then check forwarded packet 
checksum corrected and there's correct l4 chksum error counter increased.

+------------+----------+-----------+------------+----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv4     | Vxlan     | None       | Ipv4     | Bad Udp   |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv4     | Vxlan     | None       | Ipv4     | Bad Tcp   |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv4     | Vxlan     | None       | Ipv4     | Bad Sctp  |
+------------+----------+-----------+------------+----------+-----------+


Test Case: Vxlan ipv6 checksum offload
======================================
Start testpmd with tunneling packet type::

	testpmd -c ffff -n 4 -- -i --tunnel-type=1 --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2
	
Set csum packet forwarding mode and enable verbose log::

	set fwd csum
	set verbose 1


Enable VXLAN protocal on ports::

    rx_vxlan_port add 4789 0
    rx_vxlan_port add 4789 1

Enable IP,UDP,TCP,SCTP,VXLAN checksum offload::
	
    csum parse_tunnel on 0
    csum parse_tunnel on 1
    csum set ip hw 0
    csum set udp hw 0
    csum set tcp hw 0
    csum set stcp hw 0
    csum set outer-ip hw 0

Send ipv6 packet with valid checksum and check there's no chksum error counter 
increased.

+------------+----------+-----------+------------+----------+-----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Innter L4 | Pkt Error |
+------------+----------+-----------+------------+----------+-----------+-----------+
| No         | Ipv6     | None      | None       | None     | None      | None      |
+------------+----------+-----------+------------+----------+-----------+-----------+


Send ipv6 packet with invalid l3 checksum first. Then check forwarded packet 
checksum corrected and there's correct l3 chksum error counter increased.

+------------+----------+-----------+------------+----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Inner L4  |
+------------+----------+-----------+------------+----------+-----------+
| No         | Ipv6     | Vxlan     | None       | Ipv4     | None      |
+------------+----------+-----------+------------+----------+-----------+
| No         | Ipv6     | Vxlan     | None       | Bad Ipv4 | Udp       |
+------------+----------+-----------+------------+----------+-----------+

Send vlan+ipv6 packet with invalid l4 checksum first. Then check forwarded 
packet checksum corrected and there's correct l4 chksum error counter 
increased.

+------------+----------+-----------+------------+----------+-----------+
| Outer Vlan | Outer IP | Outer UDP | Inner Vlan | Inner L3 | Inner L4  |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv6     | Vxlan     | None       | Ipv4     | Bad Udp   |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv6     | Vxlan     | None       | Ipv4     | Bad Tcp   |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv6     | Vxlan     | None       | Ipv4     | Bad Sctp  |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv6     | Vxlan     | Yes        | Ipv4     | Bad Udp   |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv6     | Vxlan     | Yes        | Ipv4     | Bad Tcp   |
+------------+----------+-----------+------------+----------+-----------+
| Yes        | Ipv6     | Vxlan     | Yes        | Ipv4     | Bad Sctp  |
+------------+----------+-----------+------------+----------+-----------+

Test Case: Cloud Filter
========================
Start testpmd with tunneling packet type to vxlan and disable receive side 
scale for hardware limitation::

	testpmd -c ffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2 --txqflags=0x0
	
Set rxonly packet forwarding mode and enable verbose log::

	set fwd rxonly
	set verbose 1

Add one new Cloud filter as table listed first::

	tunnel_filter add 0 11:22:33:44:55:66 00:00:20:00:00:01 192.168.2.2 1 vxlan imac-ivlan 1 3

Then send one packet and check packet was forwarded into right queue.

+------------+------------+------------+----------+----------+--------+-------+
| Outer Mac  | Inner Mac  | Inner Vlan | Outer Ip | Inner Ip | Vni ID | Queue |
+------------+------------+------------+----------+----------+--------+-------+
| No         | Yes        | Yes        | No       | No       | No     | 1     |
+------------+------------+------------+----------+----------+--------+-------+
| No         | Yes        | Yes        | No       | No       | Yes    | 1     |
+------------+------------+------------+----------+----------+--------+-------+
| No         | Yes        | No         | No       | No       | Yes    | 1     |
+------------+------------+------------+----------+----------+--------+-------+
| No         | Yes        | No         | No       | No       | No     | 1     |
+------------+------------+------------+----------+----------+--------+-------+
| Yes        | Yes        | No         | No       | Yes      | Yes    | 1     |
+------------+------------+------------+----------+----------+--------+-------+
| No         | No         | No         | No       | Yes      | No     | 1     |
+------------+------------+------------+----------+----------+--------+-------+


Add Cloud filter to max number will be failed.

Remove Cloud filter which has been added. Then send one packet and check 
packet was received in queue 0.

Add Cloud filter with invalid Mac address "00:00:00:00:01" will be failed.

Add Cloud filter with invalid ip address "192.168.1.256" will be failed.

Add Cloud filter with invalid vlan "4097" will be failed.

Add Cloud filter with invalid vni "16777216" will be failed.

Add Cloud filter with invalid queue id "64" will be failed.

Test Case: Vxlan Checksum Offload Performance Benchmarking
==========================================================

The throughput is measured for each of these cases for vxlan tx checksum
offload of "all by software", "L3 offload by hardware", "L4 offload by
hardware", "l3&l4 offload by hardware".

The results are printed in the following table:

+----------------+--------+--------+------------+
| Calculate Type | Queues | Mpps   | % linerate |
+================+========+========+============+
| SOFTWARE ALL   | Single |        |            |
+----------------+--------+--------+------------+
| HW L4          | Single |        |            |
+----------------+--------+--------+------------+
| HW L3&L4       | Single |        |            |
+----------------+--------+--------+------------+
| SOFTWARE ALL   | Multi  |        |            |
+----------------+--------+--------+------------+
| HW L4          | Multi  |        |            |
+----------------+--------+--------+------------+
| HW L3&L4       | Multi  |        |            |
+----------------+--------+--------+------------+

Test Case: Vxlan Tunnel filter Performance Benchmarking
=======================================================
The throughput is measured for different Vxlan tunnel filter types.
Queue single mean there's only one flow and forwarded to the first queue.
Queue multi mean there're two flows and configure to different queues.

+--------+------------------+--------+--------+------------+
| Packet | Filter           | Queue  | Mpps   | % linerate |
+========+==================+========+========+============+
| Normal | None             | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | None             | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac-ivlan       | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac-ivlan-tenid | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac-tenid       | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac             | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | omac-imac-tenid  | Single |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac-ivlan       | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac-ivlan-tenid | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac-tenid       | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | imac             | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| Vxlan  | omac-imac-tenid  | Multi  |        |            |
+--------+------------------+--------+--------+------------+
