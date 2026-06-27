from app.models import Verdict


def compare_output(actual: str, expected: str) -> str:
    """逐行比对输出，返回 AC / WA / PE"""
    actual_lines = actual.rstrip("\n").split("\n")
    expected_lines = expected.rstrip("\n").split("\n")

    # 去除每行尾部空白
    actual_trimmed = [line.rstrip() for line in actual_lines]
    expected_trimmed = [line.rstrip() for line in expected_lines]

    if actual_trimmed == expected_trimmed:
        return Verdict.AC.value

    # 忽略全部空白后仍相同 → PE (Presentation Error)
    actual_stripped = "".join(actual_trimmed).replace(" ", "").replace("\t", "")
    expected_stripped = "".join(expected_trimmed).replace(" ", "").replace("\t", "")
    if actual_stripped == expected_stripped:
        return Verdict.PE.value

    return Verdict.WA.value


def calculate_icpc_result(run_results: list[tuple[str, float]]) -> tuple[str, float]:
    """
    ICPC 懒判：遇到第一个非 AC 即停止
    run_results: [(verdict, runtime), ...]
    返回 (final_verdict, max_runtime)
    """
    max_runtime = 0.0
    for verdict, runtime in run_results:
        max_runtime = max(max_runtime, runtime)
        if verdict != Verdict.AC.value:
            return verdict, max_runtime
    return Verdict.AC.value, max_runtime


def calculate_ioi_result(
    run_results: list[tuple[str, float]], total_testcases: int
) -> tuple[str, float]:
    """
    IOI 计分：每个 AC 测试点得分 = 100 / total_testcases
    返回 (final_verdict, total_score)
    """
    if total_testcases == 0:
        return Verdict.AC.value, 100.0

    points_per_case = 100.0 / total_testcases
    total_score = 0.0
    has_non_ac = False

    for verdict, _runtime in run_results:
        if verdict == Verdict.AC.value:
            total_score += points_per_case
        else:
            has_non_ac = True

    final_verdict = Verdict.AC.value if not has_non_ac else Verdict.WA.value
    return final_verdict, round(total_score, 2)
