.. Copyright (c) <2015>, Intel Corporation
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
 Fortville NVGRE
================
Cloud providers build virtual network overlays over existing network 
infrastructure that provide tenant isolation and scaling. Tunneling 
layers added to the packets carry the virtual networking frames over
existing Layer 2 and IP networks. Conceptually, this is similar to 
creating virtual private networks over the Internet. Fortville will 
process these tunneling layers by the hardware.

This document provides test plan for Fortville NVGRE packet detecting,
checksum computing and filtering.

Prerequisites
=============
1x Intel� X710 (Fortville) NICs (2x 40GbE full duplex optical ports per NIC)
plugged into the available PCIe Gen3 8-lane slot.

1x Intel� XL710-DA4 (Eagle Fountain) (1x 10GbE full duplex optical ports per NIC)
plugged into the avaiable PCIe Gen3 8-lane slot.

DUT board must be two sockets system and each cpu have more than 8 lcores.

Test Case: NVGRE ipv4 packet detect
===================================
Start testpmd with tunneling packet type to NVGRE::

    testpmd -c 0xffff -n 4 -- -i --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2
    
Set rxonly packet forwarding mode and enable verbose log::

    set fwd rxonly
    set verbose 1

Send packet as table listed and check dumped packet type the same as column 
"Rx packet type".

+-----------+-----------+----------+---------+----------|-----------+----------+-----------+---------------------+-----------+
| Outer L2  |Outer Vlan | Outer L3 | NVGRE   | Inner L2 |Inner Vlan | Inner L3 | Inner L4  | Rx packet type  | Pkt Error |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | None    | None     | None      | None     | None      | PKT_RX_IPV4_HDR     | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4     | Tcp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4     | Sctp      | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv4     | Yes     | Yes      | None      | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv4     | Yes     | Yes      | Yes       | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+



Test Case: NVGRE ipv6 packet detect
===================================
Start testpmd with tunneling packet type to NVGRE::

    testpmd -c 0xffff -n 2 -- -i --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2
    
Set rxonly packet forwarding mode and enable verbose log::

    set fwd rxonly
    set verbose 1

Send ipv6 packet as table listed and check dumped packet type the same as 
column "Rx packet type".

+-----------+-----------+----------+---------+----------|-----------+----------+-----------+---------------------+-----------+
| Outer L2  |Outer Vlan | Outer L3 | NVGRE   | Inner L2 |Inner Vlan | Inner L3 | Inner L4  | Rx packet type  | Pkt Error |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | None    | None     | None      | None     | None      | PKT_RX_IPV6_HDR     | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6     | Tcp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6     | Sctp      | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv6     | Yes     | Yes      | None      | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv6     | Yes     | Yes      | Yes       | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+

Test Case: NVGRE IPv4 Filter
========================
This test adds NVGRE IPv4 filters to the hardware, and then checks whether 
sent packets match those filters. In order to this, the packet should first 
be sent from ``Scapy`` before the filter is created, to verify that it is not 
matched by a NVGRE IPv4 filter. The filter is then added from the ``testpmd`` 
command line and the packet is sent again.

Start testpmd::

    testpmd -c 0xffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2
    
Set rxonly packet forwarding mode and enable verbose log::

    set fwd rxonly
    set verbose 1

Add one new NVGRE filter as table listed first::
    tunnel_filter add port_id outer_mac inner_mac ip_addr inner_vlan 
    tunnel_type(vxlan|nvgre) filter_type(imac-ivlan|imac-ivlan-tenid|imac-tenid|imac
    |omac-imac-tenid|iip) tenant_id queue_num
    
For example:
    tunnel_filter add 0 11:22:33:44:55:66 00:00:20:00:00:01 192.168.2.2 1 
    NVGRE imac 1 1

Then send one packet and check packet was forwarded into right queue.

+-----------+-----------+----------+---------+----------|-----------+----------+-----------+---------------------+-----------+
| Outer L2  |Outer Vlan | Outer L3 | NVGRE   | Inner L2 |Inner Vlan | Inner L3 | Inner L4  | Rx packet type  | Pkt Error |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | None    | None     | None      | None     | None      | PKT_RX_IPV4_HDR     | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4     | Tcp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4     | Sctp      | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv4     | Yes     | Yes      | None      | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv4     | Yes     | Yes      | Yes       | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+

