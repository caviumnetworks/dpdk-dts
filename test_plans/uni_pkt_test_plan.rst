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

===================
Unified Packet Type
===================
Unified packet type flag is supposed to recognize packet types and support all
possible PMDs.

This 32 bits of packet_type can be divided into several sub fields to
indicate different packet type information of a packet. The initial design
is to divide those bits into fields for L2 types, L3 types, L4 types, tunnel
types, inner L2 types, inner L3 types and inner L4 types. All PMDs should
translate the offloaded packet types into these 7 fields of information, for
user applications.

Prerequisites
=============
Enable ABI and disable vector ixgbe driver in dpdk configuration file.
Plug in three different types of nic on the board.
1x Intel® XL710-DA2 (Eagle Fountain)
1x Intel® 82599 Gigabit Ethernet Controller
1x Intel® I350 Gigabit Network Connection

Start testpmd and then enable rxonly and verbose mode::
    ./x86_64-native-linuxapp-gcc/app/testpmd -c f -n 4 -- -i --txqflags=0x0
    set fwd rxonly
    set verbose 1
    start

Test Case: L2 Packet detect
===========================
This case checked that whether Timesync, ARP, LLDP detection supported by
Fortville.

Send time sync packet from tester::
    sendp([Ether(dst='FF:FF:FF:FF:FF:FF',type=0x88f7)/"\\x00\\x02"],
        iface=txItf)

Check below message dumped by testpmd::
    (outer) L2 type: ETHER_Timesync
    
Send ARP packet from tester::
    sendp([Ether(dst='FF:FF:FF:FF:FF:FF')/ARP()],
        iface=txItf)

Check below message dumped by testpmd::
    (outer) L2 type: ETHER_ARP
        
Send LLDP packet from tester::
    sendp([Ether()/LLDP()/LLDPManagementAddress()], iface=txItf)

Check below message dumped by testpmd::
    (outer) L2 type: ETHER_LLDP

Test Case: IPv4&L4 packet type detect
=====================================
This case checked that whether L3 and L4 packet can be normally detected.
Niantic and i350 will shown that L2 type is MAC.
Only Fortville can detect icmp packet.
Only niantic and i350 can detect ipv4 extension packet.
Fortville did not detect whether packet contian ipv4 header options, so L3
type will be shown as IPV4_EXT_UNKNOWN.
Fortville will identify all unrecognized L4 packet as L4_NONFRAG.
Only Fortville can inentify L4 fragement packet.

Send IP only packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IP()/Raw('\0'*60)], iface=txItf)
    
    (outer) L2 type: ETHER
    (outer) L3 type: IPV4
    (outer) L4 type: Unknown

Send IP+UDP packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IP()/UDP()/Raw('\0'*60)], iface=txItf)

    (outer) L4 type: UDP

Send IP+TCP packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IP()/TCP()/Raw('\0'*60)], iface=txItf)

    (outer) L4 type: TCP

Send IP+SCTP packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IP()/SCTP()/Raw('\0'*60)], iface=txItf)

    (outer) L4 type: SCTP

Send IP+ICMP packet and verify L2/L3/L4 corrected(Fortville)::
    sendp([Ether()/IP()/ICMP()/Raw('\0'*60)], iface=txItf)

    (outer) L4 type: ICMP

Send IP fragment+TCP packet and verify L2/L3/L4 corrected(Fortville)::
    sendp([Ether()/IP(frag=5)/TCP()/Raw('\0'*60)], iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV4_EXT_UNKNOWN
    (outer) L4 type: L4_FRAG

Send IP extension packet and verify L2/L3 corrected(Niantic,i350)::
    sendp([Ether()/IP(ihl=10)/Raw('\0'*40)],iface=txItf)

    (outer) L3 type: IPV4_EXT
    (outer) L4 type: Unknown

Send IP extension+SCTP packet and verify L2/L3/L4 corrected(Niantic,i350)::
    sendp([Ether()/IP(ihl=10)/SCTP()/Raw('\0'*40)],iface=txItf)

    (outer) L3 type: IPV4_EXT
    (outer) L4 type: SCTP

Test Case: IPv6&L4 packet type detect
=====================================
This case checked that whether IPv6 and L4 packet can be normally detected.
Niantic and i350 will shown that L2 type is MAC.
Fortville did not detect whether packet contian ipv6 extension options, so L3
type will be shown as IPV6_EXT_UNKNOWN.
Fortville will identify all unrecognized L4 packet as L4_NONFRAG.
Only Fortville can inentify L4 fragement packet.

Send IPv6 only packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IPv6()/Raw('\0'*60)], iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV6
    (outer) L4 type: Unknown 

