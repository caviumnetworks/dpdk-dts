.. Copyright (c) <2013>, Intel Corporation
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

===============================
SRIOV and InterVM Communication
===============================

Some applications such as pipelining of virtual appliances and traffic
mirroring to virtual appliances require the high performance InterVM
communications.

The testpmd application is used to configure traffic mirroring, PF VM receive
mode, PFUTA hash table and control traffic to a VF for inter-VM communication.

The 82599 supports four separate mirroring rules, each associated with a
destination pool. Each rule is programmed with one of the four mirroring types:

1. Pool mirroring: reflect all the packets received to a pool from the network.
2. Uplink port mirroring: reflect all the traffic received from the network.
3. Downlink port mirroring: reflect all the traffic transmitted to the
   network. 
4. VLAN mirroring: reflect all the traffic received from the network
   in a set of given VLANs (either from the network or from local VMs).


Prerequisites for all 2VMs cases/Mirror 2VMs cases
==================================================

Create two VF interface VF0 and VF1 from one PF interface and then attach them
to VM0 and VM1. Suppose PF is 0000:08:00.0.Below are commands which can be
used to generate 2VFs and make them in pci-stub modes.::

    ./tools/pci_unbind.py --bind=igb_uio 0000:08:00.0
    echo 2 > /sys/bus/pci/devices/0000\:08\:00.0/max_vfs
    echo "8086 10ed" > /sys/bus/pci/drivers/pci-stub/new_id
    echo 0000:08:10.0 >/sys/bus/pci/devices/0000\:08\:10.0/driver/unbind
    echo 0000:08:10.2 >/sys/bus/pci/devices/0000\:08\:10.2/driver/unbind
    echo 0000:08:10.0 >/sys/bus/pci/drivers/pci-stub/bind
    echo 0000:08:10.2 >/sys/bus/pci/drivers/pci-stub/bind

Start PF driver on the Host and skip the VFs.::

    ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 -b 0000:08:10.0  -b 0000:08:10.2 --  -i

For VM0 start up command, you can refer to below command.::

    qemu-system-x86_64 -name vm0 -enable-kvm -m 2048 -smp 4 -cpu host -drive file=/root/Downloads/vm0.img -net nic,macaddr=00:00:00:00:00:01 -net tap,script=/etc/qemu-ifup -device pci-assign,host=08:10.0 -vnc :1 --daemonize

The /etc/qemu-ifup can be below script, need you to create first::

    #!/bin/sh
    set -x
    switch=br0
    if [ -n "$1" ];then
        /usr/sbin/tunctl -u `whoami` -t $1
        /sbin/ip link set $1 up
        sleep 0.5s
        /usr/sbin/brctl addif $switch $1
        exit 0
    else
        echo "Error: no interface specified"
    exit 1
    fi

Similar for VM1, please refer to below command for VM1::

    qemu-system-x86_64 -name vm1 -enable-kvm -m 2048 -smp 4 -cpu host -drive file=/root/Downloads/vm1.img -net nic,macaddr=00:00:00:00:00:02 -net tap,script=/etc/qemu-ifup -device pci-assign,host=08:10.2 -vnc :4 -daemonize

If you want to run all common 2VM cases, please run testpmd on VM0 and VM1 and
start traffic forward on the VM hosts. Some specific prerequisites need to be
set up in each case::

    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF0 testpmd-> set fwd rxonly
    VF0 testpmd-> start
 
    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start

Test Case1: InterVM communication test on 2VMs
==============================================

Set the VF0 destination mac address to VF1 mac address, packets send from VF0
will be forwarded to VF1 and then send out::

    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 testpmd-> show port info 0
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
 
    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  --eth-peer=0,"VF1 mac" -i
    VF0 testpmd-> set fwd mac 
    VF0 testpmd-> start

Send 10 packets with VF0 mac address and make sure the packets will be
forwarded by VF1.

