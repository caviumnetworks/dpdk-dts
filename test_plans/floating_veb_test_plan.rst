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

=====================================
VEB Switch and floating VEB Test Plan 
=====================================

VEB Switching Introduction
==========================

IEEE EVB tutorial: 
http://www.ieee802.org/802_tutorials/2009-11
/evb-tutorial-draft-20091116_v09.pdf

Virtual Ethernet Bridge (VEB) - This is an IEEE EVB term. A VEB is a VLAN 
Bridge internal to Fortville that bridges the traffic of multiple VSIs over
 an internal virtual network. 

Virtual Ethernet Port Aggregator (VEPA) - This is an IEEE EVB term. A VEPA
multiplexes the traffic of one or more VSIs onto a single Fortville Ethernet
port. The biggest difference between a VEB and a VEPA is that a VEB can
switch packets internally between VSIs, whereas a VEPA cannot. 

Virtual Station Interface (VSI) - This is an IEEE EVB term that defines 
the properties of a virtual machine's (or a physical machine's) connection 
to the network. Each downstream v-port on a Fortville VEB or VEPA defines 
a VSI. A standards-based definition of VSI properties enables network 
management tools to perform virtual machine migration and associated network 
re-configuration in a vendor-neutral manner.

My understanding of VEB is that it's an in-NIC switch(MAC/VLAN), and it can 
support VF->VF, PF->VF, VF->PF packet forwarding according to the NIC internal 
switch. It's similar as Niantic's SRIOV switch.

Floating VEB Introduction
=========================

Floating VEB is based on VEB Switching. It will address 2 problems:

Dependency on PF: When the physical port is link down, the functionality of 
the VEB/VEPA will not work normally. Even only data forwarding between the VF 
is required, one PF port will be wasted to create the related VEB.

Ensure all the traffic from VF can only forwarding within the VFs connect 
to the floating VEB, cannot forward to the outside world.

Prerequisites for VEB testing
=============================

1. Get the pci device id of DUT, for example::

    ./dpdk-devbind.py --st
    0000:05:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens785f0 drv=i40e 
    unused=
    
2.1  Host PF in kernel driver. Create 2 VFs from 1 PF with kernel driver, 
     and set the VF MAC address at PF::

    echo 2 > /sys/bus/pci/devices/0000\:05\:00.0/sriov_numvfs
    ./dpdk-devbind.py --st

    0000:05:02.0 'XL710/X710 Virtual Function' unused=
    0000:05:02.1 'XL710/X710 Virtual Function' unused=

    ip link set ens785f0 vf 0 mac 00:11:22:33:44:11
    ip link set ens785f0 vf 1 mac 00:11:22:33:44:12

2.2  Host PF in DPDK driver. Create 2VFs from 1 PF with dpdk driver:: 
    
    ./dpdk-devbind.py -b igb_uio 05:00.0 
    echo 2 >/sys/bus/pci/devices/0000:05:00.0/max_vfs
    ./dpdk-devbind.py --st
    0000:05:02.0 'XL710/X710 Virtual Function' unused=i40evf,igb_uio
    0000:05:02.1 'XL710/X710 Virtual Function' unused=i40evf,igb_uio

3. Bind the VFs to dpdk driver::

    ./tools/dpdk-devbind.py -b igb_uio 05:02.0 05:02.1

4. Reserve huge pages memory(before using DPDK)::

    echo 4096 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB
    /nr_hugepages 
    mkdir /mnt/huge  
    mount -t hugetlbfs nodev /mnt/huge    


Test Case1: Floating VEB inter VF-VF 
====================================

Summary: 1 DPDK PF, then create 2VF, PF in the host running dpdk testpmd, 
and VF0 are running dpdk testpmd, VF0 send traffic, and set the packet's 
DEST MAC to VF1, check if VF1 can receive the packets. Check Inter VF-VF 
MAC switch when PF is link down as well as up.

Launch PF testpmd::
   ./testpmd -c 0xf -n 4 --socket-mem 1024,1024
   -w 05:00.0,enable_floating_veb=1 --file-prefix=test1 -- -i

2. In the host, run testpmd with floating parameters and make the link down::

   ./testpmd -c 0xf -n 4 --socket-mem 1024,1024
   -w 05:00.0,enable_floating_veb=1 --file-prefix=test1 -- -i
   testpmd> port start all
   testpmd> show port info all

