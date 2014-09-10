# <COPYRIGHT_TAG>

"""
Excel spreadsheet generator

Example:
    excel_report = ExcelReporter('../output/test_results.xls')
    result = Result()
    result.dut = dutIP
    result.target = target
    result.nic = nic
        result.test_suite = test_suite
            result.test_case = test_case.__name__
            result.test_case_passed()
    excel_report.save(result)

Result:
    execl will be formatted as
    DUT             Target                      NIC      Test suite Test case Results
    10.239.128.117  x86_64-native-linuxapp-gcc  niantic
                                                         SUITE      CASE      PASSED


"""
import xlwt
from xlwt.ExcelFormula import Formula


class ExcelReporter(object):

    """
    Make use of a Result object generates an Excel Spreadsheet with those
    results.
    It supports saving the same file with incremental results.
    """

    def __init__(self, filename):
        self.filename = filename
        self.xsl_file = None
        self.result = None
        self.__styles()

    def __init(self):
        self.workbook = xlwt.Workbook()
        self.sheet = self.workbook.add_sheet(
            "Test Results", cell_overwrite_ok=True)

    def __add_header(self):
        self.sheet.write(0, 0, 'DUT', self.header_style)
        self.sheet.write(0, 1, 'Target', self.header_style)
        self.sheet.write(0, 2, 'NIC', self.header_style)
        self.sheet.write(0, 3, 'Test suite', self.header_style)
        self.sheet.write(0, 4, 'Test case', self.header_style)
        self.sheet.write(0, 5, 'Results', self.header_style)

        self.sheet.write(0, 7, 'Pass', self.header_style)
        self.sheet.write(0, 8, 'Fail', self.header_style)
        self.sheet.write(0, 9, 'Blocked', self.header_style)
        self.sheet.write(0, 10, 'Not Run', self.header_style)
        self.sheet.write(0, 11, 'Total', self.header_style)

        self.sheet.write(1, 7, Formula('COUNTIF(F2:F2000,"PASSED")'))
        self.sheet.write(1, 8, Formula('COUNTIF(F2:F2000,"FAILED*") + COUNTIF(F2:F2000,"IXA*")'))
        self.sheet.write(1, 9, Formula('COUNTIF(F2:F2000,"BLOCKED*")'))
        self.sheet.write(1, 11, Formula('H2+I2+J2+K2'))

        self.sheet.col(0).width = 4000
        self.sheet.col(1).width = 7500
        self.sheet.col(2).width = 3000
        self.sheet.col(3).width = 5000
        self.sheet.col(4).width = 8000
        self.sheet.col(5).width = 3000
        self.sheet.col(6).width = 1000
        self.sheet.col(7).width = 3000
        self.sheet.col(8).width = 3000
        self.sheet.col(9).width = 3000
        self.sheet.col(10).width = 3000
        self.sheet.col(11).width = 3000

    def __styles(self):
        header_pattern = xlwt.Pattern()
        header_pattern.pattern = xlwt.Pattern.SOLID_PATTERN
        header_pattern.pattern_fore_colour = xlwt.Style.colour_map['ocean_blue']

        passed_font = xlwt.Font()
        passed_font.colour_index = xlwt.Style.colour_map['black']
        self.passed_style = xlwt.XFStyle()
        self.passed_style.font = passed_font

        failed_font = xlwt.Font()
        failed_font.bold = True
        failed_font.colour_index = xlwt.Style.colour_map['red']
        self.failed_style = xlwt.XFStyle()
        self.failed_style.font = failed_font

        header_font = xlwt.Font()
        header_font.bold = True
        header_font.height = 260
        header_font.italic = True
        header_font.colour_index = xlwt.Style.colour_map['white']

        title_font = xlwt.Font()
        title_font.bold = True
        title_font.height = 220
        title_font.italic = True

        self.header_style = xlwt.XFStyle()
        self.header_style.font = header_font
        self.header_style.pattern = header_pattern

        self.title_style = xlwt.XFStyle()
        self.title_style.font = title_font

    def __write_result(self, dut, target, suite, case):
        test_result = self.result.result_for(dut, target, suite, case)
        if test_result is not None and len(test_result) > 0:
            result = test_result[0]
            if test_result[1] != '':
                result = "{0} '{1}'".format(result, test_result[1])
            if test_result[0] == 'PASSED':
                self.sheet.write(self.row, self.col + 1, result)
            else:
                self.sheet.write(
                    self.row, self.col + 1, result, self.failed_style)

    def __write_cases(self, dut, target, suite):
        for case in self.result.all_test_cases(dut, target, suite):
            self.col += 1
            if case[:5] == "test_":
                self.sheet.write(self.row, self.col, case[5:])
            else:
                self.sheet.write(self.row, self.col, case)
            self.__write_result(dut, target, suite, case)
            self.row += 1
            self.col -= 1

    def __write_suites(self, dut, target):
        for suite in self.result.all_test_suites(dut, target):
            self.row += 1
            self.col += 1
            self.sheet.write(self.row, self.col, suite)
            self.__write_cases(dut, target, suite)
            self.col -= 1

    def __write_nic(self, dut, target):
        nic = self.result.current_nic(dut, target)
        self.col += 1
        self.sheet.write(self.row, self.col, nic, self.title_style)
        self.__write_suites(dut, target)
        self.col -= 1

    def __write_failed_target(self, dut, target):
        msg = "TARGET ERROR '%s'" % self.result.target_failed_msg(dut, target)
        self.sheet.write(self.row, self.col + 4, msg, self.failed_style)
        self.row += 1

    def __write_targets(self, dut):
        for target in self.result.all_targets(dut):
            self.col += 1
            self.sheet.write(self.row, self.col, target, self.title_style)
            if self.result.is_target_failed(dut, target):
                self.__write_failed_target(dut, target)
            else:
                self.__write_nic(dut, target)
            self.row += 1
            self.col -= 1

    def __write_failed_dut(self, dut):
        msg = "PREREQ FAILED '%s'" % self.result.dut_failed_msg(dut)
        self.sheet.write(self.row, self.col + 5, msg, self.failed_style)
        self.row += 1

    def __parse_result(self):
        for dut in self.result.all_duts():
            self.sheet.write(self.row, self.col, dut, self.title_style)
            if self.result.is_dut_failed(dut):
                self.__write_failed_dut(dut)
            else:
                self.__write_targets(dut)
            self.row += 1

    def save(self, result):
        self.__init()
        self.__add_header()
        self.row = 1
        self.col = 0

        self.result = result
        self.__parse_result()

        self.workbook.save(self.filename)
