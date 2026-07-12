"""
Output comparison and scoring — Antares-OJ inspired design.

Comparison modes:
  - Line mode (default):  line-by-line with trailing whitespace trim
  - Token mode:           token-by-token, any whitespace ignored
  - Float tolerance:      optional relative/absolute error for numeric output

Scoring modes:
  - ICPC: first non-AC stops (binary pass/fail per problem)
  - IOI:  proportional points per testcase
"""
import math
from app.models import Verdict

# Default floating-point tolerance (relative)
FLOAT_TOLERANCE = 1e-6


def _is_float(s: str) -> bool:
    """Check if a string represents a floating-point number."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _floats_close(a: str, b: str, rel_tol: float = FLOAT_TOLERANCE) -> bool:
    """Compare two strings as floating-point numbers with tolerance."""
    try:
        fa, fb = float(a), float(b)
        return math.isclose(fa, fb, rel_tol=rel_tol, abs_tol=1e-9)
    except (ValueError, TypeError):
        return False


def _tokenize(text: str) -> list[str]:
    """Split text into tokens (whitespace-delimited)."""
    return text.split()


def compare_output(
    actual: str,
    expected: str,
    float_tolerance: bool = True,
) -> str:
    """
    Compare program output with expected output.

    Comparison strategy (antares-oj inspired):
      1. Exact match after trimming trailing whitespace per line → AC
      2. Token-by-token match (all whitespace ignored) → PE
      3. Float-tolerant token comparison → PE (numeric formatting)
      4. All else → WA

    Args:
        actual: Program's stdout
        expected: Expected output
        float_tolerance: If True, compare numbers with relative tolerance

    Returns one of: AC, PE, WA
    """
    # ── Normalize trailing whitespace ──
    actual = actual.rstrip()
    expected = expected.rstrip()

    # ── Edge case: both empty ──
    if actual == "" and expected == "":
        return Verdict.AC.value

    # ── Step 1: Line-by-line with trailing whitespace trim ──
    actual_lines = [line.rstrip() for line in actual.split("\n")]
    expected_lines = [line.rstrip() for line in expected.split("\n")]

    if actual_lines == expected_lines:
        return Verdict.AC.value

    # ── Step 2: Token-by-token comparison ──
    actual_tokens = _tokenize(actual)
    expected_tokens = _tokenize(expected)

    if actual_tokens == expected_tokens:
        # Same tokens but different whitespace → PE
        return Verdict.PE.value

    # ── Step 3: Float-tolerant comparison ──
    if float_tolerance and len(actual_tokens) == len(expected_tokens):
        match_count = 0
        float_mismatch = 0
        for at, et in zip(actual_tokens, expected_tokens):
            if at == et:
                match_count += 1
            elif _is_float(at) and _is_float(et):
                if _floats_close(at, et):
                    float_mismatch += 1
                else:
                    break  # float values genuinely differ → WA
            else:
                break  # non-float token differs → WA
        else:
            # All tokens match (some with float tolerance)
            if float_mismatch > 0:
                return Verdict.PE.value
            return Verdict.AC.value

    # ── Step 4: Whitespace-normalized content match (last resort PE check) ──
    actual_compact = "".join(actual_tokens)
    expected_compact = "".join(expected_tokens)
    if actual_compact == expected_compact:
        return Verdict.PE.value

    return Verdict.WA.value


def calculate_icpc_result(
    run_results: list[tuple[str, float]],
) -> tuple[str, float]:
    """
    ICPC scoring: lazy evaluation, stops at first non-AC testcase.

    Args:
        run_results: [(verdict, runtime), ...]

    Returns:
        (final_verdict, max_runtime)
    """
    max_runtime = 0.0
    for verdict, runtime in run_results:
        max_runtime = max(max_runtime, runtime)
        if verdict != Verdict.AC.value:
            return verdict, max_runtime
    return Verdict.AC.value, max_runtime


def calculate_ioi_result(
    run_results: list[tuple[str, float]],
    total_testcases: int,
) -> tuple[str, float]:
    """
    IOI scoring: each AC testcase earns proportional points.

    Args:
        run_results: [(verdict, runtime), ...]
        total_testcases: total number of testcases

    Returns:
        (final_verdict, total_score)
    """
    if total_testcases == 0:
        return Verdict.AC.value, 0.0

    points_per_case = 100.0 / total_testcases
    total_score = 0.0
    ac_count = 0

    for verdict, _runtime in run_results:
        if verdict == Verdict.AC.value:
            total_score += points_per_case
            ac_count += 1

    # Final verdict: AC only if ALL testcases passed
    final_verdict = Verdict.AC.value if ac_count == total_testcases else Verdict.WA.value

    # Partial scoring: some non-AC but points earned → mark as WA with partial score
    if ac_count > 0 and ac_count < total_testcases:
        # Consider partial verdict if score > 0
        pass  # currently mapped to WA — extensible for future "partial" verdict

    return final_verdict, round(total_score, 2)
