.. Copyright (c) <2010>, Intel Corporation
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

=====================================================================
Support of Ethernet Link Flow Control Features by Poll Mode Drivers
=====================================================================

The support of Ethernet link flow control features by Poll Mode Drivers 
consists in:

- At the receive side, if packet buffer is not enough, NIC will send out the 
  pause frame to peer and ask the peer to slow down the Ethernet frame #
  transmission.

- At the transmit side, if pause frame is received, NIC will slow down the 
  Ethernet frame transmission according to the pause frame.

MAC Control Frame Forwarding consists in:

- Control frames (PAUSE Frames) are taken by the NIC and do not pass to the 
  host.
  
- When Flow Control and MAC Control Frame Forwarding are enabled the PAUSE
  frames will be passed to the host and can be handled by testpmd.

Note: Priority flow control is not included in this test plan.

Note: the high_water, low_water, pause_time, send_xon are configured into the
NIC register. It is not necessary to validate the accuracy of these parameters.
And what change it can cause. The port_id is used to indicate the NIC to be 
configured. In certain case, a system can contain multiple NIC. However the NIC 
need not be configured multiple times. 


Prerequisites
=============

Assuming that ports ``0`` and ``2`` are connected to a traffic generator,
launch the ``testpmd`` with the following arguments::
  
  ./build/app/testpmd -cffffff -n 3 -- -i --burst=1 --txpt=32 \
  --txht=8 --txwt=0 --txfreet=0 --rxfreet=64 --mbcache=250 --portmask=0x5

The -n command is used to select the number of memory channels. 
It should match the number of memory channels on that setup.

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Test Case: test_perf_flowctrl_on_pause_fwd_on
=============================================
::

  testpmd> set flowctrl rx on tx on high_water low_water pause_time 
  send_xon mac_ctrl_frame_fwd on autoneg on port_id
  
Setup the ``csum`` forwarding mode::

  testpmd> set fwd csum
  Set csum packet forwarding mode

Start the packet forwarding::
  
  testpmd> start
    csum packet forwarding - CRC stripping disabled - packets/burst=32
    nb forwarding cores=1 - nb forwarding ports=10
    RX queues=1 - RX desc=128 - RX free threshold=64
    RX threshold registers: pthresh=8 hthresh=8 wthresh=4
    TX queues=1 - TX desc=512 - TX free threshold=0
    TX threshold registers: pthresh=32 hthresh=8 wthresh=8

Validate the NIC can generate the pause frame?
Configure the traffic generator to send IPv4/UDP packet at the length of 66Byte
at the line speed (10G). Because the 66Byte packet cannot reach line rate when 
running with testpmd, so it is expected that the pause frame will be sent to the 
peer (traffic generator). Ideally this mechanism can avoid the packet loss. And
this depends on high_water/low_water and other parameters are configured properly. 
It is strongly recommended that the user look into the data sheet before doing
any flow control configuration. By default, the flow control on 10G is disabled.
the flow control for 1G is enabled. 

Validate the NIC can deal with the pause frame.
Configure the traffic generator to send out large amount of pause frames, this 
will cause the NIC to disable / slow down the packet transmission according to 
the pause time. Once the traffic generator stop sending the pause frame, the NIC
will restore the packet transmission to the expected rate.


Test Case: test_perf_flowctrl_on_pause_fwd_off
==============================================
::

  testpmd> set flowctrl rx on tx on high_water low_water pause_time 
  send_xon mac_ctrl_frame_fwd off autoneg on port_id

Validate same behaviour as test_perf_flowctrl_on_pause_fwd_on


Test Case: test_perf_flowctrl_rx_on
===================================
::

  testpmd> set flowctrl rx on tx on high_water low_water pause_time 
  send_xon mac_ctrl_frame_fwd off autoneg on port_id

Validate same behaviour as test_perf_flowctrl_on_pause_fwd_on


Test Case: test_perf_flowctrl_off_pause_fwd_off
===============================================
This is the default mode for 10G PMD, by default, testpmd is running on this mode.
no need to execute any command::

  testpmd> set flowctrl rx off tx off high_water low_water pause_time 
  send_xon mac_ctrl_frame_fwd off autoneg on port_id
  
Validate the NIC won't generate the pause frame when the packet buffer is not 
enough. Packet loss can be observed.
Validate the NIC will not slow down the packet transmission after receiving the 
pause frame.

Test Case: test_perf_flowctrl_off_pause_fwd_on
==============================================
::
  
  testpmd> set flowctrl rx off tx off high_water low_water pause_time 
  send_xon mac_ctrl_frame_fwd on autoneg on port_id

Validate same behaviour as test_perf_flowctrl_off_pause_fwd_off

Test Case: test_perf_flowctrl_tx_on
===================================
::

  testpmd> set flowctrl rx off tx on high_water low_water pause_time 
  send_xon mac_ctrl_frame_fwd off autoneg on port_id

Validate same behaviour as test_perf_flowctrl_on_pause_fwd_off 
