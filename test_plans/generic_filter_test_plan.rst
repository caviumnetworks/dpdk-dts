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


Description 
=====================================================
This document provides the plan for testing the generic filter feature of 10GbE and 1GbE Ethernet Controller.In `testpmd`, app provides Generic Filter API to manage filter rules for kinds of packets, and calls the API to manage HW filters in HW, or SW filters in SW table.

* A generic filter provides an ability to identify specific  flows or sets of  flows and routes them to dedicated queues.  
* Based on the Generic Filter mechanism, all the SYN packets are placed in an assigned queue.  
* Based on the Generic Filter mechanism, all packets belonging to L3/L4 flows to be placed in a specific HW queue.Each filter consists of a 5-tuple (protocol, source and destination IP addresses, source and destination TCP/UDP/SCTP port) and routes packets into one of the Rx queues
* L2 Ethertype Filters provides an ability to identify packets by their L2 Ethertype and assigns them to receive queues.
`Testpmd` app is used to test all types of HW filters. Case 1~9 are the function test for the above app while case 11，12 are the performance test for Niantic, I350, 82580 and 82576.


Prerequisites
===================================================
Assuming that ports ``0`` and ``1`` are connected to a traffic generator's port ``A`` and ``B``.

Setup for ``testpmd``
-----------------------------------------------------------------
Launch the app ``testpmd`` with the following arguments::
  
    ./testpmd -c fffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=16 --nb-ports=2 

The -n command is used to select the number of memory channels. It should be matched with the number of memory channels on that setup. The value of rxq and txq is 1 by default, it's necessary  to increase them, and make sure rxq and txq more than one. At the same time rss is enable by default, so disable it. Map port queues to statistic counter registers. forvtill not support this function::

    testpmd>set stat_qmap rx 0 0 0
    testpmd>set stat_qmap rx 0 1 1
    testpmd>set stat_qmap rx 0 2 2
    testpmd>set stat_qmap rx 0 3 3   
Setup for receive all packet and disable vlan strip function::
    
    testpmd>vlan set strip off 0
    testpmd>vlan set strip off 1
    testpmd>vlan set filter off 0
    testpmd>vlan set filter off 1
    testpmd>set flush_rx on

  
Test Case 1:     SYN filter
===================================================================
SYN filters might routes TCP packets with their SYN flag set into an assigned queue.  By filtering such packets to an assigned queue, security software can monitor and
act on SYN attacks. 

Enable SYN filters with queue 2 on port 0.::
  
     testpmd> syn_filter 0 add priority high queue 2

Then setup for receive:: 

    testpmd> start
Configure the traffic generator to send 5 SYN packets and 5 non-SYN packets .
Reading the stats for port 0 after sending packets.::

     testpmd> stop
Verify that the packets are received (RX-packets incremented)on the queue 2.
Set off SYN filter::

    testpmd>syn_filter 0 del priority high queue 2 
    testpmd>start
Send 5 SYN packets, then reading the stats for port 0 after sending packets.::

    testpmd> stop   
Verify that the packets are not received (RX-packets do not increased)on the queue 2 and syn filter is removed.


Test Case 2:      5-tuple Filter
===================================================================
This filter identifies specific L3/L4 flows or sets of L3/L4 flows and routes them to dedicated queues. Each filter consists of a 5-tuple (protocol, source and destination IP addresses, source and destination TCP/UDP/SCTP port) and routes packets into one of the Rx queues.
The 5-tuple filters are configured via `dst_ip`, `src_ip`, `dst_port`, `src_port`, `protocol` and Mask.This case supports two type NIC(niantic, 82576), and their command line are different. niantic and 82576 register are different, for niantic TCP flags not need config,so used 0, 82576 must config tcp flags, the tcp flags means the package is a SYN package. 
Enable the  5-tuple Filter with queue 3 on port 0 for niantic. ::

    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f tcp_flags 0x0 priority 3 queue 3

Enable the  5-tuple Filter with queue 3 on port 0 for 82576. ::

    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x02 priority 3 queue 3

Then setup for receive:: 

    testpmd> start   
