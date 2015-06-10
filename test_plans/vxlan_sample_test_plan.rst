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
   "AS IS" AND ANY EXPR   ESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
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

============
Vxlan Sample
============
Vxlan sample simulates a VXLAN Tunnel Endpoint (VTEP) termination in DPDK.
It is used to demonstrate the offload and filtering capabilities of i40 NIC
for VXLAN packet.

Vxlan sample uses the basic virtio devices management function from vHOST 
example, and the US-vHost interface and tunnel filtering mechanism to direct 
the traffic to/from a specific VM.

Vxlan sample is also designed to show how tunneling protocols can be handled. 

Prerequisites
=============
1x Intel® X710 (Fortville) NICs (2x 40GbE full duplex optical ports per NIC)
plugged into the available PCIe Gen3 8-lane slot.

2x Intel® XL710-DA4 (Eagle Fountain) (1x 10GbE full duplex optical ports per NIC)
plugged into the avaiable PCIe Gen3 8-lane slot.

DUT board must be two sockets system and each cpu have more than 8 lcores.

Update qemu-system-x86_64 to version 2.2.0 which support hugepage based memory.
Prepare vhost-use requested modules::

    modprobe fuse
    modprobe cuse
    insmod lib/librte_vhost/eventfd_link/eventfd_link.ko

Allocate 4096*2M hugepages for vm and dpdk::

    echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

Test Case: Vxlan Sample Encap packet
====================================
Start vxlan sample with only encapsulation enable::

    tep_termination -c 0xf -n 3 --socket-mem 2048,2048 -- -p 0x1 \
        --udp-port 4789 --nb-devices 2 --filter-type 3 --tx-checksum 0 \
        --encap 1 --decap 0

Wait for vhost-net socket device created and message dumped::

    VHOST_CONFIG: bind to vhost-net

Start virtual machine with hugepage based memory and two vhost-user devices::

    qemu-system-x86_64 -name vm0 -enable-kvm -daemonize \
      -cpu host -smp 4 -m 4096 \
      -object memory-backend-file,id=mem,size=4096M,mem-path=/mnt/huge,share=on \
      -numa node,memdev=mem -mem-prealloc \
      -chardev socket,id=char0,path=./dpdk/vhost-net \
      -netdev type=vhost-user,id=netdev0,chardev=char0,vhostforce \
      -device virtio-net-pci,netdev=netdev0,mac=00:00:20:00:00:20 \
      -chardev socket,id=char1,path=./dpdk/vhost-net \
      -netdev type=vhost-user,id=netdev1,chardev=char1,vhostforce \
      -device virtio-net-pci,netdev=netdev1,mac=00:00:20:00:00:21 \
      -drive file=/storage/vm-image/vm0.img -vnc :1
Login into virtual machine and start testpmd with additional arguments::

    testpmd -c f -n 3 -- -i --txqflags=0xf00 --disable-hw-vlan

Start packet forward of testpmd and transit several packets for mac learning::

    testpmd> set fwd mac
    testpmd> start tx_first

Make sure virtIO port registered normally::

    VHOST_CONFIG: virtio is now ready for processing.
    VHOST_DATA: (1) Device has been added to data core 56
    VHOST_DATA: (1) MAC_ADDRESS 00:00:20:00:00:21 and VNI 1000 registered
    VHOST_DATA: (0) MAC_ADDRESS 00:00:20:00:00:20 and VNI 1000 registered

Send normal udp packet to PF device and packet dmac match PF device 
Verify packet has been recevied in virtIO port0 and forwarded by port1::

      testpmd> show port stats all

Verify encapsulated packet received on PF device

Test Case: Vxlan Sample Decap packet
====================================
Start vxlan sample with only de-capsulation enable::

  tep_termination -c 0xf -n 3 --socket-mem 2048,2048 -- -p 0x1 \
    --udp-port 4789 --nb-devices 2 --filter-type 3 --tx-checksum 0 \
    --encap 0 --decap 1

Start vhost-user test environment like case vxlan_sample_encap.

Send vxlan packet Ether(dst=PF mac)/IP/UDP/vni(1000)/
  Ether(dst=virtIO port0)/IP/UDP to PF device::

Verify that packet received by virtIO port0 and forwarded by virtIO port1::

  testpmd> show port stats all

Verify that PF received packet just the same as inner packet

Send vxlan packet Ether(dst=PF mac)/IP/UDP/vni(1000)/
    Ether(dst=virtIO port1)/IP/UDP to PF device

Verify that packet received by virtIO port1 and forwarded by virtIO port0::

  testpmd> show port stats all  

Make sure PF received packet received inner packet with mac reversed.

