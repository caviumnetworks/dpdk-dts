..
  <COPYRIGHT_TAG>

===============================
Multi-process Test Instructions
===============================

Simple MP Application Test
--------------------------

Description
-----------

This test is a basic multi-process test which demonstrates the basics of sharing
information between Intel DPDK processes. The same application binary is run
twice - once as a primary instance, and once as a secondary instance. Messages
are sent from primary to secondary and vice versa, demonstrating the processes
are sharing memory and can communicate using rte_ring structures.

Prerequisites
-------------
Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Assuming that an Intel� DPDK build has been set up and the multi-process sample
applications have been built.

Test Case: Basic operation
--------------------------

1. To run the application, start one copy of the simple_mp binary in one terminal,
passing at least two cores in the coremask, as follows::

	./build/simple_mp -c 3 --proc-type=primary

The process should start successfully and display a command prompt as follows::

	$ ./build/simple_mp -c 3 --proc-type=primary
	EAL: coremask set to 3
	EAL: Detected lcore 0 on socket 0
	EAL: Detected lcore 1 on socket 0
	EAL: Detected lcore 2 on socket 0
	EAL: Detected lcore 3 on socket 0
	...
	EAL: Requesting 2 pages of size 1073741824
	EAL: Requesting 768 pages of size 2097152
	EAL: Ask a virtual area of 0x40000000 bytes
	EAL: Virtual area found at 0x7ff200000000 (size = 0x40000000)
	...
	EAL: check igb_uio module
	EAL: check module finished
	EAL: Master core 0 is ready (tid=54e41820)
	EAL: Core 1 is ready (tid=53b32700)
	Starting core 1

	simple_mp >

2. To run the secondary process to communicate with the primary process, again run the
same binary setting at least two cores in the coremask.::

	./build/simple_mp -c C --proc-type=secondary

Once the process type is specified correctly, the process starts up, displaying largely
similar status messages to the primary instance as it initializes. Once again, you will be
presented with a command prompt.

3. Once both processes are running, messages can be sent between them using the send
command. At any stage, either process can be terminated using the quit command.

Validate that this is working by sending a message between each process, both from
primary to secondary and back again. This is shown below.

Transcript from the primary - text entered by used shown in "{}"::

	EAL: Master core 10 is ready (tid=b5f89820)
	EAL: Core 11 is ready (tid=84ffe700)
	Starting core 11
	simple_mp > {send hello_secondary}
	simple_mp > core 11: Received 'hello_primary'
	simple_mp > {quit}

Transcript from the secondary - text entered by the user is shown in "{}"::

	EAL: Master core 8 is ready (tid=864a3820)
	EAL: Core 9 is ready (tid=85995700)
	Starting core 9
	simple_mp > core 9: Received 'hello_secondary'
	simple_mp > {send hello_primary}
	simple_mp > {quit}

Test Case: Load test of Simple MP application
---------------------------------------------

1. Start up the sample application using the commands outlined in steps 1 & 2
above.

2. To load test, send a large number of strings (>5000), from the primary instance
to the secondary instance, and then from the secondary instance to the primary.
[NOTE: A good source of strings to use is /usr/share/dict/words which contains
>400000 ascii strings on Fedora 14]

Test Case: Test use of Auto for Application Startup
---------------------------------------------------

1. Start the primary application as in Test 1, Step 1, except replace
"--proc-type=primary" with "--proc-type=auto"

2. Validate that the application prints the line:
"EAL: Auto-detected process type: PRIMARY" on startup.

3. Start the secondary application as in Test 1, Step 2, except replace
"--proc-type=secondary" with "--proc-type=auto".

4. Validate that the application prints the line:
"EAL: Auto-detected process type: SECONDARY" on startup.

5. Verify that processes can communicate by sending strings, as in Test 1,
Step 3.

Test Case: Test running multiple processes without "--proc-type" flag
---------------------------------------------------------------------