If the NIC type is niantic, then send  different type packets such as (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp) and arp. ::

    testpmd> stop
Verify that the packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp)or (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp, `flags` = 0x2)  are received (RX-packets doesn't incremented)on the queue 3.Remove L3/L4 5-tuple  filter.   
Disable  5-tuple Filters::
                                     
    testpmd> 5tuple_filter 0 del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x02 priority 3 queue 3
    testpmd> start
Send  packets(`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp) or (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp `flags` = 0x2) .Then reading the stats for port 0 after sending packets.::
   
    testpmd> stop
Verify that the packets are not received (RX-packets do not increased)on the queue 3. A 5-bit field that masks each of the fields in the 5-tuple (L4 protocol, IP addresses, TCP/UDP ports).
If  5-tuple fields are masked with 0x0  (`mask` = 0x0), the filter will routes all the packets(ip)  on the assigned queue.For instance, enable the  5-tuple Filters with queue 3 on port 0 for niantic. however, the value of mask is set 0x0::

    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol tcp mask 0x0 flags 0x0 priority 3 queue 3 

Test Case 3:     ethertype filter
===================================================================
Enable the receipt of  ARP packets with queue 2 on port 0::

    testpmd> ethertype_filter 0 add ethertype 0x0806 priority disable 0 queue 2 
Then setup for receive:: 
   
    testpmd> start  
Configure the traffic generator to send 15 ARP packets and 15 non ARP packets::

    testpmd> stop
Verify that the arp packets are received (RX-packets incremented)on the queue 2 .
remove ethertype filter::

    testpmd> ethertype_filter 0 del ethertype 0x0806 priority disable 0 queue 2
    testpmd> start  
Configure the traffic generator to send  15 ARP packets.

    testpmd> stop
Also, you can change the value of  priority to set a new filter except the case the value of ethertype is 0x0800 with priority enable .The rest of steps are same.
For instance, enable  priority filter(just support niantic):: 
    
    testpmd> ethertype_filter 0 add ethertype 0x0806 priority enable 1 queue 2 

Test Case 4:     10GB Multiple filters 
===================================================================
Enable ethertype filter, SYN filter and  5-tuple Filter on the port 0 at same time. Assigning different filters to different queues on port 0::

    testpmd> syn_filter 0 add priority high queue 1
    testpmd> ethertype_filter  0 add ethertype 0x0806 priority disable 0 queue 3 
    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol tcp mask 0x1f priority 3 queue 3 
    testpmd> start
   
Configure the traffic generator to send  different packets. Such as,SYN packets, ARP packets, IP packets and packets with(`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp)::

    testpmd> stop
Verify that different packets are received (RX-packets incremented)on the assigned queue.
Remove ethertype filter::

    testpmd> ethertype_filter  0 del ethertype 0x0806 priority disable 0 queue 3
    testpmd>start
Send SYN packets, ARP packets and packets with (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp).::  

    testpmd> stop
Verify that all packets are received (RX-packets incremented)on the assigned queue except arp  packets, remove 5-tuple filter::

    testpmd>5tuple_filter 0 del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol tcp mask 0x1f priority 3 queue 3
    testpmd> start
Send  different packets such as,SYN packets, ARP packets,  packets with (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp)::  

    testpmd>stop
Verify that only SYN packets are received (RX-packets incremented)on the assigned queue       
set off SYN filter::

    testpmd>syn_filter 0 del priority high queue 1
    testpmd>start
Configure the traffic generator to send 5 SYN packets::

    testpmd>stop
Verify that the packets are not received (RX-packets do not increased)on the queue 1.


Test Case 5:     2-tuple filter 
===================================================================
This case is designed for NIC type:I350, 82580.
Enable the receipt of  udp packets with queue 1 on port 0::
  
    testpmd> 2tuple_filter 0 add protocol 0x11 1 dst_port 64 1 flags 0 priority 3 queue 1
Then setup for receive::

    testpmd> start
Send 15 udp packets(`dst_port` = 15, `protocol` = udp) and 15 non udp packets.Reading the stats for port 0 after sending packets::

    testpmd> stop

Verify that the udp packets are received (RX-packets incremented)on the queue 1.
Remove 2tuple filter::

    testpmd> 2tuple_filter 0 del protocol 0x11 1 dst_port 64 1 flags 0 priority 3 queue 1
    testpmd> start
Configure the traffic generator to send  udp packets(`dst_port` = 15, `protocol` = udp).
Reading the stats for port 0 after sending packets::

    testpmd> stop
Verify that the packets are not received (RX-packets do not increased)on the queue 1.
Also, you can change the value of protocol or dstport or flags to set a new filter.the rest of steps are same.For example::

Enable the receipt of  UDP packets with queue 1 on port 1::

    testpmd> 2tuple_filter 1 add protocol 0x011 1 dst_port 64 1 flags 0 priority 3 queue 2

Enable the receipt of  TCP packets with flags on queue 1 of port 1::
  
    testpmd> 2tuple_filter 1 add protocol 0x06 1 dst_port 64 1 flags 0x3F priority 3 queue 3 
  

Test Case 6: flex filter 
===================================================================
This case is designed for NIC type:I350, 82576,82580.
Enable the receipt of   packets(context) with queue 1 on port 0::
  
    testpmd> flex_filter 0 add len 16 bytes 0x0123456789abcdef0000000008060000 mask 000C priority 3 queue 1

If flex Filter is added successfully,  it displays::
    bytes[0]:01 bytes[1]:23 bytes[2]:45 bytes[3]:67 bytes[4]:89 bytes[5]:ab bytes[6]:cd bytes[7]:ef bytes[8]:00 bytes[9]:00 bytes[10]:00 bytes[11]:00 bytes[12]:08 bytes[13]:06 bytes[14]:00 bytes[15]:00
    mask[0]:00 mask[1]:0c
Then setup for receive::

    testpmd> start
Configure the traffic generator to send  packets(context) and arp packtes.
Reading the stats for port 0 after sending packets::

    testpmd> stop
Verify that the arp packets are received (RX-packets incremented)on the queue 1.
Remove flex filter::

    testpmd> flex_filter 0 add len 16 bytes 0x0123456789abcdef0000000008060000 mask 000C priority 3 queue 1
    testpmd> start
Configure the traffic generator to send packets(context).Reading the stats for port 0 after sending packets::

    testpmd> stop
Verify that the packets are not received (RX-packets do not increased)on the queue 1. Also, you can change the value of length or context or mask to set a new filter.the rest of steps are same.::

    testpmd> flex_filter 0 add len 32 bytes 0x0123456789abcdef00000000080600000123456789abcdef0000000008060000 mask 000C000C priority 1 queue 2

Test Case 7: priority filter
===================================================================
This case is designed for NIC (niantic,I350, 82576 and 82580). If packets are match on  different filters with same type, the filter with high priority will be receive packets. For example, packets are match on two five-tuple filters with different priority, the filter with high priority  will be receive packets. if packets are match on  different filters with different type, packets based on the above criteria and the following order.when syn set priority high, syn filter has highest priority than others filter. And flex filter has higher priority than 2-tuple filter.  
If the Nic is niantic, enable the 5-tuple filter::

    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x0 priority 2 queue 2
    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 2 src_port 2 protocol 0x06 mask 0x18 flags 0x0 priority 3 queue 3 
    testpmd> start
Configure the traffic generator to send  packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp).
  
    testpmd> stop
