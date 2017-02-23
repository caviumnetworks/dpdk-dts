.. Copyright (c) <2017>, Intel Corporation
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

============================
VFD as SRIOV Policy Manager
============================

VFD is SRIOV Policy Manager (daemon) running on the host allowing 
configuration not supported by kernel NIC driver, supports ixgbe and 
i40e drivers' NIC. Run on the host for policy decisions w.r.t. what a 
VF can and cannot do to the PF. Only the DPDK PF would provide a callback 
to implement these features, the normal kernel drivers would not have the 
callback so would not support the features. Allow passing information to 
application controlling PF when VF message box event received such as those 
listed below, so action could be taken based on host policy. Stop VM1 from 
asking for something that compromises VM2. 

Multiple purposes:
1) set VF MAC anti-spoofing
2) set VF VLAN anti-spoofing
3) set TX loopback
4) set VF unicast promiscuous mode
5) set VF multicast promiscuous mode
6) set VF MTU
7) get/reset VF stats
8) set VF MAC address
9) set VF VLAN stripping
10) VF VLAN insertion
12) set VF broadcast mode
12) set VF VLAN tag
13) set VF VLAN filter
14) Set/reset the queue drop enable bit for all pools(only ixgbe support)
15) Set/reset the enable drop bit in the split receive control register
   (only ixgbe support)
VFD also includes VF to PF mailbox message management by APP. When PF 
receives mailbox messages from VF, PF should call the callback provided 
by APP to know if they're permitted to be processed.

Prerequisites
=============
1. Host PF in DPDK driver. Create 2 VFs from 1 PF with dpdk driver,take 
   Niantic for example::
        ./tools/dpdk-devbind.py -b igb_uio 81:00.0
        echo 2 >/sys/bus/pci/devices/0000:81:00.0/max_vfs

2. Detach VFs from the host::
        rmmod ixgbevf

3. Passthrough VF 81:10.0 to vm0 and passthrough VF 81:10.2 to vm1, 
   start vm0 and vm1

4. Login vm0 and vm1, then bind VF0 device to igb_uio driver.

5. Start testpmd on host and vm0 in chained port topology:: 
        ./testpmd -c f -n 4 -- -i --port-topology=chained --txqflags=0


Test Case 1: Set VLAN insert for VF from PF
===========================================
1. Disable vlan insert for VF0 from PF::
	testpmd> set vf vlan insert 0 0 0

2. Start VF0 testpmd, set it in mac forwarding mode and enable verbose output

3. Send packet from tester to VF0 without vlan id

4. Stop VF0 testpmd and check VF0 can receive packet without any vlan id

5. Enable vlan insert and insert random vlan id (1~4095) for VF0 from PF::  
	testpmd> set vf vlan insert 0 0 id

6. Start VF0 testpmd

7. Send packet from tester to VF0 without vlan id 

8. Stop VF0 testpmd and check VF0 can receive packet with configured vlan id 
        

Test Case 2: Set VLAN strip for VF from PF
==========================================
1. Disable VLAN strip for all queues for VF0 from PF::
	testpmd> set vf vlan stripq 0 0 off

2. Start VF0 testpmd, add rx vlan id as random 1~4095, set it in mac 
   forwarding mode and enable verbose output::
	testpmd> rx_vlan add id 0

3. Send packet from tester to VF0 with configured vlan id 

4. Stop VF0 testpmd and check VF0 can receive packet with configured vlan id
        
5. Enable VLAN strip for all queues for VF0 from PF::
	testpmd> set vf vlan stripq 0 0 on

6. Start VF0 testpmd

7. Send packet from tester to VF0 with configured vlan id 

8. Stop VF0 testpmd and check VF0 can receive packet without any vlan id

9. Remove vlan id on VF0
 

Test Case 3: Set VLAN antispoof for VF from PF
==============================================
1. Disable vlan filter and strip from PF::
	testpmd> vlan set filter off 0
	testpmd> vlan set strip off 0

2. Add a random 1~4095 vlan id to set filter from PF for VF::
	testpmd> rx_vlan add id port 0 vf 1

3. Disable vlan antispoof for VF from PF:: 
	testpmd> set vf vlan antispoof 0 0 off

