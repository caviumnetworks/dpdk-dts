.. Copyright (c) <2016> Intel Corporation
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
         
=====================================
 Cloud filter support through Ethtool
=====================================
This feature based on X710 to classify VxLan/Geneve packets and put those into
a specified queue in VF for further processing from virtual switch.

Prerequisites
=============
Cloud filter feature based on latest i40e out of tree driver. Should also
update ethtool and XL710 firmware.
	Ethtool version: 3.18
	i40e driver: i40e-1.5.13_rc1
	Kernel version: 4.2.2
	Xl710 DA2 firmware: 5.02 0x80002282

BIOS setting:
	Enable VT-d and VT-x
Kernel command line:
	Enable Intel IOMMU with below arguments
	intel_iommu=on iommu=pt
	
Create two VFs from kernel driver:
	echo 2 > /sys/bus/pci/devices/0000\:82\:00.0/sriov_numvfs
	ifconfig $PF_INTF up

Add vxlan network interface based on PF device:
	ip li add vxlan0 type vxlan id 1 group 239.1.1.1 local 127.0.0.1 dev $PF_INTF 
	ifconfig vxlan0 up

Allocate hugepage for dpdk:
	echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages	

Bound vf device to igb_uio driver and start testpmd with multiple queues:
	cd dpdk
	modprobe uio
	insmod  ./x86_64-native-linuxapp-gcc/kmod/igb_uio.ko
	./tools/dpdk_nic_bind.py --bind=igb_uio 82:02.0 82:02.1
	./x86_64-native-linuxapp-gcc/app/testpmd -c ffff -n 4 -- -i --rxq=4 --txq=4 --disable-rss
	testpmd> set nbcore 8
	testpmd> set fwd rxonly
	testpmd> set verbose 1
	testpmd> start


Test case: cloud filter rule(inner ip)
---------------------------------------
1. Add cloud filter with inner ip address rule.
Flow type ip4 mean this rule only match inner destination ip address.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ip4 dst-ip 192.168.1.1 user-def 0xffffffff00000001 action 3 loc 1

2. Send vxlan packet with inner ip matched rule
	Ether()/IP()/UDP()/Vxlan()/Ether()/IP(dst="192.168.1.1")/UDP()/Raw('x' * 20)

3. verify packet received by queue3 of VF1, verify packet type is correct

	testpmd> port 1/queue 3: received 1 packets
    src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=106 - nb_segs=1 
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown 
	- Tunnel type: GRENAT - Inner L2 type: ETHER - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: UDP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 1 - Receive queue=0x3
	
Test case: cloud filter rule(inner mac)
---------------------------------------
1. Add cloud filter with Inner mac rule.
Dst mac mask ff:ff:ff:ff:ff:ff mean outer mac address is not in the rule.
Src mac mask 00:00:00:00:00:00 mean inner mac address is in the rule.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ether dst 00:00:00:00:00:00 m \
	ff:ff:ff:ff:ff:ff src 00:00:00:00:09:00 m 00:00:00:00:00:00 \
	user-def 0xffffffff00000001 action 3 loc 1	
	
2. Send vxlan packet with inner mac matched rule
	Ether()/IP()/UDP()/Vxlan()/Ether(dst="00:00:00:00:09:00")/IP()/TCP()/Raw('x' * 20)

3. verify packet received by queue3 of VF1, verify packet type is correct

	testpmd> port 1/queue 3: received 1 packets
	src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=120 - nb_segs=1 
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown 
	- Tunnel type: GRENAT - Inner L2 type: ETHER - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: TCP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 0 - Receive queue=0x3	

Test case: cloud filter rule(inner mac + outer mac + vni)
---------------------------------------------------------
1. Add cloud filter with Inner mac + outer mac + vni rule.
Dst mac mask 00:00:00:00:00:00 mean outer mac address is in the rule.
Src mac mask 00:00:00:00:00:00 mean inner mac address is in the rule.
User define field higher 32bit is 0x1 mean vni match 1 is in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ether dst 00:00:00:00:10:00 m \
	00:00:00:00:00:00 src 00:00:00:00:09:00 m 00:00:00:00:00:00 \
	user-def 0x100000001 action 3 loc 1	
	