packets are received (RX-packets be increased)on the queue 2.
Remove the 5tuple filter with high priority::

    testpmd>5tuple_filter 0 del dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x0 priority 2 queue 2
    testpmd> start
Configure the traffic generator to send  packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp)

    testpmd> stop
packets are received (RX-packets be increased)on the queue 3.
If the Nic is I350 or 82580, enable the 2-tuple  and flex filters::

    testpmd> flex_filter 0 add len 16 bytes 0x0123456789abcdef0000000008000000 mask 000C priority 2 queue 1 
    testpmd> 2tuple_filter 0 add protocol 0x11 1 dst_port 64 1 flags 0 priority 3 queue 2 
    testpmd> start
Configure the traffic generator to send  packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 64 `src_port` = 1 `protocol` = udp).
  
    testpmd> stop
packets are received (RX-packets be increased)on the queue 2.
Remove the 2tuple filter with high priority::

    testpmd> 2tuple_filter 0 add protocol 0x11 1 dst_port 64 1 flags 0 priority 3 queue 2
    testpmd> start
Configure the traffic generator to send  packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 64 `src_port` = 1 `protocol` = udp),
 
    testpmd> stop
packets are received (RX-packets be increased)on the queue 1.
If the Nic is 82576, enable the syn and 2-tuple filter::

    testpmd>5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x02 priority 3 queue 3
    testpmd>syn_filter 0 add priority high queue 2
    testpmd> start
