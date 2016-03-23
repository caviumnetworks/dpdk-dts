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

IEEE EVB tutorial: http://www.ieee802.org/802_tutorials/2009-11/evb-tutorial-draft-20091116_v09.pdf

Virtual Ethernet Bridge (VEB) - This is an IEEE EVB term. A VEB is a VLAN Bridge internal to Fortville that bridges the traffic of multiple VSIs over an internal virtual network. 

Virtual Ethernet Port Aggregator (VEPA) - This is an IEEE EVB term. A VEPA multiplexes the traffic of one or more VSIs onto a single Fortville Ethernet port. The biggest difference between a VEB and a VEPA is that a VEB can switch packets internally between VSIs, whereas a VEPA cannot. 

Virtual Station Interface (VSI) - This is an IEEE EVB term that defines the properties of a virtual machine's (or a physical machine's) connection to the network. Each downstream v-port on a Fortville VEB or VEPA defines a VSI. A standards-based definition of VSI properties enables network management tools to perform virtual machine migration and associated network re-configuration in a vendor-neutral manner.

My understanding of VEB is that it's an in-NIC switch(MAC/VLAN), and it can support VF->VF, PF->VF, VF->PF packet forwarding according to the NIC internal switch. It's similar as Niantic's SRIOV switch.

Floating VEB Introduction
=========================

Floating VEB is based on VEB Switching. It will address 2 problems:

Dependency on PF: When the physical port is link down, the functionality of the VEB/VEPA will not work normally. Even only data forwarding between the VF is required, one PF port will be wasted to create the related VEB.

Ensure all the traffic from VF can only forwarding within the VFs connect to the floating VEB, cannot forward out of the NIC port.

Prerequisites for VEB testing
=============================

1. Get the pci device id of DUT, for example::

    ./dpdk_nic_bind.py --st

    0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
    
2.1  Host PF in kernel driver. Create 2 VFs from 1 PF with kernel driver, and set the VF MAC address at PF0::

    echo 2 > /sys/bus/pci/devices/0000\:81\:00.0/sriov_numvfs
    ./dpdk_nic_bind.py --st

    0000:81:02.0 'XL710/X710 Virtual Function' unused=
    0000:81:02.1 'XL710/X710 Virtual Function' unused=

    ip link set ens259f0 vf 0 mac 00:11:22:33:44:11
    ip link set ens259f0 vf 1 mac 00:11:22:33:44:12

2.2  Host PF in DPDK driver. Create 2VFs from 1 PF with dpdk driver. 
    
    ./dpdk_nic_bind.py -b igb_uio 81:00.0 
    echo 2 >/sys/bus/pci/devices/0000:81:00.0/max_vfs
    ./dpdk_nic_bind.py --st

3. Detach VFs from the host, bind them to pci-stub driver::

    modprobe pci-stub

    using `lspci -nn|grep -i ethernet` got VF device id, for example "8086 154c",

    echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
    echo 0000:81:02.0 > /sys/bus/pci/devices/0000:08:02.0/driver/unbind
    echo 0000:81:02.0 > /sys/bus/pci/drivers/pci-stub/bind

    echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
    echo 0000:81:02.1 > /sys/bus/pci/devices/0000:08:02.1/driver/unbind
    echo 0000:81:02.1 > /sys/bus/pci/drivers/pci-stub/bind

4. Lauch the VM with the VF PCI passthrough. 

    taskset -c 18-19 qemu-system-x86_64 \
     -mem-path /mnt/huge -mem-prealloc \
     -enable-kvm -m 2048 -smp cores=2,sockets=1 -cpu host -name dpdk1-vm1 \
     -device pci-assign,host=81:02.0 \
     -drive file=/home/img/vm1.img \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:00:00:00:11:01 \
     -localtime -vnc :22 -daemonize
 

Test Case1: VEB Switching Inter-VM VF-VF MAC switch
===================================================

Summary: Kernel PF, then create 2VFs and 2VMs, assign one VF to one VM, say VF1 in VM1, VF2 in VM2. VFs in VMs are running dpdk testpmd, send traffic to VF1, and set the packet's DEST MAC to VF2, check if VF2 can receive the packets. Check Inter-VM VF-VF MAC switch.

Details::

1. Start VM1 with VF1, VM2 with VF2, see the prerequisite part. 
2. In VM1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,00:11:22:33:44:12
   testpmd>set mac fwd
   testpmd>set promisc off all
   testpmd>start
   
   In VM2, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i 
   testpmd>set mac fwd
   testpmd>set promisc off all
   testpmd>start

   
3. Send 100 packets to VF1's MAC address, check if VF2 can get 100 packets. Check the packet content is not corrupted.

Test Case2: VEB Switching Inter-VM VF-VF MAC/VLAN switch
========================================================

Summary: Kernel PF, then create 2VFs and 2VMs, assign VF1 with VLAN=1 in VM1, VF2 with VLAN=2 in VM2. VFs in VMs are running dpdk testpmd, send traffic to VF1 with VLAN=1, then let it forwards to VF2, it should not work since they are not in the same VLAN; set VF2 with VLAN=1, then send traffic to VF1 with VLAN=1, and VF2 can receive the packets. Check inter-VM VF-VF MAC/VLAN switch.