4. Disable vlan filter and strip on VF0
		
5. Start testpmd on VF0, set it in mac forwarding mode and enable 
   verbose output

6. Send packets with matching/non-matching/no vlan id on tester port

7. Stop VF0 testpmd and check VF0 can receive and transmit packets with 
   matching/non-matching/no vlan id

8. Enable mac antispoof and vlan antispoof for vf from PF::
	testpmd> set vf mac antispoof 0 0 on
	testpmd> set vf vlan antispoof 0 0 on

9. Start VF0 testpmd

10. Send packets with matching/non-matching/no vlan id on tester port

11. Stop VF0 testpmd and check VF0 can receive all but only transmit 
    packet with matching vlan id


Test Case 4: Set mac antispoof for VF from PF
===============================================
1. Add fake mac and use fake mac instead of transmitted mac in the 
   macswap mode, so default is non-matching SA::
	.addr_bytes = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55} 

2. Disable VF0 mac antispoof from PF::
	testpmd> set vf mac antispoof 0 0 off

3. Start testpmd on VF0, set it in macswap forwarding mode and enable 
   verbose output::
	testpmd> set fwd macswap

4. Send packet from tester to VF0 with correct SA, but code has changed 
   to use fake SA

5. Stop VF0 testpmd and check VF0 can receive then transmit packet

6. Enable VF0 mac antispoof from PF::
	testpmd> set vf mac antispoof 0 0 on

7. Start VF0 testpmd

8. Send packet from tester to VF0 with correct SA, but code has changed 
   to use fake SA

9. Stop VF0 testpmd and check VF0 can receive packet but can't transmit packet

10. Recover original code


Test Case 5: Set the MAC address for VF from PF
===============================================
1. Set VF0 different MAC address from PF, such as A2:22:33:44:55:66 ::
	testpmd> set vf mac addr 0 0 A2:22:33:44:55:66

2. Stop VF0 testpmd and restart VF0 testpmd, check VF0 address is configured 
   address A2:22:33:44:55:66

3. Set testpmd in mac forwarding mode and enable verbose output

4. Send packet from tester to VF0 configured address

5. Stop VF0 testpmd and check VF0 can receive packet


Test Case 6: Enable/disable tx loopback
=======================================
1. Disable tx loopback for VF0 from PF::
	testpmd> set tx loopback 0 off

2. Set VF0 in rxonly forwarding mode and start testpmd

3. tcpdump on the tester port

4. Send 10 packets from VF1 to VF0

5. Stop VF0 testpmd, check VF0 can't receive any packet but tester port 
   could capture packet

6. Enable tx loopback for VF0 from PF:: 
	testpmd> set tx loopback 0 on

7. Start VF0 testpmd

8. Send packet from VF1 to VF0

9. Stop VF0 testpmd, check VF0 can receive packet,but tester port can't 
   capture packet


Test Case 7: Set drop enable bit for all queues
===============================================
1. Bind VF1 device to igb_uio driver and start testpmd in chained port 
   topology

2. Disable drop enable bit for all queues from PF::
	testpmd> set all queues drop 0 off

3. Only start VF1 to capture packet, set it in rxonly forwarding mode and 
   enable verbose output

4. Send 200 packets to VF0, make VF0 queue full of packets

5. Send 20 packets to VF1 

6. Stop VF1 testpmd and check VF1 can't receive packet

7. Enable drop enable bit for all queues from PF::
	testpmd> set all queues drop 0 on

8. Start VF1 testpmd

9. Stop VF1 testpmd and check VF1 can receive original queue buffer 20 packets

10. Start VF1 testpmd

11. Send 20 packets to VF1 

12. Stop VF1 testpmd and check VF1 can receive 20 packets



Test Case 8: Set split drop enable bit for VF from PF
=====================================================
1. Disable split drop enable bit for VF0 from PF::
	testpmd> set vf split drop 0 0 off

2. Set VF0 and host in rxonly forwarding mode and start testpmd
	   
3. Send a burst of 20000 packets to VF0 and check PF and VF0 can receive 
   all packets

4. Enable split drop enable bit for VF0 from PF::
	testpmd> set vf split drop 0 0 on

