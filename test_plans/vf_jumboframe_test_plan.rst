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

 

The support of jumbo frames by Poll Mode Drivers consists in enabling a port
to receive Jumbo Frames with a configurable maximum packet length that is
greater than the standard maximum Ethernet frame length (1518 bytes), up to
a maximum value imposed by the hardware.


Prerequisites
=============
1. Create VF device from PF devices.
	./dpdk_nic_bind.py --st
	0000:87:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
	0000:87:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=

    echo 1 > /sys/bus/pci/devices/0000\:87\:00.0/sriov_numvfs
	echo 1 > /sys/bus/pci/devices/0000\:87\:00.1/sriov_numvfs

    ./dpdk_nic_bind.py --st

    0000:87:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
    0000:87:02.0 'XL710/X710 Virtual Function' unused=
    0000:87:0a.0 'XL710/X710 Virtual Function' unused=

2. Detach VFs from the host, bind them to pci-stub driver,

	/sbin/modprobe pci-stub

	using `lspci -nn|grep -i ethernet` got VF device id, for example "8086 154c",

	echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
	echo 0000:87:02.0 > /sys/bus/pci/devices/0000:87:02.0/driver/unbind
	echo 0000:87:02.0 > /sys/bus/pci/drivers/pci-stub/bind

	echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
	echo 0000:87:0a.0 > /sys/bus/pci/devices/0000:87:0a.0/driver/unbind
	echo 0000:87:0a.0 > /sys/bus/pci/drivers/pci-stub/bind

3. Passthrough VFs 87:02.0 & 87:02.1 to vm0 and start vm0,

    /usr/bin/qemu-system-x86_64  -name vm0 -enable-kvm \
	-cpu host -smp 4 -m 2048 -drive file=/home/image/sriov-fc20-1.img -vnc :1 \
	-device pci-assign,host=87:02.0,id=pt_0 \
	-device pci-assign,host=87:0a.0,id=pt_1

4. Login vm0 and them bind VF devices to igb_uio driver.

	./tools/dpdk_nic_bind.py --bind=igb_uio 00:04.0 00:05.0

5. Start testpmd, set it in mac forward mode
	testpmd -c 0x0f-- -i --portmask=0x1 \
	  --txqflags=0 --max-pkt-len=9000--port-topology=loop
	testpmd> set fwd mac
	testpmd> start

Start packet forwarding in the ``testpmd`` application with the ``start``
command. Then, make the Traffic Generator transmit to the target's port
packets of lengths (CRC included) 1517, 1518, 8999, and 9000 respectively.
Check that the same amount of frames and bytes are received back by the
Traffic Generator from its port connected to the target's port.

Note: 8259x family VF device jumbo frame setting only take effect when
VF rx mode jumbo frame is enable. VF device jumbo frame size setting shared
with PF device and testpmd parameter ``max-pkt-len`` has no effect.

Functional Tests of Jumbo Frames
================================

Testing the support of Jumbo Frames in Poll Mode Drivers consists in
configuring the maximum packet length with a value greater than 1518, and in
sending to the test machine packets with the following lengths (CRC included):

#. packet length = 1518 - 1

#. packet length = 1518

#. packet length = 1518 + 1

#. packet length = maximum packet length - 1

#. packet length = maximum packet length

#. packet length = maximum packet length + 1


Test Case: Normal frames with no jumbo frame support
====================================================
Check that packets of standard lengths are still received with setting
max-pkt-len.

Test Case: Normal frames with jumbo frame support
=================================================
Check that packets of standard lengths are still received when enabling the
receipt of Jumbo Frames.

Test Case: Jumbo frames with no jumbo frame support
====================================================
Check that with jumbo frame support, packet lengths greater than the standard
maximum frame (1518) can not received.

Test Case: Jumbo frames with jumbo frame support
================================================
Check that Jumbo Frames of lengths greater than the standard maximum frame
(1518) and lower or equal to the maximum frame length can be received.

Test Case: Jumbo frames over jumbo frame support
================================================
Check that packets larger than the configured maximum packet length are
effectively dropped by the hardware.