Send IPv6+UDP packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IPv6()/UDP()/Raw('\0'*60)], iface=txItf)

    (outer) L4 type: UDP 

Send IPv6+TCP packet and verify L2/L3/L4 corrected::
    sendp([Ether()/IPv6()/TCP()/Raw('\0'*60)], iface=txItf)

    (outer) L4 type: TCP

Send IPv6 fragment packet and verify L2/L3/L4 corrected(Fortville)::
    sendp([Ether()/IPv6()/IPv6ExtHdrFragment()/Raw('\0'*60)],iface=txItf)

    (outer) L3 type: IPV6_EXT_UNKNOWN
    (outer) L4 type: L4_FRAG

Send IPv6 fragment packet and verify L2/L3/L4 corrected(Niantic,i350)::
    sendp([Ether()/IPv6()/IPv6ExtHdrFragment()/Raw('\0'*60)],iface=txItf)

    (outer) L3 type: IPV6_EXT
    (outer) L4 type: Unknown
    
Test Case: IP in IPv4 tunnel packet type detect
===============================================
This case checked that whether IP in IPv4 tunnel packet can be normally
detected by Fortville.

Send IPv4+IPv4 fragment packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP(frag=5)/UDP()/Raw('\0'*40)], iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV4_EXT_UNKNOWN
    (outer) L4 type: Unknown
    Tunnel type: IP
    Inner L2 type: Unknown
    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG

Send IPv4+IPv4 packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPv4+IPv4+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/UDP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: UDP
    
Send IPv4+IPv4+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/TCP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: TCP

Send IPv4+IPv4+SCTP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/SCTP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: SCTP

Send IPv4+IPv4+ICMP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/SCTP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: ICMP
    
Send IPv4+IPv6 fragment packet and inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/IPv6ExtHdrFragment()/Raw('\0'*40)],iface=txItf)

    Inner L3 type: IPV6_EXT_UNKNOWN
    Inner L4 type: L4_FRAG  
    
Send IPv4+IPv6 packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: L4_NONFRAG   

Send IPv4+IPv6+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/UDP()/Raw('\0'*40)],iface=txItf)
    
    Inner L4 type: UDP

Send IPv4+IPv6+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/TCP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: TCP

Send IPv4+IPv6+SCTP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6(nh=132)/SCTP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: SCTP
    
Send IPv4+IPv6+ICMP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6(nh=58)/ICMP()/Raw('\0'*40)],iface=txItf)
    
    Inner L4 type: ICMP

Test Case: IPv6 in IPv4 tunnel packet type detect by niantic and i350
=====================================================================
This case checked that whether IPv4 in IPv6 tunnel packet can be normally
detected by Niantic and i350.

Send IPv4+IPv6 packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/Raw('\0'*40)], iface=txItf)

    (outer) L2 type: MAC
    (outer) L3 type: IPV4
    (outer) L4 type: Unknown
    Tunnel type: IP
    Inner L2 type: Unknown
    Inner L3 type: IPV6
    Inner L4 type: Unknown
    
Send IPv4+IPv6_EXT packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/IPv6ExtHdrRouting()/Raw('\0'*40)], iface=txItf)
    
    Inner L3 type: IPV6_EXT
    
Send IPv4+IPv6+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/UDP()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: UDP

Send IPv4+IPv6+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/TCP()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: TCP
    
Send IPv4+IPv6_EXT+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/IPv6ExtHdrRouting()/UDP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L3 type: IPV6_EXT
    Inner L4 type: UDP

Send IPv4+IPv6_EXT+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/IPv6ExtHdrRouting()/TCP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L3 type: IPV6_EXT
    Inner L4 type: TCP

    
Test Case: IP in IPv6 tunnel packet type detect
===============================================
This case checked that whether IP in IPv6 tunnel packet can be normally
detected by Fortville.

