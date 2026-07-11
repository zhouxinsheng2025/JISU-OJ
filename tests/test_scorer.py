import pytest
from app.judge.scorer import compare_output, calculate_icpc_result, calculate_ioi_result
from app.models import Verdict


class TestCompareOutput:
    def test_identical(self):
        assert compare_output("hello\nworld\n", "hello\nworld\n") == Verdict.AC.value

    def test_whitespace_difference_ac(self):
        """尾部空格被 rstrip 忽略 → AC"""
        assert compare_output("hello  \nworld\n", "hello\nworld\n") == Verdict.AC.value

    def test_pe_when_only_whitespace_differs(self):
        """全空白被忽略后仍然相同 → PE"""
        assert compare_output("hello world\n", "hello  world\n") == Verdict.PE.value

    def test_trailing_newline(self):
        """末尾换行符不同 → AC"""
        assert compare_output("hello\n", "hello") == Verdict.AC.value

    def test_content_difference_wa(self):
        assert compare_output("hello\n", "world\n") == Verdict.WA.value

    def test_extra_line_wa(self):
        assert compare_output("hello\nworld\n", "hello\n") == Verdict.WA.value

    def test_missing_line_wa(self):
        assert compare_output("hello\n", "hello\nworld\n") == Verdict.WA.value


class TestICPC:
    def test_all_ac(self):
        runs = [("AC", 0.1), ("AC", 0.2), ("AC", 0.05)]
        verdict, max_runtime = calculate_icpc_result(runs)
        assert verdict == Verdict.AC.value
        assert max_runtime == 0.2

    def test_first_wa_stops(self):
        """ICPC 懒判：遇到第一个非 AC 就停"""
        runs = [("AC", 0.1), ("WA", 0.3), ("AC", 0.5)]
        verdict, max_runtime = calculate_icpc_result(runs)
        assert verdict == Verdict.WA.value
        assert max_runtime == 0.3

    def test_tle(self):
        runs = [("AC", 0.1), ("TLE", 2.0), ("AC", 0.1)]
        verdict, max_runtime = calculate_icpc_result(runs)
        assert verdict == Verdict.TLE.value


class TestIOI:
    def test_all_ac_full_score(self):
        runs = [("AC", 0.1), ("AC", 0.2), ("AC", 0.3), ("AC", 0.4)]
        verdict, score = calculate_ioi_result(runs, total_testcases=4)
        assert verdict == Verdict.AC.value
        assert score == 100.0

    def test_partial_score(self):
        runs = [("AC", 0.1), ("WA", 0.2), ("AC", 0.3), ("WA", 0.4)]
        verdict, score = calculate_ioi_result(runs, total_testcases=4)
        assert verdict == Verdict.WA.value  # 有 WA，最终 verdict 为 WA
        assert score == 50.0  # 4题，每题25分，AC 2题

    def test_three_cases(self):
        runs = [("AC", 0.1), ("AC", 0.2), ("WA", 0.3)]
        verdict, score = calculate_ioi_result(runs, total_testcases=3)
        assert score == pytest.approx(66.67, abs=0.01)

    def test_empty(self):
        verdict, score = calculate_ioi_result([], total_testcases=0)
        assert verdict == Verdict.AC.value
        assert score == 0.0
