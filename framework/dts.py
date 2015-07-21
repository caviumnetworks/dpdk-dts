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

import re           # regression module
import ConfigParser  # config parse module
import os           # operation system module
import texttable    # text format
import traceback    # exception traceback
import inspect      # load attribute
import atexit       # register callback when exit
import json         # json format
import signal       # signal module for debug mode
import time         # time module for unique output folder

import rst          # rst file support
from crbs import crbs
from tester import Tester
from dut import Dut
from settings import FOLDERS, NICS, DRIVERS
from serializer import Serializer
from exception import VerifyFailure
from test_case import TestCase
from test_result import Result
from stats_reporter import StatsReporter
from excel_reporter import ExcelReporter
from utils import *
from exception import TimeoutException
from logger import getLogger
import logger
import debugger
from virt_scene import VirtScene

import sys
reload(sys)
sys.setdefaultencoding('UTF8')

PROJECT_MODULE_PREFIX = 'project_'

debug_mode = False
debug_case = False
config = None
table = None
results_table_rows = []
results_table_header = []
performance_only = False
functional_only = False
nic = None
rx_mode = None
requested_tests = None
dut = None
duts = None
tester = None
result = None
excel_report = None
stats = None
log_handler = None
module = None
Package = ''
Patches = []
drivername = ""
interrupttypr = ""


def report(text, frame=False, annex=False):
    """
    Save report text into rst file.
    """
    if frame:
        rst.write_frame(text, annex)
    else:
        rst.write_text(text, annex)


def close_crb_sessions():
    """
    Close session to DUT and tester.
    """
    if dut is not None:
        dut.close()
    if tester is not None:
        tester.close()
    log_handler.info("DTS ended")


def get_crb_os(crb):
    if 'OS' in crb:
        return crb['OS']

    return 'linux'


def dts_parse_param(section):
    """
    Parse execution file parameters.
    """
    global performance_only
    global functional_only
    global paramDict
    global drivername
    performance_only = False
    functional_only = False
    # Set parameters
    parameters = config.get(section, 'parameters').split(':')
    drivername = config.get(section, 'drivername').split('=')[-1]
    paramDict = dict()
    for param in parameters:
        (key, _, value) = param.partition('=')
        paramDict[key] = value

    if 'perf' in paramDict and paramDict['perf'] == 'true':
        performance_only = True
    if 'func' in paramDict and paramDict['func'] == 'true':
        functional_only = True

    if not functional_only and not performance_only:
        functional_only = True


def dts_parse_config(section):
    """
    Parse execution file configuration.
    """
    try:
        scenario = config.get(section, 'scenario')
    except:
        scenario = ''

    global nic
    global rx_mode

    duts = [dut_.strip() for dut_ in config.get(section,
                                                'crbs').split(',')]
    targets = [target.strip()
               for target in config.get(section, 'targets').split(',')]
    test_suites = [suite.strip()
                   for suite in config.get(section, 'test_suites').split(',')]
    try:
        rx_mode = config.get(section, 'rx_mode').strip()
    except:
        rx_mode = None

    for suite in test_suites:
        if suite == '':
            test_suites.remove(suite)

    nic = [_.strip() for _ in paramDict['nic_type'].split(',')][0]

    return duts[0], targets, test_suites, nic, scenario


def get_project_obj(project_name, super_class, crbInst, serializer):
    """
    Load project module and return crb instance.
    """
    global PROJECT_MODULE_PREFIX
    project_obj = None
    try:
        project_module = __import__(PROJECT_MODULE_PREFIX + project_name)

        for project_subclassname, project_subclass in get_subclasses(project_module, super_class):
            project_obj = project_subclass(crbInst, serializer)
        if project_obj is None:
            project_obj = super_class(crbInst, serializer)
    except Exception as e:
        log_handler.info("LOAD PROJECT MODULE INFO: " + str(e))
        project_obj = super_class(crbInst, serializer)

    return project_obj


def dts_log_testsuite(test_suite, log_handler, test_classname):
    """
    Change to SUITE self logger handler.
    """
    global duts
    test_suite.logger = getLogger(test_classname)
    test_suite.logger.config_suite(test_classname)
    log_handler.config_suite(test_classname, 'dts')
    dut.logger.config_suite(test_classname, 'dut')
    dut.test_classname = test_classname
    tester.logger.config_suite(test_classname, 'tester')
    if duts and len(duts):
        for crb in duts:
            crb.logger.config_suite(test_classname, 'virtdut')
    try:
        if tester.it_uses_external_generator():
            getattr(tester, 'ixia_packet_gen')
            tester.ixia_packet_gen.logger.config_suite(test_classname, 'ixia')
    except Exception as ex:
        pass