2. Send vxlan packet with inner mac match rule
	Ether(dst="00:00:00:00:10:00")/IP()/UDP()/Vxlan(vni=1)/Ether(dst="00:00:00:00:09:00")/IP()/TCP()/Raw('x' * 20)

3. verify packet received by queue3 of VF1, verify packet type is correct

	testpmd> port 1/queue 3: received 1 packets
	src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=120 - nb_segs=1 
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown 
	- Tunnel type: GRENAT - Inner L2 type: ETHER - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: TCP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 0 - Receive queue=0x3	
	
Test case: cloud filter rule(inner mac + inner vlan + vni)
---------------------------------------------------------
1. Add cloud filter with Inner mac + inner vlan + vni rule.
Dst mac mask ff:ff:ff:ff:ff:ff mean outer mac address is not in the rule.
Src mac mask 00:00:00:00:00:00 mean inner mac address is in the rule.
Vlan 1 mean vlan match is in the rule.
User define field higher 32bit is 0x1 mean vni match 1 is in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ether dst 00:00:00:00:00:00 m \
	ff:ff:ff:ff:ff:ff src 00:00:00:00:09:00 m 00:00:00:00:00:00 \
	vlan 1 user-def 0x100000001 action 3 loc 1	
	
2. Send vxlan packet with inner mac match rule
	Ether()/IP()/UDP()/Vxlan(vni=1)/Ether(dst="00:00:00:00:09:00")/Dot1Q(vlan=1)/IP()/TCP()/Raw('x' * 20)

3. verify packet received by queue3 of VF1, verify packet type is correct

	testpmd> port 1/queue 3: received 1 packets
	src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=124 - nb_segs=1
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown
	- Tunnel type: GRENAT - Inner L2 type: ETHER_VLAN - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: TCP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 1 - Receive queue=0x3

Test case: cloud filter rule(inner mac + inner vlan)
---------------------------------------------------------
1. Add cloud filter with Inner mac + inner vlan rule.
Dst mac mask ff:ff:ff:ff:ff:ff mean outer mac address is not in the rule.
Src mac mask 00:00:00:00:00:00 mean inner mac address is in the rule.
Vlan 1 mean vlan match is in the rule.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ether dst 00:00:00:00:00:00 m \
	ff:ff:ff:ff:ff:ff src 00:00:00:00:09:00 m 00:00:00:00:00:00 \
	vlan 1 user-def 0xffffffff00000001 action 3 loc 1	
	
2. Send vxlan packet with inner mac match rule
	Ether()/IP()/UDP()/Vxlan(vni=1)/Ether(dst="00:00:00:00:09:00")/Dot1Q(vlan=1)/IP()/TCP()/Raw('x' * 20)

3. verify packet received by queue3 of VF1, verify packet type is correct

	testpmd> port 1/queue 3: received 1 packets
	src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=124 - nb_segs=1
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown
	- Tunnel type: GRENAT - Inner L2 type: ETHER_VLAN - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: TCP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 1 - Receive queue=0x3	

Test case: Remove cloud filter rule 
-----------------------------------
Remove cloud filter rule in location 1.
	ethtool -N $PF_INTF delete 1
Dump rule and check there's no rule listed.
	ethtool -n $PF_INTF
	Total 0 rules
Send packet match last rule.
	Ether(dst not match PF&VF)/IP()/UDP()/Vxlan(vni=1)/Ether(dst="00:00:00:00:09:00")/Dot1Q(vlan=1)/IP()/TCP()/Raw('x' * 20)
Check packet only received on PF device.

Test case: Multiple cloud filter rules
--------------------------------------
1. Add cloud filter with Inner mac + inner vlan rule.
Dst mac mask ff:ff:ff:ff:ff:ff mean outer mac address is not in the rule.
Src mac mask 00:00:00:00:00:00 mean inner mac address is in the rule.
Vlan 1 mean vlan match is in the rule.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ether dst 00:00:00:00:00:00 m \
	ff:ff:ff:ff:ff:ff src 00:00:00:00:09:00 m 00:00:00:00:00:00 \
	vlan 1 user-def 0xffffffff00000001 action 3 loc 1
	
