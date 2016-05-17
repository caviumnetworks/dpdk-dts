.. Copyright (c) <2016>, Intel Corporation
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
Fortville, Support for VLAN ethertype config
============================================

Description
===========
for single vlan defaut TPID is 0x8100.
for QinQ, default S-Tag+C-Tag VLAN TPIDs 0x88A8 + 0x8100. 
This feature implemented configuration of VLAN ethertype TPID,
such as changing single vlan TPID 0x8100 to 0xA100, or changing QinQ "0x88A8 + 0x8100" \
to "0x9100+0xA100" or "0x8100+0x8100"

Prerequisites
=============

1. Hardware:
   one Fortville NIC (4x 10G or 2x10G or 2x40G or 1x10G) 
  
2. software: 
  dpdk: http://dpdk.org/git/dpdk
  scapy: http://www.secdev.org/projects/scapy/

3. Assuming that DUT ports ``0`` and ``1`` are connected to the tester's port ``A`` and ``B``.

Test Case 1: change VLAN TPID
=================================
1) start testpmd, start in rxonly mode,

./testpmd -c 0xff -n 4 -- -i --portmask=0x3 --txqflags=0
testpmd> set fwd rxonly
testpmd> set verbose 1
testpmd> start

2) change VLAN TPIDs to 0xA100,

testpmd> vlan set inner tpid 0xA100 0

3) send a packet with VLAN TPIDs = 0xA100, verify it can be recognized as vlan packet.

Test Case 2: test VLAN filtering on/off
=======================================
1) start testpmd, setup vlan filter on, start in mac forwarding mode

./testpmd -c 0xff -n 4 -- -i --portmask=0x3 --txqflags=0
testpmd> set fwd mac
testpmd> vlan set filter on 0
testpmd> start

2) send 1 packet with the VLAN Tag 16 on port ``A``,
Verify that the VLAN packet cannot be received in port ``B``.

3) disable vlan filtering on port ``0``::

testpmd> vlan set filter off 0

4) send 1 packet with the VLAN Tag 16 on port ``A``,
Verify that the VLAN packet can be received in port ``B``.

Test Case 3: test adding VLAN Tag Identifier with changing VLAN TPID
====================================================================

1) start testpmd, setup vlan filter on, start in mac forwarding mode,

./testpmd -c 0xff -n 4 -- -i --portmask=0x3 --txqflags=0
testpmd> set fwd mac
testpmd> vlan set filter on 0
testpmd> vlan set strip off 0
testpmd> start

2) Add a VLAN Tag Identifier ``16`` on port ``0``::

testpmd> rx_vlan add 16 0

3) send 1 packet with the VLAN Tag 16 on port ``A``, 
Verify that the VLAN packet can be received in port ``B`` and TPID is 0x8100

4) Change VLAN TPID to 0xA100 on port ``0``

testpmd> vlan set inner tpid 0xA100 0

5) send 1 packet with VLAN TPID 0xA100 and VLAN Tag 16 on port ``A``, 
Verify that the VLAN packet can be received in port ``B`` and TPID is 0xA100

4) Remove the VLAN Tag Identifier ``16`` on port ``0``::

testpmd> rx_vlan rm 16 0

5) send 1 packet with VLAN TPID 0xA100 and VLAN Tag 16 on port ``A``, 
Verify that the VLAN packet cannot be received in port ``B``.

Test Case 4: test VLAN header striping with changing VLAN TPID
==============================================================

1) start testpmd, setup vlan filter off, vlan strip on, start in mac forwarding mode,

./testpmd -c 0xff -n 4 -- -i --portmask=0x3 --txqflags=0
testpmd> set fwd mac
testpmd> vlan set filter off 0
testpmd> vlan set strip on 0
testpmd> start

2) send 1 packet with the VLAN Tag 16 on port ``A``, 
Verify that packet received in port ``B`` without VLAN Tag Identifier

3) Change VLAN TPID to 0xA100 on port ``0``

testpmd> vlan set inner tpid 0xA100 0

