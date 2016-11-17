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
VM Power Management
===================

This test plan is for the test and validation of feature VM Power Management
of DPDK 1.8.

VM Power Manager would use a hint based mechanism by which a VM can
communicate to a host based governor about its current processing
requirements. By mapping VMs virtual CPUs to physical CPUs the Power Manager
can then make decisions according to some policy as to what power state the
physical CPUs can transition to.

VM Agent shall have the ability to send the following hints to host:
- Scale frequency down
- Scale frequency up
- Reduce frequency to min
- Increase frequency to max

The Power manager is responsible for enabling the Linux userspace power
governor and interacting via its sysfs entries to get/set frequencies.

The power manager will manage the file handles for each core(<n>) below:
- /sys/devices/system/cpu/cpu<n>/cpufreq/scaling_governor
- /sys/devices/system/cpu/cpu<n>/cpufreq/scaling_available_frequencies
- /sys/devices/system/cpu/cpu<n>/cpufreq/scaling_cur_freq
- /sys/devices/system/cpu/cpu<n>/cpufreq/scaling_setspeed

Prerequisites
=============
1. Hardware:
	- CPU: Haswell, IVB(CrownPass)
	- NIC: Niantic 82599

2. BIOS:
	- Enable VT-d and VT-x
	- Enable Enhanced Intel SpeedStep(R) Tech
	- Disable Intel(R) Turbo Boost Technology
	- Enable Processor C3
	- Enable Processor C6
	- Enable Intel(R) Hyper-Threading Tech

3. OS and Kernel:
	- Fedora 20
	- Enable Kernel features Huge page, UIO, IOMMU, KVM
	- Enable Intel IOMMU in kernel commnand
	- Disable Selinux
       - Disable intel_pstate

3. Virtualization:
	- QEMU emulator version 1.6.1
	- libvirtd (libvirt) 1.1.3.5
	- Add virio-serial port

4. IXIA Traffic Generator Configuration
	LPM table used for packet routing is:

		+---------+------------------------+----+
		| Entry # | LPM prefix (IP/length) |    |
		+---------+------------------------+----+
		| 0       | 1.1.1.0/24             | P0 |
		+---------+------------------------+----+
		| 1       | 2.1.1.0/24             | P1 |
		+---------+------------------------+----+


	The flows should be configured and started by the traffic generator.

		+------+---------+------------+---------+------+-------+--------+
		| Flow | Traffic | IPv4       | IPv4    | Port | Port  | L4     |
		|      | Gen.    | Src.       | Dst.    | Src. | Dest. | Proto. |
		|      | Port    | Address    | Address |      |       |        |
		+------+---------+------------+---------+------+-------+--------+
		| 1    | TG0     | 0.0.0.0    | 2.1.1.0 | any  | any   | UDP    |
		+------+---------+------------+---------+------+-------+--------+
		| 2    | TG1     | 0.0.0.0    | 1.1.1.0 | any  | any   | UDP    |
		+------+---------+------------+---------+------+-------+--------+



Test Case 1: VM Power Management Channel
========================================
1. Configure VM XML to pin VCPUs/CPUs:

		<vcpu placement='static'>5</vcpu>
          <cputune>
	      <vcpupin vcpu='0' cpuset='1'/>
	      <vcpupin vcpu='1' cpuset='2'/>
	      <vcpupin vcpu='2' cpuset='3'/>
	      <vcpupin vcpu='3' cpuset='4'/>
	      <vcpupin vcpu='4' cpuset='5'/>
		</cputune>

2. Configure VM XML to set up virtio serial ports

	Create temporary folder for vm_power socket.

        mkdir /tmp/powermonitor

    Setup one serial port for every one vcpu in VM.

		<channel type='unix'>
	    <source mode='bind' path='/tmp/powermonitor/<vm_name>.<channel_num>'/>
	    <target type='virtio' name='virtio.serial.port.poweragent.<channel_num>'/>
	    <address type='virtio-serial' controller='0' bus='0' port='4'/>
	    </channel>

3. Run power-manager in Host

		./build/vm_power_mgr -c 0x3 -n 4

4. Startup VM and run guest_vm_power_mgr

		guest_vm_power_mgr -c 0x1f -n 4 -- -i
5. Add vm in host and check vm_power_mgr can get frequency normally

		vmpower> add_vm <vm_name>
		vmpower> add_channels <vm_name> all
		vmpower> show_cpu_freq <core_num>
6. Check vcpu/cpu mapping can be detected normally

		vmpower> show_vm <vm_name>
		VM:
		vCPU Refresh: 1
		Channels 5
		  [0]: /tmp/powermonitor/<vm_name>.0, status = 1
		  [1]: /tmp/powermonitor/<vm_name>.1, status = 1
		  [2]: /tmp/powermonitor/<vm_name>.2, status = 1
		  [3]: /tmp/powermonitor/<vm_name>.3, status = 1
		  [4]: /tmp/powermonitor/<vm_name>.4, status = 1
		Virtual CPU(s): 5
		  [0]: Physical CPU Mask 0x2
		  [1]: Physical CPU Mask 0x4
		  [2]: Physical CPU Mask 0x8
		  [3]: Physical CPU Mask 0x10
		  [4]: Physical CPU Mask 0x20