Send IPv4+IPv4 fragment packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP(frag=5)/UDP()/Raw('\0'*40)],iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV4_EXT_UNKNOWN
    (outer) L4 type: Unknown
    Tunnel type: IP
    Inner L2 type: Unknown
    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG

Send IPv4+IPv4 packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/Raw('\0'*40)],iface=txItf)
    
    Inner L4 type: L4_NONFRAG

Send IPv4+IPv4+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/UDP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: UDP
    
Send IPv4+IPv4+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/TCP()/Raw('\0'*40)],iface=txItf)

    Inner L4 type: TCP
    
Send IPv4+IPv4+SCTP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/SCTP()/Raw('\0'*40)],iface=txItf)
    
    Inner L4 type: SCTP

Send IPv4+IPv4+ICMP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IP()/SCTP()/Raw('\0'*40)],iface=txItf)
    
    Inner L4 type: ICMP
    
Send IPv4+IPv6 fragment packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/IPv6ExtHdrFragment()/Raw('\0'*40)],
    iface=txItf)

    Inner L3 type: IPV6_EXT_UNKNOWN
    Inner L4 type: L4_FRAG
    
Send IPv4+IPv6 packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: L4_NONFRAG

Send IPv4+IPv6+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/UDP()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: UDP

Send IPv4+IPv6+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6()/TCP()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: TCP

Send IPv4+IPv6+SCTP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6(nh=132)/SCTP()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: SCTP
    
Send IPv4+IPv6+ICMP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/IPv6(nh=58)/ICMP()/Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: ICMP
    

Test Case: NVGRE tunnel packet type detect
==========================================
This case checked that whether NVGRE tunnel packet can be normally detected
by Fortville.
Fortville did not distinguish GRE/Teredo/Vxlan packets, all those types will
be displayed as GRENAT.
    
Send IPv4+NVGRE fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/IP(frag=5)/Raw('\0'*40)],
    iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV4_EXT_UNKNOWN
    (outer) L4 type: Unknown
    Tunnel type: GRENAT
    Inner L2 type: ETHER
    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG

    
Send IPV4+NVGRE+MAC packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/IP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPv4+NVGRE+MAC_VLAN packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/Raw('\0'*40)], iface=txItf)

    Inner L2 type: ETHER_VLAN
    Inner L4 type: Unknown
    
Send IPv4+NVGRE+MAC_VLAN+IPv4 fragment packet and verify inner and outer
L2/L3/L4 corrected::

    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IP(frag=5)/Raw('\0'*40)],
    iface=txItf)

    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG
    
Send IPv4+NVGRE+MAC_VLAN+IPv4 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPv4+NVGRE+MAC_VLAN+IPv4+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IP()/UDP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: UDP
        
Send IPv4+NVGRE+MAC_VLAN+IPv4+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IP()/TCP()/Raw('\0'*40)],
    iface=txItf)
    Inner L4 type: TCP  

Send IPv4+NVGRE+MAC_VLAN+IPv4+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IP()/SCTP()/Raw('\0'*40)],
    iface=txItf)
    Inner L4 type: SCTP
    
Send IPv4+NVGRE+MAC_VLAN+IPv4+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IP()/ICMP()/Raw('\0'*40)],
    iface=txItf)
    Inner L4 type: ICMP
    
Send IPv4+NVGRE+MAC_VLAN+IPv6+IPv6 fragment acket and verify inner and outer
L2/L3/L4 corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IPv6()/IPv6ExtHdrFragment()/
    Raw('\0'*40)], iface=txItf)

    Inner L3 type: IPV6_EXT_UNKOWN
    Inner L4 type: L4_FRAG
    
Send IPv4+NVGRE+MAC_VLAN+IPv6 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IPv6()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPv4+NVGRE+MAC_VLAN+IPv6+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IPv6()/UDP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: UDP
Send IPv4+NVGRE+MAC_VLAN+IPv6+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IPv6()/TCP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: TCP
    
Send IPv4+NVGRE+MAC_VLAN+IPv6+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IPv6(nh=132)/SCTP()/
    Raw('\0'*40)],iface=txItf)

    Inner L4 type: SCTP
    
