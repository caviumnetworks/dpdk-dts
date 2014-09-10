# <COPYRIGHT_TAG>

import re           # regression module
import ConfigParser  # config parse module
import os           # operation system module
import texttable    # text format
import traceback    # exception traceback
import inspect      # load attribute
import atexit       # register callback when exit
import json         # json format

import rst          # rst file support
from crbs import crbs
from tester import Tester
from dut import Dut
from settings import NICS
from serializer import Serializer
from exception import VerifyFailure
from test_case import TestCase
from test_result import Result
from stats_reporter import StatsReporter
from excel_reporter import ExcelReporter
from exception import TimeoutException
from logger import getLogger
import logger

import sys
reload(sys)
sys.setdefaultencoding('UTF8')


config = None
table = None
results_table_rows = []
results_table_header = []
performance_only = False
functional_only = False
nics = None
requested_tests = None
dut = None
tester = None
result = None
excel_report = None
stats = None
log_handler = None
drivername = ""
interrupttypr = ""


def RED(text):
    return "\x1B[" + "31;1m" + text + "\x1B[" + "0m"


def BLUE(text):
    return "\x1B[" + "36;1m" + text + "\x1B[" + "0m"


def GREEN(text):
    return "\x1B[" + "32;1m" + text + "\x1B[" + "0m"


def regexp(s, to_match, allString=False):
    """
    Ensure that the re `to_match' only has one group in it.
    """

    scanner = re.compile(to_match, re.DOTALL)
    if allString:
        return scanner.findall(s)
    m = scanner.search(s)
    if m is None:
        log_handler.warning("Failed to match " + to_match + " in the string " + s)
        return None
    return m.group(1)


def pprint(some_dict):
    return json.dumps(some_dict, sort_keys=True, indent=4)


def report(text, frame=False, annex=False):
    if frame:
        rst.write_frame(text, annex)
    else:
        rst.write_text(text, annex)


# exit function will close session to DUT and tester
def close_crb_sessions():
    if dut is not None:
        dut.close()
    if tester is not None:
        tester.close()
    log_handler.info("DTF ended")


def accepted_nic(pci_id):
    """
    Return True if the pci_id is a known NIC card in the settings file and if
    it is selected in the execution file, otherwise it returns False.
    """
    if pci_id not in NICS.values():
        return False

    if 'any' in nics:
        return True

    else:
        for selected_nic in nics:
            if pci_id == NICS[selected_nic]:
                return True

    return False


def get_crb_os(crb):
    if 'OS' in crb:
        return crb['OS']

    return 'linux'


# Parse execution file parameters
def dcts_parse_param(section):
    global performance_only
    global functional_only
    global paramDict
    performance_only = False
    functional_only = False
    # Set parameters
    parameters = config.get(section, 'parameters').split(':')
    drivername = config.get(section, "drivername").split('=')[-1]
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


# Parse execution file configuration
def dcts_parse_config(section):
    duts = [dut_.strip() for dut_ in config.get(section,
                                                'crbs').split(',')]
    targets = [target.strip()
               for target in config.get(section, 'targets').split(',')]
    test_suites = [suite.strip()
                   for suite in config.get(section, 'test_suites').split(',')]

    nics = [_.strip() for _ in paramDict['nic_type'].split(',')]

    return duts, targets, test_suites, nics


# load project module and return crb instance
def get_project_obj(project_name, super_class, crbInst, serializer):
    project_obj = None
    try:
        project_module = __import__("project_" + project_name)

        for project_subclassname, project_subclass in get_subclasses(project_module, super_class):
            project_obj = project_subclass(crbInst, serializer)
        if project_obj is None:
            project_obj = super_class(crbInst, serializer)
    except Exception as e:
        log_handler.info("LOAD PROJECT MODULE INFO: " + e)
        project_obj = super_class(crbInst, serializer)

    return project_obj


# config logger to SUITE.log
def dcts_log_testsuite(test_suite, log_handler, test_classname):
    test_suite.logger = getLogger(test_classname)
    test_suite.logger.config_suite(test_classname)
    log_handler.config_suite(test_classname, 'dcts')
    dut.logger.config_suite(test_classname, 'dut')
    tester.logger.config_suite(test_classname, 'tester')
    try:
        if tester.it_uses_external_generator():
            getattr(tester, 'ixia_packet_gen')
            tester.ixia_packet_gen.logger.config_suite(test_classname, 'ixia')
    except Exception as ex:
        pass


