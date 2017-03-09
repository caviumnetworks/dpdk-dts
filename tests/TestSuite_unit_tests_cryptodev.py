# BSD LICENSE
#
# Copyright(c) 2016-2017 Intel Corporation. All rights reserved.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of Intel Corporation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import utils
from test_case import TestCase


class UnitTestsCryptodev(TestCase):

    def set_up_all(self):

        self.core_config = "1S/2C/1T"
        self.number_of_ports = 1
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= self.number_of_ports,
                    "Not enough ports for " + self.nic)
        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.logger.info("core config = " + self.core_config)
        self.logger.info("number of ports = " + str(self.number_of_ports))
        self.logger.info("dut ports = " + str(self.dut_ports))
        self.logger.info("ports_socket = " + str(self.ports_socket))

        self.core_mask = utils.create_mask(self.dut.get_core_list(
            self.core_config,
            socket=self.ports_socket))
        self.port_mask = utils.create_mask([self.dut_ports[0]])

        self.tx_port = self.tester.get_local_port(self.dut_ports[0])
        self.rx_port = self.tester.get_local_port(self.dut_ports[0])

        self.tx_interface = self.tester.get_interface(self.tx_port)
        self.rx_interface = self.tester.get_interface(self.rx_port)

        self.logger.info("core mask = " + self.core_mask)
        self.logger.info("port mask = " + self.port_mask)
        self.logger.info("tx interface = " + self.tx_interface)
        self.logger.info("rx interface = " + self.rx_interface)

        # Rebuild the dpdk with cryptodev pmds CONFIG_RTE_LIBRTE_PMD_ZUC=n
        self.dut.send_expect("export AESNI_MULTI_BUFFER_LIB_PATH=/root/ipsec_043/code/", "#")
        self.dut.send_expect("export LIBSSO_SNOW3G_PATH=/root/libsso_snow3g/snow3g/", "#")
        self.dut.send_expect("export LIBSSO_ZUC_PATH=/root/libsso_zuc.1.0.1.1-8/zuc", "#")
        self.dut.send_expect("export LIBSSO_KASUMI_PATH=/root/LibSSO_0_3_1/isg_cid-wireless_libs/ciphers/kasumi/", "#")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=n$/CONFIG_RTE_LIBRTE_PMD_QAT=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=n$/CONFIG_RTE_LIBRTE_PMD_KASUMI=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_OPENSSL=n$/CONFIG_RTE_LIBRTE_PMD_OPENSSL=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=n$/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_ZUC=n$/CONFIG_RTE_LIBRTE_PMD_ZUC=y/' config/common_base", "# ")
        self.dut.skip_setup = False
        self.dut.build_install_dpdk(self.dut.target)

        # Bind QAT VF devices
        out = self.dut.send_expect("lspci -d:443|awk '{print $1}'", "# ", 10)
        self.dut.send_expect('echo "8086 0443" > /sys/bus/pci/drivers/igb_uio/new_id', "# ", 10)
        for line in out.replace("\r", "\n").replace("\n\n", "\n").split("\n"):
            cmd = "echo 0000:{} > /sys/bus/pci/devices/0000\:{}/driver/unbind".format(line, line.replace(":", "\:"))
            self.dut.send_expect(cmd, "# ", 10)
            cmd = "echo 0000:{} > /sys/bus/pci/drivers/igb_uio/bind".format(line)
            self.dut.send_expect(cmd, "# ", 10)

    def set_up(self):
        pass

    def tear_down(self):
        self.dut.kill_all()

    def tear_down_all(self):
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=y$/CONFIG_RTE_LIBRTE_PMD_QAT=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=y$/CONFIG_RTE_LIBRTE_PMD_KASUMI=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_OPENSSL=y$/CONFIG_RTE_LIBRTE_PMD_OPENSSL=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_ZUC=y$/CONFIG_RTE_LIBRTE_PMD_ZUC=n/' config/common_base", "# ")

    def test_cryptodev_qat_autotest(self):
        self.__run_unit_test("cryptodev_qat_autotest")

    def test_cryptodev_qat_perftest(self):
        self.__run_unit_test("cryptodev_qat_perftest")

    def test_cryptodev_aesni_mb_perftest(self):
        self.__run_unit_test("cryptodev_aesni_mb_perftest")

    def test_cryptodev_sw_snow3g_perftest(self):
        self.__run_unit_test("cryptodev_sw_snow3g_perftest")

    def test_cryptodev_qat_snow3g_perftest(self):
        self.__run_unit_test("cryptodev_qat_snow3g_perftest")

    def test_cryptodev_aesni_gcm_perftest(self):
        self.__run_unit_test("cryptodev_aesni_gcm_perftest")

    def test_cryptodev_openssl_perftest(self):
        self.__run_unit_test("cryptodev_openssl_perftest")

    def test_cryptodev_qat_continual_perftest(self):
        self.__run_unit_test("cryptodev_qat_continual_perftest")

    def test_cryptodev_aesni_mb_autotest(self):
        self.__run_unit_test("cryptodev_aesni_mb_autotest")

    def test_cryptodev_openssl_autotest(self):
        self.__run_unit_test("cryptodev_openssl_autotest")

    def test_cryptodev_aesni_gcm_autotest(self):
        self.__run_unit_test("cryptodev_aesni_gcm_autotest")

    def test_cryptodev_null_autotest(self):
        self.__run_unit_test("cryptodev_null_autotest")

    def test_cryptodev_sw_snow3g_autotest(self):
        self.__run_unit_test("cryptodev_sw_snow3g_autotest")

    def test_cryptodev_sw_kasumi_autotest(self):
        self.__run_unit_test("cryptodev_sw_kasumi_autotest")

    def test_cryptodev_sw_zuc_autotest(self):
        self.__run_unit_test("cryptodev_sw_zuc_autotest")

    def __run_unit_test(self, testsuite, timeout=600):
        self.logger.info("STEP_TEST: " + testsuite)
        self.dut.send_expect("dmesg -C", "# ", 30)
        self.dut.send_expect("./{target}/app/test -n 1 -c 0xf".format(target=self.dut.target), "RTE>>", 30)
        out = ""
        try:
            out = self.dut.send_expect(testsuite, "RTE>>", timeout)
            self.dut.send_expect("quit", "# ", 30)
        except Exception, ex:
            self.logger.error("Cryptodev Unit Tests Exception")
            dmesg = self.dut.alt_session.send_expect("dmesg", "# ", 30)
            self.logger.error("dmesg info:")
            self.logger.error(dmesg)

        self.logger.info(out)
        self.verify("Test OK" in out, "Test Failed")