4) send 1 packet with VLAN TPID 0xA100 and VLAN Tag 16 on port ``A``, 
Verify that packet received in port ``B`` without VLAN Tag Identifier

5) Disable vlan header striping on port ``0``::

testpmd> vlan set strip off 0

6) send 1 packet with VLAN TPID 0xA100 and VLAN Tag 16 on port ``A``, 
Verify that packet received in port ``B`` with VLAN Tag Identifier.


Test Case 5: test VLAN header inserting with changing VLAN TPID
===============================================================

1) start testpmd, enable vlan packet forwarding, start in mac forwarding mode,

./testpmd -c 0xff -n 4 -- -i --portmask=0x3 --txqflags=0
testpmd> set fwd mac
testpmd> vlan set filter off 0
testpmd> vlan set strip off 0
testpmd> start

2) Insert VLAN Tag Identifier ``16`` on port ``1``::

testpmd> tx_vlan set 1 16

3) send 1 packet without VLAN Tag Identifier on port ``A``,
Verify that packet received in port ``B`` with VLAN Tag Identifier 16 and TPID is 0x8100

4) Change VLAN TPID to 0xA100 on port ``1``

testpmd> vlan set inner tpid 0xA100 1

5)send 1 packet without VLAN Tag Identifier on port ``A``,
Verify that packet received in port ``B`` with VLAN Tag Identifier 16 and TPID is 0xA100.

6) Delete the VLAN Tag Identifier ``16`` on port ``1``::

testpmd> tx_vlan reset 1

7) send 1 packet without VLAN Tag Identifieron port ``A``,
Verify that packet received in port ``B`` without VLAN Tag Identifier 16.


Test Case 6: Change S-Tag and C-Tag within QinQ
=================================================

1) start testpmd, enable QinQ, start in rxonly mode,

./testpmd -c 0xff -n 4 -- -i --portmask=0x3 --txqflags=0
testpmd> vlan set qinq on 0
testpmd> set fwd rxonly
testpmd> set verbose 1
testpmd> start

2) change S-Tag+C-Tag VLAN TPIDs to 0x88A8 + 0x8100,

testpmd> vlan set outer tpid 0x88A8 0
testpmd> vlan set inner tpid 0x8100 0

3) send a packet with set S-Tag+C-Tag VLAN TPIDs to 0x88A8 + 0x8100, 
verify it can be recognized as qinq packet.

4) change S-Tag+C-Tag VLAN TPIDs to 0x9100+0xA100,

testpmd> vlan set outer tpid 0x9100 0
testpmd> vlan set inner tpid 0xA100 0

5) send a packet with set S-Tag+C-Tag VLAN TPIDs to 0x9100+0xA100, 
verify it can be recognized as qinq packet.

4) change S-Tag+C-Tag VLAN TPIDs to 0x8100+0x8100,

testpmd> vlan set outer tpid 0x8100 0
testpmd> vlan set inner tpid 0x8100 0

5) send a packet with set S-Tag+C-Tag VLAN TPIDs to 0x8100+0x8100, 
verify it can be recognized as qinq packet.


Note:

send packet with specific S-Tag+C-Tag VLAN TPID,
1. wrpcap("qinq.pcap",[Ether(dst="68:05:CA:3A:2E:58")/Dot1Q(type=0x8100,vlan=16)/Dot1Q(type=0x8100,vlan=1006)/ IP(src="192.168.0.1", dst="192.168.0.2")]).
2. hexedit qinq.pcap; change tpid field, "ctrl+w" to save, "ctrl+x" to exit.
3. sendp(rdpcap("qinq.pcap"), iface="ens260f0").

send packet with specific VLAN TPID,
1. wrpcap("vlan.pcap",[Ether(dst="68:05:CA:3A:2E:58")/Dot1Q(type=0x8100,vlan=16)/IP(src="192.168.0.1", dst="192.168.0.2")]).
2. hexedit vlan.pcap; change tpid field, "ctrl+w" to save, "ctrl+x" to exit.
3. sendp(rdpcap("vlan.pcap"), iface="ens260f0").