Test Case2: Mirror Traffic between 2VMs with Pool mirroring
===========================================================

Set up common 2VM prerequisites.

Add one mirror rule that will mirror VM0 income traffic to VM1::

    PF testpmd-> set port 0 mirror-rule 0 pool-mirror 0x1 dst-pool 1 on

Send 10 packets to VM0 and verify the packets has been mirrored to VM1 and
forwarded the packet.

After test need reset mirror rule::

    PF testpmd-> reset port 0 mirror-rule 0
  

Test Case3: Mirror Traffic between 2VMs with Uplink mirroring
=============================================================

Set up common 2VM prerequisites.

Add one mirror rule that will mirror VM0 income traffic to VM1::

    PF testpmd-> set port 0 mirror-rule 0 uplink-mirror dst-pool 1 on

Send 10 packets to VM0 and verify the packets has been mirrored to VM1 and
forwarded the packet.

After test need reset mirror rule::
    
	PF testpmd-> reset port 0 mirror-rule 0
  
Test Case4: Mirror Traffic between 2VMs with Downlink mirroring
===============================================================

Run testpmd on VM0 and VM1 and start traffic forward on the VM hosts::

    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i


Add one mirror rule that will mirror VM0 outcome traffic to VM1::

    PF testpmd-> set port 0 mirror-rule 0 downlink-mirror dst-pool 1 on

Make sure VM1 in receive only mode, VM0 send 16 packets, and verify the VM0
packets has been mirrored to VM1::
    
    VF1 testpmd-> set fwd rxonly
    VF1 testpmd-> start
    VF0 testpmd-> start tx_first 
  
Note: don't let VF1 fwd packets since downlink mirror will mirror back the
packets to received packets, which will be an infinite loop.

After test need reset mirror rule::

    PF testpmd-> reset port 0 mirror-rule 0  
  
Test Case5: Mirror Traffic between VMs with Vlan mirroring
==========================================================

Set up common 2VM prerequisites.

Add rx vlan-id 0 on VF0, add one mirror rule that will mirror VM0 income
traffic with specified vlan to VM1::

    PF testpmd-> rx_vlan add 0 port 0 vf 0x1
    PF testpmd-> set port 0 mirror-rule 0 vlan-mirror 0 dst-pool 1 on

Send 10 packets with vlan-id0/vm0 MAC to VM0 and verify the packets has been
mirrored to VM1 and forwarded the packet.

After test need reset mirror rule::
    
	PF testpmd-> reset port 0 mirror-rule 0

Test Case6: Mirror Traffic between 2VMs with Vlan & Pool mirroring
==================================================================

Set up common 2VM prerequisites.

Add rx vlan-id 3 of VF1, and 2 mirror rules, one is VM0 income traffic to VM1,
one is VM1 vlan income traffic to VM0::

    PF testpmd-> rx_vlan add 3 port 0 vf 0x2
    PF testpmd-> set port 0 mirror-rule 0 pool-mirror 0x1 dst-pool 1 on
    PF testpmd-> set port 0 mirror-rule 1 vlan-mirror 3 dst-pool 0 on
  
Send 2 flows one by one, first 10 packets with VM0 mac, and the second 100
packets with VM1 vlan and mac, and verify the first 10 packets has been
mirrored first to VM1, second 100 packets go to VM0 and the packets have been
forwarded.

After test need reset mirror rule::

    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
  
Test Case7: Mirror Traffic between 2VMs with Uplink & Downlink mirroring
========================================================================

Run testpmd on VM0 and VM1 and start traffic forward on the VM hosts::
    
    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i

Add 2 mirror rules that will mirror VM0 outcome and income traffic to VM1::
  
    PF testpmd-> set port 0 mirror-rule 0 downlink-mirror dst-pool 1 on
    PF testpmd-> set port 0 mirror-rule 0 uplink-mirror dst-pool 1 on

