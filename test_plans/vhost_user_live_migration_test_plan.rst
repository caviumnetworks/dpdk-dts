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
This feature is to make sure vhost user live migration works based on testpmd.

Prerequisites
-------------
HW setup

1. Connect three ports to one switch, these three ports are from Host, Backup
host and tester. Ensure the tester can send packets out, then host/backup server ports 
can receive these packets.
2. Better to have 2 similar machine with the same OS. 

NFS configuration
1. Make sure host nfsd module updated to v4 version(v2 not support file > 4G)

2. Start nfs service and export nfs to backup host IP:
    host# service rpcbind start
	host# service nfs-server start
	host# service nfs-mountd start 
	host# systemctrl stop firewalld.service
	host# vim /etc/exports
    host# /home/vm-image backup-host-ip(rw,sync,no_root_squash)
	
3. Mount host nfs folder on backup host: 
	backup# mount -t nfs -o nolock,vers=4  host-ip:/home/vm-image /mnt/nfs

On host server side: 

1. Create enough hugepages for vhost-switch and qemu backend memory.
    host# echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    host# mount -t hugetlbfs hugetlbfs /mnt/huge

2. Bind host port to igb_uio and start testpmd with vhost port:
    #./tools/dpdk-devbind.py -b igb_uio 83:00.1
    #./x86_64-native-linuxapp-gcc/app/testpmd -c 0xc0000 -n 4 --vdev 'eth_vhost0,iface=./vhost-net,queues=1' --socket-mem 1024,1024 -- -i
    testpmd>start
	
3. Start VM on host, here we set 5432 as the serial port, 3333 as the qemu monitor port, 5555 as the SSH port. 
    taskset -c 22-23 qemu-system-x86_64 -name vm1host \
    -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on \
    -numa node,memdev=mem -mem-prealloc -smp 2 -cpu host -drive file=/home/qxu10/img/vm1.img \
    -net nic,model=e1000,addr=1f -net user,hostfwd=tcp:127.0.0.1:5555-:22 \
    -chardev socket,id=char0,path=./vhost-net \
    -netdev type=vhost-user,id=netdev0,chardev=char0,vhostforce \
    -device virtio-net-pci,netdev=netdev0,mac=52:54:00:00:00:01 \
    -monitor telnet::3333,server,nowait \
    -serial telnet:localhost:5432,server,nowait \
    -daemonize
	
On the backup server, run the vhost testpmd on the host and launch VM: 

4.  Set huge page, bind one port to igb_uio and run testpmd on the backup server, the command is very similar to host: 
    backup server# echo 4096 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    backup server# mount -t hugetlbfs hugetlbfs /mnt/huge
    backup server#./tools/dpdk-devbind.py -b igb_uio 81:00.1
    backup server#./x86_64-native-linuxapp-gcc/app/testpmd -c 0xc0000 -n 4 --vdev 'eth_vhost0,iface=./vhost-net,queues=1' --socket-mem 1024,1024 -- -i
    testpmd>start
	
5. Launch VM on the backup server, and the script is similar to host, but note the 2 differences:
   1. need add " -incoming tcp:0:4444 " for live migration. 
   2. need make sure the VM image is the NFS mounted folder, VM image is the exact one on host server. 
   
   Backup server # 
   qemu-system-x86_64 -name vm2 \
   -enable-kvm -m 2048 -object memory-backend-file,id=mem,size=2048M,mem-path=/mnt/huge,share=on \
   -numa node,memdev=mem -mem-prealloc -smp 4 -cpu host -drive file=/mnt/nfs/vm1.img \
   -net nic,model=e1000,addr=1f -net user,hostfwd=tcp:127.0.0.1:5555-:22 \
   -chardev socket,id=char0,path=./vhost-net \
   -netdev type=vhost-user,id=netdev0,chardev=char0,vhostforce \
   -device virtio-net-pci,netdev=netdev0,mac=52:54:00:00:00:01 \
   -monitor telnet::3333,server,nowait \
   -serial telnet:localhost:5432,server,nowait \
   -incoming tcp:0:4444 \
   -daemonize


