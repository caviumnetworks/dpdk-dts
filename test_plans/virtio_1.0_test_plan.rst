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

=================================
Virtio-1.0 Support Test Plan 
=================================

Virtio 1.0 is a new version of virtio. And the virtio 1.0 spec link is at  http://docs.oasis-open.org/virtio/virtio/v1.0/virtio-v1.0.pdf. The major difference is at PCI layout. For testing virtio 1.0 pmd, we need test the basic RX/TX, different path(txqflags), mergeable on/off, and also test with virtio0.95 to ensure they can co-exist. Besides, we need test virtio 1.0's performance to ensure it has similar performance as virtio0.95. 


Test Case1: test_func_vhost_user_virtio1.0-pmd with different txqflags 
======================================================================

Note: For virtio1.0 usage, we need use qemu version >2.4, such as 2.4.1 or 2.5.0.

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1.::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 0 --zero-copy 0 --vm2vm 0 

2. Start VM with 1 virtio, note: we need add "disable-modern=false" to enable virtio 1.0. 

    taskset -c 22-23 \
    /root/qemu-versions/qemu-2.5.0/x86_64-softmmu/qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/virtio-1.0/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,disable-modern=false \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -nographic


3. In the VM, change the config file--common_linuxapp, "CONFIG_RTE_LIBRTE_VIRTIO_DEBUG_INIT=y"; Run dpdk testpmd in VM::

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0 

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags 0x0f00 --disable-hw-vlan 
    
     $ >set fwd mac
    
     $ >start tx_first

    We expect similar output as below, and see modern virtio pci detected. 
 
    PMD: virtio_read_caps(): [98] skipping non VNDR cap id: 11
    PMD: virtio_read_caps(): [84] cfg type: 5, bar: 0, offset: 0000, len: 0
    PMD: virtio_read_caps(): [70] cfg type: 2, bar: 4, offset: 3000, len: 4194304
    PMD: virtio_read_caps(): [60] cfg type: 4, bar: 4, offset: 2000, len: 4096
    PMD: virtio_read_caps(): [50] cfg type: 3, bar: 4, offset: 1000, len: 4096
    PMD: virtio_read_caps(): [40] cfg type: 1, bar: 4, offset: 0000, len: 4096
    PMD: virtio_read_caps(): found modern virtio pci device.
    PMD: virtio_read_caps(): common cfg mapped at: 0x7f2c61a83000
    PMD: virtio_read_caps(): device cfg mapped at: 0x7f2c61a85000
    PMD: virtio_read_caps(): isr cfg mapped at: 0x7f2c61a84000
    PMD: virtio_read_caps(): notify base: 0x7f2c61a86000, notify off multiplier: 409                                                                                                                     6
    PMD: vtpci_init(): modern virtio pci detected.


4. Send traffic to virtio1(MAC1=52:54:00:00:00:01) with VLAN ID=1000. Check if virtio packet can be RX/TX and also check the TX packet size is same as the RX packet size.

5. Also run the dpdk testpmd in VM with txqflags=0xf01 for the virtio pmd optimization usage::

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags=0x0f01 --disable-hw-vlan 
    
     $ >set fwd mac
    
     $ >start tx_first

6. Send traffic to virtio1(MAC1=52:54:00:00:00:01) and VLAN ID=1000. Check if virtio packet can be RX/TX and also check the TX packet size is same as the RX packet size. Check the packet content is correct.

Test Case2: test_func_vhost_user_virtio1.0-pmd for packet sequence check
========================================================================

Note: For virtio1.0 usage, we need use qemu version >2.4, such as 2.4.1 or 2.5.0.

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1.::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 0 --zero-copy 0 --vm2vm 0 

2. Start VM with 1 virtio, note: we need add "disable-modern=false" to enable virtio 1.0. 

    taskset -c 22-23 \
    /root/qemu-versions/qemu-2.5.0/x86_64-softmmu/qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/virtio-1.0/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,disable-modern=false \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -nographic


3. In the VM, change the config file--common_linuxapp, "CONFIG_RTE_LIBRTE_VIRTIO_DEBUG_INIT=y"; Run dpdk testpmd in VM::

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0 

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags 0x0f00 --disable-hw-vlan 
    
     $ >set fwd mac
    
     $ >start tx_first

    We expect similar output as below, and see modern virtio pci detected. 
 
    PMD: virtio_read_caps(): [98] skipping non VNDR cap id: 11
    PMD: virtio_read_caps(): [84] cfg type: 5, bar: 0, offset: 0000, len: 0
    PMD: virtio_read_caps(): [70] cfg type: 2, bar: 4, offset: 3000, len: 4194304
    PMD: virtio_read_caps(): [60] cfg type: 4, bar: 4, offset: 2000, len: 4096
    PMD: virtio_read_caps(): [50] cfg type: 3, bar: 4, offset: 1000, len: 4096
    PMD: virtio_read_caps(): [40] cfg type: 1, bar: 4, offset: 0000, len: 4096
    PMD: virtio_read_caps(): found modern virtio pci device.
    PMD: virtio_read_caps(): common cfg mapped at: 0x7f2c61a83000
    PMD: virtio_read_caps(): device cfg mapped at: 0x7f2c61a85000
    PMD: virtio_read_caps(): isr cfg mapped at: 0x7f2c61a84000
    PMD: virtio_read_caps(): notify base: 0x7f2c61a86000, notify off multiplier: 409                                                                                                                     6
    PMD: vtpci_init(): modern virtio pci detected.