Make sure VM1 in receive only mode, VM0 first send 16 packets, and verify the
VM0 packets has been mirrored to VM1:: 
    
    VF1 testpmd-> set fwd rxonly
    VF1 testpmd-> start
    VF0 testpmd-> start tx_first 

Note: don't let VF1 fwd packets since downlink mirror will mirror back the
packets to received packets, which will be an infinite loop.

Send 10 packets to VF0 with VF0 MAC from ixia, verify that all VF0 received
packets and transmitted packets will mirror to VF1::

    VF0 testpmd-> stop 
    VF0 testpmd-> start  

After test need reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0  

Test Case8: Mirror Traffic between 2VMs with Vlan & Pool & Uplink & Downlink mirroring
======================================================================================

Run testpmd on VM0 and VM1 and start traffic forward on the VM hosts::
    
    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i


Add rx vlan-id 0 on VF0 and add 4 mirror rules::

    PF testpmd-> reset port 0 mirror-rule 1
    PF testpmd-> set port 0 mirror-rule 0 downlink-mirror dst-pool 1 on
    PF testpmd-> set port 0 mirror-rule 1 uplink-mirror dst-pool 1 on
    PF testpmd-> rx_vlan add 0 port 0 vf 0x2
    PF testpmd-> set port 0 mirror-rule 2 vlan-mirror 0 dst-pool 0 on
    PF testpmd-> set port 0 mirror-rule 3 pool-mirror 0x1 dst-pool 1 on
  
Make sure VM1 in receive only mode, VM0 first send 16 packets, and verify the
VM0 packets has been mirrored to VM1, VF1, RX, 16packets (downlink mirror)::

    VF1 testpmd-> set fwd rxonly
    VF1 testpmd-> start
    VF0 testpmd-> start tx_first 
  
Note: don't let VF1 fwd packets since downlink mirror will mirror back the
packets to received packets, which will be an infinite loop.

Send 1 packet to VF0 with VF0 MAC from ixia, check if VF0 RX 1 packet and TX 1
packet, and VF1 has 2 packets mirror from VF0(uplink mirror/downlink/pool)::

    VF0 testpmd-> stop 
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start  

Send 1 packet with VM1 vlan id and mac, and verify that VF0 have 1 RX packet, 1
TX packet, and VF1 have 2 packets(downlink mirror)::
    
    VF0 testpmd-> stop 
    VF0 testpmd-> set fwd rxonly  
    VF0 testpmd-> start 
  
After test need reset mirror rule::

    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1  
    PF testpmd-> reset port 0 mirror-rule 2
    PF testpmd-> reset port 0 mirror-rule 3  

  
Test Case9: Add Multi exact MAC address on VF
=============================================

Add an exact destination mac address on VF0::

    PF testpmd-> mac_addr add port 0 vf 0 00:11:22:33:44:55
  
Send 10 packets with dst mac 00:11:22:33:44:55 to VF0 and make sure VF0 will
receive the packets.

Add another exact destination mac address on VF0::
    
    PF testpmd-> mac_addr add port 0 vf 0 00:55:44:33:22:11

Send 10 packets with dst mac 00:55:44:33:22:11 to VF0 and make sure VF0 will
receive the packets.

After test need restart PF and VF for clear exact mac addresss, first quit VF,
then quit PF.

Test Case10: Enable/Disable one uta MAC address on VF
=====================================================

Enable PF promisc mode and enable VF0 accept uta packets::

    PF testpmd-> set promisc 0 on
    PF testpmd-> set port 0 vf 0 rxmode ROPE on 
 
Add an uta destination mac address on VF0::
    
    PF testpmd-> set port 0 uta 00:11:22:33:44:55 on
 
Send 10 packets with dst mac 00:11:22:33:44:55 to VF0 and make sure VF0 will
the packets.

