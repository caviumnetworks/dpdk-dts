Configuring DPDK Test Suite 
===========================

DPDK Test Suite command line
----------------------------

DPDK Test Suite supports multiple parameters and these parameters, which will select different of working mode of test framework. In the meantime, DPDK Test Suite can work with none parameter, then  every parameter will set to its default value.
For Example, please see specific usage, you can get these information via DPDK Test Suite help messages.

.. code-block:: console

   usage: main.py [-h] [--config-file CONFIG_FILE] [--git GIT] [--patch PATCH]
                  [--snapshot SNAPSHOT] [--output OUTPUT] [-s] [-r] [-p PROJECT]
                  [--suite-dir SUITE_DIR] [-t TEST_CASES] [-d DIR] [-v]
                  [--virttype VIRTTYPE] [--debug] [--debugcase]


DPDK Test Suite supports the following parameters:

.. table::

    +---------------------------+---------------------------------------------------+------------------+
    | parameter                 | description                                       | Default Value    |
    +---------------------------+---------------------------------------------------+------------------+
    | -h,--help                 | show this help message and exit                   |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | --config-file CONFIG_FILE | configuration file that describes the test cases, | execution.cfg    |
    |                           | DUTs and targets                                  |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | --git GIT                 | Indicate git label to use as input                | None             |
    +---------------------------+---------------------------------------------------+------------------+
    | --patch PATCH             | apply a patch to the package under test           | None             |
    +---------------------------+---------------------------------------------------+------------------+
    | --snapshot SNAPSHOT       | snapshot .tgz file to use as input                | dep/dpdk.tar.gz  |
    +---------------------------+---------------------------------------------------+------------------+
    | --output OUTPUT           | Output directory where DPDK Test Suite log and    | output           |
    |                           | result saved                                      |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | -s --skip-setup           | Skips all possible setup steps done on both DUT   |                  |
    |                           | and tester boards.                                |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | -r                        | Reads the DUT configuration from a cache. If not  |                  |
    |                           | specified, the DUT configuration will be          |                  |
    |                           | calculated as usual and cached.                   |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | -p PROJECT                | Specify that which project will be tested dpdk    |                  |
    | --project PROJECT         |                                                   |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | -t TEST_CASES             | Executes only the followings test cases           | None             |
    | [TEST_CASES ...]          |                                                   |                  |
    | --test-cases              |                                                   |                  |
    | TEST_CASES                |                                                   |                  |
    | [TEST_CASES ...]          |                                                   |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | -d DIR --dir DIR          | Output directory where dpdk package is extracted  | dpdk             |
    +---------------------------+---------------------------------------------------+------------------+
    | --suite-dir               | Test suite directory where test suites will be    | tests            |
    |                           | imported                                          |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | -v, --verbose             | Enable verbose output, all log shown on screen    |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | --virttype                | Set virtualization hypervisor type. Support kvm   |                  |
    |                           | and libvirtd by now.                              |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | --debug                   | Enable debug mode, running process can be         |                  |
    |                           | interrupted and enter debug mode.                 |                  |
    +---------------------------+---------------------------------------------------+------------------+
    | --debugcase               | Enter into debug mode before running every test   |                  |
    |                           | case.                                             |                  |
    +---------------------------+---------------------------------------------------+------------------+

Please see more information about some critical parameters as the following:

**--config-file**

DPDK Test Suite configure file defines some critical parameters.  It must contain the DUT CRB IP address, wish list of test suites, DPDK target information and test mode parameter.

**--git**

When we use –-git parameter, DPDK Test Suite will clone the source code from dpdk.org git repository, then checkout branch specified by the parameter. 

**--patch**

DPDK Test Suite also support apply specified patch list by --patch parameter before build DPDK packet. 

**--skip-setup**

If DPDK source code doesn’t changed, you can use --skip-setup to skip unzip and compilation of DPDK source code, just reuse original source code. 

**--project**

Parameter –-project can load customized project model and do its own project initialization.

**--output**

If we perform multiple validation at the same time, result files in output folder maybe overwritten. Then we can use –-output parameter to specify the output folder and save execution log and result files. This option will make sure that all test result will be stored in the different excel files and rst files, doesn’t conflict each other.

.. note::
   The current working folder of DPDK Test Suite is "DTS root directory"  and default output folder is “output”

**--t**

You can only run some specified cases in test suites.

We can use parameter –-t to determine those cases.

**--suite-dir**

DPDK Test Suite support load suites from different folders, this will be helpful when there’s several projects existing in the same time. 

**--verbose**

DPDK Test Suite support verbose mode. When enable this mode, all log messages will be output on screen and helpful for debug.

**--virttype**

Choose virtualization hypervisor type. By now this configuration is useless.

**--debug**

DPDK Test Suite support debug mode. After keyboard ctrl+c message to DTS process, will run into this mode. User can do further debug by attached to sessions or call pdb module by interact interface.

Debug interact support commands as below:

.. code-block:: console

    help(): show help message
    list(): list all connected sessions
    connect(name): connect to session directly
    exit(): exit dts
    quit(): quit debug mode and into noraml mode
    debug(): call python debug module

**--debugcase**

Another approach to run into debug mode. With this option on, DTS will hang and wait for user command before execution of each test case.

DPDK Release Preparation
------------------------

Firstly, you need to download the latest code from dpdk.org, then archive and compress it into zipped file. After that, please move this zipped file to DPDK Test Suite "dep" folder. Once launch test framework, DPDK Test Suite will copy this zipped file to root folder on DUT. Finally this source code zip file will be unzipped and built.

.. code-block:: console

    [root@tester dts]#  ls
    [root@tester dts]#  conf dep doc dts executions framework output test_plans tests tools


