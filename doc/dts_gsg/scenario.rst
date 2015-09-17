Virtualization Scenario
=======================

When enable virtualization scenario setting in execution cfg, DTS will load scenario configurations and prepare resource and devices for VMs. After VMs started, scenario module will prepare test suite running environment. After all suites finished, scenario module will stop VMs and then clean up the scene.

Configuration File
------------------

With below configuration, DTS will create one scenario which created one VM with two VF devices attached. In scene section and according to configurations defined in suite. DUT object in suite will be VM DUT object, tester and DUT port network topology will be discovered automatically. Now DTS only support kvm typed hypervisor to create virtualization scenario.


.. code-block:: console

	# vm configuration for vf passthrough cases
	# numa 0,1,yes yes mean cpu numa match the first port
	# skipcores list mean those core will not be used by vm
	# dut=vm_dut; mean vm_dut act as dut
	# dut=dut; mean host dut act as dut
	# portmap=cfg; mean vm_dut port map will be load from cfg
	# portmap=auto; mean vm_dut will create portmap automatically
	# devices = dev_gen/host/dev_gen+host not useful now
	[scene]
	suite =
		dut=vm_dut,portmap=auto;
		tester=tester;
	type=kvm;

Virtual machine "vm0" section configured cpu, memory, disk and device settings in VM. As below configurations, VM will not use the first four lcores on DUT. DTS will generate two VF devices from first two host PF devices. These two VF devices will be pass-through into guest and their pci address will be auto assigned by qemu.

.. code-block:: console

	[vm0]
	cpu =
		model=host,number=4,numa=auto,skipcores=0 1 2 3;
	mem =
		size=2048,hugepage=no;
	disk =
		file=/storage/vm-image/vm0.img;
	dev_gen =
		pf_idx=0,vf_num=1,driver=default;
		pf_idx=1,vf_num=1,driver=default;
	device =
		vf_idx=0,pf_dev=0,guestpci=auto;
		vf_idx=0,pf_dev=1,guestpci=auto;
	vnc =
	displayNum=1;

All suites will be run in scenario like below picture.

.. figure:: image/scene_pf_passthrough.svg

Scenario Parameters
-------------------

Options for suite:

.. table::

	+------------------+----------------------------------+-----------------+---------------+-----------+
	| option           | Description                      | Options         | Default value | Must have |
	+------------------+----------------------------------+-----------------+---------------+-----------+
	| dut              | type of dut for dts suite        | vm_dut,dut      | dut           | No        |
	+------------------+----------------------------------+-----------------+---------------+-----------+
	| dut->portmap     | method to generate dut port maps | auto, cfg       | auto          | No        |
	+------------------+----------------------------------+-----------------+---------------+-----------+
	| tester           | type of tester for dts suite[Not | N/A             | N/A           | No        |
	|                  | used by now]                     |                 |               |           |
	+------------------+----------------------------------+-----------------+---------------+-----------+
	| type             | type of hypervisor               | kvm,libvirtd    | kvm           | No        |
	+------------------+----------------------------------+-----------------+---------------+-----------+

Options for cpu:

.. table::

    +------------------+----------------------------------+-----------------+---------------+-----------+
    | option           | Description                      | Options         | Default value | Must have |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | model            | type of dut for dts suite        |                 | host          | Yes       |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | number           | number of cores in virtual       |                 | 4             | Yes       | 
    |                  | machine                          |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | numa_aware       | numa id of cores allocated from  | 0,1,auto        | 0             | Yes       |
    |                  | resource module                  |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | skipcores        | cores should not be used, most   |                 |               | No        |
    |                  | time for those cores will be used|                 |               |           |
    |                  | by dpdk on host                  |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+

Options for mem:

.. table::

    +------------------+----------------------------------+-----------------+---------------+-----------+
    | option           | Description                      | Options         | Default value | Must have |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | size             | virtual machine memory size in   |                 | 2048          | Yes       | 
    |                  | MBs                              |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | hugepage         | whether allocate memory from     |                 | No            | No        |
    |                  | hugepages                        |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+

Options for dev_gen:

.. table::

    +------------------+----------------------------------+-----------------+---------------+-----------+
    | option           | Description                      | Options         | Default value | Must have |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | pf_idx           | PF device index of host port     |                 | 0             | Yes       | 
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | pf_inx->vf_num   | number of VFs created by this PF |                 | 0             | Yes       |
    |                  | device                           |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | pf_inx->driver   | Allocate VF devices from which PF| igb_uio,default | default       | Yes       |
    |                  | host driver                      | vfio-pci        |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+

Options for device:

.. table::

    +------------------+----------------------------------+-----------------+---------------+-----------+
    | option           | Description                      | Options         | Default value | Must have |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | pf_idx           | PF device index of host port     |                 | 0             | Yes       |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | pf_idx->guestpci | pci address in virtual machine   |                 |               | No        |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | vf_idx           | VF devices index of all VFs      |                 |               | No        |
    |                  | belong to same PF devices        |                 |               |           |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | vf_idx->pf_dev   | PF device index of this VF device|                 |               | Yes       |
    +------------------+----------------------------------+-----------------+---------------+-----------+
    | vf_idx->guestpci | pci address in virtual machine   |                 |               | No        |
    +------------------+----------------------------------+-----------------+---------------+-----------+

Options for ports:

.. table::

	+------------------+----------------------------------+-----------------+---------------+-----------+
	| option           | Description                      | Options         | Default value | Must have |
	+------------------+----------------------------------+-----------------+---------------+-----------+
	| dev_idx          | device index of virtual machine  |                 |               | No        |
	|                  | ports                            |                 |               |           |
	+------------------+----------------------------------+-----------------+---------------+-----------+
	| dev_idx->peer    | tester peer port's pci address   |                 |               | No        |
	+------------------+----------------------------------+-----------------+---------------+-----------+
