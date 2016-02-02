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

VF to VF Bridge testplan
========================
This test suite aims to validate the bridge function on physical functional
for virtual functional to virtual functional communication. Cases of the
suite based on the vm to vm test scenario, echo vm needs on vf, and both of
the vfs generated from the same pf port.

Prerequisites:
==============

On host:

        Hugepages: at least 10 G hugepages, 6G(for vm on which run pktgen as stream source end) + 2G(for vm on which run testpmd as receive end) + 2G(for host used)

        Guset: two img with os for kvm qemu

        NIC: one pf port

        pktgen-dpdk: copy $DTS/dep/tgen.tgz to guest from which send the stream

On Guest:

        Stream Source end: scapy pcpay and essential tarballs for compile pktgen-dpdk tools


Set up basic virtual scenario:
==============================

step 1: generate two vfs on the target pf port (i.e. 0000:85:00.0):

        echo 2 > /sys/bus/pci/devices/0000\:85\:00.0/sriov_numvfs

step 2: bind the two vfs to pci-stub:

        echo "8086 10ed" > /sys/bus/pci/drivers/pci-stub/new_id
        echo 0000:85:10.0 > /sys/bus/pci/devices/0000:85:10.0/driver/unbind
        echo 0000:85:10.0 > /sys/bus/pci/drivers/pci-stub/bind
        echo 0000:85:10.2 > /sys/bus/pci/devices/0000:85:10.2/driver/unbind
        echo 0000:85:10.2 > /sys/bus/pci/drivers/pci-stub/bind

step 3: passthrough vf 0 to vm0 and start vm0:

        taskset -c 20,21,22,23 /usr/local/qemu-2.4.0/x86_64-softmmu/qemu-system-x86_64 \
        -name vm0 -enable-kvm -chardev socket,path=/tmp/vm0_qga0.sock,server,nowait,id=vm0_qga0 \
        -device virtio-serial -device virtserialport,chardev=vm0_qga0,name=org.qemu.guest_agent.0 \
        -daemonize -monitor unix:/tmp/vm0_monitor.sock,server,nowait \
        -net nic,vlan=0,macaddr=00:00:00:e2:4f:fb,addr=1f \
        -net user,vlan=0,hostfwd=tcp:10.239.128.125:6064-:22 \
        -device pci-assign,host=85:10.0,id=pt_0 -cpu host -smp 4 -m 6144 \
        -object memory-backend-file,id=mem,size=6144M,mem-path=/mnt/huge,share=on \
        -numa node,memdev=mem -mem-prealloc -drive file=/home/img/vm0.img -vnc :4

step 4: passthrough vf 1 to vm1 and start vm1:

        taskset -c 30,31,32,33 /usr/local/qemu-2.4.0/x86_64-softmmu/qemu-system-x86_64  \
        -name vm1 -enable-kvm -chardev socket,path=/tmp/vm1_qga0.sock,server,nowait,id=vm1_qga0 \
        -device virtio-serial -device virtserialport,chardev=vm1_qga0,name=org.qemu.guest_agent.0 \
        -daemonize -monitor unix:/tmp/vm1_monitor.sock,server,nowait \
        -net nic,vlan=0,macaddr=00:00:00:7b:d5:cb,addr=1f \
        -net user,vlan=0,hostfwd=tcp:10.239.128.125:6126-:22 \
        -device pci-assign,host=85:10.2,id=pt_0 -cpu host -smp 4 -m 6144 \
        -object memory-backend-file,id=mem,size=6144M,mem-path=/mnt/huge,share=on \
        -numa node,memdev=mem -mem-prealloc -drive file=/home/img/vm1.img -vnc :5


Test Case1: test_2vf_d2d_pktgen_stream
===========================================
both vfs in the two vms using the dpdk driver, send stream from vf1 in vm1 by dpdk pktgen
to vf in vm0, and verify the vf on vm0 can receive stream.

step 1: run testpmd on vm0:

        ./x86_64-native-linuxapp-gcc/app/testpmd -c 0x7 -n 1  -- -i  --txqflags=0

step 2: set rxonly and start on vm0:

        set fwd rxonly
        start

step 3: copy pktgen-dpdk tarball to vm1:

        scp tgen.tgz to vm1
        tar xvf tgen.tgz

step 4: generate pcap file on vm1:

        Context: [Ether(dst="52:54:12:45:67:10", src="52:54:12:45:67:11")/IP()/Raw(load='X'\*46)]

step 5: send stream by pkt-gen on vm1:

        ./app/app/x86_64-native-linuxapp-gcc/app/pktgen -c 0xf -n 2 --proc-type auto -- -P -T -m '1.0' -s P:flow.pcap

step 6: verify vf 0 receive status on vm0: Rx-packets equal to send packets count, 100

        show port stats 0
        ######################## NIC statistics for port 0  ########################
        RX-packets: 100  RX-missed: 0          RX-bytes:  6000
        RX-errors: 0
        RX-nombuf:  0   
        TX-packets: 0          TX-errors: 0          TX-bytes:  0
        ############################################################################

Test Case2: test_2vf_d2k_pktgen_stream
======================================
step 1: bind vf to kernel driver on vm0

step 2: start up vf interface and using tcpdump to capature received packets

step 3: copy pktgen-dpdk tarball to vm1:

        scp tgen.tgz to vm1
        tar xvf tgen.tgz

step 4: generate pcap file on vm1:

        Context: [Ether(dst="52:54:12:45:67:10", src="52:54:12:45:67:11")/IP()/Raw(load='X'\*46)]

step 5: send stream by pkt-gen on vm1:

        ./app/app/x86_64-native-linuxapp-gcc/app/pktgen -c 0xf -n 2 --proc-type auto -- -P -T -m '1.0' -s P:flow.pcap

step 6: verify vf 0 receive status on vm0: Rx-packets equal to send packets count, 100

Test Case3: test_2vf_k2d_scapy_stream
======================================
step 1: run testpmd on vm0:

        ./x86_64-native-linuxapp-gcc/app/testpmd -c 0x7 -n 1  -- -i  --txqflags=0

step 2: set rxonly and start on vm0:

        set fwd rxonly
        start

step 3: bind vf to kernel driver on vm0

step 4: using scapy to send packets

step 5:verify vf 0 receive status on vm0: Rx-packets equal to send packets count, 100

        show port stats 0
        ######################## NIC statistics for port 0  ########################
        RX-packets: 100  RX-missed: 0          RX-bytes:  6000
        RX-errors: 0
        RX-nombuf:  0
        TX-packets: 0          TX-errors: 0          TX-bytes:  0
        ############################################################################
