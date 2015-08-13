.. <COPYRIGHT_TAG>

======================================
Intel® DPDK Shutdown API Feature Tests
======================================

This tests for Shutdown API feature can be run on linux userspace. It
will check if NIC port can be stopped and restarted without exiting the
application process. Furthermore, it will check if it can reconfigure
new configurations for a port after the port is stopped, and if it is
able to restart with those new configurations. It is based on testpmd
application.

The test is performed by running the testpmd application and using a
traffic generator. Port/queue configurations can be set interactively,
and still be set at the command line when launching the application in
order to be compatible with previous test framework.

Prerequisites
-------------

Support igb_uio and vfio driver, if used vfio, kernel need 3.6+ and enable vt-d in bios.
When used vfio , used "modprobe vfio" and "modprobe vfio-pci" insmod vfiod driver, then used
"./tools/dpdk_nic_bind.py --bind=vfio-pci device_bus_id" to bind vfio driver to test driver.

Assume port A and B are connected to the remote ports, e.g. packet generator.
To run the testpmd application in linuxapp environment with 4 lcores,
4 channels with other default parameters in interactive mode.

	$ ./testpmd -c 0xf -n 4 -- -i

Test Case: Stop and Restart
---------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "start" to start forwarding packets.
3. check that testpmd is able to forward traffic.
4. run "stop" to stop forwarding packets.
5. run "port stop all" to stop all ports.
6. check on the tester side that the ports are down using ethtool.
7. run "port start all" to restart all ports.
8. check on the tester side that the ports are up using ethtool
9. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully.

Test Case: Reset RX/TX Queues
-----------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "port stop all" to stop all ports.
3. run "port config all rxq 2" to change the number of receiving queues to two.
4. run "port config all txq 2" to change the number of transmiting queues to two.
5. run "port start all" to restart all ports.
6. check with "show config rxtx" that the configuration for these parameters changed.
7. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully.

Test Case: Set promiscuous mode
-------------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if promiscuous mode setting works well after reconfiguring
it while all ports are stopped
2. run "port stop all" to stop all ports.
3. run "set promisc all off" to disable promiscuous mode on all ports.
4. run "port start all" to restart all ports.
5. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check that testpmd is NOT able to receive and forward packets
successfully.
6. run "port stop all" to stop all ports.
7. run "set promisc all on" to enable promiscuous mode on all ports.
8. run "port start all" to restart all ports.
9. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check that testpmd is able to receive and forward packets
successfully.



Test Case: Reconfigure All Ports With The Same Configurations (CRC)
-------------------------------------------------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "port stop all" to stop all ports.
3. run "port config all crc-strip on" to enable the CRC stripping mode.
4. run "port start all" to restart all ports.
5. check with "show config rxtx" that the configuration for these parameters changed.
6. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully. Check that the packet received is 4 bytes smaller than the packet sent.

Test Case: Change Link Speed
----------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "port stop all" to stop all ports.
3. run "port config all speed SPEED duplex HALF/FULL" to select the new config for the link.
4. run "port start all" to restart all ports.
5. check on the tester side that the configuration actually changed using ethtool.
6. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully.
7. repeat this process for every compatible speed depending on the NIC driver.

Test Case: Enable/Disable Jumbo Frame
-------------------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "port stop all" to stop all ports.
3. run "port config all max-pkt-len 2048" to set the maximum packet length.
4. run "port start all" to restart all ports.
5. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully. Check this with the following packet sizes: 2047, 2048 & 2049. Only the third one should fail.

Test Case: Enable/Disable RSS
-----------------------------

1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "port stop all" to stop all ports.
3. run "port config rss ip" to enable RSS.
4. run "port start all" to restart all ports.
5. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully.

Test Case: Change the Number of rxd/txd
---------------------------------------
1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "port stop all" to stop all ports.
3. run "port config all rxd 1024" to change the rx descriptors.
4. run "port config all txd 1024" to change the tx descriptors.
5. run "port start all" to restart all ports.
6. check with "show config rxtx" that the descriptors were actually changed.
6. run "start" again to restart the forwarding, then start packet generator to transmit
and receive packets, and check if testpmd is able to receive and forward packets
successfully.

Test Case: link stats
---------------------------------------
1. If the testpmd application is not launched, run it as above command. Follow
below steps to check if it works well after reconfiguring all ports without
changing any configurations.
2. run "set fwd mac" to set fwd type.
3. run "start" to start the forwarding, then start packet generator to transmit
and receive packets
4. run "set link-down port X" to set all port link down
5. check on the tester side that the configuration actually changed using ethtool.
6. start packet generator to transmit and not receive packets
7. run "set link-up port X" to set all port link up
8. start packet generator to transmit and receive packets
successfully