2. Add another cloud filter with Inner mac + inner vlan rule.
Dst mac mask ff:ff:ff:ff:ff:ff mean outer mac address is not in the rule.
Src mac mask 00:00:00:00:00:00 mean inner mac address is in the rule.
Vlan 2 mean vlan match is in the rule.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 0 mean packet will be forwarded to VF0.
Action 3 mean packet will be redirected to queue 3.
Locate 2 mean this rule will be added to index 2.

	ethtool -N $PF_INTF flow-type ether dst 00:00:00:00:00:00 m \
	ff:ff:ff:ff:ff:ff src 00:00:00:00:10:00 m 00:00:00:00:00:00 \
	vlan 2 user-def 0xffffffff00000000 action 0 loc 2

3. Dump cloud filter rules
	ethtool -n $PF_INTF
	64 RX rings available
	Total 2 rules

4. Send packet match rule 1
	Ether()/IP()/UDP()/Vxlan(vni=1)/Ether(dst="00:00:00:00:09:00")/Dot1Q(vlan=1)/IP()/TCP()/Raw('x' * 20)

5. verify packet received by queue3 of VF1, verify packet type is correct
	testpmd> port 1/queue 3: received 1 packets
	src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=124 - nb_segs=1 
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown 
	- Tunnel type: GRENAT - Inner L2 type: ETHER_VLAN - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: TCP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 1 - Receive queue=0x3

6. Send packet match rule 2
	Ether()/IP()/UDP()/Vxlan(vni=1)/Ether(dst="00:00:00:00:10:00")/Dot1Q(vlan=2)/IP()/TCP()/Raw('x' * 20)

7. verify packet received by queue3 of VF0, verify packet type is correct
	testpmd> port 0/queue 3: received 1 packets
	src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=124 - nb_segs=1
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown - Tunnel type: GRENAT
	- Inner L2 type: ETHER_VLAN - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: TCP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 1 - Receive queue=0x3

Test case: Bifurcated between kernel VF and dpdk VF
---------------------------------------------------
1. Add cloud filter with inner ip address rule.
Flow type ip4 mean this rule only match inner destination ip address.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 1 mean packet will be forwarded to VF1.
Action 3 mean packet will be redirected to queue 3.

	ethtool -N $PF_INTF flow-type ip4 dst-ip 192.168.1.1 user-def 0xffffffff00000001 action 3 loc 1

2. Add cloud filter with inner ip address rule.
Flow type ip4 mean this rule only match inner destination ip address.
User define field higher 32bit is all 0xf mean vni id is not in the rule.
Lower 32bit is 0 mean packet will be forwarded to VF0.
Action 0 mean packet will be redirected to queue 0.

	ethtool -N $PF_INTF flow-type ip4 dst-ip 192.168.2.1 user-def 0xffffffff00000000 action 0 loc 2

3. Send vxlan packet which matched first rule
	Ether()/IP()/UDP()/Vxlan()/Ether()/IP(dst="192.168.1.1")/UDP()/Raw('x' * 20)
	
4. verify packet received by queue3 of VF1, verify packet type is correct

	testpmd> port 1/queue 3: received 1 packets
    src=00:00:00:00:00:00 - dst=00:00:00:00:09:00 - type=0x0800 - length=106 - nb_segs=1 
	- (outer) L2 type: ETHER - (outer) L3 type: IPV4_EXT_UNKNOWN - (outer) L4 type: Unknown 
	- Tunnel type: GRENAT - Inner L2 type: ETHER - Inner L3 type: IPV4_EXT_UNKNOWN - Inner L4 type: UDP
	- VXLAN packet: packet type =24721, Destination UDP port =8472, VNI = 1 - Receive queue=0x3

5. Send vxlan packet which matched second rule
	Ether()/IP()/UDP()/Vxlan()/Ether()/IP(dst="192.168.2.1")/UDP()/Raw('x' * 20)
	
6. verify packet received by VF0, verify packet content is correct