Disable PF promisc mode, repeat step3, check VF0 should not accept uta packets::

    PF testpmd-> set promisc 0 off
    PF testpmd-> set port 0 vf 0 rxmode ROPE off

Test Case11: Add Multi uta MAC addresses on VF
==============================================

Add 2 uta destination mac address on VF0::
    
    PF testpmd-> set port 0 uta 00:55:44:33:22:11 on
    PF testpmd-> set port 0 uta 00:55:44:33:22:66 on
 
Send 2 flows, first 10 packets with dst mac 00:55:44:33:22:11, another 100
packets with dst mac 00:55:44:33:22:66 to VF0 and make sure VF0 will receive
all the packets.

Test Case12: Add/Remove uta MAC address on VF
=============================================

Add one uta destination mac address on VF0::

    PF testpmd-> set port 0 uta 00:55:44:33:22:11 on
  
Send 10 packets with dst mac 00:55:44:33:22:11 to VF0 and make sure VF0 will
receive the packets.

Remove the uta destination mac address on VF0::
    
    PF testpmd-> set port 0 uta 00:55:44:33:22:11 off

Send 10 packets with dst mac 00:11:22:33:44:55 to VF0 and make sure VF0 will
not receive the packets.

Add an uta destination mac address on VF0 again::

    PF testpmd-> set port 0 uta 00:11:22:33:44:55 on
 
Send packet with dst mac 00:11:22:33:44:55 to VF0 and make sure VF0 will
receive again and forwarded the packet. This step is to make sure the on/off
switch is working.

Test Case13: Pause RX Queues
============================

Pause RX queue of VF0 then send 10 packets to VF0 and make sure VF0 will not
receive the packets::
    
    PF testpmd-> set port 0 vf 0 rx off 

Enable RX queue of VF0 then send 10 packets to VF0 and make sure VF0 will
receive the packet::

    PF testpmd-> set port 0 vf 0 rx on

Repeat the off/on twice to check the switch capability, and ensure on/off can
work stable.

Test Case14: Pause TX Queues
============================

Pause TX queue of VF0 then send 10 packets to VF0 and make sure VF0 will not
forward the packet::

    PF testpmd-> set port 0 vf 0 tx off 

Enable RX queue of VF0 then send 10 packets to VF0 and make sure VF0 will
forward the packet::
    
    PF testpmd-> set port 0 vf 0 tx on
 
Repeat the off/on twice to check the switch capability, and ensure on/off can
work stable.

Test Case15: Prevent Rx of Broadcast on VF
==========================================

Disable VF0 rx broadcast packets then send broadcast packet to VF0 and make
sure VF0 will not receive the packet::
    
    PF testpmd-> set port 0 vf 0 rxmode  BAM off
 
Enable VF0 rx broadcast packets then send broadcast packet to VF0 and make sure
VF0 will receive and forward the packet::
    
    PF testpmd-> set port 0 vf 0 rxmode  BAM on
 
Repeat the off/on twice to check the switch capability, and ensure on/off can
work stable.

Test Case16: Negative input to commands
=======================================

Input invalid commands on PF/VF to make sure the commands can't work::

    1. PF testpmd-> set port 0 vf 65 tx on
    2. PF testpmd-> set port 2 vf -1 tx off
    3. PF testpmd-> set port 0 vf 0 rx oneee
    4. PF testpmd-> set port 0 vf 0 rx offdd
    5. PF testpmd-> set port 0 vf 0 rx oneee
    6. PF testpmd-> set port 0 vf 64 rxmode BAM on
    7. PF testpmd-> set port 0 vf 64 rxmode BAM off
    8. PF testpmd-> set port 0 uta 00:11:22:33:44 on
    9. PF testpmd-> set port 7 uta 00:55:44:33:22:11 off
    10. PF testpmd-> set port 0 vf 34 rxmode ROPE on 
    11. PF testpmd-> mac_addr add port 0 vf 65 00:55:44:33:22:11
    12. PF testpmd-> mac_addr add port 5 vf 0 00:55:44:88:22:11
    13. PF testpmd-> set port 0 mirror-rule 0 pool-mirror 65 dst-pool 1 on
    14. PF testpmd-> set port 0 mirror-rule 0xf uplink-mirror dst-pool 1 on
    15. PF testpmd-> set port 0 mirror-rule 2 vlan-mirror 9 dst-pool 1 on
    16. PF testpmd-> set port 0 mirror-rule 0 downlink-mirror 0xf dst-pool 2 off
    17. PF testpmd-> reset port 0 mirror-rule 4
    18. PF testpmd-> reset port 0xff mirror-rule 0