7. Run vm_power_mgr in vm

		guest_cli/build/vm_power_mgr -c 0x1f -n 4
   Check monitor channel for all cores has been connected.

Test Case 2: VM Power Management Numa
=====================================
1.Get core and socket information by cpu_layout

		./tools/cpu_layout.py
2. Configure VM XML to pin VCPUs on Socket1:
3. Repeat Case1 steps 3-7 sequentially
4. Check vcpu/cpu mapping can be detected normally

Test Case 3: VM Scale CPU Frequency Down
========================================
1. Setup VM power management environment
2. Send cpu frequency down hints to Host

		vmpower(guest)> set_cpu_freq 0 down
3. Verify the frequency of physical CPU has been set down correctly

		vmpower> show_cpu_freq 1
		Core 1 frequency: 2700000

4. Check other CPUs' frequency is not affected by change above
5. check if the other VM works fine (if they use different CPUs)
6. Repeat step2-5 several times


Test Case 4: VM Scale CPU Frequency UP
======================================
1. Setup VM power management environment
2. Send cpu frequency down hints to Host

		vmpower(guest)> set_cpu_freq 0 up

3. Verify the frequency of physical CPU has been set up correctly

		vmpower> show_cpu_freq 1
		Core 1 frequency: 2800000
4. Check other CPUs' frequency is not affected by change above
5. check if the other VM works fine (if they use different CPUs)
6. Repeat step2-5 several times

Test Case 5: VM Scale CPU Frequency to Min
==========================================
1. Setup VM power management environment
2. Send cpu frequency scale to minimum hints.

		vmpower(guest)> set_cpu_freq 0 min
3. Verify the frequency of physical CPU has been scale to min correctly

		vmpower> show_cpu_freq 1
		Core 1 frequency: 1200000
4. Check other CPUs' frequency is not affected by change above
5. check if the other VM works fine (if they use different CPUs)

Test Case 6: VM Scale CPU Frequency to Max
==========================================
1. Setup VM power management environment
2. Send cpu frequency down hints to Host

		vmpower(guest)> set_cpu_freq 0 max
3. Verify the frequency of physical CPU has been set to max correctly

		vmpower> show_cpu_freq 1
		Core 1 frequency: 2800000
4. Check other CPUs' frequency is not affected by change above
5. check if the other VM works fine (if they use different CPUs)

Test Case 7: VM Power Management Multi VMs
==========================================
1. Setup VM power management environment for VM1
2. Setup VM power management environment for VM2
3. Run power-manager in Host

		./build/vm_power_mgr -c 0x3 -n 4
4. Startup VM1 and VM2
5. Add VM1 in host and check vm_power_mgr can get frequency normally

		vmpower> add_vm <vm1_name>
		vmpower> add_channels <vm1_name> all
		vmpower> show_cpu_freq <core_num>
6. Add VM2 in host and check vm_power_mgr can get frequency normally

		vmpower> add_vm <vm2_name>
		vmpower> add_channels <vm2_name> all
		vmpower> show_cpu_freq <core_num>
7. Run Case3-6 and check VM1 and VM2 cpu frequency can by modified by guest_cli
8. Poweroff VM2 and remove VM2 from host vm_power_mgr

		vmpower> rm_vm <vm2_name>

Test Case 8: VM l3fwd-power Latency
===================================
1. Connect two physical ports to IXIA
2. Start VM and run l3fwd-power

	    l3fwd-power -c 6 -n 4 -- -p 0x3 --config
             '(P0,0,C{1.1.0}),(P1,0,C{1.2.0})'

3. Configure packet flow in IxiaNetwork
4. Start to send packets from IXIA and check the receiving packets and latency
5. Record the latency of frame sizes 128
6. Compare latency value with sample l3fwd

Test Case 9: VM l3fwd-power Performance
=======================================
Start VM and run l3fwd-power

	l3fwd-power -c 6 -n 4 -- -p 0x3 --config
            '(P0,0,C{1.1.0}),(P1,0,C{1.2.0})'

Input traffic linerate varied from 0 to 100%, in order to see cpu frequency
changes.

The test report should provide the throughput rate measurements (in Mpps and %
of the line rate for 2x NIC ports) and cpu frequency as listed in the table
below:

	+---------------+---------------+-----------+
	| % Tx linerate | Rx % linerate |  Cpu freq |
	+---------------+---------------+-----------+
	| 0             |               |           |
	+---------------+---------------+-----------+
	| 20            |               |           |
	+---------------+---------------+-----------+
	| 40            |               |           |
	+---------------+---------------+-----------+
	| 60            |               |           |
	+---------------+---------------+-----------+
	| 80            |               |           |
	+---------------+---------------+-----------+
	| 100           |               |           |
	+---------------+---------------+-----------+