3. In VM1, run testpmd::

   ./testpmd -c 0xf0 -n 4 --socket-mem 1024,1024
   -w 05:02.0 --file-prefix=test2 -- -i --crc-strip 
   testpmd>mac_addr add 0 vf1_mac_address
   testpmd>set fwd rxonly
   testpmd>start
   testpmd>show port stats all
   
  In VM2, run testpmd::

 ./testpmd -c 0xf00 -n 4 --socket-mem 1024,1024 -w 05:02.1 --file-prefix=test3
 -- -i --crc-strip --eth-peer=0,vf1_mac_address
 testpmd>set fwd txonly
 testpmd>start
 testpmd>show port stats all

4. check if VF1 can get all the packets. Check the packet content is no 
   corrupted. RX-packets=TX-packets, but there is a little RX-error. 
   RF receive no packets.

5. Set "testpmd> port stop all" and "testpmd> start" in step2, 
   then run the step3-4 again. same result.


Test Case2: Floating VEB PF can't get traffic from VF    
=====================================================
DPDK PF, then create 1VF, PF in the host running dpdk testpmd, 
send traffic from PF to VF0, VF0 can't receive any packets; 
send traffic from VF0 to PF, PF can't receive any packets either.
 

1. In host, launch testpmd::

   ./testpmd -c 0x3 -n 4 -w 82:00.0,enable_floating_veb=1 -- -i
   testpmd> set fwd rxonly
   testpmd> port start all
   testpmd> start
   testpmd> show port stats all

3. In VM1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,pf_mac_addr
   testpmd>set fwd txonly
   testpmd>start
   testpmd>show port stats all

4. Check if PF can not get any packets, so VF1->PF is not working. 

5. Set "testpmd> port stop all" in step2, then run the test case again.
   Same result.



Test Case3 Floating VEB VF can't receive traffic from outside world 
===================================================================

DPDK PF, then create 1VF, send traffic from tester to VF1, 
in floating mode, check VF1 can't receive traffic from tester.

1. Start VM1 with VF1, see the prerequisite part.

2. In host, launch testpmd::

   ./testpmd -c 0x3 -n 4 -w 82:00.0,enable_floating_veb=1 -- -i 
   testpmd> set fwd mac
   testpmd> port start all
   testpmd> start
   testpmd> show port stats all
   

   In VM1, run testpmd:

   ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>show port info all    //get VF_mac_address
    testpmd>set fwd rxonly
    testpmd>start
    testpmd>show port stats all

   In tester, run scapy

   packet=Ether(dst="VF_mac_address")/IP()/UDP()/Raw('x'*20)
   sendp(packet,iface="enp132s0f0")
   
3. Check if VF1 can not get any packets, so tester->VF1 is not working.
4. Set "testpmd> port stop all" in step2 in Host, then run the test case 
   again. same result.PF can't receive any packets. 


Test Case4: Floating VEB VF can not communicate with legacy VEB VF 
==================================================================

Summary: DPDK PF, then create 4VFs and 4VMs, VF1,VF3,VF4, floating VEB; 
VF2, lagecy VEB. Make PF link down(the cable can be pluged out), 
VFs in VMs are running dpdk testpmd.
1. VF1 send traffic, and set the packet's DEST MAC to VF2, 
   check VF2 can not receive the packets. 
2. VF1 send traffic, and set the packet's DEST MAC to VF3, 
   check VF3 can receive the packets. 
3. VF4 send traffic, and set the packet's DEST MAC to VF3, 
   check VF3 can receive the packets.
4. VF2 send traffic, and set the packet's DEST MAC to VF1, 
   check VF1 can not receive the packets. 
Check Inter-VM VF-VF MAC switch when PF is link down as well as up.

Launch PF testpmd:: 
  ./testpmd -c 0x3 -n 4 
   -w "82:00.0,enable_floating_veb=1,floating_veb_list=0;2-3" -- -i

1. Start VM1 with VF1, VM2 with VF2, VM3 with VF3, 
   VM4 with VF4,see the prerequisite part.

2. In the host, run testpmd with floating parameters and make the link down::

   ./testpmd -c 0x3 -n 4 
    -w "82:00.0,enable_floating_veb=1,floating_veb_list=0;2-3" -- -i     
    //VF1 and VF3 in floating VEB, VF2 in legacy VEB
   
   testpmd> port stop all     
   //this step should be executed after vf running testpmd.
    
   testpmd> show port info all