Prerequisites for Scaling 4VFs per 1PF
======================================

Create 4VF interface VF0, VF1, VF2, VF3 from one PF interface and then attach
them to VM0, VM1, VM2 and VM3.Start PF driver on the Host and skip the VF
driver will has been already attached to VMs::
    
    On PF ./tools/pci_unbind.py --bind=igb_uio 0000:08:00.0
    echo 2 > /sys/bus/pci/devices/0000\:08\:00.0/max_vfs
    ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 -b 0000:08:10.0 -b 0000:08:10.2 -b 0000:08:10.4 -b 0000:08:10.6 --  -i
 
If you want to run all common 4VM cases, please run testpmd on VM0, VM1, VM2
and VM3 and start traffic forward on the VM hosts. Some specific prerequisites
are set up in each case::

    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF2 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF3 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i

Test Case17: Scaling Pool Mirror on 4VFs
========================================

Make sure prerequisites for Scaling 4VFs per 1PF is set up.

Add one mirror rules that will mirror VM0/VM1/VM2 income traffic to VM3::
    
    PF testpmd-> set port 0 mirror-rule 0 pool-mirror 0x7 dst-pool 3 on
    VF0 testpmd-> set fwd rxonly
    VF0 testpmd-> start
    VF1 testpmd-> set fwd rxonly
    VF1 testpmd-> start
    VF2 testpmd-> set fwd rxonly
    VF2 testpmd-> start
    VF3 testpmd-> set fwd rxonly
    VF3 testpmd-> start
  
Send 3 flows to VM0/VM1/VM2, one with VM0 mac, one with VM1 mac, one with VM2
mac, and verify the packets has been mirrored to VM3.

Reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0

Set another 2 mirror rules. VM0/VM1 income traffic mirror to VM2 and VM3::
    
    PF testpmd-> set port 0 mirror-rule 0 pool-mirror 0x3 dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 1 pool-mirror 0x3 dst-pool 3 on

Send 2 flows to VM0/VM1, one with VM0 mac, one with VM1 mac and verify the
packets has been mirrored to VM2/VM3 and VM2/VM3 have forwarded these packets.

Reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
  
Test Case18: Scaling Uplink Mirror on 4VFs
==========================================

Make sure prerequisites for Scaling 4VFs per 1PF is set up.

Add one mirror rules that will mirror all income traffic to VM2 and VM3::
    
    PF testpmd-> set port 0 mirror-rule 0 uplink-mirror dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 1 uplink-mirror dst-pool 3 on
    VF0 testpmd-> set fwd rxonly
    VF0 testpmd-> start
    VF1 testpmd-> set fwd rxonly
    VF1 testpmd-> start
    VF2 testpmd-> set fwd rxonly
    VF2 testpmd-> start
    VF3 testpmd-> set fwd rxonly
    VF3 testpmd-> start
  
Send 4 flows to VM0/VM1/VM2/VM3, one packet with VM0 mac, one packet with VM1
mac, one packet with VM2 mac, and one packet with VM3 mac and verify the
income packets has been mirrored to VM2 and VM3. Make sure VM2/VM3 will have 4
packets.

Reset mirror rule:: 
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
  
Test Case19: Scaling Downlink Mirror on 4VFs
============================================