If enables patch option, DPDK Test Suite will also make patch the unzipped folder and compile it.

.. code-block:: console

   [root@tester dcts]# ./dts --patch 1.patch --patch 2.patch 

Create your own execution configuration
---------------------------------------

First of all, you must create a file named execution.cfg as below.

.. code-block:: console

   [Execution1]
   crbs=192.168.1.1
   test_suites=
   hello_world,
   l2fwd
   targets=
   x86_64-default-linuxapp-gcc,
   parameters=nic_type=niantic:func=true
   linkspeed=<Link Speed of NIC>Mb/s
   scenario=pf_passthrough

*   crbs: IP address of the DUT CRB. The detail information of this CRB is defined in file crbs.py.
*   test_suites:  defines list of test suites, which will plan to be executed.
*   targets: list of DPDK targets to be tested.
*   parameters: you can define multiple keywords
*   linkspeed: you can define linkspeed for your Cavium Device
*   scenario: Senario of DPDK virtualization environment for this execution.

    – nic_type : is the type of the NIC to use. The types are defined in the file settings.py.

    – func=true run only functional test

    – perf=true run only performance test

Then please add the detail information about your CRB in **conf/crbs.conf** as follows:

.. code-block:: console

   [192.168.1.1]
   dut_ip=192.168.1.1
   dut_user=root
   dut_passwd=
   os=linux
   tester_ip=192.168.1.2
   tester_passwd=
   ixia_group=group1
   channels=4
   bypass_core0=True


.. table::

    +-----------------+----------------------------------------------------+
    | Item            | description                                        |
    +-----------------+----------------------------------------------------+
    | dut_ip          | IP address of DUT                                  |
    +-----------------+----------------------------------------------------+
    | dut_user        | UserName of DPDK Test Suite used to login into DUT |
    +-----------------+----------------------------------------------------+
    | dut_passwd      | Password of DPDK Test Suite used to login into DUT |
    +-----------------+----------------------------------------------------+
    | os              | Distribution of operation system                   |
    +-----------------+----------------------------------------------------+
    | tester_ip       | IP address of tester                               |
    +-----------------+----------------------------------------------------+
    | tester_passwd   | Password to login into Tester                      |
    +-----------------+----------------------------------------------------+
    | ixia_group      | IXIA group name for DUT                            |
    +-----------------+----------------------------------------------------+
    | channels        | number of memory channels for DPDK EAL             |
    +-----------------+----------------------------------------------------+
    | bypass_core0    | skip the first core when initialize DPDK           |
    +-----------------+----------------------------------------------------+

Launch DPDK Test Suite
----------------------

After we have prepared the zipped dpdk file and configuration file, just type the followed command “./dts”, it will start the validation process.

DPDK Test Suite will create communication sessions first.

.. code-block:: console

   DUT 192.168.1.1
   INFO: ssh root@192.168.1.1
   INFO: ssh root@192.168.1.1
   INFO: ssh root@192.168.1.2
   INFO: ssh root@192.168.1.2


Then copy snapshot zipped dpdk source code to DUT.

.. code-block:: console

   DTS_DUT_CMD: scp dep/dpdk.tar.gz root@192.168.1.1:

Collect CPU core and network device information of DUT and tester.

Automatically detect the network topology of DUT and tester.

.. code-block:: console

   DTS_TESTER_RESULT: DUT PORT MAP: [4, 5, 6, 7]

Build dpdk source code and then setup the running environment. 

.. code-block:: console

   DTS_DUT_CMD: make -j install T=x86_64-native-linuxapp-gcc
   DTS_DUT_CMD: awk '/Hugepagesize/ {print $2}' /proc/meminfo
   DTS_DUT_CMD: awk '/HugePages_Total/ { print $2 }' /proc/meminfo
   DTS_DUT_CMD: umount `awk '/hugetlbfs/ { print $2 }' /proc/mounts`
   DTS_DUT_CMD: mkdir -p /mnt/huge
   DTS_DUT_CMD: mount -t hugetlbfs nodev /mnt/huge
   DTS_DUT_CMD: modprobe uio
   DTS_DUT_CMD: rmmod -f igb_uio
   DTS_DUT_CMD: insmod ./x86_64-native-linuxapp-gcc/kmod/igb_uio.ko
   DTS_DUT_CMD: lsmod | grep igb_uio
   DTS_DUT_CMD: tools/dpdk_nic_bind.py --bind=igb_uio 08:00.0 08:00.1 0a:00.0 0a:00.1

Begin the validation process of test suite.

.. code-block:: console

   TEST SUITE : TestCmdline
                     INFO: NIC :        niantic
       SUITE_DUT_CMD: make -j -C examples/cmdline
       SUITE_DUT_CMD: ./examples/cmdline/build/app/cmdline -n 1 -c 0x2
                               INFO: Test Case test_cmdline_sample_commands Begin


Clean-up DUT and tester after all validation finished.

.. code-block:: console

        DTS_DUT_CMD: rmmod igb_uio
        DTS_DUT_CMD: modprobe igb
        DTS_DUT_CMD: modprobe ixgbe
        DTS_DUT_CMD: modprobe e1000e
        DTS_DUT_CMD: modprobe e1000
        DTS_DUT_CMD: modprobe virtio_net
     DTS_TESTER_CMD: rmmod igb_uio
     DTS_TESTER_CMD: modprobe igb
     DTS_TESTER_CMD: modprobe ixgbe
     DTS_TESTER_CMD: modprobe e1000e
     DTS_TESTER_CMD: modprobe e1000
     DTS_TESTER_CMD: modprobe virtio_net