5. Send a burst of 20000 packets to VF0 and check some packets dropped 
   on PF and VF0



Test Case 9: Get/Reset stats for VF from PF
===========================================
1. Add testpmd and some print code in the rte_pmd_i40e_set_vf_vlan_filter() 
   function(drivers/net/i40e/i40e_ethdev.c) to start test, rebuild the code 

2. Get stats output for VF0 from PF, and check RX/TX packets is 0::
	testpmd> get vf stats 0 0

3. Set VF0 in mac forwarding mode and start testpmd

4. Send 10 packets to VF0 and check VF0 can receive 10 packets	 

5. Get stats for VF0 from PF, and check RX/TX packets is 10

6. Reset stats for VF0 from PF, and check PF and VF0 RX/TX packets is 0::
	testpmd> reset vf stats 0 0
	testpmd> get vf stats 0 0


Test Case 10: enhancement to identify VF MTU change
===================================================
1. Set VF0 in mac forwarding mode and start testpmd

2. Default mtu size is 1500, send one packet with length bigger than default 
   mtu size, such as 2000 from tester,check VF0 can receive but can't transmit 
   packet

3. Set VF0 mtu size as 3000, but need to stop then restart port to active mtu::
	testpmd> port stop all
	testpmd> port config mtu 0 3000
	testpmd> port start all
	testpmd> start
4. Send one packet with length 2000 from tester,check VF0 can receive and 
   transmit packet

5. Send one packet with length bigger than configured mtu size, such as 5000 
   from tester, check VF0 can receive but can't transmit packet


Test Case 11: Enable/disable vlan tag forwarding to VSIs  
========================================================
1. Disable VLAN tag for VF0 from PF::
	testpmd> set vf vlan tag 0 0 off

2. Start VF0 testpmd, add rx vlan id as random 1~4095, set it in mac forwarding 
   mode and enable verbose output

3. Send packet from tester to VF0 with vlan tag(vlan id should same as rx_vlan)

4. Stop VF0 testpmd and check VF0 can't receive vlan tag packet 

5. Enable VLAN tag for VF0 from PF::
	testpmd> set vf vlan tag 0 0 on

6. Start VF0 testpmd

7. Send packet from tester to VF0 with vlan tag(vlan id should same as rx_vlan)

8. Stop VF0 testpmd and check VF0 can receive vlan tag packet

9. Remove vlan id on VF0


Test Case 12: Broadcast mode
============================
1. Start testpmd on VF0, set it in rxonly mode and enable verbose output

2. Disable broadcast mode for VF0 from PF::
        testpmd>set vf broadcast 0 0 off

3. Send packets from tester with broadcast address,ff:ff:ff:ff:ff:ff, and check 
   VF0 can not receive the packet

4. Enable broadcast mode for VF0 from PF::
        testpmd>set vf broadcast 0 0 on

5. Send packets from tester with broadcast address,ff:ff:ff:ff:ff:ff, and check 
   VF0 can receive the packet


Test Case 13: Multicast mode
====================================
1. Start testpmd on VF0, set it in rxonly mode and enable verbose output

2. Disable promisc and multicast mode for VF0 from PF::
        testpmd>set vf promisc 0 0 off
        testpmd>set vf allmulti 0 0 off

3. Send packet from tester to VF0 with multicast MAC, and check VF0 can not 
   receive the packet

4. Enable multicast mode for VF0 from PF::
        testpmd>set vf allmulti 0 0 on

5. Send packet from tester to VF0 with multicast MAC, and check VF0 can receive 
   the packet



Test Case 14: Promisc mode
==================================
1. Start testpmd on VF0, set it in rxonly mode and enable verbose output

2. Disable promisc mode for VF from PF::
        testpmd>set vf promisc 0 0 off

3. Send packet from tester to VF0 with random MAC, and check VF0 can not 
   receive the packet

4. Send packet from tester to VF0 with correct MAC, and check VF0 can receive 
   the packet

5. Enable promisc mode for VF from PF::
        testpmd>set vf promisc 0 0 on

6. Send packet from tester to VF0 with random MAC, and the packet can be 
   received by VF0

7. Send packet from tester to VF0 with correct MAC, and the packet can be 
   received by VF0



