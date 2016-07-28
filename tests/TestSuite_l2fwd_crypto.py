# BSD LICENSE
#
# Copyright(c) 2010-2014 Intel Corporation. All rights reserved.
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

import dts
import time

from test_case import TestCase


class TestL2fwdCrypto(TestCase):

    def set_up_all(self):

        self.core_config = "1S/4C/1T"
        self.number_of_ports = 2
        self.dut_ports = self.dut.get_ports(self.nic)
        self.verify(len(self.dut_ports) >= self.number_of_ports,
                    "Not enough ports for " + self.nic)
        self.ports_socket = self.dut.get_numa_id(self.dut_ports[0])

        self.logger.info("core config = " + self.core_config)
        self.logger.info("number of ports = " + str(self.number_of_ports))
        self.logger.info("dut ports = " + str(self.dut_ports))
        self.logger.info("ports_socket = " + str(self.ports_socket))

        self.core_mask = dts.create_mask(self.dut.get_core_list(
                                         self.core_config,
                                         socket=self.ports_socket))
        self.port_mask = dts.create_mask([self.dut_ports[0],
                                         self.dut_ports[1]])

        self.tx_port = self.tester.get_local_port(self.dut_ports[0])
        self.rx_port = self.tester.get_local_port(self.dut_ports[1])

        self.tx_interface = self.tester.get_interface(self.tx_port)
        self.rx_interface = self.tester.get_interface(self.rx_port)

        self.logger.info("core mask = " + self.core_mask)
        self.logger.info("port mask = " + self.port_mask)
        self.logger.info("tx interface = " + self.tx_interface)
        self.logger.info("rx interface = " + self.rx_interface)

        # Rebuild the dpdk with cryptodev pmds
        self.dut.send_expect("export AESNI_MULTI_BUFFER_LIB_PATH=/root/ipsec_043/code/", "#")
        self.dut.send_expect("export LIBSSO_SNOW3G_PATH=/root/libsso_snow3g/snow3g/", "#")
        self.dut.send_expect("export LIBSSO_KASUMI_PATH=/root/LibSSO_0_3_1/isg_cid-wireless_libs/ciphers/kasumi/", "#")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=n$/CONFIG_RTE_LIBRTE_PMD_QAT=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=n$/CONFIG_RTE_LIBRTE_PMD_KASUMI=y/' config/common_base", "# ")
        self.dut.build_install_dpdk(self.dut.target)

        # l2fwd-crypto compile
        out = self.dut.build_dpdk_apps("./examples/l2fwd-crypto")
        self.verify("Error" not in out, "Compilation error")
        self.verify("No such" not in out, "Compilation error")

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

    def test_qat_AES(self):

        result = True

        self.logger.info("Test qat_c_AES_CBC_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_AES_CBC_01"):
            result = False

        self.logger.info("Test qat_c_AES_CTR_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_AES_CTR_01"):
            result = False

        self.logger.info("Test qat_c_AES_GCM_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_AES_GCM_01"):
            result = False

        self.verify(result, True)

    def test_qat_SHA(self):

        result = True

        self.logger.info("Test qat_h_SHA1_HMAC_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_SHA1_HMAC_01"):
            result = False

        self.logger.info("Test qat_h_SHA256_HMAC_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_SHA256_HMAC_01"):
            result = False

        self.logger.info("Test qat_h_SHA512_HMAC_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_SHA512_HMAC_01"):
            result = False

        self.verify(result, True)

    def test_qat_AES_XCBC_MAC(self):

        result = True

        self.logger.info("Test qat_h_AES_XCBC_MAC_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_AES_XCBC_MAC_01"):
            result = False

        self.verify(result, True)

    def test_qat_SNOW3G(self):

        result = True

        self.logger.info("Test qat_c_UEA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_c_UEA2_01"):
            result = False

        self.logger.info("Test qat_h_UIA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_h_UIA2_01"):
            result = False

        self.verify(result, True)

    def test_qat_AES_GCM_AES_GCM(self):

        result = True

        self.logger.info("Test qat_ch_AES_GCM_AES_GCM_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "qat_ch_AES_GCM_AES_GCM_01"):
            result = False

        self.verify(result, True)

    def test_aesni_AES_GCM_AES_GCM(self):

        result = True

        self.logger.info("Test aesni_ch_AES_GCM_AES_GCM_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "aesni_ch_AES_GCM_AES_GCM_01"):
            result = False

        self.verify(result, True)

    def test_kasumi_KASUMI(self):

        result = True

        self.logger.info("Test kasumi_c_F8_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "kasumi_c_F8_01"):
            result = False

        self.logger.info("Test kasumi_h_F9_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "kasumi_h_F9_01"):
            result = False

        self.verify(result, True)

    def test_null_NULL(self):

        result = True

        self.logger.info("Test null_c_NULL_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "null_c_NULL_01"):
            result = False

        self.verify(result, True)

    def test_snow3g_SNOW3G(self):

        result = True

        self.logger.info("Test snow3g_c_UEA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "snow3g_c_UEA2_01"):
            result = False

        self.logger.info("Test snow3g_h_UIA2_01")
        if not self.__execute_l2fwd_crypto_test(
                test_vectors, "snow3g_h_UIA2_01"):
            result = False

        self.verify(result, True)

    def __execute_l2fwd_crypto_test(self, test_vectors, test_vector_name):

        if test_vector_name not in test_vectors:
            self.logger.warn("SKIP : " + test_vector_name)
            return True

        test_vector = test_vectors[test_vector_name]

        result = True
        cmd_str = self.__test_vector_to_cmd(test_vector,
                                            core_mask=self.core_mask,
                                            port_mask=self.port_mask)

        self.dut.send_expect(cmd_str, "==", 30)

        self.tester.send_expect("rm -rf %s.pcap" % (self.rx_interface), "#")
        self.tester.send_expect("tcpdump -w %s.pcap -i %s &" % (self.rx_interface, self.rx_interface), "#")
        # Wait 5 sec for tcpdump stable
        time.sleep(5)

        payload = self.__format_hex_to_param(test_vector["input"], "\\x", "\\x")

        PACKET_COUNT = 65

        self.tester.scapy_foreground()
        self.tester.scapy_append('sendp([Ether(src="52:00:00:00:00:00")/IP(src="192.168.1.1",dst="192.168.1.2")/Raw(load=\"%s\")], iface="%s", count=%s)' % (payload, self.tx_interface, PACKET_COUNT))

        self.tester.scapy_execute()

        time.sleep(5)

        self.tester.send_expect("killall tcpdump", "#")
        self.tester.send_expect("^C", "#")

        # Wait 5 secs for tcpdump exit
        time.sleep(5)

        self.tester.send_expect("scapy", ">>>")
        self.tester.send_expect("p=rdpcap('%s.pcap', count=%s)" % (self.rx_interface, PACKET_COUNT), ">>>")

        hex_list = []
        for i in range(PACKET_COUNT):
            cmd = "linehexdump(p[%s],onlyhex=1)" % i
            hex_list.append(self.tester.send_expect(cmd, ">>>"))

        # Exit the scapy
        self.tester.send_expect("exit()", "#", 60)

        for hex_str in hex_list:
            packet_hex = hex_str.split(" ")
            # self.logger.info(hex_str)
            # self.logger.info(packet_hex)

            cipher_offset = 34
            cipher_length = len(test_vector["output_cipher"])/2
            if cipher_length == 0:
                cipher_length = len(test_vector["input"])/2
            cipher_text = "".join(packet_hex[cipher_offset:cipher_offset+cipher_length])
            # self.logger.info("Cipher text in packet = " + cipher_text)
            # self.logger.info("Ref Cipher text       = " + test_vector["output_cipher"])
            if str.lower(cipher_text) == str.lower(test_vector["output_cipher"]):
                self.logger.info("Cipher Matched.")
            else:
                if test_vector["output_cipher"] != "":
                    result = False
                    self.logger.info("Cipher NOT Matched.")
                    self.logger.info("Cipher text in packet = " + cipher_text)
                    self.logger.info("Ref Cipher text       = " + test_vector["output_cipher"])
                else:
                    self.logger.info("Skip Cipher, Since no cipher text set")

            hash_offset = cipher_offset + cipher_length
            hash_length = len(test_vector["output_hash"])/2
            if hash_length != 0:
                hash_text = "".join(packet_hex[hash_offset:hash_offset+hash_length])
                # self.logger.info("Hash text in packet = " + hash_text)
                # self.logger.info("Ref Hash text       = " + test_vector["output_hash"])
                if str.lower(hash_text) == str.lower(test_vector["output_hash"]):
                    self.logger.info("Hash Matched")
                else:
                    result = False
                    self.logger.info("Hash NOT Matched")
                    self.logger.info("Hash text in packet = " + hash_text)
                    self.logger.info("Ref Hash text       = " + test_vector["output_hash"])
            else:
                self.logger.info("Skip Hash, Since no hash text set")

        # Close l2fwd-crypto
        # self.dut.send_expect("killall -9 l2fwd-crypto", "# ", 15)
        self.dut.send_expect("^C", "# ", 15)

        if result:
            self.logger.info("PASSED")
        else:
            self.logger.info("FAILED")

        return result

    def tear_down(self):
        pass

    def tear_down_all(self):
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=y$/CONFIG_RTE_LIBRTE_PMD_QAT=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=y$/CONFIG_RTE_LIBRTE_PMD_KASUMI=n/' config/common_base", "# ")

    def __test_vector_to_cmd(self, test_vector, core_mask="", port_mask=""):
        L2FWD_CRYPTO_APP = "./examples/l2fwd-crypto/build/app/l2fwd-crypto"
        EAL_CORE_MASK = " -cf" if core_mask == "" else " -c" + core_mask
        EAL_MM_CHANNEL = " -n4"
        EAL_SEP = " --"
        PORT_MASK = "" if port_mask == "" else " -p" + port_mask
        QUEUE_NUM = ""

        vdev = ""
        if self.__check_field_in_vector(test_vector, "vdev"):
            vdev = " --vdev " + test_vector["vdev"]

        chain = ""
        if self.__check_field_in_vector(test_vector, "chain"):
            chain = " --chain " + test_vector["chain"]

        cdev_type = ""
        if self.__check_field_in_vector(test_vector, "cdev_type"):
            cdev_type = " --cdev_type " + test_vector["cdev_type"]

        cipher_algo = ""
        if self.__check_field_in_vector(test_vector, "cipher_algo"):
            cipher_algo = " --cipher_algo " + test_vector["cipher_algo"]

        cipher_op = ""
        if self.__check_field_in_vector(test_vector, "cipher_op"):
            cipher_op = " --cipher_op " + test_vector["cipher_op"]

        cipher_key = ""
        if self.__check_field_in_vector(test_vector, "cipher_key"):
            cipher_key = " --cipher_key " + self.__format_hex_to_param(test_vector["cipher_key"])

        iv = ""
        if self.__check_field_in_vector(test_vector, "iv"):
            iv = " --iv " + self.__format_hex_to_param(test_vector["iv"])

        auth_algo = ""
        if self.__check_field_in_vector(test_vector, "auth_algo"):
            auth_algo = " --auth_algo " + test_vector["auth_algo"]

        auth_op = ""
        if self.__check_field_in_vector(test_vector, "auth_op"):
            auth_op = " --auth_op " + test_vector["auth_op"]

        auth_key = ""
        if self.__check_field_in_vector(test_vector, "auth_key"):
            auth_key = " --auth_key " + self.__format_hex_to_param(test_vector["auth_key"])

        auth_key_random_size = ""
        if self.__check_field_in_vector(test_vector, "auth_key_random_size"):
            auth_key_random_size = " --auth_key_random_size " + test_vector["auth_key_random_size"]

        aad = ""
        if self.__check_field_in_vector(test_vector, "aad"):
            aad = " --aad " + self.__format_hex_to_param(test_vector["aad"])

        aad_random_size = ""
        if self.__check_field_in_vector(test_vector, "aad_random_size"):
            aad_random_size = " --aad_random_size " + test_vector["aad_random_size"]

        cmd_str = "".join([L2FWD_CRYPTO_APP, EAL_CORE_MASK, EAL_MM_CHANNEL, vdev, vdev, EAL_SEP,
                          PORT_MASK, QUEUE_NUM, chain, cdev_type, cipher_algo, cipher_op, cipher_key,
                          iv, auth_algo, auth_op, auth_key, auth_key_random_size, aad, aad_random_size])

        return cmd_str

    def __check_field_in_vector(self, test_vector, field_name):
        if field_name in test_vector and test_vector[field_name]:
            return True
        return False

    def __format_hex_to_param(self, hex_str, sep=":", prefix=""):
        if not hex_str:
            return ""
        if len(hex_str) == 1:
            return prefix + "0" + hex_str

        result = prefix + hex_str[0:2]
        for i in range(2, len(hex_str), 2):
            if len(hex_str) < i + 2:
                result = result + sep + "0" + hex_str[i:]
            else:
                result = result + sep + hex_str[i:i+2]

        return result

test_vectors = {

    "qat_c_AES_CBC_01": {
        "vdev": "",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "AES_CBC",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "96A702D1CC8DD6D625D971915FCE8C40B8C522042B7126D51BB204CECA048C13793B75FF84A4B524370A45534C2BC476",
        "output_hash": "",
    },

    "qat_c_AES_CTR_01": {
        "vdev": "",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "AES_CTR",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "1B851AA4507FE154E0D28549D742FB4B1372FD85770963878BCBEC1E5AB51ECD0B3C85A2000DB4E9ACD3D95CDD38FD56",
        "output_hash": "",
    },

    "qat_c_AES_GCM_01": {
        "vdev": "",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "AES_GCM",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "1b851aa4507fe154e0d28549d742fb4b1372fd85770963878bcbec1e5ab51ecd0b3c85a2000db4e9acd3d95cdd38fd56",
        "output_hash": "",
    },

    "qat_h_SHA1_HMAC_01": {
        "vdev": "",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "SHA1_HMAC",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111100000000000000000000000000000000",
        "output_cipher": "",
        "output_hash": "12E2EF8B7EBFE556C73307B04E1E46D12BA34884"
    },

    "qat_h_SHA256_HMAC_01": {
        "vdev": "",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "SHA256_HMAC",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111100000000000000000000000000000000",
        "output_cipher": "",
        "output_hash": "AC9E0BA3A0716F4F4A2734B407BE28D6F276CE0472B827D6EE47B7E518C2BC0D"
    },

    "qat_h_SHA512_HMAC_01": {
        "vdev": "",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "SHA512_HMAC",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "1111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111110000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "output_cipher": "",
        "output_hash": "C8917E7490FC2CFF0CFDD0509C1C0D711CD27FFDFAAEA375E123F25F7532D4FA7D02D95CD52FAC8A27E21B3F5F734241897A37BB8953C52FFADB3B605A864569"
    },

    "qat_h_AES_XCBC_MAC_01": {
        "vdev": "",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "AES_XCBC_MAC",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "",
        "output_hash": "A7AD120ED744A9EC0618C0D9"
    },

    "qat_ch_AES_CBC_SHA1_HMAC_01": {
        "vdev": "",
        "chain": "CIPHER_HASH",
        "cdev_type": "ANY",
        "cipher_algo": "AES_CBC",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "SHA1_HMAC",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "96A702D1CC8DD6D625D971915FCE8C40B8C522042B7126D51BB204CECA048C13793B75FF84A4B524370A45534C2BC476",
        "output_hash": "2D6EFD5929812460E2DE34A1BD768F209C985143BA7333E8D59EFED291517EF7"
    },

    "qat_c_UEA2_01": {
        "vdev": "",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "SNOW3G_UEA2",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "fa0d2ff5dbf973e7082b128396fbc2c1ff5721099a1eb82918e66c1fa1b8fd52ce1763963f73859595d89b0b8d3907a8",
        "output_hash": ""
    },

    "qat_h_UIA2_01": {
        "vdev": "",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "SNOW3G_UIA2",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "000102030405060708090a0b0c0d0e0f",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "",
        "output_hash": "741D4316"
    },

    "snow3g_c_UEA2_01": {
        "vdev": "cryptodev_snow3g_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "SNOW3G_UEA2",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "fa0d2ff5dbf973e7082b128396fbc2c1ff5721099a1eb82918e66c1fa1b8fd52ce1763963f73859595d89b0b8d3907a8",
        "output_hash": ""
    },

    "snow3g_h_UIA2_01": {
        "vdev": "cryptodev_snow3g_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "SNOW3G_UIA2",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "000102030405060708090a0b0c0d0e0f",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "",
        "output_hash": "741D4316"
    },

    "kasumi_c_F8_01": {
        "vdev": "cryptodev_kasumi_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "KASUMI_F8",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "0001020304050607",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "ede654ff0caab546b654cd7a3b0a4199e957579214f45bd7e25fcbbda41e38fc885fbbd6195cf8e22905480191b2f861",
        "output_hash": ""
    },

    "kasumi_h_F9_01": {
        "vdev": "cryptodev_kasumi_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "HASH_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "",
        "cipher_op": "",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "KASUMI_F9",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        # aad length min=8 max=8
        "aad": "0001020304050607",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "",
        "output_hash": "D1C2BE1E"
    },

    "null_c_NULL_01": {
        "vdev": "cryptodev_null_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "CIPHER_ONLY",
        "cdev_type": "ANY",
        "cipher_algo": "NULL",
        "cipher_op": "ENCRYPT",
        "cipher_key": "",
        "iv": "",
        "auth_algo": "",
        "auth_op": "",
        "auth_key": "",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_hash": ""
    },

    "qat_ch_AES_GCM_AES_GCM_01": {
        "vdev": "",
        "chain": "CIPHER_HASH",
        "cdev_type": "ANY",
        "cipher_algo": "AES_GCM",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "AES_GCM",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        # aad length min=8 max=12
        "aad": "0001020304050607",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "1372fd85770963878bcbec1e5ab51ecd0b3c85a2000db4e9acd3d95cdd38fd565c1abac3884e8e167332357956a4c21f",
        "output_hash": "00A2EBC33A8A1C8C"
    },

    "aesni_ch_AES_GCM_AES_GCM_01": {
        "vdev": "cryptodev_aesni_gcm_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "CIPHER_HASH",
        "cdev_type": "ANY",
        "cipher_algo": "AES_GCM",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "AES_GCM",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        # aad length min=8 max=12
        "aad": "0001020304050607",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "1372fd85770963878bcbec1e5ab51ecd0b3c85a2000db4e9acd3d95cdd38fd565c1abac3884e8e167332357956a4c21f",
        "output_hash": "00A2EBC33A8A1C8C"
    },

    "aesni_ch_AES_CBC_SHA1_HMAC_01": {
        "vdev": "cryptodev_aesni_mb_pmd,socket_id=1,max_nb_sessions=128",
        "chain": "CIPHER_HASH",
        "cdev_type": "ANY",
        "cipher_algo": "AES_CBC",
        "cipher_op": "ENCRYPT",
        "cipher_key": "000102030405060708090a0b0c0d0e0f",
        "iv": "000102030405060708090a0b0c0d0e0f",
        "auth_algo": "SHA1_HMAC",
        "auth_op": "GENERATE",
        "auth_key": "000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f000102030405060708090a0b0c0d0e0f",
        "auth_key_random_size": "",
        "aad": "",
        "aad_random_size": "",
        "input": "111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
        "output_cipher": "96A702D1CC8DD6D625D971915FCE8C40B8C522042B7126D51BB204CECA048C13793B75FF84A4B524370A45534C2BC476",
        "output_hash": "2D6EFD5929812460E2DE34A1BD768F209C985143BA7333E8D59EFED291517EF7"
    },

}