Remove NVGRE filter which has been added. Then send one packet and check 
packet was received in queue 0.


Test Case: NVGRE IPv4 Filter invalid
========================
This test adds NVGRE IPv6 filters by invalid command, and then checks command 
result.

Start testpmd::

    testpmd -c 0xffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2
    
Set rxonly packet forwarding mode and enable verbose log::

    set fwd rxonly
    set verbose 1

Add NVGRE filter as table listed first::
    tunnel_filter add port_id outer_mac inner_mac ip_addr inner_vlan 
    tunnel_type(vxlan|nvgre) filter_type(imac-ivlan|imac-ivlan-tenid|imac-tenid|imac
    |omac-imac-tenid|iip) tenant_id queue_num

Validte the filter command with wrong parameter::

Add Cloud filter with invalid Mac address "00:00:00:00:01" will be failed.

Add Cloud filter with invalid ip address "192.168.1.256" will be failed.

Add Cloud filter with invalid vlan "4097" will be failed.

Add Cloud filter with invalid vni "16777216" will be failed.

Add Cloud filter with invalid queue id "64" will be failed.

Test Case: NVGRE IPv6 Filter
========================
This test adds NVGRE IPv6 filters to the hardware, and then checks whether 
sent packets match those filters. In order to this, the packet should first 
be sent from ``Scapy`` before the filter is created, to verify that it is not 
matched by a NVGRE IPv6 filter. The filter is then added from the ``testpmd`` 
command line and the packet is sent again.

Start testpmd::

    testpmd -c 0xffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2
    
Set rxonly packet forwarding mode and enable verbose log::

    set fwd rxonly
    set verbose 1

Add NVGRE filter as table listed first::
    tunnel_filter add port_id outer_mac inner_mac ip_addr inner_vlan 
    tunnel_type(vxlan|nvgre) filter_type(imac-ivlan|imac-ivlan-tenid|imac-tenid|imac
    |omac-imac-tenid|iip) tenant_id queue_num
    
For example:
    tunnel_filter add 0 11:22:33:44:55:66 00:00:20:00:00:01 192.168.2.2 1 
    NVGRE imac 1 1

Then send one packet and check packet was forwarded into right queue.

+-----------+-----------+----------+---------+----------|-----------+----------+-----------+---------------------+-----------+
| Outer L2  |Outer Vlan | Outer L3 | NVGRE   | Inner L2 |Inner Vlan | Inner L3 | Inner L4  | Rx packet type  | Pkt Error |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | None    | None     | None      | None     | None      | PKT_RX_IPV6_HDR     | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6     | Tcp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6     | Sctp      | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv6     | Yes     | Yes      | None      | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv6     | Yes     | Yes      | Yes       | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+

Remove NVGRE filter which has been added. Then send one packet and check 
packet was received in queue 0.

Test Case: NVGRE ipv4 checksum offload
======================================
This test validates NVGRE IPv4 checksum by the hardware. In order to this, the packet should first 
be sent from ``Scapy`` with wrong checksum(0x00) value. Then the pmd forward package while checksum 
is modified on DUT tx port by hardware. To verify it, tcpdump captures the 
forwarded packet and checks the forwarded packet checksum correct or not.

Start testpmd with tunneling packet type to NVGRE::

    testpmd -c 0xffff -n 4 -- -i --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2 --enable-rx-cksum
    
Set csum packet forwarding mode and enable verbose log::

    set fwd csum
    csum set ip hw <dut tx_port>
    csum set udp hw <dut tx_port>
    csum set tcp hw <dut tx_port>
    csum set sctp hw <dut tx_port>
    csum set nvgre hw <dut tx_port>
    csum parse_tunnel on <dut tx_port>
    set verbose 1

Send packet with invalid checksum first. Then check forwarded packet checksum 
correct or not.