def dts_log_execution(log_handler):
    """
    Change to DTS default logger handler.
    """
    log_handler.config_execution('dts')
    dut.logger.config_execution('dut')
    tester.logger.config_execution('tester')
    if duts and len(duts):
        for crb in duts:
            crb.logger.config_execution('virtdut')
    try:
        if tester.it_uses_external_generator():
            getattr(tester, 'ixia_packet_gen')
            tester.ixia_packet_gen.logger.config_execution('ixia')
    except Exception as ex:
        pass


def dts_crbs_init(crbInst, skip_setup, read_cache, project, base_dir, nic, virttype):
    """
    Create dts dut/tester instance and initialize them.
    """
    global dut
    global tester
    serializer.set_serialized_filename(FOLDERS['Output'] +
                                       '/.%s.cache' % crbInst['IP'])
    serializer.load_from_file()

    dut = get_project_obj(project, Dut, crbInst, serializer)
    tester = get_project_obj(project, Tester, crbInst, serializer)
    dts_log_execution(log_handler)
    dut.tester = tester
    tester.dut = dut
    dut.set_virttype(virttype)
    dut.set_speedup_options(read_cache, skip_setup)
    dut.set_directory(base_dir)
    dut.set_nic_type(nic)
    tester.set_speedup_options(read_cache, skip_setup)
    show_speedup_options_messages(read_cache, skip_setup)
    dut.set_test_types(func_tests=functional_only, perf_tests=performance_only)
    tester.set_test_types(func_tests=functional_only, perf_tests=performance_only)
    tester.init_ext_gen()


def dts_crbs_exit():
    """
    Call dut and tester exit function after execution finished
    """
    dut.crb_exit()
    tester.crb_exit()


def dts_run_prerequisties(pkgName, patch):
    """
    Run dts prerequisties function.
    """
    try:
        tester.prerequisites(performance_only)
        dut.prerequisites(pkgName, patch)

        serializer.save_to_file()
    except Exception as ex:
        log_handler.error(" PREREQ EXCEPTION " + traceback.format_exc())
        result.add_failed_dut(dut, str(ex))
        log_handler.info('CACHE: Discarding cache.')
        serializer.discard_cache()
        return False


def dts_run_target(crbInst, targets, test_suites, nic, scenario):
    """
    Run each target in execution targets.
    """
    if scenario != '':
        scene = VirtScene(dut, tester, scenario)
    else:
        scene = None

    if scene:
        scene.load_config()
        scene.create_scene()

    for target in targets:
        log_handler.info("\nTARGET " + target)
        result.target = target

        try:
            if scene:
                scene.set_target(target)
                # skip set_target when host has been setup by scenario
                if not scene.host_bound:
                    dut.set_target(target, bind_dev=False)
            else:
                dut.set_target(target)
        except AssertionError as ex:
            log_handler.error(" TARGET ERROR: " + str(ex))
            result.add_failed_target(result.dut, target, str(ex))
            continue
        except Exception as ex:
            log_handler.error(" !!! DEBUG IT: " + traceback.format_exc())
            result.add_failed_target(result.dut, target, str(ex))
            continue

        if 'nic_type' not in paramDict:
            paramDict['nic_type'] = 'any'
            nic = 'any'

        dts_run_suite(crbInst, test_suites, target, nic, scene)

    if scene:
        scene.destroy_scene()
        scene = None

    dut.restore_interfaces()
    tester.restore_interfaces()


def dts_run_suite(crbInst, test_suites, target, nic, scene):
    """
    Run each suite in test suite list.
    """
    try:
        for test_suite in test_suites:
            # prepare rst report file
            result.test_suite = test_suite
            rst.generate_results_rst(crbInst['name'], target, nic, test_suite, performance_only)
            test_module = __import__('TestSuite_' + test_suite)
            global module
            module = test_module
            for test_classname, test_class in get_subclasses(test_module, TestCase):

                if scene and scene.vm_dut_enable:
                    global duts
                    duts = scene.get_vm_duts()
                    tester.dut = duts[0]
                    test_suite = test_class(duts[0], tester, target, test_suite)
                else:
                    test_suite = test_class(dut, tester, target, test_suite)
                result.nic = test_suite.nic

                dts_log_testsuite(test_suite, log_handler, test_classname)

                log_handler.info("\nTEST SUITE : " + test_classname)
                log_handler.info("NIC :        " + nic)
                if execute_test_setup_all(test_suite):
                    execute_all_test_cases(test_suite)
                    execute_test_tear_down_all(test_suite)
                else:
                    test_cases_as_blocked(test_suite)

                log_handler.info("\nTEST SUITE ENDED: " + test_classname)
                dts_log_execution(log_handler)

            dut.kill_all()
    except VerifyFailure:
        log_handler.error(" !!! DEBUG IT: " + traceback.format_exc())
    except KeyboardInterrupt:
        log_handler.error(" !!! STOPPING DCTS")
    except Exception as e:
        log_handler.error(str(e))
    finally:
        execute_test_tear_down_all(test_suite)