Test Case 1: migrate with virtio-pmd
====================================
Make sure all Prerequisites has been done

6. SSH to VM and scp the DPDK folder from host to VM:
    host # ssh -p 5555 localhost, then input password to log in. 
	host # scp  -P 5555 -r <dpdk_folder>/  localhost:/root, then input password to let the file transfer.
	
7. Telnet the serial port and run testpmd in VM:  

    host # telnet localhost 5432
	Input Enter, then log in to VM
	If need leave the session, input "CTRL" + "]", then quit the telnet session. 
	On the Host server VM, run below commands to launch testpmd
	host vm # 
	cd /root/dpdk
    modprobe uio
    insmod ./x86_64-native-linuxapp-gcc/kmod/igb_uio.ko
    ./tools/dpdk_nic_bind.py --bind=igb_uio 00:03.0 
    echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
    ./x86_64-native-linuxapp-gcc/app/testpmd -c 0x3 -n 4 -- -i
	>set fwd rxonly
	>set verbose 1 
	>start tx_first

8.  Check host vhost pmd connect with VM’s virtio device:
    testpmd> host testpmd message for connection

9. 	Send continuous packets with the physical port's mac(e.g: 90:E2:BA:69:C9:C9)
from tester port:
	tester# scapy
	tester# p = Ether(dst="90:E2:BA:69:C9:C9")/IP()/UDP()/
	            Raw('x'*20)
	tester# sendp(p, iface="p5p1", inter=1, loop=1)
	
	Then check the host VM can receive the packet: 
	host VM# testpmd> port 0/queue 0: received 1 packets
	
10. Start Live migration, ensure the traffic is continuous at the HOST VM side: 
    host server # telnet localhost 3333
	(qemu)migrate -d tcp:backup server:4444 
	e.g: migrate -d tcp:10.239.129.176:4444
	(qemu)info migrate
	Check if the migrate is active and not failed.
	
11. Check host vm can receive packet before migration done

12. Query stats of migrate in monitor, check status of migration, when the status is completed, then the migration is done. 
    host# (qemu)info migrate
    host# (qemu)	
    Migration status: completed

13. After live migration, go to the backup server and check if the virtio-pmd can continue to receive packets. 
    Backup server # telnet localhost 5432
	log in then see the same screen from the host server, and check if the virtio-pmd can continue receive the packets. 

Test Case 2: migrate with virtio-net
====================================
Make sure all Prerequisites has been done.
6. Telnet the serial port and run testpmd in VM:  

    host # telnet localhost 5432
	Input Enter, then log in to VM
	If need leave the session, input "CTRL" + "]", then quit the telnet session. 
	
7. Let the virtio-net link up:     
	host vm # ifconfig eth1 up

8. Send continuous packets with the physical port's mac(e.g: 90:E2:BA:69:C9:C9)
   from tester port:
	tester# scapy
	tester# p = Ether(dst="90:E2:BA:69:C9:C9")/IP()/UDP()/
	            Raw('x'*20)
	tester# sendp(p, iface="p5p1", inter=1, loop=1)
	
9. Check the host VM can receive the packet: 
	host VM# tcpdump -i eth1	
	
10. Start Live migration, ensure the traffic is continuous at the HOST VM side: 
    host server # telnet localhost 3333
	(qemu)migrate -d tcp:backup server:4444 
	e.g: migrate -d tcp:10.239.129.176:4444
	(qemu)info migrate
	Check if the migrate is active and not failed.
	
11. Check host vm can receive packet before migration done

12. Query stats of migrate in monitor, check status of migration, when the status is completed, then the migration is done. 
    host# (qemu)info migrate
    host# (qemu)	
    Migration status: completed

13. After live migration, go to the backup server and check if the virtio-pmd can continue to receive packets. 
    Backup server # telnet localhost 5432
	log in then see the same screen from the host server, and check if the virtio-net can continue receive the packets. 