Make sure prerequisites for scaling 4VFs per 1PF is set up.

Add one mirror rules that will mirror all outcome traffic to VM2 and VM3::
    
    PF testpmd-> set port 0 mirror-rule 0 downlink-mirror dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 1 downlink-mirror dst-pool 3 on
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start 
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
    VF2 testpmd-> set fwd rxonly
    VF2 testpmd-> start
    VF3 testpmd-> set fwd rxonly
    VF3 testpmd-> start
  
Send 2 flows to VM0/VM1, one with VM0 mac, one with VM1 mac, and verify VM0/VM1
will forward these packets. And verify the VM0/VM1 outcome packets have been
mirrored to VM2 and VM3.

Reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
  
Test Case20: Scaling Vlan Mirror on 4VFs
========================================

Make sure prerequisites for scaling 4VFs per 1PF is set up.

Add 3 mirror rules that will mirror VM0/VM1/VM2 vlan income traffic to VM3::
    
    PF testpmd-> rx_vlan add 1 port 0 vf 0x1
    PF testpmd-> rx_vlan add 2 port 0 vf 0x2
    PF testpmd-> rx_vlan add 3 port 0 vf 0x4
    PF testpmd-> set port 0 mirror-rule 0 vlan-mirror 1,2,3 dst-pool 3 on
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
    VF2 testpmd-> set fwd mac
    VF2 testpmd-> start
    VF3 testpmd-> set fwd mac
    VF3 testpmd-> start
  
Send 3 flows to VM0/VM1/VM2, one with VM0 mac/vlanid, one with VM1 mac/vlanid,
one with VM2 mac/vlanid,and verify the packets has been mirrored to VM3 and
VM3 has forwards these packets.

Reset mirror rule:: 
    
    PF testpmd-> reset port 0 mirror-rule 0

Set another 2 mirror rules. VM0/VM1 income traffic mirror to VM2 and VM3::
    
    PF testpmd-> set port 0 mirror-rule 0 vlan-mirror 1 dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 1 vlan-mirror 2 dst-pool 3 on

Send 2 flows to VM0/VM1, one with VM0 mac/vlanid, one with VM1 mac/vlanid and
verify the packets has been mirrored to VM2 and VM3, then VM2 and VM3 have
forwarded these packets.

Reset mirror rule:: 
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
  
Test Case21: Scaling Vlan Mirror & Pool Mirror on 4VFs
======================================================

Make sure prerequisites for scaling 4VFs per 1PF is set up.

Add 3 mirror rules that will mirror VM0/VM1 vlan income traffic to VM2, VM0/VM1
pool will come to VM3::
    
    PF testpmd-> rx_vlan add 1 port 0 vf 0x1
    PF testpmd-> rx_vlan add 2 port 0 vf 0x2
    PF testpmd-> set port 0 mirror-rule 0 vlan-mirror 1 dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 1 vlan-mirror 2 dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 2 pool-mirror 0x3 dst-pool 3 on
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
    VF2 testpmd-> set fwd mac
    VF2 testpmd-> start
    VF3 testpmd-> set fwd mac
    VF3 testpmd-> start
  
Send 2 flows to VM0/VM1, one with VM0 mac/vlanid, one with VM1 mac/vlanid, and
verify the packets has been mirrored to VM2 and VM3, and VM2/VM3 have
forwarded these packets.

Reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
    PF testpmd-> reset port 0 mirror-rule 2

Set 3 mirror rules. VM0/VM1 income traffic mirror to VM2, VM2 traffic will
mirror to VM3:: 
    
    PF testpmd-> set port 0 mirror-rule 0 vlan-mirror 1,2 dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 2 pool-mirror 0x2 dst-pool 3 on

Send 2 flows to VM0/VM1, one with VM0 mac/vlanid, one with VM1 mac/vlanid and
verify the packets has been mirrored to VM2, VM2 traffic will be mirrored to
VM3, then VM2 and VM3 have forwarded these packets.

Reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
    PF testpmd-> reset port 0 mirror-rule 2
  
Test Case22: Scaling Uplink Mirror & Downlink Mirror on 4VFs
============================================================

Make sure prerequisites for scaling 4VFs per 1PF is set up.

Add 2 mirror rules that will mirror all income traffic to VM2, all outcome
traffic to VM3. Make sure VM2 and VM3 rxonly::
    
    PF testpmd-> set port 0 mirror-rule 0 uplink-mirror dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 1 downlink-mirror dst-pool 3 on
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
    VF2 testpmd-> set fwd rxonly
    VF2 testpmd-> start
    VF3 testpmd-> set fwd rxonly
    VF3 testpmd-> start
  
Send 2 flows to VM0/VM1, one with VM0 mac, one with VM1 mac and make sure
VM0/VM1 will forward packets. Verify the income packets have been mirrored to
VM2, the outcome packets has been mirrored to VM3.

Reset mirror rule::
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1

Test Case23: Scaling Pool & Vlan & Uplink & Downlink Mirror on 4VFs
===================================================================

Make sure prerequisites for scaling 4VFs per 1PF is set up.

Add mirror rules that VM0 vlan mirror to VM1, all income traffic mirror to VM2,
all outcome traffic mirror to VM3, all VM1 traffic will mirror to VM0. Make
sure VM2 and VM3 rxonly::
   
    PF testpmd-> rx_vlan add 1 port 0 vf 0x1
    PF testpmd-> set port 0 mirror-rule 0 vlan-mirror 1 dst-pool 1 on
    PF testpmd-> set port 0 mirror-rule 1 pool-mirror 0x2 dst-pool 0 on
    PF testpmd-> set port 0 mirror-rule 2 uplink-mirror dst-pool 2 on
    PF testpmd-> set port 0 mirror-rule 3 downlink-mirror dst-pool 3 on
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
    VF2 testpmd-> set fwd rxonly
    VF2 testpmd-> start
    VF3 testpmd-> set fwd rxonly
    VF3 testpmd-> start
  
Send 10 packets to VM0 with VM0 mac/vlanid, verify that VM1 will be mirrored
and packets will be forwarded, VM2 will have all income traffic mirrored, VM3
will have all outcome traffic mirrored

Send 10 packets to VM1 with VM1 mac, verify that VM0 will be mirrored and
packets will be forwarded, VM2 will have all income traffic mirrored; VM3 will
have all outcome traffic mirrored

Reset mirror rule:: 
    
    PF testpmd-> reset port 0 mirror-rule 0
    PF testpmd-> reset port 0 mirror-rule 1
    PF testpmd-> reset port 0 mirror-rule 2
    PF testpmd-> reset port 0 mirror-rule 3

Test Case24: Scaling InterVM communication on 4VFs
==================================================

Set the VF0 destination mac address to VF1 mac address, packets send from VF0
will be forwarded to VF1 and then send out. Similar for VF2 and VF3:: 

    VF1 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF1 testpmd-> show port info 0
    VF1 testpmd-> set fwd mac
    VF1 testpmd-> start
 
    VF0 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  --eth-peer=0,"VF1 mac" -i
    VF0 testpmd-> set fwd mac
    VF0 testpmd-> start
 
    VF3 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  -i
    VF3 testpmd-> show port info 0
    VF3 testpmd-> set fwd mac
    VF3 testpmd-> start
 
    VF2 ./x86_64-default-linuxapp-gcc/app/testpmd -c f -n 4 --  --eth-peer=0,"VF3 mac" -i
    VF2 testpmd-> set fwd mac
    VF2 testpmd-> start

Send 2 flows, one with VF0 mac address and make sure the packets will be
forwarded by VF1, another with VF2 mac address and make sure the packets will
be forwarded by VF3.