# config logger to dcts.log
def dcts_log_execution(log_handler):
    log_handler.config_execution('dcts')
    dut.logger.config_execution('dut')
    tester.logger.config_execution('tester')
    try:
        if tester.it_uses_external_generator():
            getattr(tester, 'ixia_packet_gen')
            tester.ixia_packet_gen.logger.config_execution('ixia')
    except Exception as ex:
        pass


# create dcts crbs and initialize them
def dcts_crbs_init(crbInst, skip_setup, read_cache, project, base_dir):
    global dut
    global tester
    serializer.set_serialized_filename('../.%s.cache' % crbInst['IP'])
    serializer.load_from_file()

    dut = get_project_obj(project, Dut, crbInst, serializer)
    tester = get_project_obj(project, Tester, crbInst, serializer)
    dut.tester = tester
    tester.dut = dut
    dut.set_speedup_options(read_cache, skip_setup)
    dut.set_directory(base_dir)
    tester.set_speedup_options(read_cache, skip_setup)
    show_speedup_options_messages(read_cache, skip_setup)
    dut.set_test_types(func_tests=functional_only, perf_tests=performance_only)
    tester.set_test_types(func_tests=functional_only, perf_tests=performance_only)
    tester.init_ext_gen()


# when crbs exit remove logger handler
def dcts_crbs_exit():
    dut.logger.logger_exit()
    tester.logger.logger_exit()


# run dcts prerequisties function
def dcts_run_prerequisties(pkgName, patch):
    try:
        dut.prerequisites(pkgName, patch)
        tester.prerequisites(performance_only)

        serializer.save_to_file()
    except Exception as ex:
        log_handler.error(" PREREQ EXCEPTION " + traceback.format_exc())
        result.add_failed_dut(dut, str(ex))
        log_handler.info('CACHE: Discarding cache.')
        serializer.discard_cache()
        return False


# run each target in execution
def dcts_run_target(crbInst, targets, test_suites, nics):
    for target in targets:
        log_handler.info("\nTARGET " + target)
        result.target = target

        try:
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
            nics = ['any']
        nic = nics[0]
        result.nic = nic

        dcts_run_suite(crbInst, test_suites, target, nic)

    dut.restore_interfaces()
    dut.close()
    tester.restore_interfaces()
    tester.close()


# run each suite in target
def dcts_run_suite(crbInst, test_suites, target, nic):
    try:
        for test_suite in test_suites:
            # prepare rst report file
            result.test_suite = test_suite
            rst.generate_results_rst(crbInst['name'], target, nic, test_suite, performance_only)
            test_module = __import__('TestSuite_' + test_suite)
            for test_classname, test_class in get_subclasses(test_module, TestCase):

                test_suite = test_class(dut, tester, target, nic)
                dcts_log_testsuite(test_suite, log_handler, test_classname)

                log_handler.info("\nTEST SUITE : " + test_classname)
                log_handler.info("NIC :        " + nic)
                if execute_test_setup_all(test_suite):
                    execute_all_test_cases(test_suite)
                    execute_test_tear_down_all(test_suite)
                else:
                    test_cases_as_blocked(test_suite)

                log_handler.info("\nTEST SUITE ENDED: " + test_classname)
                dcts_log_execution(log_handler)

            dut.kill_all()
    except VerifyFailure:
        log_handler.error(" !!! DEBUG IT: " + traceback.format_exc())
    except KeyboardInterrupt:
        log_handler.error(" !!! STOPPING DCTS")
    finally:
        execute_test_tear_down_all(test_suite)


