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

===================
Vhost TSO Test Plan 
===================

The feature enabled the DPDK Vhost TX offload(checksum and TSO), so that it will let the NIC to do the TX offload, and it can improve performance. The feature added the negotiation between DPDK user space vhost and virtio-net, so we will verify the DPDK Vhost user + virtio-net for the TSO/cksum in the TCP/IP stack enabled environment. DPDK vhost + virtio-pmd will not be covered by this plan since virtio-pmd doesn't have TCP/IP stack and virtio TSO is not enabled, so it will not be tested. 

In the test plan, we will use vhost switch sample to test. 
When testing vm2vm case, we will only test vm2vm=1(software switch), not test vm2vm=2(hardware switch). 

Prerequisites: 
==============

Install iperf on both host and guests. 


Test Case1: DPDK vhost user + virtio-net one VM fwd tso
=======================================================

HW preparation: Connect 2 ports directly. In our case, connect 81:00.0(port1) and 81:00.1(port2) two ports directly. Port1 is binded to igb_uio for vhost-sample to use, while port2 is in kernel driver. 

SW preparation: Change one line of the vhost sample and rebuild::

    #In function virtio_tx_route(xxx)
    m->vlan_tci = vlan_tag; 
    #changed to 
    m->vlan_tci = 1000;

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1. For TSO/CSUM test, we need set "--mergeable 1--tso 1 --csum 1".::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 1 --zero-copy 0 --vm2vm 0 --tso 1 --csum 1

2. Launch VM1::

    taskset -c 21-22 \
    qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 1024 -object memory-backend-file,id=mem,size=1024M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/dpdk-vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/vhost-tso-test/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,csum=on,gso=on,guest_csum=on,guest_tso4=on,guest_tso6=on,guest_ecn=on  \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:10:00:00:11:01 -nographic

3. On host,configure port2, then you can see there is a interface called ens260f1.1000.::
   
    ifconfig ens260f1
    vconfig add ens260f1 1000
    ifconfig ens260f1.1000 1.1.1.8

4. On the VM1, set the virtio IP and run iperf::

    ifconfig ethX 1.1.1.2
    ping 1.1.1.8 # let virtio and port2 can ping each other successfully, then the arp table will be set up automatically. 
    
5. In host, run : `iperf -s -i 1` ; In guest, run `iperf -c 1.1.1.2 -i 1 -t 60`, check if there is 64K (size: 65160) packet. If there is 64K packet, then TSO is enabled, or else TSO is disabled.  

6. On the VM1, run `tcpdump -i ethX -n -e -vv` to check if the cksum is correct. You should not see incorrect cksum output.

Test Case2: DPDK vhost user + virtio-net VM2VM=1 fwd tso
========================================================

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1. For TSO/CSUM test, we need set "--mergeable 1--tso 1 --csum 1 --vm2vm 1".::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 1 --zero-copy 0 --vm2vm 1 --tso 1 --csum 1

2. Launch VM1 and VM2. ::

    taskset -c 21-22 \
    qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 1024 -object memory-backend-file,id=mem,size=1024M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/dpdk-vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/vhost-tso-test/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,csum=on,gso=on,guest_csum=on,guest_tso4=on,guest_tso6=on,guest_ecn=on  \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:10:00:00:11:01 -nographic

    taskset -c 23-24 \
    qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 1024 -object memory-backend-file,id=mem,size=1024M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm1.img  \
     -chardev socket,id=char1,path=/home/qxu10/vhost-tso-test/dpdk/vhost-net -netdev type=vhost-user,id=mynet2,chardev=char1,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:02,netdev=mynet2  \
     -netdev tap,id=ipvm1,ifname=tap4,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:10:00:00:11:02 -nographic

3. On VM1, set the virtio IP and run iperf

    ifconfig ethX 1.1.1.2
    arp -s 1.1.1.8 52:54:00:00:00:02
    arp # to check the arp table is complete and correct. 

4. On VM2, set the virtio IP and run iperf

    ifconfig ethX 1.1.1.8
    arp -s 1.1.1.2 52:54:00:00:00:01
    arp # to check the arp table is complete and correct. 
 
5. Ensure virtio1 can ping virtio2. Then in VM1, run : `iperf -s -i 1` ; In VM2, run `iperf -c 1.1.1.2 -i 1 -t 60`, check if there is 64K (size: 65160) packet. If there is 64K packet, then TSO is enabled, or else TSO is disabled.  

6. On the VM1, run `tcpdump -i ethX -n -e -vv`. 

    
