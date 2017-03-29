# dpdk-dts
Changes done to run dts on Octeontx(83xx/81xxx)/Thunder(88xx) platforms

1) Cavium devices with 177d:a034 and 177d:0011 PCI IDs are added to NICs list, both of which are supported by thunder-nicvf driver
2) When appending pci devices info, the only Cavium NICs appended are the ones with 10Gb/s linkspeed
3) For arm64 architecture the hugepage size is detected and if it is 524288, then lesser amount of hugepages is acquired
4) Created a method in Dut class for getting the right binding script (if someone chooses to use older DPDK version)
5) Checking link is done via IPv4 ping alternately, so that DUT can be a system without IPv6 (previously link was detected solely by checking if an interface obtained an IPv6 address and then by using ping6). This also makes force binding necessary, as those interfaces are detected as active.
6) Checking whether vfio-pci was loaded using lsmod can be deceptive. If someone decides to use DPDK on a system with modules built into the kernel, then this approach will fail. Instead, DPDK binding script can be used and if it shows that vfio-pci can be used, DTS proceeds, otherwise it send with an error due to a failed assertion.
7) test_enable_disablejumbo(self) from shutdown api testsuite checks whether setting VLAN strip off fails and if so it skips part of tests involving frames with VLAN
8) Short live test suite is no longer assuming x86_64-native-linuxapp-gcc target
9) Appending --disable-hw-vlan-filter flag to testpmd params in PmdOutput class, as thunder driver does not offer VLAN filtering capability. The same applies to TestSuite_pmdpcap.
10) For TestSuite_ip_reassembly and tcpdump_command method additional splitting is performed on the result as casting to int may fail if it is performed on output containing alphabetical text.
11) Added tests that are not applicable for cavium NICs to conf/dpdk_test_case_checklist.xls