# main process of dcts
def run_all(config_file, pkgName, git, patch, skip_setup,
            read_cache, project, suite_dir, test_cases,
            base_dir, output_dir):
    """
    Run all test suites in the config file
    """

    global config
    global serializer
    global nics
    global requested_tests
    global result
    global excel_report
    global stats
    global log_handler

    # prepare the output folder
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # init log_handler handler
    logger.log_dir = output_dir
    log_handler = getLogger('dcts')
    log_handler.config_execution('dcts')

    # run designated test case
    requested_tests = test_cases

    # Read config file
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    # register exit action
    atexit.register(close_crb_sessions)

    sys.path.append(suite_dir)
    os.environ["TERM"] = "dumb"

    serializer = Serializer()

    # excel report and statistics file
    result = Result()
    rst.path2Result = output_dir
    excel_report = ExcelReporter(output_dir + '/test_results.xls')
    stats = StatsReporter(output_dir + '/statistics.txt')

    # for all Exectuion sections
    for section in config.sections():
        dcts_parse_param(section)

        # verify if the delimiter is good if the lists are vertical
        duts, targets, test_suites, nics = dcts_parse_config(section)

        for dutIP in duts:
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
            dcts_crbs_init(crbInst, skip_setup, read_cache, project, base_dir)

            # Run DUT prerequisites
            if dcts_run_prerequisties(pkgName, patch) is False:
                dcts_crbs_exit()
                continue

            dcts_run_target(crbInst, targets, test_suites, nics)

            dcts_crbs_exit()

    save_all_results()


# save result as test case blocked
def test_cases_as_blocked(test_suite):
    if functional_only:
        for test_case in get_functional_test_cases(test_suite):
            result.test_case = test_case.__name__
            result.test_case_blocked('set_up_all failed')
    if performance_only:
        for test_case in get_performance_test_cases(test_suite):
            result.test_case = test_case.__name__
            result.test_case_blocked('set_up_all failed')


# get module attribute name and attribute
def get_subclasses(module, clazz):
    for subclazz_name, subclazz in inspect.getmembers(module):
        if hasattr(subclazz, '__bases__') and clazz in subclazz.__bases__:
            yield (subclazz_name, subclazz)


# get all functional test cases
def get_functional_test_cases(test_suite):
    return get_test_cases(test_suite, r'test_(?!perf_)')


# get all performance test cases
def get_performance_test_cases(test_suite):
    return get_test_cases(test_suite, r'test_perf_')


# check if test case has been requested
def has_it_been_requested(test_case, test_name_regex):
    name_matches = re.match(test_name_regex, test_case.__name__)

    if requested_tests is not None:
        return name_matches and test_case.__name__ in requested_tests

    return name_matches


# return all case list which matched regex
def get_test_cases(test_suite, test_name_regex):
    for test_case_name in dir(test_suite):
        test_case = getattr(test_suite, test_case_name)
        if callable(test_case) and has_it_been_requested(test_case, test_name_regex):
            yield test_case


# execute suite setup_all function
def execute_test_setup_all(test_case):
    try:
        test_case.set_up_all()
        return True
    except Exception:
        log_handler.error('set_up_all failed:\n' + traceback.format_exc())
        return False


# execute all test cases in one suite
def execute_all_test_cases(test_suite):
    if functional_only:
        for test_case in get_functional_test_cases(test_suite):
            execute_test_case(test_suite, test_case)
    if performance_only:
        for test_case in get_performance_test_cases(test_suite):
            execute_test_case(test_suite, test_case)


# execute one test case in one suite
def execute_test_case(test_suite, test_case):
    result.test_case = test_case.__name__

    rst.write_title("Test Case: " + test_case.__name__)
    if performance_only:
        rst.write_annex_title("Annex: " + test_case.__name__)
    try:
        log_handler.info('Test Case %s Begin' % test_case.__name__)
        test_suite.set_up()
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
        result.test_case_failed(str(e))
        log_handler.error('Test Case %s Result FAILED: ' % (test_case.__name__) + str(e))
    except Exception:
        trace = traceback.format_exc()
        result.test_case_failed(trace)
        log_handler.error('Test Case %s Result ERROR: ' % (test_case.__name__) + trace)
    finally:
        test_suite.tear_down()
        save_all_results()


# execute suite tear_down_all function
def execute_test_tear_down_all(test_case):
    try:
        test_case.tear_down_all()
    except Exception:
        log_handler.error('tear_down_all failed:\n' + traceback.format_exc())

    dut.kill_all()
    tester.kill_all()


# add header to result table
def results_table_add_header(header):
    global table, results_table_header, results_table_rows

    results_table_rows = []
    results_table_rows.append([])
    table = texttable.Texttable(max_width=150)
    results_table_header = header


def results_table_add_row(row):
    results_table_rows.append(row)


# show off result table
def results_table_print():
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


# save all result to files
def save_all_results():
    excel_report.save(result)
    stats.save(result)