3. VF1 send traffic, and set the packet's DEST MAC to VF2, 
   check VF2 can not receive the packets.

    In VM2, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>set fwd rxonly
    testpmd>mac_addr add 0 vf2_mac_address     //set the vf2_mac_address
    testpmd>start
    testpmd>show port stats all
   
    In VM1, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,vf2_mac_address
    testpmd>set fwd txonly
    testpmd>start
    testpmd>show port stats all

    Check VF2 can not get any packets, so VF1->VF2 is not working.

4. VF1 send traffic, and set the packet's DEST MAC to VF3, 
   check VF3 can receive the packets.

    In VM3, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>set fwd rxonly
    testpmd>show port info all     //get the vf3_mac_address
    testpmd>start
    testpmd>show port stats all

    In VM1, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,vf3_mac_address
    testpmd>set fwd txonly
    testpmd>start
    testpmd>show port stats all

 Check VF3 can get all the packets. Check the packet content is no corrupted.
 so VF1->VF2 is working.

5. VF2 send traffic, and set the packet's DEST MAC to VF1, 
   check VF1 can not receive the packets. 

    In VM1, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>set fwd rxonly
    testpmd>show port info all     //get the vf1_mac_address
    testpmd>start
    testpmd>show port stats all

    In VM2, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,vf1_mac_address
    testpmd>set fwd txonly
    testpmd>start
    testpmd>show port stats all

    Check VF1 can not get any packets, so VF2->VF1 is not working.

6. Set "testpmd> port start all" and "testpmd> start" in step2, 
   then run the step3-5 again. same result.


Test Case5: PF interaction with Floating VF and legacy VF 
=========================================================
DPDK PF, then create 2VFs, VF0 is in floating VEB, VF1 is in legacy VEB.
1. Send traffic from VF0 to PF, then check PF will not see any traffic;
2. Send traffic from VF1 to PF, then check PF will receive all the packets.
3. send traffic from tester to VF0, check VF0 can't receive traffic from 
   tester.
4. send traffic from tester to VF1, check VF1 can receive all the traffic 
   from tester.

1. In host, launch testpmd::

   ./testpmd -c 0x3 -n 4 
    -w 82:00.0,enable_floating_veb=1,floating_veb_list=0 -- -i
   testpmd> set fwd rxonly
   testpmd> port start all
   testpmd> start
   testpmd> show port stats all

3. In VF1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,pf_mac_addr
   testpmd>set fwd txonly
   testpmd>start
   testpmd>show port stats all

   Check PF can not get any packets, so VF1->PF is not working. 

4. In VF2, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,pf_mac_addr
   testpmd>set fwd txonly
   testpmd>start
   testpmd>show port stats all

   Check PF can get all the packets, so VF2->PF is working.

5. Set "testpmd> port stop all" in step2 in Host, 
   then run the test case again. same result.

6. In host, launch testpmd::

   ./testpmd -c 0x3 -n 4 
    -w 82:00.0,enable_floating_veb=1,floating_veb_list=0 -- -i   
   testpmd> set fwd mac
   testpmd> port start all
   testpmd> start
   testpmd> show port stats all
   

7. In VF1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>show port info all    //get VF1_mac_address
    testpmd>set fwd rxonly
    testpmd>start
    testpmd>show port stats all

   In tester, run scapy

   packet=Ether(dst="VF1_mac_address")/IP()/UDP()/Raw('x'*20)
   sendp(packet,iface="enp132s0f0")
   
   Check VF1 can not get any packets, so tester->VF1 is not working. 

8. In VF2, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>show port info all    //get VF2_mac_address
    testpmd>set fwd rxonly
    testpmd>start
    testpmd>show port stats all

   In tester, run scapy

   packet=Ether(dst="VF2_mac_address")/IP()/UDP()/Raw('x'*20)
   sendp(packet,iface="enp132s0f0")
   
   Check VF1 can get all the packets, so tester->VF2 is working.

5. Set "testpmd> port stop all" in step2 in Host, then run the test case again. 
   VF1 and VF2 cannot receive any packets. (because PF link down, 
   and PF can't receive any packets. so even if VF2 can't receive any packets.)