Test Case: Vxlan Sample Encap and Decap
=======================================
Start vxlan sample with only de-capsulation enable::

  tep_termination -c 0xf -n 3 --socket-mem 2048,2048 -- -p 0x1 \
    --udp-port 4789 --nb-devices 2 --filter-type 3 --tx-checksum 0 \
    --encap 1 --decap 1

Start vhost-user test environment like case vxlan_sample_encap

Send vxlan packet Ether(dst=PF mac)/IP/UDP/vni(1000)/
  Ether(dst=virtIO port0)/IP/UDP to PF device

Verify that packet received by virtIO port0 and forwarded by virtIO port1::

  testpmd> show port stats all

Verify encapsulated packet received on PF device.
Verify that inner packet src and dst mac address have been conversed.

Test Case: Vxlan Sample Checksum
================================
Start vxlan sample with only decapsulation enable::

  tep_termination -c 0xf -n 3 --socket-mem 2048,2048 -- -p 0x1 \
    --udp-port 4789 --nb-devices 2 --filter-type 3 --tx-checksum 1 \
    --encap 1 --decap 1

Start vhost-user test environment like case vxlan_sample_encap

Send vxlan packet with Ether(dst = PF mac)/IP/UDP/vni(1000)/ 
  Ether(dst = virtIO port0)/IP wrong chksum/ UDP wrong chksum

Verify that packet recevied by virtIO port0 and forwarded by virtIO port1::

  testpmd> show port stats all

Verify encapsulated packet received on PF device.
Verify that inner packet src and dst mac address have been conversed.
Verify that inner packet ip checksum and udp checksum were corrected.

Send vxlan packet with Ether(dst = PF mac)/IP/UDP/vni(1000)/ 
  Ether(dst = virtIO port0)/IP wrong chksum/ TCP wrong chksum

Verify that packet recevied by virtIO port0 and forwarded by virtIO port1::

  testpmd> show port stats all

Verify encapsulated packet received on PF device.
Verify that inner packet src and dst mac address have been conversed.
Verify that inner packet ip checksum and tcp checksum were corrected.

Send vxlan packet with Ether(dst = PF mac)/IP/UDP/vni(1000)/ 
  Ether(dst = virtIO port0)/IP wrong chksum/ SCTP wrong chksum

Verify that packet received by virtIO port0 and forwarded by virtIO port1::

  testpmd> show port stats all

Verify encapsulated packet received on PF device.
Verify that inner packet src and dst mac address have been conversed.
Verify that inner packet ip checksum and sctp checksum were corrected.

Test Case: Vxlan Sample TSO
===========================
Start vxlan sample with tso enable, tx checksum must enable too.
For hardware limitation, tso segment size must be larger 256::

  tep_termination -c 0xf -n 3 --socket-mem 2048,2048 -- -p 0x1 \
    --udp-port 4789 --nb-devices 2 --filter-type 3 --tx-checksum 1 \
    --encap 1 --decap 1 --tso-segsz 256

Start vhost-user test environment like case vxlan_sample_encap

Send vxlan packet with Ether(dst = PF mac)/IP/UDP/vni(1000)/ 
  Ether(dst = virtIO port0)/TCP/892 Bytes data, total length will be 1000

Verify that packet recevied by virtIO port0 and forwarded by virtIO port1::

  testpmd> show port stats all

Verify that four separated vxlan packets received on PF devices.
Make sure tcp packet payload is 256, 256, 256 and 124.

Test Case: Vxlan Sample Performance Benchmarking
================================================
The throughput is measured for different operations taken by vxlan sample.
Virtio single mean there's only one flow and forwarded by single port in vm.
Virtio two mean there're two flows and forwarded by both two ports in vm.

+================+===========+=======+============+
| Function       | VirtIO    | Mpps  | % linerate |
+================+===========+=======+============+
| Decap          | Single    |       |            |
+----------------+-----------+-------+------------+
| Encap          | Single    |       |            |
+----------------+-----------+-------+------------+
| Decap&Encap    | Single    |       |            |
+----------------+-----------+-------+------------+
| Checksum       | Single    |       |            |
+----------------+-----------+-------+------------+
| Checksum&Decap | Single    |       |            |
+----------------+-----------+-------+------------+
| Decap          | Two Ports |       |            |
+----------------+-----------+-------+------------+
| Encap          | Two Ports |       |            |
+----------------+-----------+-------+------------+
| Decap&Encap    | Two Ports |       |            |
+----------------+-----------+-------+------------+
| Checksum       | Two Ports |       |            |
+----------------+-----------+-------+------------+
| Checksum&Decap | Two Ports |       |            |
+----------------+-----------+-------+------------+