1. Start up the primary process as in Test 1, Step 1, except omit the
"--proc-type" flag completely.

2. Validate that process starts up as normal, and returns the "simple_mp> "
prompt.

3. Start up the secondary process as in Test 1, Step 2, except omit the
"--proc-type" flag.

4. Verify that the process *fails* to start and prints an error message as
below:
"PANIC in rte_eal_config_create():
Cannot create lock on '/path/to/.rte_config'. Is another primary process running?"

Symmetric MP Application Test
=============================

Description
-----------

This test is a multi-process test which demonstrates how multiple processes can
work together to perform packet I/O and packet processing in parallel, much as
other example application work by using multiple threads. In this example, each
process reads packets from all network ports being used - though from a different
RX queue in each case. Those packets are then forwarded by each process which
sends them out by writing them directly to a suitable TX queue.

Prerequisites
-------------

Assuming that an Intel� DPDK build has been set up and the multi-process sample
applications have been built. It is also assumed that a traffic generator has
been configured and plugged in to the NIC ports 0 and 1.

Test Methodology
----------------

As with the simple_mp example, the first instance of the symmetric_mp process
must be run as the primary instance, though with a number of other application
specific parameters also provided after the EAL arguments. These additional
parameters are:

* -p <portmask>, where portmask is a hexadecimal bitmask of what ports on the
  system are to be used. For example: -p 3 to use ports 0 and 1 only.
* --num-procs <N>, where N is the total number of symmetric_mp instances that
  will be run side-by-side to perform packet processing. This parameter is used to
  configure the appropriate number of receive queues on each network port.
* --proc-id <n>, where n is a numeric value in the range 0 <= n < N (number of
  processes, specified above). This identifies which symmetric_mp instance is being
  run, so that each process can read a unique receive queue on each network port.

The secondary symmetric_mp instances must also have these parameters specified,
and the first two must be the same as those passed to the primary instance, or errors
result.

For example, to run a set of four symmetric_mp instances, running on lcores 1-4, all
performing level-2 forwarding of packets between ports 0 and 1, the following
commands can be used (assuming run as root)::

 ./build/symmetric_mp -c 2 --proc-type=auto -- -p 3 --num-procs=4 --proc-id=0
 ./build/symmetric_mp -c 4 --proc-type=auto -- -p 3 --num-procs=4 --proc-id=1
 ./build/symmetric_mp -c 8 --proc-type=auto -- -p 3 --num-procs=4 --proc-id=2
 ./build/symmetric_mp -c 10 --proc-type=auto -- -p 3 --num-procs=4 --proc-id=3

To run only 1 or 2 instances, the above parameters to the 1 or 2 instances being
run should remain the same, except for the "num-procs" value, which should be
adjusted appropriately.


Test Case: Performance Tests
----------------------------

Run the multiprocess application using standard IP traffic - varying source
and destination address information to allow RSS to evenly distribute packets
among RX queues. Record traffic throughput results as below.

+-------------------+-----+-----+-----+-----+-----+-----+
| Num-procs         |  1  |  2  |  2  |  4  |  4  |  8  |
+-------------------+-----+-----+-----+-----+-----+-----+
| Cores/Threads     | 1/1 | 1/2 | 2/1 | 2/2 | 4/1 | 4/2 |
+-------------------+-----+-----+-----+-----+-----+-----+
| Num Ports         |  2  |  2  |  2  |  2  |  2  |  2  |
+-------------------+-----+-----+-----+-----+-----+-----+
| Packet Size       |  64 |  64 |  64 |  64 |  64 |  64 |
+-------------------+-----+-----+-----+-----+-----+-----+
| %-age Line Rate   |  X  |  X  |  X  |  X  |  X  |  X  |
+-------------------+-----+-----+-----+-----+-----+-----+
| Packet Rate(mpps) |  X  |  X  |  X  |  X  |  X  |  X  |
+-------------------+-----+-----+-----+-----+-----+-----+