Details: 

1. Start VM1 with VF1, VM2 with VF2, see the prerequisite part. 

2. Set the VLAN id of VF1 and VF2:: 

    ip link set ens259f0 vf 0 vlan 1
    ip link set ens259f0 vf 1 vlan 2 

3. In VM1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,00:11:22:33:44:12
   testpmd>set mac fwd
   testpmd>set promisc all off
   testpmd>start
   
   In VM2, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i 
   testpmd>set mac fwd
   testpmd>set promisc all off
   testpmd>start

   
4. Send 100 packets with VF1's MAC address and VLAN=1, check if VF2 can't get 100 packets since they are not in the same VLAN.
 
5. Change the VLAN id of VF2::

    ip link set ens259f0 vf 1 vlan 1

6. Send 100 packets with VF1's MAC address and VLAN=1, check if VF2 can get 100 packets since they are in the same VLAN now. Check the packet content is not corrupted. 

Test Case3: VEB Switching Inter-VM PF-VF MAC switch
===================================================

Summary: DPDK PF, then create 1VF, assign VF1 to VM1, PF in the host running dpdk traffic, send traffic from PF to VF1, ensure PF->VF1(let VF1 in promisc mode); send traffic from VF1 to PF, ensure VF1->PF can work.

Details:

1. Start VM1 with VF1, see the prerequisite part. 

3. In host, launch testpmd::

   ./testpmd -c 0xc0000 -n 4 -- -i 
   testpmd>set mac fwd
   testpmd>set promisc all on
   testpmd>start
   
   In VM1, run testpmd::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,pf_mac_addr (Note: this will let VF1 forwards packets to PF)
   testpmd>set mac fwd
   testpmd>set promisc all on
   testpmd>start
   
4. Send 100 packets with VF1's MAC address, check if PF can get 100 packets, so VF1->PF is working. Check the packet content is not corrupted. 

5. Remove "--eth-peer" in VM1 testpmd commands, then send 100 packets with PF's MAC address, check if VF1 can get 100 packets, so PF->VF1 is working. Check the packet content is not corrupted. 
 

Test Case4: VEB Switching Inter-VM PF-VF/VF-VF MAC switch Performance
=====================================================================

Performance testing, repeat Testcase1(VF-VF) and Testcase3(PF-VF) to check the performance at different sizes(64B--1518B and jumbo frame--3000B) with 100% rate sending traffic.

Test Case5: Floating VEB Inter-VM VF-VF 
=======================================

Summary: DPDK PF, then create 2VFs and 2VMs, assign one VF to one VM, say VF1 in VM1, VF2 in VM2, and make PF link down(the cable can be pluged out). VFs in VMs are running dpdk testpmd, send traffic to VF1, and set the packet's DEST MAC to VF2, check if VF2 can receive the packets. Check Inter-VM VF-VF MAC switch when PF is link down as well as up.

Details: 

1. Start VM1 with VF1, VM2 with VF2, see the prerequisite part. 
2. In the host, run testpmd with floating parameters and make the link down::

    ./testpmc -c 0xc0000 -n 4 --floating -- -i
    testpmd> port stop all
    testpmd> show port info all

3. In VM1, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,00:11:22:33:44:12
    testpmd>set mac fwd
    testpmd>set promisc off all
    testpmd>start
   
   In VM2, run testpmd::

    ./testpmd -c 0x3 -n 4 -- -i 
    testpmd>set mac fwd
    testpmd>set promisc off all
    testpmd>start

   
4. Send 100 packets to VF1's MAC address, check if VF2 can get 100 packets. Check the packet content is not corrupted. Also check the PF's port stats, and there should be no packets RX/TX at PF port. 

5. In the host, run testpmd with floating parameters and keep the link up, then do step3 and step4, PF should have no RX/TX packets even when link is up::
   
    ./testpmc -c 0xc0000 -n 4 --floating -- -i
    testpmd> port start all
    testpmd> show port info all
    

Test Case6: Floating VEB Inter-VM VF traffic can't be out of NIC
================================================================

DPDK PF, then create 1VF, assign VF1 to VM1, send traffic from VF1 to outside world, then check outside world will not see any traffic.

Details: 

1. Start VM1 with VF1, see the prerequisite part. 
2. In the host, run testpmd with floating parameters.

   ./testpmc -c 0xc0000 -n 4 --floating -- -i

3. In VM1, run testpmd, ::

   ./testpmd -c 0x3 -n 4 -- -i --eth-peer=0,pf_mac_addr
   testpmd>set fwd txonly
   testpmd>start
   
  
4. At PF side, check the port stats to see if there is any RX/TX packets, and also check the traffic generator side(e.g: IXIA ports or another port connected to the DUT port) to ensure no packets. 


Test Case7: Floating VEB VF-VF Performance
==========================================

Testing VF-VF performance at different sizes(64B--1518B and jumbo frame--3000B) with 100% rate sending traffic.