Configure the traffic generator to send  packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp `flags` = "S").
  
    testpmd>stop
packets are received (RX-packets be increased)on the queue 2.
Remove the syn filter with high priority::

    testpmd>syn_filter 0 del priority high queue 2
    testpmd>start
Configure the traffic generator to send  packets (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 64 `src_port` = 1 `protocol` = tcp `flags` = "S").

    testpmd> stop
packets are received (RX-packets be increased)on the queue 3.
    

   
Test Case 8: 1GB Multiple filters 
===================================================================
This case is designed for NIC(I350, 82576,82580). Enable syn filter and ethertype filter on the port 0 at the same time.  Assigning different filters to different queues on port 0.Enable the filters::

    testpmd> syn_filter 0 add priority high queue 1
    testpmd> ethertype_filter 0 add ethertype 0x0806 priority disable 0 queue 3 
    testpmd> start
    
Configure the traffic generator to send ethertype packets and arp packets . ::
    
    testpmd> stop
Then Verify that the packet are received on the queue 1,queue 3.
Remove all the filter::
    
    testpmd> syn_filter 0 add priority high queue 1
    testpmd> ethertype_filter 0 add ethertype 0x0806 priority disable 0 queue 3

Configure the traffic generator to send udp packets and arp packets. Then Verify that the packet are not received on the queue 1 and queue 3 ::
        
    testpmd> quit  

Test Case 9: jumbo framesize filter 
===================================================================
 This case is designed for NIC (niantic,I350, 82576 and 82580). Since ``Testpmd`` could transmits packets with jumbo frame size , it also could transmit above packets on assigned queue. 
Launch the app ``testpmd`` with the following arguments::
    
    testpmd -c ffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=8 --nb-ports=2 --rxd=1024 --txd=1024 --burst=144 --txpt=32 --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 --mbcache=200 --mbuf-size=2048 --max-pkt-len=9600 

    testpmd>set stat_qmap rx 0 0 0
    testpmd>set stat_qmap rx 0 1 1
    testpmd>set stat_qmap rx 0 2 2 
    testpmd>vlan set strip off 0
    testpmd>vlan set strip off 1
    testpmd>vlan set filter off 0
    testpmd>vlan set filter off 1 
Enable the syn filters with large size::

    testpmd> syn_filter 0 add priority high queue 1
    testpmd> start
    
Configure the traffic generator to send syn packets(framesize=2000) . ::
    
    testpmd> stop
Then Verify that the packet are received on the queue 1.
Remove  the filter::
    
    testpmd> syn_filter 0 del priority high queue 1 

Configure the traffic generator to send syn packets and s. Then Verify that the packet are not received on the queue 1   ::
        
    testpmd> quit  

Test Case 10: 128 queues  
===================================================================
This case is designed for NIC(niantic). Since NIC(niantic) has 128 transmit queues, it should be supports  128 kinds of filter if Hardware have enough cores. 
Launch the app ``testpmd`` with the following arguments::

    ./testpmd -c fffff -n 4 -- -i --disable-rss --rxq=128 --txq=128 --nb-cores=16 --nb-ports=2 --total-num-mbufs=60000
    
    testpmd>set stat_qmap rx 0 0 0
    testpmd>set stat_qmap rx 0 64 1
    testpmd>set stat_qmap rx 0 64 2 
    testpmd>vlan set strip off 0
    testpmd>vlan set strip off 1
    testpmd>vlan set filter off 0
    testpmd>vlan set filter off 1 
