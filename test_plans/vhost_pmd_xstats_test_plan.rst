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

================
Vhost PMD xstats
================

This test plan will cover the basic vhost pmd xstats case and will be worked 
as a regression test plan. In the test plan, we will use vhost as a pmd port 
in testpmd. 

Test Case1: xstats based on packet size
=======================================

flow: 
TG-->NIC-->>Vhost TX-->Virtio RX-->Virtio TX-->Vhsot RX-->NIC-->TG

1. Bind one physical port to igb_uio, then launch the testpmd

2. Launch VM1 with using hugepage, 2048M memory, 2 cores, 
   1 cockets ,1 virtio-net-pci::
    taskset -c 6-7 qemu-system-x86_64 -name us-vhost-vm1 -cpu host -enable-kvm 
    -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,
    share=on -numa node,memdev=mem -mem-prealloc -smp cores=2,sockets=1 -drive 
    file=/home/osimg/ubuntu16.img -chardev socket,id=char0,path=./vhost-net 
    -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce,queues=1 
    -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,mrg_rxbuf=off,mq=on 
    -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,
    netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -localtime -vnc :10 -daemonize
   
3. On VM1, run testpmd

4. On host, testpmd, set ports to the mac forward mode
   
    testpmd>set fwd mac
    testpmd>start tx_first

5. On VM, testpmd, set port to the mac forward mode
   
    testpmd>set fwd mac
    testpmd>start
	
6. On host run "show port xstats all" at least twice to check the packets number

7. Let TG generate different size of packets, send 10000 packets for each packet 
   sizes(64,128,255, 512, 1024, 1523), check the statistic number is correct

8. On host run "clear port xstats all" , then all the statistic date should be 0

Test Case2: xstats based on packet types
========================================

Similar as Test Case1, all steps are similar except step6,7: 
 
6. On host run "show port xstats all" at least twice to check the packets type:

7. Let TG generate different type of packets, broadcast, multicast, ucast, check 
   the statistic number is correct 

8. On host run "clear port xstats all" , then all the statistic date should be 0

Test Case3: stability case with multiple queues
===============================================
1. No need bind any physical port to igb_uio,then launch the testpmd

2. Launch VM1, set queues=2, vectors=2xqueues+2, mq=on, with using hugepage,
   2048M memory, 2 cores, 1 cockets ,1 virtio-net-pci::
    taskset -c 6-7 qemu-system-x86_64 -name us-vhost-vm1 -cpu host -enable-kvm 
    -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,\
    share=on -numa node,memdev=mem -mem-prealloc \
    -smp cores=2,sockets=1 -drive file=/home/osimg/ubuntu16.img  \
    -chardev socket,id=char0,path=./vhost-net \
    -netdev type=vhost-user,id=mynet1,chardev=char0,vhostforce,queues=1 \
    -device virtio-net-pci,mac=52:54:00:00:00:01,netdev=mynet1,mrg_rxbuf=off,mq=on \
    -netdev tap,id=ipvm1,ifname=tap3,script=/etc/qemu-ifup -device rtl8139,
    netdev=ipvm1,id=net0,mac=00:00:00:00:10:01 -localtime -vnc :10 -daemonize

3. On VM1, run testpmd

4. On host, testpmd, set ports to the mac forward mode
   
    testpmd>set fwd io retry
    testpmd>start tx_first 8

5. On VM, testpmd, set port to the mac forward mode
   
    testpmd>start

6. Send packets for 30 minutes, check the Xstatsa still can work correctly
   testpmd>show port xstats all
	


	


