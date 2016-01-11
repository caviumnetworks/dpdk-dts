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


Test Case 1: test_kernel_2pf_2vf_1vm_iplink_macfilter
=====================================================

1. Get the pci device id of DUT, for example::

./dpdk_nic_bind.py --st

0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
0000:81:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=

2. Create 2 VFs from 2 PFs, and set the VF MAC address at PF0::

echo 1 > /sys/bus/pci/devices/0000\:81\:00.0/sriov_numvfs
echo 1 > /sys/bus/pci/devices/0000\:81\:00.1/sriov_numvfs

./dpdk_nic_bind.py --st
0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
0000:81:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=
0000:81:02.0 'XL710/X710 Virtual Function' unused=
0000:81:0a.0 'XL710/X710 Virtual Function' unused=

ip link set ens259f0 vf 0 mac 00:11:22:33:44:55

3. Detach VFs from the host, bind them to pci-stub driver::

/sbin/modprobe pci-stub

using `lspci -nn|grep -i ethernet` got VF device id, for example "8086 154c",

echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
echo 0000:81:02.0 > /sys/bus/pci/devices/0000:08:02.0/driver/unbind
echo 0000:81:02.0 > /sys/bus/pci/drivers/pci-stub/bind

echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
echo 0000:81:0a.0 > /sys/bus/pci/devices/0000:08:0a.0/driver/unbind
echo 0000:81:0a.0 > /sys/bus/pci/drivers/pci-stub/bind

or using the following more easy way,

virsh nodedev-detach pci_0000_81_02_0; 
virsh nodedev-detach pci_0000_81_0a_0;

./dpdk_nic_bind.py --st

0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
0000:81:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=
0000:81:02.0 'XL710/X710 Virtual Function' if= drv=pci-stub unused=
0000:81:0a.0 'XL710/X710 Virtual Function' if= drv=pci-stub unused=

it can be seen that VFs 81:02.0 & 81:0a.0 's driver is pci-stub.

4. Passthrough VFs 81:02.0 & 81:0a.0 to vm0, and start vm0::

/usr/bin/qemu-system-x86_64  -name vm0 -enable-kvm \
-cpu host -smp 4 -m 2048 -drive file=/home/image/sriov-fc20-1.img -vnc :1 \
-device pci-assign,host=81:02.0,id=pt_0 \
-device pci-assign,host=81:0a.0,id=pt_1

5. Login vm0, got VFs pci device id in vm0, assume they are 00:06.0 & 00:07.0, bind them to igb_uio driver,
and then start testpmd, enable CRC strip, disable promisc mode,set it in mac forward mode::

./tools/dpdk_nic_bind.py --bind=igb_uio 00:06.0 00:07.0
./x86_64-native-linuxapp-gcc/app/testpmd -c 0x0f -n 4 -w 00:06.0 -w 00:07.0 -- -i --portmask=0x3 --txqflags=0

testpmd> port stop all
testpmd> port config all crc-strip on
testpmd> port start all
testpmd> set promisc all off
testpmd> set fwd mac
testpmd> start

6. Use scapy to send 100 random packets with ip link set MAC to VF, verify the packets can be received by one 
VF and can be forward to another VF correctly.

7. Also use scapy to send 100 random packets with a wrong MAC to VF, verify the packets can't be received by one
VF and can be forward to another VF correctly.

Test Case 2: test_kernel_2pf_2vf_1vm_mac_add_filter
===================================================

1. Get the pci device id of DUT, for example::

./dpdk_nic_bind.py --st

0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
0000:81:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=

2. Create 2 VFs from 2 PFs, and don't set the VF MAC address at PF0::

echo 1 > /sys/bus/pci/devices/0000\:81\:00.0/sriov_numvfs
echo 1 > /sys/bus/pci/devices/0000\:81\:00.1/sriov_numvfs

./dpdk_nic_bind.py --st
0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
0000:81:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=
0000:81:02.0 'XL710/X710 Virtual Function' unused=
0000:81:0a.0 'XL710/X710 Virtual Function' unused=

3. Detach VFs from the host, bind them to pci-stub driver::

/sbin/modprobe pci-stub

using `lspci -nn|grep -i ethernet` to get VF device id, for example "8086 154c",

echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
echo 0000:81:02.0 > /sys/bus/pci/devices/0000:08:02.0/driver/unbind
echo 0000:81:02.0 > /sys/bus/pci/drivers/pci-stub/bind

echo "8086 154c" > /sys/bus/pci/drivers/pci-stub/new_id
echo 0000:81:0a.0 > /sys/bus/pci/devices/0000:08:0a.0/driver/unbind
echo 0000:81:0a.0 > /sys/bus/pci/drivers/pci-stub/bind

or using the following more easy way,

virsh nodedev-detach pci_0000_81_02_0;
virsh nodedev-detach pci_0000_81_0a_0;

./dpdk_nic_bind.py --st

0000:81:00.0 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f0 drv=i40e unused=
0000:81:00.1 'Ethernet Controller X710 for 10GbE SFP+' if=ens259f1 drv=i40e unused=
0000:81:02.0 'XL710/X710 Virtual Function' if= drv=pci-stub unused=
0000:81:0a.0 'XL710/X710 Virtual Function' if= drv=pci-stub unused=

it can be seen that VFs 81:02.0 & 81:0a.0 's driver is pci-stub.

4. Passthrough VFs 81:02.0 & 81:0a.0 to vm0, and start vm0::

/usr/bin/qemu-system-x86_64  -name vm0 -enable-kvm \
-cpu host -smp 4 -m 2048 -drive file=/home/image/sriov-fc20-1.img -vnc :1 \
-device pci-assign,host=81:02.0,id=pt_0 \
-device pci-assign,host=81:0a.0,id=pt_1

5. login vm0, got VFs pci device id in vm0, assume they are 00:06.0 & 00:07.0, bind them to igb_uio driver,
and then start testpmd, enable CRC strip on VF, disable promisc mode, add a new MAC to VF0 and then start::

./tools/dpdk_nic_bind.py --bind=igb_uio 00:06.0 00:07.0
./x86_64-native-linuxapp-gcc/app/testpmd -c 0x0f -n 4 -w 00:06.0 -w 00:07.0 -- -i --portmask=0x3 --txqflags=0

testpmd> port stop all
testpmd> port config all crc-strip on
testpmd> port start all
testpmd> set promisc all off
testpmd> mac_addr add 0 00:11:22:33:44:55
testpmd> set fwd mac
testpmd> start

Note: In Jan,2016, i40e doesn't support mac_addr add operation, so the case will be failed for FVL/Fort park NICs.

6. Use scapy to send 100 random packets with current VF0's MAC, verify the packets can be received by one
VF and can be forward to another VF correctly.

7. Use scapy to send 100 random packets with new added VF0's MAC, verify the packets can be received by one
VF and can be forward to another VF correctly.

8. Use scapy to send 100 random packets with a wrong MAC to VF0, verify the packets can't be received by one
VF and can be forward to another VF correctly.




