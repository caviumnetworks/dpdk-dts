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

import hmac
import hashlib
import binascii
import time
import os
import sys
import dts
import utils
import commands
import copy
import time
import random
from test_case import TestCase


class TestCryptoPerf(TestCase):

    def set_up_all(self):

        self.filename = ""
        self.__LTCY = ""
        self.__THPT = ""
        self.qat_wilte_list = []
        self.total_buffer_list = []
        self.waiting_to_coll_buf = []

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
        self.dut.send_expect("export AESNI_MULTI_BUFFER_LIB_PATH=/root/ipsec_044/code/", "#")
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

        # test-crypto-perf compile
        out = self.dut.build_dpdk_apps("./app/test-crypto-perf")

        # Bind QAT VF devices
        out = self.dut.send_expect("lspci -d:37c9|awk '{print $1}'", "# ", 10)
        self.dut.send_expect('echo "8086 37c9" > /sys/bus/pci/drivers/igb_uio/new_id', "# ", 10)
        for line in out.replace("\r", "\n").replace("\n\n", "\n").split("\n"):
            cmd = "echo 0000:{} > /sys/bus/pci/devices/0000\:{}/driver/unbind".format(line, line.replace(":", "\:"))
            qat_device = "0000:{}".format(line, line.replace(":", "\:"))
            self.qat_wilte_list.append(qat_device)
            self.dut.send_expect(cmd, "# ", 10)
            cmd = "echo 0000:{} > /sys/bus/pci/drivers/igb_uio/bind".format(line)
            self.dut.send_expect(cmd, "# ", 10)
        self.__check_buffer_size_number()

    def set_up(self):
        pass

    def test_qat_AES_CBC_perf(self):
        result = True
        self.logger.info("Test qat_c_AES_CBC_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_AES_CBC_Perf")
        self.verify(result, True)

    def test_qat_AES_CTR_perf(self):
        result = True
        self.logger.info("Test qat_c_AES_CTR_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_AES_CTR_Perf")
        self.verify(result, True)

    def test_qat_AES_GCM_perf(self):
        result = True
        self.logger.info("Test qat_c_AES_GCM_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_AES_GCM_Perf")
        self.verify(result, True)

    def test_qat_3DES_CBC_perf(self):
        result = True
        self.logger.info("Test qat_c_3DES_CTR_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_3DES_CTR_Perf")
        self.verify(result, True)

    def test_qat_3DES_CTR_perf(self):
        result = True
        self.logger.info("Test qat_c_3DES_CBC_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_3DES_CBC_Perf")
        self.verify(result, True)

    def test_qat_KASUMI_perf(self):
        result = True
        self.logger.info("Test qat_c_KASUMMI_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_KASUMMI_Perf")
        self.verify(result, True)

    def test_qat_SNOW3G_perf(self):
        result = True
        self.logger.info("Test qat_c_SNOW3G_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_c_SNOW3G_Perf")
        self.verify(result, True)

    def test_qat_HASH_perf(self):
        result = True
        self.logger.info("Test qat_h_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_h_auto_Perf")
        self.verify(result, True)

    def test_qat_NULL_perf(self):
        result = True
        self.logger.info("Test qat_NULL_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "qat_NULL_auto_Perf")
        self.verify(result, True)

    def test_aesni_mb_AES_CBC_perf(self):
        result = True
        self.logger.info("Test aesni_mb_c_AES_CBC_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "aesni_mb_c_AES_CBC_Perf")
        self.verify(result, True)

    def test_aesni_mb_AES_CTR_perf(self):
        result = True
        self.logger.info("Test aesni_mb_c_AES_CTR_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "aesni_mb_c_AES_CTR_Perf")
        self.verify(result, True)

    def test_aesni_mb_HASH_perf(self):
        result = True
        self.logger.info("Test aesni_mb_h_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "aesni_mb_h_auto_Perf")
        self.verify(result, True)

    def test_aesni_gcm_AES_GCM_perf(self):
        result = True
        self.logger.info("Test aes_gcm_c_AES_GCM_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "aes_gcm_c_AES_GCM_Perf")
        self.verify(result, True)

    def test_kasumi_KASUMI_perf(self):
        result = True
        self.logger.info("Test kasumi_KASUMI_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "kasumi_KASUMI_auto_Perf")
        self.verify(result, True)

    def test_snow3g_SNOW3G_perf(self):
        result = True
        self.logger.info("Test snow3g_SNOW3G_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "snow3g_SNOW3G_auto_Perf")
        self.verify(result, True)

    def test_zuc_ZUC_perf(self):
        result = True
        self.logger.info("Test zuc_ZUC_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "zuc_ZUC_auto_Perf")
        self.verify(result, True)

    def test_null_NULL_perf(self):
        result = True
        self.logger.info("Test null_NULL_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "null_NULL_auto_Perf")
        self.verify(result, True)

    def test_openssl_AES_CBC_perf(self):
        result = True
        self.logger.info("Test openssl_c_AES_CBC_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "openssl_c_AES_CBC_Perf")
        self.verify(result, True)

    def test_openssl_AES_CTR_perf(self):
        result = True
        self.logger.info("Test openssl_c_AES_CTR_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "openssl_c_AES_CTR_Perf")
        self.verify(result, True)

    def test_openssl_AES_GCM_perf(self):
        result = True
        self.logger.info("Test openssl_c_AES_GCM_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "openssl_c_AES_GCM_Perf")
        self.verify(result, True)

    def test_openssl_3DES_CBC_perf(self):
        result = True
        self.logger.info("Test openssl_c_3DES_CBC_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "openssl_c_3DES_CBC_Perf")
        self.verify(result, True)

    def test_openssl_3DES_CTR_perf(self):
        result = True
        self.logger.info("Test openssl_c_3DES_CTR_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "openssl_c_3DES_CTR_Perf")
        self.verify(result, True)

    def test_openssl_HASH_perf(self):
        result = True
        self.logger.info("Test openssl_h_HASH_auto_Perf")
        result = self.__execute_crypto_perf_test(
                 test_vectors, "openssl_h_HASH_auto_Perf")
        self.verify(result, True)

    def test_calculatr_case_number(self):

        self.__calculate_totall_cases_numb()

    def __execute_crypto_perf_test(self, test_vectors, test_vector_name):
        failed_count = 0
        result = True

        if test_vector_name not in test_vectors:
            self.logger.warn("SKIP : " + test_vector_name)
            return True

        test_vector = test_vectors[test_vector_name]

        test_vector_list = self.__test_vector_to_vector_list(test_vector,
                                                             core_mask=self.core_mask,
                                                             port_mask=self.port_mask)

        currently_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        case_line = "<<<[{time}][{name}] Total Generated: [{num}] Cases>>>\n".format(
                     time=currently_time, name=test_vector_name, num=len(test_vector_list))
        self.logger.info(case_line)

        for test_vector in test_vector_list:
            self.logger.debug(test_vector)
            cmd_str = self.__test_vector_to_cmd(test_vector,
                                                core_mask=self.core_mask,
                                                port_mask=self.port_mask)
            out = self.dut.send_expect(cmd_str, "]# ", 600)
            self.logger.info("Test Result:\n*********************\n {ret}".format(ret=out))
            ret = self.__result_collection(out, test_vector)
            if ret is False:
                failed_count = failed_count + 1
            result = result and ret
        self.logger.info(("[{name}] Total Failed cases: [{num}]\n".format(
                            name=test_vector_name, num=failed_count)))
        return result

    def tear_down(self):
        pass

    def tear_down_all(self):
        f = open(self.filename, "a")
        currently_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        f.write("...Test Finished [{time}]...".format(time=currently_time))
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_QAT=y$/CONFIG_RTE_LIBRTE_PMD_QAT=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_GCM=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=y$/CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_SNOW3G=y$/CONFIG_RTE_LIBRTE_PMD_SNOW3G=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_KASUMI=y$/CONFIG_RTE_LIBRTE_PMD_KASUMI=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_OPENSSL=y$/CONFIG_RTE_LIBRTE_PMD_OPENSSL=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=y$/CONFIG_RTE_LIBRTE_PMD_AESNI_MB=n/' config/common_base", "# ")
        self.dut.send_expect("sed -i 's/CONFIG_RTE_LIBRTE_PMD_ZUC=y$/CONFIG_RTE_LIBRTE_PMD_ZUC=n/' config/common_base", "# ")
        f.close()

    def __check_buffer_size_number(self):
        buf_numb = 0
        buf_list = []
        for vector_name in test_vectors:
            temp_numb = 0
            temp_list = []
            vector = test_vectors[vector_name]
            if vector["buffer-sz"] != "":
                if vector["buffer-sz"].find(",") != -1:
                    buf = vector["buffer-sz"].split(",")
                    temp_list = copy.deepcopy(buf)
                    temp_numb = len(buf)
                elif vector["buffer-sz"].find(":") != -1:
                    buf = vector["buffer-sz"].split(":")
                    if len(buf) != 3:
                        self.logger.info("buffer-sz format is invalid")
                    else:
                        temp = buf[0]
                        while temp <= buf[2]:
                            temp_list.append(temp)
                            temp_numb = temp_numb + 1
                            temp = temp + buf[1]
                else:
                    temp_numb = 1
            if temp_numb > buf_numb:
                buf_numb = temp_numb
                buf_list = copy.deepcopy(temp_list)

        head = "PMD,chain,ptest,cipher_algo,cipher_op,cipher_key,iv,auth_algo,auth_op,auth_key,aad,digest,"
        self.__LTCY = head
        self.__THPT = head
        self.total_buffer_list = copy.deepcopy(buf_list)
        for buf_sz in buf_list:
            self.__LTCY = self.__LTCY + "buf{buffer} Ltcy(us),buf{buffer} Cyc,".format(buffer=buf_sz)
            self.__THPT = self.__THPT + "buf{buffer} Thpt(Gbps),buf{buffer} Ops,".format(buffer=buf_sz)
        self.__LTCY = self.__LTCY[:len(self.__LTCY) - 1] + "\n"
        self.__THPT = self.__THPT[:len(self.__THPT) - 1] + "\n"

        str_pid = str(os.getpid())
        self.filename = "/tmp/test_crypto_perf_{0}.csv".format(time.time())
        f = open(self.filename, "a")
        if f is None:
            self.logger.info("open scv file failed.")
            return

        current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        f.write("...Test Start [{time}]...\n".format(time=current_time))
        f.write(self.__THPT)
        f.write(self.__LTCY)
        f.close()

    def __calculate_totall_cases_numb(self):
        alg_map = {}
        pmd_map = {}
        map_combine = {}
        count = 0
        alg = ""
        pmd = ""
        alg_list = ["AES_CBC", "AES_CTR", "AES_GCM", "3DES_CBC",
                    "3DES_CTR", "SNOW3G", "KASUMI", "ZUC", "NULL", "MD_SHA"]
        pmd_list = ["qat", "aesni_mb", "aesni_gcm", "snow3g",
                    "kasumi", "zuc", "openssl", "null"]
        valid_map = {
                    "qat": ["AES_CBC", "AES_CTR", "AES_GCM", "3DES_CBC",
                            "3DES_CTR", "SNOW3G", "KASUMI", "NULL", "MD_SHA"],
                    "aesni_mb": ["AES_CBC", "AES_CTR"],
                    "aesni_gcm": ["AES_GCM"],
                    "snow3g": ["SNOW3G"],
                    "kasumi": ["KASUMI"],
                    "zuc": ["ZUC"],
                    "openssl": ["AES_CBC", "AES_CTR", "AES_GCM", "3DES_CBC", "3DES_CTR", "MD_SHA"],
                    "null": ["NULL"]
                    }

        for index, value in test_vectors.iteritems():
            test_vector_list = self.__test_vector_to_vector_list(value,
                                                                 core_mask="-1",
                                                                 port_mask=self.port_mask)
            count = count + len(test_vector_list)
            for i in alg_list:
                if (index.upper()).find(i) != -1:
                    alg = i
                    if i in alg_map:
                        alg_map[i] += len(test_vector_list)
                    else:
                        alg_map[i] = len(test_vector_list)
            for j in pmd_list:
                if (index).find(j) != -1:
                    pmd = j
                    if j in pmd_map:
                        pmd_map[j] += len(test_vector_list)
                    else:
                        pmd_map[j] = len(test_vector_list)
            if (pmd != "") and (alg in valid_map[pmd]):
                temp_str = pmd + "_" + alg
                if temp_str in map_combine:
                    map_combine[temp_str] += len(test_vector_list)
                else:
                    map_combine[temp_str] = len(test_vector_list)
        for k, v in alg_map.iteritems():
            self.logger.info("Total {name} cases:\t\t\t{number}".format(name=k, number=v))
        for k, v in pmd_map.iteritems():
            self.logger.info("Total {name} cases:\t\t\t{number}".format(name=k, number=v))
        for k, v in map_combine.iteritems():
            self.logger.info("Total {name} cases:\t\t\t{number}".format(name=k, number=v))
        self.logger.info("Total cases:\t\t\t {0}".format(count))

    def __parse_througuput_data(self, original_out):
        throughPut_line = ""
        count = 0
        data_finished = False
        index = original_out.find("# lcore id")
        if index == -1:
            seg_index = original_out.find("Segmentation fault")
            throughPut_line = "sgtf,sgtf" if seg_index != -1 else "otf,otf"
        else:
            value_data = (original_out[index:]).replace("\r", "")
            value_list = (value_data.replace("\n\n", "\n")).split("\n")
            temp_list = filter(lambda x: (x.find("lcore id") == -1) and (x != ""), value_list)
            length = len(temp_list)
            for data_list in temp_list:
                count = count + 1
                value_data_list = (data_list).split(";")
                if length == count:
                    data_finished = True
                throughPut_line = throughPut_line + self.__buffer_size_result_check(
                                           value_data_list[1], value_data_list[8],
                                           value_data_list[7], data_finished)
        throughPut_line = throughPut_line + "\n"
        return throughPut_line

    def __parse_latency_data(self, original_out):
        latency = ""
        count = 0
        data_finished = False
        index = original_out.find("# lcore")
        if index == -1:
            seg_index = original_out.find("Segmentation fault")
            latency = "sgtf,sgtf" if seg_index != -1 else "otf,otf"
        else:
            value_data = (original_out[index:]).replace("\r", "")
            value_list = (value_data.replace("\r", "")).split("\n")
            temp_list = filter(lambda x: (x.find("lcore") == -1) and (x != ""), value_list)
            length = len(temp_list)
            for data_list in temp_list:
                count = count + 1
                value_data_list = data_list.split(";")
                if length == count:
                    data_finished = True
                latency = latency + self.__buffer_size_result_check(
                                        value_data_list[1], value_data_list[5],
                                        value_data_list[4], data_finished)
        latency = latency + "\n"
        return latency

    def __buffer_size_result_check(self, buf_size, thpt_ltcy, ops_cycl, finished):
        count = 0
        result = ""
        buffer_sz = copy.deepcopy(self.total_buffer_list)

        for buf in self.waiting_to_coll_buf:
            if int(buf_size) > int(buf):
                count = count + 1
                result = result + "*,*,"
            elif int(buf_size) == int(buf):
                count = count + 1
                self.waiting_to_coll_buf = self.waiting_to_coll_buf[count:]
                result = result + "{throughput_latenct},{ops_cycle},".format(
                             buffer=buf_size, throughput_latenct=thpt_ltcy, ops_cycle=ops_cycl)
            else:
                if finished is True:
                    result = result + "*,*,"
                else:
                    break
        return result

    def __parse_dut_out_data(self, original_out, test_vector):
        perf_data_collect = ""
        if test_vector["ptest"] == "latency":
            perf_data_collect = self.__parse_latency_data(original_out)
        else:
            perf_data_collect = self.__parse_througuput_data(original_out)

        return perf_data_collect

    def __valid_data_write_line(self, test_vector):
        iv = "{IV}".format(IV=test_vector["cipher-iv-sz"]) if test_vector["cipher-iv-sz"] != "" else "/"
        aad = "{Aad}".format(Aad=test_vector["auth-aad-sz"]) if test_vector["auth-aad-sz"] != "" else "/"
        ptest = (test_vector["ptest"]).upper()
        optype = test_vector["optype"]
        digest = "{dgst}".format(dgst=test_vector["auth-digest-sz"]) if test_vector["auth-digest-sz"] != "" else "/"
        auth_op = (test_vector["auth-op"]).capitalize() if test_vector["auth-op"] != "" else "/"
        devtype = ((test_vector["devtype"]).replace("crypto_", "")).upper()
        auth_key = "{key}".format(key=test_vector["auth-key-sz"]) if test_vector["auth-key-sz"] != "" else "/"
        cipher_op = (test_vector["cipher-op"]).capitalize() if test_vector["cipher-op"] != "" else "-"
        auth_algo = ((test_vector["auth-algo"]).replace("-", "_")).upper() if test_vector["auth-algo"] != "" else "/"
        cipher_key = "{key}".format(key=test_vector["cipher-key-sz"]) if test_vector["cipher-key-sz"] != "" else "/"
        cipher_algo = ((test_vector["cipher-algo"]).replace("-", "_")).upper() if test_vector["cipher-algo"] != "" else "/"

        if optype.find("only") != -1:
            chain = (optype.replace("-", "_")).upper()
        else:
            chain = ((optype.replace("-then-", "_")).replace("auth", "hash")).upper()

        w_line = "{pmd},{Chain},{test_type},{cAlg},{cop},{cKey},{IV},{hAlg},{hop},{hkey},{Aad},{dgst},".format(
                pmd=devtype, Chain=chain, test_type=ptest, cAlg=cipher_algo, cop=cipher_op, cKey=cipher_key, IV=iv,
                hAlg=auth_algo, hop=auth_op, hkey=auth_key, Aad=aad, dgst=digest)

        return w_line

    def __result_collection(self, original_out, test_vector):
        result = True
        perf_line = ""
        f = open(self.filename, "a")
        if f is None:
            logger.info("open scv file failed.")
            return
        self.waiting_to_coll_buf = copy.deepcopy(self.total_buffer_list)
        perf_line = self.__valid_data_write_line(test_vector) + self.__parse_dut_out_data(original_out, test_vector)
        f.write(perf_line)

        if (perf_line.find("sgtf") != -1) or (perf_line.find("otf") != -1):
            result = False
        return result

    def __test_vector_to_cmd(self, test_vector, core_mask="", port_mask=""):
        TEST_CRYPTO_PERF = "./app/test-crypto-perf/build/app/dpdk-test-crypto-perf"
        EAL_CORE_MASK = " -cf" if core_mask == "" else " -c" + core_mask
        EAL_SEP = " --"
        QUEUE_NUM = " "
        CSV_FRIENDLY = " --csv-friendly"

        # port info
        pci_bus = ""
        for port in self.dut.ports_info:
            pci_bus = " -w " + port['pci']

        qat_bus = ""
        if len(self.qat_wilte_list) > 0:
            qat_bus = " -w " + self.qat_wilte_list[random.randint(0, len(self.qat_wilte_list) - 1)]

        vdev = ""
        if self.__check_field_in_vector(test_vector, "vdev"):
            vdev = " --vdev " + test_vector["vdev"]

        ptest = ""
        if self.__check_field_in_vector(test_vector, "ptest"):
            ptest = " --ptest " + test_vector["ptest"]

        devtype = ""
        if self.__check_field_in_vector(test_vector, "devtype"):
            devtype = " --devtype " + test_vector["devtype"]

        chain = ""
        if self.__check_field_in_vector(test_vector, "optype"):
            chain = " --optype " + test_vector["optype"]

        cipher_algo = ""
        if self.__check_field_in_vector(test_vector, "cipher-algo"):
            cipher_algo = " --cipher-algo " + test_vector["cipher-algo"]

        cipher_op = ""
        if self.__check_field_in_vector(test_vector, "cipher-op"):
            cipher_op = " --cipher-op " + test_vector["cipher-op"]

        cipher_key = ""
        if self.__check_field_in_vector(test_vector, "cipher-key-sz"):
            cipher_key = " --cipher-key-sz {size}".format(size=test_vector["cipher-key-sz"])

        iv = ""
        if self.__check_field_in_vector(test_vector, "cipher-iv-sz"):
            iv = " --cipher-iv-sz {size}".format(size=test_vector["cipher-iv-sz"])

        auth_algo = ""
        if self.__check_field_in_vector(test_vector, "auth-algo"):
            auth_algo = " --auth-algo " + test_vector["auth-algo"]

        auth_op = ""
        if self.__check_field_in_vector(test_vector, "auth-op"):
            auth_op = " --auth-op " + test_vector["auth-op"]

        auth_key = ""
        if self.__check_field_in_vector(test_vector, "auth-key-sz"):
            auth_key = " --auth-key-sz {size}".format(size=test_vector["auth-key-sz"])

        aad = ""
        if self.__check_field_in_vector(test_vector, "auth-aad-sz"):
            aad = " --auth-aad-sz {size}".format(size=test_vector["auth-aad-sz"])

        digest = ""
        if self.__check_field_in_vector(test_vector, "auth-digest-sz"):
            digest = " --auth-digest-sz {size}".format(size=test_vector["auth-digest-sz"])

        total_ops = ""
        if self.__check_field_in_vector(test_vector, "total-ops"):
            total_ops = " --total-ops {size}".format(size=test_vector["total-ops"])

        burst_size = ""
        if self.__check_field_in_vector(test_vector, "burst-sz"):
            burst_size = " --burst-sz {size}".format(size=test_vector["burst-sz"])

        buffer_size = ""
        if self.__check_field_in_vector(test_vector, "buffer-sz"):
            buffer_size = " --buffer-sz {size}".format(size=test_vector["buffer-sz"])

        cmd_str = "".join([TEST_CRYPTO_PERF, EAL_CORE_MASK, vdev, pci_bus, qat_bus, EAL_SEP, QUEUE_NUM,
                           ptest, devtype, chain, cipher_algo, cipher_op, cipher_key, iv, auth_algo,
                           auth_op, auth_key, aad, digest, total_ops, burst_size, buffer_size, CSV_FRIENDLY])

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

    def __var2list(self, var):
        var_list = var if isinstance(var, list) else [var]
        return var_list

    def __is_valid_op(self, chain, op):
        chain_op_map = {
                "aead": ["encrypt", "generate"],
                "cipher-only": ["encrypt", "decrypt"],
                "auth-only": ["generate", "verify"],
                "cipher-then-auth": ["encrypt", "generate"],
                "auth-then-cipher": ["decrypt", "verify"],
                }
        if op in chain_op_map[chain]:
            return True
        return False

    def __is_valid_size(self, key_type, algo, size):
        algo_size_map = {
                "aes-cbc": {
                    "cipher-key-sz": [16, 24, 32],
                    "cipher-iv-sz": [16]
                    },
                "aes-ctr": {
                    "cipher-key-sz": [16, 24, 32],
                    "cipher-iv-sz": [16]
                    },
                "3des-cbc": {
                    "cipher-key-sz": [16, 24],
                    "cipher-iv-sz": [8]
                    },
                "3des-ctr": {
                    "cipher-key-sz": [16, 24],
                    "cipher-iv-sz": [8]
                    },
                "aes-gcm": {
                    "cipher-key-sz": [16, 24, 32],
                    "auth-key-sz": [16, 24, 32],
                    "auth-aad-sz": [1, 2, 3, 4, 5, 6, 8, 9, 12, 16, 24, 32, 64, 128, 155, 256, 1024, 65535],
                    "cipher-iv-sz": [12, 16],
                    "auth-digest-sz": [16]
                    },
                "snow3g-uea2": {
                    "cipher-key-sz": [16],
                    "cipher-iv-sz": [16]
                    },
                "kasumi-f8": {
                    "cipher-key-sz": [16],
                    "cipher-iv-sz": [8]
                    },
                "zuc-eea3": {
                    "cipher-key-sz": [16],
                    "cipher-iv-sz": [16]
                    },
                "null": {
                    "cipher-key-sz": [0],
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "cipher-iv-sz": [0],
                    "auth-digest-sz": [0]
                    },
                "md5-hmac": {
                    "auth-key-sz": [64],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [16]
                    },
                "sha1-hmac": {
                    "auth-key-sz": [64],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [20]
                    },
                "sha2-224-hmac": {
                    "auth-key-sz": [64],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [28]
                    },
                "sha2-256-hmac": {
                    "auth-key-sz": [64],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [32]
                    },
                "sha2-384-hmac": {
                    "auth-key-sz": [128],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [48]
                    },
                "sha2-512-hmac": {
                    "auth-key-sz": [128],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [64]
                    },
                "aes-gmac": {
                    "auth-key-sz": [16, 24, 32],
                    "auth-aad-sz": [1, 2, 3, 4, 5, 6, 8, 9, 12, 16, 24, 32, 64, 128, 155, 256, 1024, 65535],
                    "auth-digest-sz": [16]
                    },
                "aes-xcbc-hmac": {
                    "auth-key-sz": [16],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [16]
                    },
                "snow3g-uia2": {
                    "auth-key-sz": [16],
                    "auth-aad-sz": [16],
                    "auth-digest-sz": [4]
                    },
                "kasumi-f9": {
                    "auth-key-sz": [16],
                    "auth-aad-sz": [8],
                    "auth-digest-sz": [4]
                    },
                "zuc-eia3": {
                    "auth-key-sz": [16],
                    "auth-aad-sz": [16],
                    "auth-digest-sz": [4]
                    },
                "md5": {
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [16]
                    },
                "sha1": {
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [20]
                    },
                "sha2-224": {
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [28]
                    },
                "sha2-256": {
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [32]
                    },
                "sha2-384": {
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [48]
                    },
                "sha2-512": {
                    "auth-key-sz": [0],
                    "auth-aad-sz": [0],
                    "auth-digest-sz": [64]
                    },
                }
        result = False
        if algo in algo_size_map:
            if key_type in algo_size_map[algo]:
                if size in algo_size_map[algo][key_type]:
                    result = True
        return result

    def __actually_aesni_mb_digest(self, vector):

        if ((vector["vdev"]).find("crypto_aesni_mb") == -1):
            return

        auth_algo_dgst_map = {
                "md5-hmac": 12,
                "sha1-hamc": 12,
                "sha2-224-hamc": 14,
                "sha2-256-hamc": 16,
                "sha2-384-hamc": 24,
                "sha2-512-hamc": 32
                }
        if vector["auth-algo"] in auth_algo_dgst_map:
            digest = auth_algo_dgst_map[vector["auth-algo"]]
            vector["auth-digest-sz"] = digest

    def __iter_optype(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        chain_list = self.__var2list(test_vector["optype"])
        for op_type in chain_list:
            test_vector = vector.copy()
            test_vector["optype"] = op_type
            self.__iter_cipher_algo(test_vector, vector_list, core_mask, port_mask)

    def __iter_cipher_algo(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "auth-only":
            test_vector["cipher-algo"] = ""
            self.__iter_cipher_op(test_vector, vector_list, core_mask, port_mask)
        else:
            cipher_algo_list = self.__var2list(test_vector["cipher-algo"])
            for cipher_algo in cipher_algo_list:
                test_vector = vector.copy()
                test_vector["cipher-algo"] = cipher_algo
                self.__iter_cipher_op(test_vector, vector_list, core_mask, port_mask)

    def __iter_cipher_op(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "auth-only":
            test_vector["cipher-op"] = ""
            self.__iter_cipher_key(test_vector, vector_list, core_mask, port_mask)
        else:
            cipher_op_list = self.__var2list(test_vector["cipher-op"])
            for cipher_op in cipher_op_list:
                if self.__is_valid_op(test_vector["optype"], cipher_op):
                    test_vector = vector.copy()
                    test_vector["cipher-op"] = cipher_op
                    self.__iter_cipher_key(test_vector, vector_list,
                                           core_mask, port_mask)

    def __iter_cipher_key(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "auth-only":
            test_vector["cipher-key-sz"] = ""
            self.__iter_iv(test_vector, vector_list, core_mask, port_mask)
        else:
            cipher_key_list = self.__var2list(test_vector["cipher-key-sz"])
            for cipher_key in cipher_key_list:
                test_vector = vector.copy()
                if isinstance(cipher_key, int):
                    if self.__is_valid_size("cipher-key-sz",
                                            test_vector["cipher-algo"],
                                            cipher_key):
                        test_vector["cipher-key-sz"] = cipher_key
                        self.__iter_iv(test_vector, vector_list, core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["cipher-key-sz"] = 0
                    self.__iter_iv(test_vector, vector_list, core_mask, port_mask)

    def __iter_iv(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "auth-only":
            test_vector["cipher-iv-sz"] = ""
            self.__iter_auth_algo(test_vector, vector_list, core_mask, port_mask)
        else:
            iv_list = self.__var2list(test_vector["cipher-iv-sz"])
            for iv in iv_list:
                test_vector = vector.copy()
                if isinstance(iv, int):
                    if self.__is_valid_size("cipher-iv-sz",
                                            test_vector["cipher-algo"],
                                            iv):
                        test_vector["cipher-iv-sz"] = iv
                        self.__iter_auth_algo(test_vector, vector_list, core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["cipher-iv-sz"] = 0
                    self.__iter_auth_algo(test_vector, vector_list,
                                          core_mask, port_mask)

    def __iter_auth_algo(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "cipher-only":
            test_vector["auth-algo"] = ""
            self.__iter_auth_op(test_vector, vector_list, core_mask, port_mask)
        else:
            auth_algo_list = self.__var2list(test_vector["auth-algo"])
            for auth_algo in auth_algo_list:
                test_vector = vector.copy()
                test_vector["auth-algo"] = auth_algo
                self.__iter_auth_op(test_vector, vector_list, core_mask, port_mask)

    def __iter_auth_op(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "cipher-only":
            test_vector["auth-op"] = ""
            self.__iter_auth_key(test_vector, vector_list, core_mask, port_mask)
        else:
            auth_op_list = self.__var2list(test_vector["auth-op"])
            for auth_op in auth_op_list:
                if self.__is_valid_op(test_vector["optype"], auth_op):
                    test_vector = vector.copy()
                    test_vector["auth-op"] = auth_op
                    self.__iter_auth_key(test_vector, vector_list,
                                         core_mask, port_mask)

    def __iter_auth_key(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "cipher-only":
            test_vector["auth-key-sz"] = ""
            self.__iter_aad(test_vector, vector_list, core_mask, port_mask)
        else:
            auth_key_list = self.__var2list(test_vector["auth-key-sz"])
            for auth_key in auth_key_list:
                test_vector = vector.copy()
                if isinstance(auth_key, int):
                    if self.__is_valid_size("auth-key-sz",
                                            test_vector["auth-algo"],
                                            auth_key):
                        test_vector["auth-key-sz"] = auth_key
                        self.__iter_aad(test_vector, vector_list, core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["auth-key-sz"] = 0
                    self.__iter_aad(test_vector, vector_list, core_mask, port_mask)

    def __iter_aad(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "cipher-only":
            test_vector["auth-aad-sz"] = ""
            self.__iter_digest(test_vector, vector_list, core_mask, port_mask)
        else:
            aad_list = self.__var2list(test_vector["auth-aad-sz"])
            for aad in aad_list:
                test_vector = vector.copy()
                if isinstance(aad, int):
                    if self.__is_valid_size("auth-aad-sz",
                                            test_vector["auth-algo"],
                                            aad):
                        test_vector["auth-aad-sz"] = aad
                        self.__iter_digest(test_vector, vector_list,
                                           core_mask, port_mask)
                    else:
                        continue
                else:
                    test_vector["auth-aad-sz"] = 0
                    self.__iter_digest(test_vector, vector_list,
                                       core_mask, port_mask)

    def __iter_digest(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        if test_vector["optype"] == "cipher-only":
            test_vector["auth-digest-sz"] = ""
            self.__iter_buffer_size(test_vector, vector_list,
                                    core_mask, port_mask)
        else:
            digest_list = self.__var2list(vector["auth-digest-sz"])
            for digest in digest_list:
                test_vector = vector.copy()
                if isinstance(digest, int):
                    if self.__is_valid_size("auth-digest-sz",
                                            test_vector["auth-algo"],
                                            digest):
                        test_vector["auth-digest-sz"] = digest
                    else:
                        continue
                else:
                    test_vector["auth-digest-sz"] = 0
                self.__actually_aesni_mb_digest(test_vector)
                self.__iter_buffer_size(test_vector, vector_list,
                                        core_mask, port_mask)

    def __iter_buffer_size(self, vector, vector_list, core_mask="", port_mask=""):
        test_vector = vector.copy()
        buffer_sz_list = vector["buffer-sz"]
        if buffer_sz_list == "":
            buffer_sz_list = "32,64,128,256, 512,768, 1024,1280,1536,1792,2048"
        test_vector["buffer-sz"] = buffer_sz_list
        vector_list.append(test_vector)

    def __test_vector_to_vector_list(self, test_vector, core_mask="", port_mask=""):
        vector_list = []
        ptest_list = self.__var2list(test_vector["ptest"])
        for ptest in ptest_list:
            test_vector["ptest"] = ptest
            self.__iter_optype(test_vector, vector_list, core_mask, port_mask)

        return vector_list

test_vectors = {

    "qat_c_AES_CBC_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["aes-cbc"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_c_AES_CTR_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["aes-ctr"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_c_AES_GCM_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["aead"],
        "cipher-algo": ["aes-gcm"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["aes-gcm", "aes-gmac", "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0, 8, 12],
        "auth-digest-sz": [8, 12, 16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_c_3DES_CBC_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["3des-cbc"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24],
        "cipher-iv-sz": [8],
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_c_3DES_CTR_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["3des-ctr"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24],
        "cipher-iv-sz": [8],
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_c_KASUMMI_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["kasumi-f8"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16],
        "cipher-iv-sz": [8],
        "auth-algo": ["kasumi-f9"],
        "auth-op": ["generate"],
        "auth-key-sz": [16],
        "auth-aad-sz": [8],
        "auth-digest-sz": [4],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_c_SNOW3G_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["snow3g-uea2"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16],
        "cipher-iv-sz": [16],
        "auth-algo": ["snow3g-uia2"],
        "auth-op": ["generate"],
        "auth-key-sz": [16],
        "auth-aad-sz": [16],
        "auth-digest-sz": [4],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_h_auto_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["auth-only"],
        "cipher-algo": "",
        "cipher-op": "",
        "cipher-key-sz": "",
        "cipher-iv-sz": "",
        "auth-algo": ["aes-gcm", "aes-gmac", "kasumi-f9", "snow3g-uia2", "md5-hmac",
                      "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac", "sha2-384-hmac",
                       "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0, 8, 12],
        "auth-digest-sz": [4, 8, 12, 16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "qat_NULL_auto_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only"],
        "cipher-algo": ["null"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [0],
        "cipher-iv-sz": [0],
        "auth-algo": ["null"],
        "auth-op": ["generate"],
        "auth-key-sz": [0],
        "auth-aad-sz": [0],
        "auth-digest-sz": [0],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "aesni_mb_c_AES_CBC_Perf": {
        "vdev": "crypto_aesni_mb_pmd",
        "devtype": "crypto_aesni_mb",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["aes-cbc"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [12, 14, 16, 24, 32],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "aesni_mb_c_AES_CTR_Perf": {
        "vdev": "crypto_aesni_mb_pmd",
        "devtype": "crypto_aesni_mb",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["aes-ctr"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [12, 14, 16, 24, 32],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "aesni_mb_h_auto_Perf": {
        "vdev": "crypto_aesni_mb_pmd",
        "devtype": "crypto_aesni_mb",
        "ptest": ["throughput", "latency"],
        "optype": ["auth-only", "cipher-then-auth"],
        "cipher-algo": "",
        "cipher-op": "",
        "cipher-key-sz": "",
        "cipher-iv-sz": "",
        "auth-algo": ["md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [8, 16, 24, 32, 40, 48, 56, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [12, 14, 16, 24, 32],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "aes_gcm_c_AES_GCM_Perf": {
        "vdev": "crypto_aesni_gcm_pmd",
        "devtype": "crypto_aesni_gcm",
        "ptest": ["throughput", "latency"],
        "optype": ["aead"],
        "cipher-algo": ["aes-gcm"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 32],
        "cipher-iv-sz": [12],
        "auth-algo": ["aes-gcm", "aes-gmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [16, 32],
        "auth-aad-sz": [1, 4, 8, 12, 16, 65535],
        "auth-digest-sz": [8, 12, 16],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "kasumi_KASUMI_auto_Perf": {
        "vdev": "crypto_kasumi_pmd",
        "devtype": "crypto_kasumi",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "auth-only", "cipher-then-auth"],
        "cipher-algo": ["kasumi-f8"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16],
        "cipher-iv-sz": [8],
        "auth-algo": ["kasumi-f9"],
        "auth-op": ["generate"],
        "auth-key-sz": [16],
        "auth-aad-sz": [8],
        "auth-digest-sz": [4],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "snow3g_SNOW3G_auto_Perf": {
        "vdev": "crypto_snow3g_pmd",
        "devtype": "crypto_snow3g",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "auth-only", "cipher-then-auth"],
        "cipher-algo": ["snow3g-uea2"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16],
        "cipher-iv-sz": [16],
        "auth-algo": ["snow3g-uia2"],
        "auth-op": ["generate"],
        "auth-key-sz": [16],
        "auth-aad-sz": [16],
        "auth-digest-sz": [4],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "zuc_ZUC_auto_Perf": {
        "vdev": "crypto_zuc_pmd",
        "devtype": "crypto_zuc",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "auth-only", "cipher-then-auth"],
        "cipher-algo": ["zuc-eea3"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16],
        "cipher-iv-sz": [16],
        "auth-algo": ["zuc-eia3"],
        "auth-op": ["generate"],
        "auth-key-sz": [16],
        "auth-aad-sz": [16],
        "auth-digest-sz": [4],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "null_NULL_auto_Perf": {
        "vdev": "",
        "devtype": "crypto_qat",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only"],
        "cipher-algo": ["null"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [0],
        "cipher-iv-sz": [0],
        "auth-algo": ["null"],
        "auth-op": ["generate"],
        "auth-key-sz": [0],
        "auth-aad-sz": [0],
        "auth-digest-sz": [0],
        "buffer-sz": "32,64,128,256,512,768,1024,1280,1536,1792,2048",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "openssl_c_AES_CBC_Perf": {
        "vdev": "crypto_openssl_pmd",
        "devtype": "crypto_openssl",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["aes-cbc"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["md5", "sha1", "sha2-224", "sha2-256", "sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [0, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "openssl_c_AES_CTR_Perf": {
        "vdev": "crypto_openssl_pmd",
        "devtype": "crypto_openssl",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["aes-ctr"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24, 32],
        "cipher-iv-sz": [16],
        "auth-algo": ["md5", "sha1", "sha2-224", "sha2-256", "sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [0, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "openssl_c_AES_GCM_Perf": {
        "vdev": "crypto_openssl_pmd",
        "devtype": "crypto_openssl",
        "ptest": ["throughput", "latency"],
        "optype": ["aead"],
        "cipher-algo": ["aes-gcm"],
        "cipher-op": ["aead"],
        "cipher-key-sz": [16],
        "cipher-iv-sz": [12, 16],
        "auth-algo": ["aes-gcm", "aes-gmac", "md5", "sha1", "sha2-224", "sha2-256",
                      "sha2-384", "sha2-512", "md5-hmac", "sha1-hmac", "sha2-224-hmac",
                      "sha2-256-hmac", "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [0, 16, 24, 32, 64, 128],
        "auth-aad-sz": [0, 8, 12],
        "auth-digest-sz": [8, 12, 16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64,128,256",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "openssl_c_3DES_CBC_Perf": {
        "vdev": "crypto_openssl_pmd",
        "devtype": "crypto_openssl",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["3des-cbc"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24],
        "cipher-iv-sz": [8],
        "auth-algo": ["md5", "sha1", "sha2-224", "sha2-256", "sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [0, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "openssl_c_3DES_CTR_Perf": {
        "vdev": "crypto_openssl_pmd",
        "devtype": "crypto_openssl",
        "ptest": ["throughput", "latency"],
        "optype": ["cipher-only", "cipher-then-auth"],
        "cipher-algo": ["3des-ctr"],
        "cipher-op": ["encrypt", "decrypt"],
        "cipher-key-sz": [16, 24],
        "cipher-iv-sz": [8],
        "auth-algo": ["md5", "sha1", "sha2-224", "sha2-256", "sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [0, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64",
        "burst-sz": 32,
        "total-ops": 10000000
    },

    "openssl_h_HASH_auto_Perf": {
        "vdev": "crypto_openssl_pmd",
        "devtype": "crypto_openssl",
        "ptest": ["throughput", "latency"],
        "optype": ["auth-only"],
        "cipher-algo": "",
        "cipher-op": "",
        "cipher-key-sz": "",
        "cipher-iv-sz": "",
        "auth-algo": ["md5", "sha1", "sha2-224", "sha2-256", "sha2-384", "sha2-512",
                      "md5-hmac", "sha1-hmac", "sha2-224-hmac", "sha2-256-hmac",
                      "sha2-384-hmac", "sha2-512-hmac"],
        "auth-op": ["generate"],
        "auth-key-sz": [0, 64, 128],
        "auth-aad-sz": [0],
        "auth-digest-sz": [16, 20, 28, 32, 48, 64],
        "buffer-sz": "32,64",
        "burst-sz": 32,
        "total-ops": 10000000
    },
}