Send IPv4+NVGRE+MAC_VLAN+IPv6+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/NVGRE()/Ether()/Dot1Q()/IPv6(nh=58)/ICMP()/
    Raw('\0'*40)],iface=txItf)

    Inner L4 type: ICMP
    
Test Case: NVGRE in IPv6 tunnel packet type detect
==================================================
This case checked that whether NVGRE in IPv6 tunnel packet can be normally
detected by Fortville.
Fortville did not distinguish GRE/Teredo/Vxlan packets, all those types will
be displayed as GRENAT.

Send IPV6+NVGRE+MAC packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Raw('\0'*18)], iface=txItf)
    
    (outer) L2 type: ETHER
    (outer) L3 type: IPV6_EXT_UNKNOWN
    (outer) L4 type: Unknown
    Tunnel type: GRENAT
    Inner L2 type: ETHER
    Inner L3 type: Unkown
    Inner L4 type: Unknown
    
Send IPV6+NVGRE+MAC+IPv4 fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IP(frag=5)/Raw('\0'*40)],
    iface=txItf)
    
    Inner L3 type: IPV4_EXT_UNKNOWN 
    Inner L4 type: L4_FRAG
    
Send IPV6+NVGRE+MAC+IPv4 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: L4_NONFRAG

Send IPV6+NVGRE+MAC+IPv4+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IP()/UDP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: UDP

Send IPV6+NVGRE+MAC+IPv4+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IP()/TCP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: TCP

Send IPV6+NVGRE+MAC+IPv4+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IP()/SCTP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: SCTP

Send IPV6+NVGRE+MAC+IPv4+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IP()/ICMP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: ICMP
    
Send IPV6+NVGRE+MAC+IPv6 fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IPv6()/IPv6ExtHdrFragment()
    /Raw('\0'*40)],iface=txItf)
    
    Inner L3 type: IPV6_EXT_UNKOWN
    Inner L4 type: L4_FRAG

Send IPV6+NVGRE+MAC+IPv6 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IPv6()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPV6+NVGRE+MAC+IPv6+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IPv6()/UDP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: UDP
    
Send IPV6+NVGRE+MAC+IPv6+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IPv6()/TCP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: TCP
    
Send IPV6+NVGRE+MAC+IPv6+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IPv6(nh=132)/SCTP()/
    Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: SCTP

Send IPV6+NVGRE+MAC+IPv6+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/IPv6(nh=58)/ICMP()/
    Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: ICMP

Send IPV6+NVGRE+MAC_VLAN+IPv4 fragment packet and inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IP(frag=5)/
    Raw('\0'*40)], iface=txItf)

    Inner L2 type: ETHER_VLAN
    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG
    
Send IPV6+NVGRE+MAC_VLAN+IPv4 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IP()/
    Raw('\0'*40)], iface=txItf)
    
    Inner L4 type: L4_NONFRAG

Send IPV6+NVGRE+MAC_VLAN+IPv4+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IP()/UDP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: UDP
    
Send IPV6+NVGRE+MAC_VLAN+IPv4+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IP()/TCP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: TCP

Send IPV6+NVGRE+MAC_VLAN+IPv4+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IP()/SCTP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: SCTP

Send IPV6+NVGRE+MAC_VLAN+IPv4+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IP()/ICMP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: ICMP
    
Send IPV6+NVGRE+MAC_VLAN+IPv6 fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IPv6()/
    IPv6ExtHdrFragment()/Raw('\0'*40)], iface=txItf)

    Inner L3 type: IPV6_EXT_UNKOWN
    Inner L4 type: L4_FRAG

Send IPV6+NVGRE+MAC_VLAN+IPv6 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IPv6()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPV6+NVGRE+MAC_VLAN+IPv6+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IPv6()/UDP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: UDP
    
Send IPV6+NVGRE+MAC_VLAN+IPv6+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IPv6()/TCP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: TCP

Send IPV6+NVGRE+MAC_VLAN+IPv6+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IPv6(nh=132)/SCTP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: SCTP

Send IPV6+NVGRE+MAC_VLAN+IPv6+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IPv6(nh=47)/NVGRE()/Ether()/Dot1Q()/IPv6(nh=58)/ICMP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: ICMP

