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


The support of VLAN offload features by VF device consists in:

- the filtering of received VLAN packets
- VLAN header stripping by hardware in received [VLAN] packets
- VLAN header insertion by hardware in transmitted packets

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

5. Start testpmd, set it in rxonly mode and enable verbose output
	testpmd -c 0x0f -n 4 -w 00:04.0 -w 00:05.0 -- -i --portmask=0x3 --txqflags=0
	testpmd> set fwd rxonly
	testpmd> set verbose 1
	testpmd> start

Test Case 1: Add port based vlan on VF
======================================
Linux network configration tool only set pvid on VF devices.

1. Add pvid on VF0 from PF device
	ip link set $PF_INTF vf 0 vlan 2

2. Send packet with same vlan id and check VF can receive

3. Send packet without vlan and check VF can't receive

4. Send packet with wrong and check Vf can't receive

5. Check pf device show correct pvid setting
	ip link show ens259f0
	...
    vf 0 MAC 00:00:00:00:00:00, vlan 1, spoof checking on, link-state auto

Test Case 2: Remove port based vlan on VF
=========================================
1. Remove added vlan from PF device
	ip link set $PF_INTF vf 0 vlan 0

2. Restart testpmd and send packet without vlan and check VF can receive

3. Set packet with vlan id 0 and check VF can receive

4. Set packet with random id 1-4095 and check VF can't receive

Test Case 3: VF port based vlan tx
==================================
1. Add pvid on VF0 from PF device
	ip link set $PF_INTF vf 0 vlan 2

2. Start testpmd with mac forward mode
	testpmd> set fwd mac
	testpmd> start

3. Send packet from tester port1 and check packet recevied by tester port0
	Check port1 recevied packet with configured vlan 2

Test Case 3: VF tagged vlan tx
===============================
1. Start testpmd with full-featured tx code path and with mac forward mode
	testpmd -c f -n 3 -- -i --txqflags=0x0
	testpmd> set fwd mac
	testpmd> start

2. Add tx vlan offload on VF0, take care the first param is port
	testpmd> tx_vlan 0 1

3. Send packet from tester port1 and check packet recevied by tester port0
	Check port- recevied packet with configured vlan 1

4. rerun with step2-3 with random vlan and max vlan 4095

Test case4: VF tagged vlan rx
=============================
1. Make sure port based vlan disabled on VF0 and VF1
2. Start testpmd with rxonly mode
	testpmd> set fwd rxonly
	testpmd> set verbose 1
	testpmd> start

3. Send packet without vlan and check packet received

4. Send packet with vlan 0 and check packet received

5. Add vlan on VF0 from VF driver
	testpmd> rx_vlan add 1 0

6. Send packet with vlan0/1 and check packet received

7. rerun with step5-6 with random vlan and max vlan 4095

8. Remove vlan on VF0
	rx_vlan rm 1 0

9. Send packet with vlan 0 and check packet received

10. Send packet without vlan and check packet received

11. Send packe with vlan 1 and check packet can't recevied

Test case5: VF Vlan strip test
==============================
1. Start testpmd with mac forward mode
	testpmd> set fwd mac
	testpmd> set verbose 1
	testpmd> start

2. Add tagged vlan 1 on VF0
	testpmd> rx_vlan add 1 0

3. Disable VF0 vlan strip and sniff packet on tester port1
	testpmd> vlan set strip off 0

4. set packet from tester port0 with vlan 1 and check sniffed packet has vlan

5. enable vlan strip on VF0 and sniff packet on tester port1
	testpmd> vlan set strip on 0

6. send packet from tester port0 with vlan 1 and check sniffed packet without vlan

7. send packet from tester port0 with vlan 0 and check sniffed packet without vlan

8. rerun with step 2-8 with random vlan and max vlan 4095
