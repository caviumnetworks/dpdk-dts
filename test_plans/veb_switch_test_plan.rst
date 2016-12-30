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


Test Case1: VEB Switching Inter VF-VF MAC switch
===================================================

Summary: Kernel PF, then create 2VFs. VFs running dpdk testpmd, send traffic 
to VF1, and set the packet's DEST MAC to VF2, check if VF2 can receive the 
packets. Check Inter VF-VF MAC switch.
 
Details::

1. In VF1, run testpmd::

   ./x86_64-native-linuxapp-gcc/app/testpmd -c 0x3 -n 4 --socket-mem 1024,1024
   -w 05:02.0 --file-prefix=test1 -- -i --crc-strip --eth-peer=0,00:11:22:33:44:12
   testpmd>set fwd mac
   testpmd>set promisc all off
   testpmd>start
   
   In VF2, run testpmd::

   ./x86_64-native-linuxapp-gcc/app/testpmd -c 0xa -n 4 --socket-mem 1024,1024
   -w 05:02.1 --file-prefix=test2 -- -i --crc-strip
   testpmd>set fwd mac
   testpmd>set promisc all off 
   testpmd>start

   
2. Send 100 packets to VF1's MAC address, check if VF2 can get 100 packets. 
Check the packet content is no corrupted.

Test Case2: VEB Switching Inter VF-VF MAC/VLAN switch
========================================================

Summary: Kernel PF, then create 2VFs, assign VF1 with VLAN=1 in, VF2 with 
VLAN=2. VFs are running dpdk testpmd, send traffic to VF1 with VLAN=1,
then let it forwards to VF2,it should not work since they are not in the 
same VLAN; set VF2 with VLAN=1, then send traffic to VF1 with VLAN=1, 
and VF2 can receive the packets. Check inter VF MAC/VLAN switch.

Details: 
1. Set the VLAN id of VF1 and VF2:: 

    ip link set ens785f0 vf 0 vlan 1
    ip link set ens785f0 vf 1 vlan 2 

2. In VF1, run testpmd::

   ./testpmd -c 0xf -n 4 --socket-mem 1024,1024 -w 0000:05:02.0 
   --file-prefix=test1 -- -i --crc-strip --eth-peer=0,00:11:22:33:44:12
   testpmd>set fwd mac
   testpmd>set promisc all off
   testpmd>start
   
   In VF2, run testpmd::

   ./testpmd -c 0xf0 -n 4 --socket-mem 1024,1024 -w 0000:05:02.1 
   --file-prefix=test2 -- -i --crc-strip
   testpmd>set fwd rxonly            
   testpmd>set promisc all off
   testpmd>start

   
4. Send 100 packets with VF1's MAC address and VLAN=1, check if VF2 can't 
   get 100 packets since they are not in the same VLAN.
 
5. Change the VLAN id of VF2::

    ip link set ens785f0 vf 1 vlan 1

6. Send 100 packets with VF1's MAC address and VLAN=1, check if VF2 can get 
   100 packets since they are in the same VLAN now. Check the packet 
   content is not corrupted::

   sendp([Ether(dst="00:11:22:33:44:11")/Dot1Q(vlan=1)/IP()
   /Raw('x'*40)],iface="ens785f1")


Test Case3: VEB Switching Inter PF-VF MAC switch
===================================================

Summary: DPDK PF, then create 1VF, PF in the host running dpdk testpmd, 
send traffic from PF to VF1, ensure PF->VF1(let VF1 in promisc mode); 
send traffic from VF1 to PF,ensure VF1->PF can work.

Details:

1. vf->pf
   In host, launch testpmd::

   ./testpmd -c 0x3 -n 4 -- -i 
   testpmd>set fwd rxonly
   testpmd>set promisc all off
   testpmd>start
   
   In VM1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,pf_mac_addr
   testpmd>set fwd txonly
   testpmd>set promisc all off
   testpmd>start

2. pf->vf
   In host, launch testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,vf1_mac_addr
   testpmd>set fwd txonly
   testpmd>set promisc all off
   testpmd>start

   In VM1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i
   testpmd>mac_addr add 0 vf1_mac_addr
   testpmd>set fwd rxonly
   testpmd>set promisc all off
   testpmd>start

3. tester->vf
   
4. Send 100 packets with PF's MAC address from VF, check if PF can get 
100 packets, so VF1->PF is working. Check the packet content is not corrupted. 

5. Send 100 packets with VF's MAC address from PF, check if VF1 can get 
100 packets, so PF->VF1 is working. Check the packet content is not corrupted. 

6. Send 100 packets with VF's MAC address from tester, check if VF1 can get 
100 packets, so tester->VF1 is working. Check the packet content is not 
corrupted.
 

Test Case4: VEB Switching Inter-VM PF-VF/VF-VF MAC switch Performance
=====================================================================

Performance testing, repeat Testcase1(VF-VF) and Testcase3(PF-VF) to check 
the performance at different sizes(64B--1518B and jumbo frame--3000B) 
with 100% rate sending traffic
