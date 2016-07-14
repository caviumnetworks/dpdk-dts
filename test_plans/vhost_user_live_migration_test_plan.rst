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

==============================
DPDK vhost user live migration
==============================
This feature is to make sure vhost user live migration works based on vhost-switch.

Prerequisites
-------------
Connect three ports to one switch, these three ports are from Host, Backup
host and tester.

Start nfs service and export nfs to backup host IP:
    host# service rpcbind start
	host# service nfs start
	host# cat /etc/exports
    host# /home/vm-image backup-host-ip(rw,sync,no_root_squash)

Make sure host nfsd module updated to v4 version(v2 not support file > 4G)

Create enough hugepages for vhost-switch and qemu backend memory.
    host# echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    host# mount -t hugetlbfs hugetlbfs /mnt/huge

Bind host port to igb_uio and start vhost switch:
    host# vhost-switch -c f -n 4 --socket-mem 1024 -- -p 0x1

Start host qemu process:
	host# qemu-system-x86_64 -name host -enable-kvm -m 2048 \
	-drive file=/home/vm-image/vm0.img,format=raw \
	-serial telnet:localhost:5556,server,nowait \
	-cpu host -smp 4 \
	-net nic,model=e1000 \
	-net user,hostfwd=tcp:127.0.0.1:5555-:22 \
	-chardev socket,id=char1,path=/root/dpdk_org/vhost-net \
	-netdev type=vhost-user,id=mynet1,chardev=char1,vhostforce \
	-device virtio-net-pci,mac=00:00:00:00:00:01,netdev=mynet1 \
	-object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on \
	-numa node,memdev=mem -mem-prealloc \
	-monitor unix:/tmp/host.sock,server,nowait \
	-daemonize

Wait for virtual machine start up and up virtIO interface:
	host-vm# ifconfig eth1 up

Check vhost-switch connected and send packet with mac+vlan can received by
virtIO interface in VM:
	VHOST_DATA: (0) mac 00:00:00:00:00:01 and vlan 1000 registered

Mount host nfs folder on backup host: 
	backup# mount -t nfs -o nolock,vers=4  host-ip:/home/vm-image /mnt/nfs

Create enough hugepages for vhost-switch and qemu backend memory.
    backup# echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    backup# mount -t hugetlbfs hugetlbfs /mnt/huge

Bind backup host port to igb_uio and start vhost switch:
    backup# vhost-switch -c f -n 4 --socket-mem 1024 -- -p 0x1

Start backup host qemu with additional parameter:
	-incoming tcp:0:4444

Test Case 1: migrate with kernel driver
=======================================
Make sure all Prerequisites has been done
1. Login into host virtual machine and capture incoming packets.
	host# telnet localhost 5556
	host vm# ifconfig eth1 up

2. Send continous packets with mac(00:00:00:00:00:01) and vlan(1000)
from tester port:
	tester# scapy
	tester# p = Ether(dst="00:00:00:00:00:01")/Dot1Q(vlan=1000)/IP()/UDP()/
	            Raw('x'*20)
	tester# sendp(p, iface="p5p1", inter=1, loop=1)

3. Check packet normally recevied by virtIO interface
	host vm# tcpdump -i eth1 -xxx

4. Connect to qemu monitor session and start migration
	host# nc -U /tmp/host.sock
    host# (qemu)migrate -d tcp:backup host ip:4444

5. Check host vm can receive packet before migration done

6. Query stats of migrate in monitor, check status of migration
    host# (qemu)info migrate
    host# after finished:	

7. After migartion done, login into backup vm and re-enable virtIO interface
	backup vm# ifconfig eth1 down
	backup vm# ifconfig eth1 up	

8. Check backup host reconnected and packet normally recevied

Test Case 2: migrate with dpdk
==============================
Make sure all Prerequisites has been done
1. Send continous packets with mac(00:00:00:00:00:01) and vlan(1000)
	tester# scapy
	tester# p = Ether(dst="00:00:00:00:00:01")/Dot1Q(vlan=1000)/IP()/UDP()/
	            Raw('x'*20)
	tester# sendp(p, iface="p5p1", inter=1, loop=1)

2. bind virtIO interface to igb_uio and start testpmd
	host vm# testpmd -c 0x7 -n 4

3. Check packet normally recevied by testpmd:
	host vm# testpmd> set fwd rxonly
	host vm# testpmd> set verbose 1
	host vm# testpmd> port 0/queue 0: received 1 packets

4. Connect to qemu monitor session and start migration
	host# nc -U /tmp/host.sock
    host# (qemu)migrate -d tcp:backup host ip:4444

5. Check host vm can receive packet before migration done

6. Query stats of migrate in monitor, check status of migration
    host# (qemu)info migrate
    host# after finished:	

7. After migartion done, login into backup vm and check packets recevied
	backup vm# testpmd> port 0/queue 0: received 1 packets