+-----------+-----------+----------+---------+----------|-----------+----------+-----------+---------------------+-----------+
| Outer L2  |Outer Vlan | Outer L3 | NVGRE   | Inner L2 |Inner Vlan | Inner L3 | Inner L4  | Rx packet type  | Pkt Error |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | None    | None     | None      | None     | None      | PKT_RX_IPV4_HDR     | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4(Bad)| Yes     | Yes      | None      | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4     | Yes     | Yes      | None      | Ipv4(Bad)| Tcp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv4(Bad)| Yes     | Yes      | None      | Ipv4(Bad)| Sctp      | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv4(Bad)| Yes     | Yes      | None      | Ipv4     | Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv4     | Yes     | Yes      | Yes       | Ipv4(Bad)| Udp       | PKT_RX_IPV4_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+

Test Case: NVGRE ipv6 checksum offload
======================================
This test validates NVGRE IPv6 checksum by the hardware. In order to this, the packet should first 
be sent from ``Scapy`` with wrong checksum(0x00) value. Then the pmd forward package while checksum 
is modified on DUT tx port by hardware. To verify it, tcpdump captures the 
forwarded packet and checks the forwarded packet checksum correct or not.

Start testpmd with tunneling packet type::

    testpmd -c ffff -n 4 -- -i --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2  --enable-rx-cksum
    
Set csum packet forwarding mode and enable verbose log::

    set fwd csum
    csum set ip hw <dut tx_port>
    csum set udp hw <dut tx_port>
    csum set tcp hw <dut tx_port>
    csum set sctp hw <dut tx_port>
    csum set nvgre hw <dut tx_port>
    csum parse_tunnel on <dut tx_port>
    set verbose 1

Send packet with invalid checksum first. Then check forwarded packet checksum 
correct or not.

+-----------+-----------+----------+---------+----------|-----------+----------+-----------+---------------------+-----------+
| Outer L2  |Outer Vlan | Outer L3 | NVGRE   | Inner L2 |Inner Vlan | Inner L3 | Inner L4  | Rx packet type  | Pkt Error |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | None    | None     | None      | None     | None      | PKT_RX_IPV6_HDR     | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6(Bad)| Yes     | Yes      | None      | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6     | Yes     | Yes      | None      | Ipv6(Bad)| Tcp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | None      | Ipv6(Bad)| Yes     | Yes      | None      | Ipv6(Bad)| Sctp      | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv6(Bad)| Yes     | Yes      | None      | Ipv6     | Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+
| Yes       | Yes       | Ipv6     | Yes     | Yes      | Yes       | Ipv6(Bad)| Udp       | PKT_RX_IPV6_HDR_EXT | None      |
+-----------+-----------+----------+---------+----------+-----------+----------+-----------+---------------------+-----------+



Test Case: NVGRE Checksum Offload Performance Benchmarking
==========================================================

The throughput is measured for each of these cases for NVGRE tx checksum
offload of "all by software", "inner l3 offload by hardware", "inner l4
offload by hardware", "inner l3&l4 offload by hardware", "outer l3 offload 
by hardware", "outer l4 offload by hardware", "outer l3&l4 offload by 
hardware", "all by hardware".

The results are printed in the following table:

+----------------+---------------+------------+---------------+------------+---------------+------------+
| Calculate Type | 1S/1C/1T Mpps | % linerate | 1S/1C/2T Mpps | % linerate | 1S/2C/1T Mpps | % linerate |
+================+===============+============+===============+============+===============+============+
| SOFTWARE ALL   |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HW OUTER L3    |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HW OUTER L4    |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HW OUTER L3&L4 |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HW INNER L3    |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HW INNER L4    |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HW INNER L3&L4 |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+
| HARDWARE ALL   |               |            |               |            |               |            |
+----------------+---------------+------------+---------------+------------+---------------+------------+

Test Case: NVGRE Tunnel filter Performance Benchmarking
=======================================================
The throughput is measured for different NVGRE tunnel filter types.
Queue single mean there's only one flow and forwarded to the first queue.
Queue multi mean there're two flows and configure to different queues.

+--------+------------------+--------+--------+------------+
| Packet | Filter           | Queue  | Mpps   | % linerate |
+========+==================+========+========+============+
| Normal | None             | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | None             | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac-ivlan       | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac-ivlan-tenid | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac-tenid       | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac             | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | omac-imac-tenid  | Single |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac-ivlan       | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac-ivlan-tenid | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac-tenid       | Multi  |        |            |
+--------+------------------+--------+--------+------------+
| NVGRE  | imac             | Multi  |        |            |
+--------+------------------+--------+--------+------------+