4. Send 100 packets at rate 25% at small packet(e.g: 70B) to the virtio with VLAN=1000, and insert the sequence number at byte offset 44 bytes. Make the sequence number starting from 00 00 00 00 and the step 1, first ensure no packet loss at IXIA, then check if the received packets have the same order as sending side.If out of order, then it's an issue.


Test Case3: test_func_vhost_user_virtio1.0-pmd with mergeable enabled
=====================================================================

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1.::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 1 --zero-copy 0 --vm2vm 0 

2. Start VM with 1 virtio, note: we need add "disable-modern=false" to enable virtio 1.0. 

    taskset -c 22-23 \
    /root/qemu-versions/qemu-2.5.0/x86_64-softmmu/qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/virtio-1.0/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,disable-modern=false \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -nographic


3. Run dpdk testpmd in VM::

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0 

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags 0x0f00 --disable-hw-vlan --max-pkt-len=9000
    
     $ >set fwd mac
    
     $ >start tx_first

4. Send traffic to virtio1(MAC1=52:54:00:00:00:01) with VLAN ID=1000. Check if virtio packet can be RX/TX and also check the TX packet size is same as the RX packet size. Check packet size(64-1518) as well as the jumbo frame(3000,9000) can be RX/TX.


Test Case4: test_func_vhost_user_one-vm-virtio1.0-one-vm-virtio0.95
===================================================================

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1.::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 0 --zero-copy 0 --vm2vm 1 

2. Start VM1 with 1 virtio, note: we need add "disable-modern=false" to enable virtio 1.0. 

    taskset -c 22-23 \
    /root/qemu-versions/qemu-2.5.0/x86_64-softmmu/qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/virtio-1.0/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,disable-modern=false \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -nographic

3. Start VM2 with 1 virtio, note: 

    taskset -c 24-25 \
    /root/qemu-versions/qemu-2.5.0/x86_64-softmmu/qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm2.img  \
     -chardev socket,id=char0,path=/home/qxu10/virtio-1.0/dpdk/vhost-net -netdev type=vhost-user,id=mynet2,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:02,netdev=mynet2,disable-modern=true \
     -netdev tap,id=ipvm2,ifname=tap4,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm2,id=net1,mac=00:00:00:00:10:02 -nographic

3. Run dpdk testpmd in VM1 and VM2::

     VM1:     

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0 

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags 0x0f00 --disable-hw-vlan --eth-peer=0,52:54:00:00:00:02 
    
     $ >set fwd mac
    
     $ >start tx_first

     VM2: 

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0 

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags 0x0f00 --disable-hw-vlan 
    
     $ >set fwd mac
    
     $ >start tx_first

4. Send 100 packets at low rate to virtio1, and the expected flow is ixia-->NIC-->VHOST-->Virtio1-->Virtio2-->Vhost-->NIC->ixia port. Check the packet back at ixia port is content correct, no size change and payload change. 

Test Case5: test_perf_vhost_user_one-vm-virtio1.0-pmd
=====================================================

Note: For virtio1.0 usage, we need use qemu version >2.4, such as 2.4.1 or 2.5.0.

1. Launch the Vhost sample by below commands, socket-mem is set for the vhost sample to use, need ensure that the PCI port located socket has the memory. In our case, the PCI BDF is 81:00.0, so we need assign memory for socket1.::

    taskset -c 18-20 ./examples/vhost/build/vhost-switch -c 0x1c0000 -n 4 --huge-dir /mnt/huge --socket-mem 0,2048 -- -p 1 --mergeable 0 --zero-copy 0 --vm2vm 0 

2. Start VM with 1 virtio, note: we need add "disable-modern=false" to enable virtio 1.0. 

    taskset -c 22-23 \
    /root/qemu-versions/qemu-2.5.0/x86_64-softmmu/qemu-system-x86_64 -name us-vhost-vm1 \
     -cpu host -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on -numa node,memdev=mem -mem-prealloc \
     -smp cores=2,sockets=1 -drive file=/home/img/vm1.img  \
     -chardev socket,id=char0,path=/home/qxu10/virtio-1.0/dpdk/vhost-net -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce \
     -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,disable-modern=false \
     -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -nographic


3. In the VM, run dpdk testpmd in VM::

     ./<dpdk_folder>/tools/dpdk_nic_bind.py --bind igb_uio 00:03.0 

     ./<dpdk_folder>/x86_64-native-linuxapp-gcc/app/test-pmd/testpmd -c 0x3 -n 4 -- -i --txqflags 0x0f00 --disable-hw-vlan 
    
     $ >set fwd mac
    
     $ >start tx_first

4. Send traffic at line rate to virtio1(MAC1=52:54:00:00:00:01) with VLAN ID=1000. Check the performance at different packet size(68,128,256,512,1024,1280,1518) and record it as the performance data. The result should be similar as virtio0.95. 