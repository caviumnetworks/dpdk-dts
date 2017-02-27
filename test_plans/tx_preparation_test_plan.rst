.. Copyright (c) <2017>, Intel Corporation
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

==========================
TX preparation forwarding 
==========================

The support of TX preparation forwarding feature consists in:
- Do necessary preparations of packet burst to be safely transmitted 
  on device for desired HW offloads:
  Set/reset checksum field according to the hardware requirements.
  Check HW constraints (number of segments per packet, etc).
- Provide information about max segments of TSO and non-TSO packets 
  accepted by device.

APPLICATION (CASE OF USE):
- Application should initialize burst of packets to send, set required 
  tx offload flags and required fields, like l2_len, l3_len, l4_len and 
  tso_segsz.
- Application passes burst to check required conditions to send packets 
  through the NIC.
- The result can be used to send valid packets and restore invalid packets 
  if function fails.

Prerequisites
=============
Support igb_uio, test txprep forwarding features on e1000, i40e, ixgbe and 
fm10k drivers.Send packets from tester platform through the interface eth1 to 
the tested port 0, then testpmd sends back packet using same port and uses 
tcpdump to capture packet information.
Tester      DUT
eth1 <---> port 0

Turn off all hardware offloads on tester machine::
  ethtool -K eth1 rx off tx off tso off gso off gro off lro off

Change mtu for large packet:: 
  ifconfig eth1 mtu 9000

Launch the ``testpmd`` with the following arguments, set ``--txqflags=0`` to 
let TX checksum offloads, TSO mode in the “Full Featured” TX path, add 
--max-pkt-len for large packet::
  ./testpmd -c 0x6 -n 4  -- -i --txqflags=0 --port-topology=chained 
  --max-pkt-len=9000

Set the ``csum`` forwarding mode::
  testpmd> set fwd csum

Set the verbose level to 1 to display informations for each received packet::
  testpmd> set verbose 1 

Enable hardware checksum for IP/TCP/UDP packets::
  testpmd> csum set ip hw 0
  testpmd> csum set tcp hw 0
  testpmd> csum set udp hw 0


Test Case: TX preparation forwarding of non-TSO packets
=======================================================
Set TSO turned off::
  testpmd> tso set 0 0
Start the packet forwarding::
  testpmd> start

Send few IP/TCP/UDP packets from tester machine to DUT. Check IP/TCP/UDP 
checksum correctness in captured packet, such as correct as below:: 
Transmitted packet::
  03:06:36.569730 3c:fd:fe:9d:64:30 > 90:e2:ba:63:22:e8, ethertype IPv4 
  (0x0800), length 104: (tos 0x0, ttl 64, id 1, offset 0, flags [none], 
  proto TCP (6), length 90)
    127.0.0.1.ftp-data > 127.0.0.1.http: Flags [.], cksum 0x1998 (correct), 
  seq 0:50, ack 0, win 8192, length 50: HTTP

Captured packet::
  03:06:36.569816 90:e2:ba:63:22:e8 > 02:00:00:00:00:00, ethertype IPv4 
  (0x0800), length 104: (tos 0x0, ttl 64, id 1, offset 0, flags [none], 
  proto TCP (6), length 90)
    127.0.0.1.ftp-data > 127.0.0.1.http: Flags [.], cksum 0x1998 (correct), 
  seq 0:50, ack 1, win 8192, length 50: HTTP


Test Case: TX preparation forwarding of TSO packets
====================================================

Set TSO turned on::
  testpmd> tso set 1460 0
  TSO segment size for non-tunneled packets is 1460

Start the packet forwarding::
  testpmd> start

Send few IP/TCP packets from tester machine to DUT. Check IP/TCP checksum 
correctness in captured packet and verify correctness of HW TSO offload 
for large packets. One large TCP packet (5214 bytes + headers) segmented 
to four fragments (1460 bytes+header,1460 bytes+header,1460 bytes+header 
and 834 bytes + headers), checksums are also ok::
Transmitted packet::
  21:48:24.214136 00:00:00:00:00:00 > 3c:fd:fe:9d:69:68, ethertype IPv6 
  (0x86dd), length 5288: (hlim 64, next-header TCP (6) payload length: 5234) 
   ::1.ftp-data > ::1.http: Flags [.], cksum 0xac95 (correct), seq 0:5214, 
  ack 1, win 8192, length 5214: HTTP

Captured packet::
  21:48:24.214207 3c:fd:fe:9d:69:68 > 02:00:00:00:00:00, ethertype IPv6 
  (0x86dd), length 1534: (hlim 64, next-header TCP (6) payload length: 1480) 
  ::1.ftp-data > ::1.http: Flags [.], cksum 0xa641 (correct), seq 0:1460, 
  ack 1, win 8192, length 1460: HTTP
  21:48:24.214212 3c:fd:fe:9d:69:68 > 02:00:00:00:00:00, ethertype IPv6 
  (0x86dd), length 1534: (hlim 64, next-header TCP (6) payload length: 1480) 
  ::1.ftp-data > ::1.http: Flags [.], cksum 0xae89 (correct), seq 1460:2920, 
  ack 1, win 8192, length 1460: HTTP
  21:48:24.214213 3c:fd:fe:9d:69:68 > 02:00:00:00:00:00, ethertype IPv6 
  (0x86dd), length 1534: (hlim 64, next-header TCP (6) payload length: 1480) 
  ::1.ftp-data > ::1.http: Flags [.], cksum 0xfdb6 (correct), seq 2920:4380, 
  ack 1, win 8192, length 1460: HTTP
  21:48:24.214215 3c:fd:fe:9d:69:68 > 02:00:00:00:00:00, ethertype IPv6 
  (0x86dd), length 908: (hlim 64, next-header TCP (6) payload length: 854) 
  ::1.ftp-data > ::1.http: Flags [.], cksum 0xe629 (correct), seq 4380:5214, 
  ack 1, win 8192, length 834: HTTP

Note: 
Generally TSO only supports TCP packets but unsupports UDP packets due to 
hardware segmentation limitation, for example packets are sent on niantic 
NIC, but not segmented.


Packet::
 ########
 # IPv4 #
 ########

 # checksum TCP
 p=Ether()/IP()/TCP(flags=0x10)/Raw(RandString(50))

 # bad IP checksum
 p=Ether()/IP(chksum=0x1234)/TCP(flags=0x10)/Raw(RandString(50))

 # bad TCP checksum
 p=Ether()/IP()/TCP(flags=0x10, chksum=0x1234)/Raw(RandString(50))

 # large packet
 p=Ether()/IP()/TCP(flags=0x10)/Raw(RandString(length))
        
 # bad checksum and large packet
 p=Ether()/IP(chksum=0x1234)/TCP(flags=0x10,chksum=0x1234)/
 Raw(RandString(length))


 ########
 # IPv6 #
 ########

 # checksum TCP
 p=Ether()/IPv6()/TCP(flags=0x10)/Raw(RandString(50))

 # checksum UDP
 p=Ether()/IPv6()/UDP()/Raw(RandString(50))

 # bad TCP checksum
 p=Ether()/IPv6()/TCP(flags=0x10, chksum=0x1234)/Raw(RandString(50))

 # large packet
 p=Ether()/IPv6()/TCP(flags=0x10)/Raw(RandString(length))