Enable the  5-tuple Filters with different queues (64,127) on port 0 for niantic. ::

    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x0 priority 3 queue 64 index 1
    testpmd> 5tuple_filter 0 add dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 2 src_port 1 protocol 0x06 mask 0x1f flags 0x0 priority 3 queue 127 index 1
Send  packets(`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 1 `src_port` = 1 `protocol` = tcp) and (`dst_ip` = 2.2.2.5 `src_ip` = 2.2.2.4 `dst_port` = 2 `src_port` = 1 `protocol` = tcp ) . Then reading the stats for port 0 after sending packets. packets are received on the queue 64 and queue 127
 When setting 5-tuple Filter with queue(128), it will display failure because the number of queues no more than 128.


    
Test Case 11: 10G NIC Performance 
===================================================================
This case is designed for Niantic. It provides the performance data with and without  generic filter. ::
    Launch app without filter
    ./testpmd -c fffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=16 --nb-ports=2
    testpmd> start
    
Send the packets stream from packet generator::  
     
    testpmd> quit
Enable the filters on app::

    ./testpmd -c fffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=16 --nb-ports=2

    testpmd>set stat_qmap rx 0 0 0
    testpmd>set stat_qmap rx 0 1 1
    testpmd>set stat_qmap rx 0 2 2
    testpmd>set stat_qmap rx 0 3 3
    testpmd>set flush_rx on
    testpmd> add_syn_filter 0 priority high queue 1
    testpmd> add_ethertype_filter 0 ethertype 0x0806 priority disable 0 queue 2 index 1
    testpmd> add_5tuple_filter 0 dst_ip 2.2.2.5 src_ip 2.2.2.4 dst_port 1 src_port 1 protocol 0x06 mask 0x1f flags 0x02 priority 3 queue 3 index 1
    testpmd> start
     
Send the packets stream from packet generator:: 
     
    testpmd> quit



+-------+---------+---------+
| Frame | disable | enable  |   
| Size  | filter  | filter  |      
+-------+---------+---------+
|  64   |         |         |       
+-------+---------+---------+
|  128  |         |         |      
+-------+---------+---------+
|  256  |         |         |
+-------+---------+---------+
|  512  |         |         |         
+-------+---------+---------+
|  1024 |         |         |
+-------+---------+---------+
|  1280 |         |         |     
+-------+---------+---------+
|  1518 |         |         |
+-------+---------+---------+    

  
Test Case 12: 1G NIC Performance  
===================================================================
This case is designed for NIC (I350, 82580, and 82576). It provides the performance data with and without  generic filter.::

    ./testpmd -c fffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=16 --nb-ports=2
    testpmd> start
    
Send the packets stream from packet generator::
           
    testpmd> quit
  
Enable the filter ::

    ./testpmd -c fffff -n 4 -- -i --disable-rss --rxq=4 --txq=4 --nb-cores=16 --nb-ports=2

    testpmd>set stat_qmap rx 0 0 0
    testpmd>set stat_qmap rx 0 1 1
    testpmd>set stat_qmap rx 0 2 2
    testpmd>set stat_qmap rx 0 3 3
    testpmd>set flush_rx on
    testpmd> add_syn_filter 0 priority high queue 1
    testpmd> add_ethertype_filter 0 ethertype 0x0806 priority disable 0 queue 2 index 1   
    testpmd> start
     
    
Send the packets stream from packet generator::
          
    testpmd> quit



+-------+---------+---------+
| Frame | disable | enable  |   
| Size  | filter  | filter  |      
+-------+---------+---------+
|  64   |         |         |       
+-------+---------+---------+
|  128  |         |         |      
+-------+---------+---------+
|  256  |         |         |
+-------+---------+---------+
|  512  |         |         |         
+-------+---------+---------+
|  1024 |         |         |
+-------+---------+---------+
|  1280 |         |         |     
+-------+---------+---------+
|  1518 |         |         |
+-------+---------+---------+    