def run_all(config_file, pkgName, git, patch, skip_setup,
            read_cache, project, suite_dir, test_cases,
            base_dir, output_dir, verbose, virttype, debug, debugcase):
    """
    Main process of DTS, it will run all test suites in the config file.
    """

    global config
    global serializer
    global nic
    global requested_tests
    global result
    global excel_report
    global stats
    global log_handler
    global debug_mode
    global debug_case
    global Package
    global Patches
    global scenario

    # save global variable
    Package = pkgName
    Patches = patch

    # prepare the output folder
    if output_dir == '':
        output_dir = FOLDERS['Output']

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # add python module search path
    for folder in FOLDERS.values():
        sys.path.append(folder)
    sys.path.append(suite_dir)

    # enable debug mode
    if debug is True:
        debug_mode = True
    if debugcase is True:
        debug_case = True

    # init log_handler handler
    if verbose is True:
        logger.set_verbose()

    logger.log_dir = output_dir
    log_handler = getLogger('dts')
    log_handler.config_execution('dts')

    # run designated test case
    requested_tests = test_cases

    # Read config file
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    # register exit action
    atexit.register(close_crb_sessions)

    os.environ["TERM"] = "dumb"

    serializer = Serializer()

    # excel report and statistics file
    result = Result()
    rst.path2Result = output_dir
    excel_report = ExcelReporter(output_dir + '/test_results.xls')
    stats = StatsReporter(output_dir + '/statistics.txt')

    # for all Exectuion sections
    for section in config.sections():
        dts_parse_param(section)

        # verify if the delimiter is good if the lists are vertical
        dutIP, targets, test_suites, nics, scenario = dts_parse_config(section)

        log_handler.info("\nDUT " + dutIP)

        # look up in crbs - to find the matching IP
        crbInst = None
        for crb in crbs:
            if crb['IP'] == dutIP:
                crbInst = crb
                break

        # only run on the dut in known crbs
        if crbInst is None:
            log_handler.error(" SKIP UNKNOWN CRB")
            continue

        result.dut = dutIP

        # init dut, tester crb
        dts_crbs_init(crbInst, skip_setup, read_cache, project, base_dir, nics, virttype)

        # Run DUT prerequisites
        if dts_run_prerequisties(pkgName, patch) is False:
            dts_crbs_exit()
            continue

        dts_run_target(crbInst, targets, test_suites, nics, scenario)

        dts_crbs_exit()

    save_all_results()


def test_cases_as_blocked(test_suite):
    """
    Save result as test case blocked.
    """
    if functional_only:
        for test_case in get_functional_test_cases(test_suite):
            result.test_case = test_case.__name__
            result.test_case_blocked('set_up_all failed')
    if performance_only:
        for test_case in get_performance_test_cases(test_suite):
            result.test_case = test_case.__name__
            result.test_case_blocked('set_up_all failed')


def get_subclasses(module, clazz):
    """
    Get module attribute name and attribute.
    """
    for subclazz_name, subclazz in inspect.getmembers(module):
        if hasattr(subclazz, '__bases__') and clazz in subclazz.__bases__:
            yield (subclazz_name, subclazz)


def copy_instance_attr(from_inst, to_inst):
    for key in from_inst.__dict__.keys():
            to_inst.__dict__[key] = from_inst.__dict__[key]


def get_functional_test_cases(test_suite):
    """
    Get all functional test cases.
    """
    return get_test_cases(test_suite, r'test_(?!perf_)')


def get_performance_test_cases(test_suite):
    """
    Get all performance test cases.
    """
    return get_test_cases(test_suite, r'test_perf_')


def has_it_been_requested(test_case, test_name_regex):
    """
    Check whether test case has been requested for validation.
    """
    name_matches = re.match(test_name_regex, test_case.__name__)

    if requested_tests is not None:
        return name_matches and test_case.__name__ in requested_tests

    return name_matches


def get_test_cases(test_suite, test_name_regex):
    """
    Return case list which name matched regex.
    """
    for test_case_name in dir(test_suite):
        test_case = getattr(test_suite, test_case_name)
        if callable(test_case) and has_it_been_requested(test_case, test_name_regex):
            yield test_case