Client Server Multiprocess Tests
================================

Description
-----------
The client-server sample application demonstrates the ability of Intel� DPDK
to use multiple processes in which a server process performs packet I/O and one
or multiple client processes perform packet processing. The server process
controls load balancing on the traffic received from a number of input ports to
a user-specified number of clients. The client processes forward the received
traffic, outputting the packets directly by writing them to the TX rings of the
outgoing ports.

Prerequisites
-------------
Assuming that an Intel� DPDK build has been set up and the multi-process
sample application has been built.
Also assuming a traffic generator is connected to the ports "0" and "1".

It is important to run the server application before the client application,
as the server application manages both the NIC ports with packet transmission
and reception, as well as shared memory areas and client queues.

Run the Server Application:

- Provide the core mask on which the server process is to run using -c, e.g. -c 3 (bitmask number).
- Set the number of ports to be engaged using -p, e.g. -p 3 refers to ports 0 & 1.
- Define the maximum number of clients using -n, e.g. -n 8.

The command line below is an example on how to start the server process on
logical core 2 to handle a maximum of 8 client processes configured to
run on socket 0 to handle traffic from NIC ports 0 and 1::

	root@host:mp_server# ./build/mp_server -c 2 -- -p 3 -n 8
	
NOTE: If an additional second core is given in the coremask to the server process
that second core will be used to print statistics. When benchmarking, only a
single lcore is needed for the server process

Run the Client application:

- In another terminal run the client application.
- Give each client a distinct core mask with -c.
- Give each client a unique client-id with -n.

An example commands to run 8 client processes is as follows::

	root@host:mp_client# ./build/mp_client -c 40 --proc-type=secondary -- -n 0 &
	root@host:mp_client# ./build/mp_client -c 100 --proc-type=secondary -- -n 1 &
	root@host:mp_client# ./build/mp_client -c 400 --proc-type=secondary -- -n 2 &
	root@host:mp_client# ./build/mp_client -c 1000 --proc-type=secondary -- -n 3 &
	root@host:mp_client# ./build/mp_client -c 4000 --proc-type=secondary -- -n 4 &
	root@host:mp_client# ./build/mp_client -c 10000 --proc-type=secondary -- -n 5 &
	root@host:mp_client# ./build/mp_client -c 40000 --proc-type=secondary -- -n 6 &
	root@host:mp_client# ./build/mp_client -c 100000 --proc-type=secondary -- -n 7 &

Test Case: Performance Measurement
----------------------------------
- On the traffic generator set up a traffic flow in both directions specifying
  IP traffic.
- Run the server and client applications as above.
- Start the traffic and record the throughput for transmitted and received packets.

An example set of results is shown below.

+----------------------+-----+-----+-----+-----+-----+-----+
| Server threads       |  1  |  1  |  1  |  1  |  1  |  1  |
+----------------------+-----+-----+-----+-----+-----+-----+
| Server Cores/Threads | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
+----------------------+-----+-----+-----+-----+-----+-----+
| Num-clients          |  1  |  2  |  2  |  4  |  4  |  8  |
+----------------------+-----+-----+-----+-----+-----+-----+
| Client Cores/Threads | 1/1 | 1/2 | 2/1 | 2/2 | 4/1 | 4/2 |
+----------------------+-----+-----+-----+-----+-----+-----+
| Num Ports            |  2  |  2  |  2  |  2  |  2  |  2  |
+----------------------+-----+-----+-----+-----+-----+-----+
| Packet Size          |  64 |  64 |  64 |  64 |  64 |  64 |
+----------------------+-----+-----+-----+-----+-----+-----+
| %-age Line Rate      |  X  |  X  |  X  |  X  |  X  |  X  |
+----------------------+-----+-----+-----+-----+-----+-----+
| Packet Rate(mpps)    |  X  |  X  |  X  |  X  |  X  |  X  |
+----------------------+-----+-----+-----+-----+-----+-----+
