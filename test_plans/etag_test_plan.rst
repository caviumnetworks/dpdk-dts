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


In some systems an additional external tag (E-tag) can be present before the
VLAN. NIC X550 support VLANs in presence of external tags.
E-tag mode is used for systems where the device adds a tag to identify a
subsystem (usually a VM) and the near end switch adds a tag indicating the
destination subsystem.

The support of E-tag features by X550 consists in:
- the filtering of received E-tag packets
- E-tag header stripping by VF device in received packets
- E-tag header insertion by VF device in transmitted packets
- E-tag forwarding to assigned VF by E-tag id

Prerequisites
=============
1. Create 2VF devices from PF device.
    ./dpdk_nic_bind.py --st
    0000:84:00.0 'Device 1563' drv=igb_uio unused=
    echo 2 > /sys/bus/pci/devices/0000\:84\:00.0/max_vfs

2. Detach VFs from the host, bind them to pci-stub driver,

    /sbin/modprobe pci-stub

    using `lspci -nn|grep -i ethernet` got VF device id, for example "8086 1565",

    echo "8086 1565" > /sys/bus/pci/drivers/pci-stub/new_id
    echo 0000:84:10.0 > /sys/bus/pci/devices/0000:84:10.0/driver/unbind
    echo 0000:84:10.0 > /sys/bus/pci/drivers/pci-stub/bind
    echo 0000:84:10.2 > /sys/bus/pci/devices/0000:84:10.2/driver/unbind
    echo 0000:84:10.2 > /sys/bus/pci/drivers/pci-stub/bind

3. Passthrough VF 84:10.0 & 84:10.2 to vm0 and start vm0,

    /usr/bin/qemu-system-x86_64  -name vm0 -enable-kvm \
    -cpu host -smp 4 -m 2048 -drive file=/home/image/sriov-fc20-1.img -vnc :1 \
    -device pci-assign,host=84:10.0,id=pt_0 \
    -device pci-assign,host=84:10.2,id=pt_1

4. Login vm0 and them bind VF devices to igb_uio driver.

    ./tools/dpdk_nic_bind.py --bind=igb_uio 00:04.0 00:05.0

5. Start host testpmd, set it in rxonly mode and enable verbose output
    testpmd -c f -n 3 -- -i
    testpmd> set fwd rxonly
    testpmd> set verbose 1
    testpmd> start
    
6. Start guest testpmd, set it in mac forward mode
    testpmd -c 0x3 -n 1  -- -i  --txqflags=0x0
    testpmd> set fwd mac
    testpmd> start

Test Case 1: L2 tunnel filter
=============================
Enable E-tag l2 tunnel support means enabling ability of parsing E-tag packet.
This ability should be enabled before we enable filtering, forwarding,
offloading for this specific type of tunnel.

    testpmd> port config 0 l2-tunnel E-tag enable

Send 802.1BR packet to PF and VFs, check packet normally recevied.
   - type=0x893f - length=150 - nb_segs=1 - (outer) L2 type: Unknown
   - (outer) L3 type: IPV4 - (outer) L4 type: UDP

Test Case 2: E-tag filter
=========================
Enable E-tag packet forwarding and add E-tag on VF0, Send 802.1BR packet with
broardcast mac and check packet only recevied on VF0

    testpmd> E-tag set forwarding on port 0
    testpmd> E-tag set filter add e-tag-id 1000 dst-pool 0 port 0

Same E-tag forwarding to VF1, Send 802.1BR packet with broardcast mac and
check packet only recevied on VF1

    testpmd> E-tag set filter add e-tag-id 1000 dst-pool 1 port 0

Same E-tag forwarding to PF0, Send 802.1BR packet with broardcast mac and
check packet only recevied on PF

    testpmd> E-tag set filter add e-tag-id 1000 dst-pool 2 port 0
    
Remove E-tag, Send 802.1BR packet with broardcast mac and check packet not
recevied

    testpmd> E-tag set filter del e-tag-id 1000 port 0

Test Case 3: E-tag insertion
============================
Enable E-tag insertion in VF0, send normal packet to VF1 and check forwared
packet contain E-tag

    testpmd> E-tag set insertion on port-tag-id 1000 port 0 vf 0

Test Case 4: E-tag strip
=========================
Enable E-tag strip on PF, Send 802.1BR packet to VF and check forwarded packet
without E-tag.

    testpmd> E-tag set stripping on port 0

Disable E-tag strip on PF, Send 802.1BR packet and check forwarded packet with
E-tag.

    testpmd> E-tag set stripping off port 0