def execute_test_setup_all(test_case):
    """
    Execute suite setup_all function before cases.
    """
    try:
        # clear all previous output
        test_case.dut.get_session_output(timeout=0.1)
        test_case.tester.get_session_output(timeout=0.1)
        test_case.set_up_all()
        return True
    except Exception:
        log_handler.error('set_up_all failed:\n' + traceback.format_exc())
        return False


def execute_all_test_cases(test_suite):
    """
    Execute all test cases in one suite.
    """
    if functional_only:
        for test_case in get_functional_test_cases(test_suite):
            execute_test_case(test_suite, test_case)
    if performance_only:
        for test_case in get_performance_test_cases(test_suite):
            execute_test_case(test_suite, test_case)


def execute_test_case(test_suite, test_case):
    """
    Execute specified test case in specified suite. If any exception occured in
    validation process, save the result and tear down this case.
    """
    global debug_mode
    global debug_case
    global module
    result.test_case = test_case.__name__

    rst.write_title("Test Case: " + test_case.__name__)
    if performance_only:
        rst.write_annex_title("Annex: " + test_case.__name__)
    try:
        log_handler.info('Test Case %s Begin' % test_case.__name__)
        test_suite.running_case = test_case.__name__
        # clear all previous output
        test_suite.dut.get_session_output(timeout=0.1)
        test_suite.tester.get_session_output(timeout=0.1)
        # run set_up function for each case
        test_suite.set_up()
        # prepare debugger re-run case environment
        if debug_mode or debug_case:
            debugger.AliveSuite = test_suite
            debugger.AliveModule = module
            debugger.AliveCase = test_case.__name__
        if debug_case:
            debugger.keyboard_handle(signal.SIGINT, None)
        else:
            test_case()

        result.test_case_passed()

        if dut.want_perf_tests:
            log_handler.info('Test Case %s Result FINISHED:' % test_case.__name__)
        else:
            rst.write_result("PASS")
            log_handler.info('Test Case %s Result PASSED:' % test_case.__name__)

    except VerifyFailure as v:
        result.test_case_failed(str(v))
        rst.write_result("FAIL")
        log_handler.error('Test Case %s Result FAILED: ' % (test_case.__name__) + str(v))
    except KeyboardInterrupt:
        result.test_case_blocked("Skipped")
        log_handler.error('Test Case %s SKIPED: ' % (test_case.__name__))
        raise KeyboardInterrupt("Stop DCTS")
    except TimeoutException as e:
        rst.write_result("FAIL")
        msg = str(e)
        result.test_case_failed(msg)
        log_handler.error('Test Case %s Result FAILED: ' % (test_case.__name__) + msg)
        log_handler.error('%s' % (e.get_output()))
    except Exception:
        trace = traceback.format_exc()
        result.test_case_failed(trace)
        log_handler.error('Test Case %s Result ERROR: ' % (test_case.__name__) + trace)
    finally:
        test_suite.tear_down()
        save_all_results()


def execute_test_tear_down_all(test_case):
    """
    execute suite tear_down_all function
    """
    try:
        test_case.tear_down_all()
    except Exception:
        log_handler.error('tear_down_all failed:\n' + traceback.format_exc())

    dut.kill_all()
    tester.kill_all()


def results_table_add_header(header):
    """
    Add the title of result table.
    Usage:
    results_table_add_header(header)
    results_table_add_row(row)
    results_table_print()
    """
    global table, results_table_header, results_table_rows

    results_table_rows = []
    results_table_rows.append([])
    table = texttable.Texttable(max_width=150)
    results_table_header = header


def results_table_add_row(row):
    """
    Add one row to result table.
    """
    results_table_rows.append(row)


def results_table_print():
    """
    Show off result table.
    """
    table.add_rows(results_table_rows)
    table.header(results_table_header)

    alignments = []
    # all header align to left
    for _ in results_table_header:
        alignments.append("l")
    table.set_cols_align(alignments)

    out = table.draw()
    rst.write_text('\n' + out + '\n\n')
    log_handler.info('\n' + out)


def results_plot_print(image, width=90):
    """
    Includes an image in the report file.
    The image name argument must include the path. <path>/<image name>
    """
    rst.include_image(image, width)


def create_mask(indexes):
    """
    Convert index to hex mask.
    """
    val = 0
    for index in indexes:
        val |= 1 << int(index)

    return hex(val).rstrip("L")


def show_speedup_options_messages(read_cache, skip_setup):
    if read_cache:
        log_handler.info('CACHE: All configuration will be read from cache.')
    else:
        log_handler.info('CACHE: Cache will not be read.')

    if skip_setup:
        log_handler.info('SKIP: Skipping DPDK setup.')
    else:
        log_handler.info('SKIP: The DPDK setup steps will be executed.')


def save_all_results():
    """
    Save all result to files.
    """
    excel_report.save(result)
    stats.save(result)