Test Case: GRE tunnel packet type detect
========================================
This case checked that whether GRE tunnel packet can be normally detected by
Fortville.
Fortville did not distinguish GRE/Teredo/Vxlan packets, all those types will
be displayed as GRENAT.

Send IPv4+GRE+IPv4 fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/GRE()/IP(frag=5)/Raw('x'*40)], iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV4_EXT_UNKNOWN
    (outer) L4 type: Unknown
    Tunnel type: GRENAT
    Inner L2 type: Unknown
    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG

Send IPv4+GRE+IPv4 packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/GRE()/IP()/Raw('x'*40)], iface=txItf)

    Inner L4 type: L4_NONFRAG

Send IPv4+GRE+IPv4+UDP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/GRE()/IP()/UDP()/Raw('x'*40)], iface=txItf)

    Inner L4 type: UDP
    
Send IPv4+GRE+IPv4+TCP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/GRE()/IP()/TCP()/Raw('x'*40)], iface=txItf)

    Inner L4 type: TCP
    
Send IPv4+GRE+IPv4+SCTP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/GRE()/IP()/SCTP()/Raw('x'*40)], iface=txItf)

    Inner L4 type: SCTP
Send IPv4+GRE+IPv4+ICMP packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/GRE()/IP()/ICMP()/Raw('x'*40)], iface=txItf)

    Inner L4 type: ICMP
Send IPv4+GRE packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/GRE()/Raw('x'*40)], iface=txItf)

    Inner L3 type: Unkown
    Inner L4 type: Unknown

Test Case: Vxlan tunnel packet type detect
==========================================
This case checked that whether Vxlan tunnel packet can be normally detected by
Fortville.
Fortville did not distinguish GRE/Teredo/Vxlan packets, all those types
will be displayed as GRENAT.

Add vxlan tunnle port filter on receive port::
    rx_vxlan_port add 4789 0
Send IPv4+Vxlan+MAC+IPv4 fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IP(frag=5)/Raw('\0'*40)],
    iface=txItf)

    (outer) L2 type: ETHER
    (outer) L3 type: IPV4_EXT_UNKNOWN
    (outer) L4 type: Unknown
    Tunnel type: GRENAT
    Inner L2 type: ETHER
    Inner L3 type: IPV4_EXT_UNKNOWN
    Inner L4 type: L4_FRAG
    
Send IPv4+Vxlan+MAC+IPv4 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: L4_NONFRAG
    
Send IPv4+Vxlan+MAC+IPv4+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IP()/UDP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: UDP
    
Send IPv4+Vxlan+MAC+IPv4+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IP()/TCP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: TCP
    
Send IPv4+Vxlan+MAC+IPv4+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IP()/SCTP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: SCTP
    
Send IPv4+Vxlan+MAC+IPv4+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IP()/ICMP()/Raw('\0'*40)],
    iface=txItf)
    
    Inner L4 type: ICMP
    
Send IPv4+Vxlan+MAC+IPv6 fragment packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IPv6()/IPv6ExtHdrFragment()/
    Raw('\0'*40)], iface=txItf)

    Inner L3 type: IPV6_EXT_UNKOWN
    Inner L4 type: L4_FRAG
    
Send IPv4+Vxlan+MAC+IPv6 packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IPv6()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: L4_NONFRAG
    
Send IPv4+Vxlan+MAC+IPv6+UDP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IPv6()/UDP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: UDP
    
Send IPv4+Vxlan+MAC+IPv6+TCP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IPv6()/TCP()/Raw('\0'*40)],
    iface=txItf)

    Inner L4 type: TCP
    
Send IPv4+Vxlan+MAC+IPv6+SCTP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IPv6(nh=132)/SCTP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: SCTP
    
Send IPv4+Vxlan+MAC+IPv6+ICMP packet and verify inner and outer L2/L3/L4
corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/IPv6(nh=28)/ICMP()/
    Raw('\0'*40)], iface=txItf)

    Inner L4 type: ICMP
    
Send IPv4+Vxlan+MAC packet and verify inner and outer L2/L3/L4 corrected::
    sendp([Ether()/IP()/UDP()/Vxlan()/Ether()/Raw('\0'*40)], iface=txItf)
    
    Inner L3 type: Unkown
    Inner L4 type: Unknown
