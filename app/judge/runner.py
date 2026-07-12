"""
Subprocess Runner — lightweight execution without Docker.

Used when USE_DOCKER_SANDBOX=false (development / simple deployments).
For production, prefer the Docker sandbox which provides real isolation.

Execution model:
  - C/C++:   compiled binary executed directly
  - Python:   python3 interpreter
  - Java:     java VM with classpath

Memory limits are enforced via prlimit(1) when available;
falls back to ulimit via shell wrapper.
"""
import asyncio
import os
import shutil
import subprocess
import time

from app.config import settings


def _prlimit_available() -> bool:
    """Check if prlimit command is available."""
    return shutil.which("prlimit") is not None


async def run_program(
    exe_path: str,
    language: str,
    work_dir: str,
    input_data: str,
    time_limit: float,
    memory_limit_mb: int,
) -> tuple[str | None, str, float, str]:
    """
    Run a compiled/interpreted program and return execution results.

    Args:
        exe_path: Path to executable or source file (Python)
        language: One of c, cpp, python, java
        work_dir: Working directory (must contain the compiled artifact)
        input_data: Text to pipe to stdin
        time_limit: CPU time limit in seconds
        memory_limit_mb: Memory limit in MB

    Returns:
        (verdict, stdout, runtime_seconds, stderr)
        verdict=None: normal exit, output needs comparison
    """
    work_dir = os.path.abspath(work_dir)
    output_path = os.path.join(work_dir, "output.txt")
    error_path = os.path.join(work_dir, "error.txt")

    # ── Build the command ──
    if language == "python":
        exe_path = os.path.abspath(exe_path)
        cmd_args = ["/usr/bin/python3.11", exe_path]
        cmd_label = f"python3 {os.path.basename(exe_path)}"
    elif language == "java":
        class_dir = os.path.abspath(os.path.dirname(exe_path))
        cmd_args = ["java", "-cp", class_dir, "Main"]
        cmd_label = f"java -cp {class_dir} Main"
    else:
        # C / C++ compiled binary
        exe_path = os.path.abspath(exe_path)
        cmd_args = [exe_path]
        cmd_label = os.path.basename(exe_path)

    # ── Wrap with memory limit (prlimit or ulimit) ──
    memory_bytes = memory_limit_mb * 1024 * 1024
    if _prlimit_available():
        # prlimit: clean, no shell needed
        cmd_args = [
            "prlimit",
            f"--as={memory_bytes}",
            f"--cpu={int(time_limit) + 2}",
            "--",
        ] + cmd_args
        cmd_label = f"prlimit --as={memory_bytes} {cmd_label}"
    else:
        # Fallback: use shell ulimit
        ulimit_kb = memory_limit_mb * 1024
        inner_cmd = " ".join(cmd_args)
        cmd_args = [
            "/bin/sh", "-c",
            f"ulimit -v {ulimit_kb} && exec {inner_cmd}",
        ]
        cmd_label = f"ulimit -v {ulimit_kb} && {inner_cmd}"

    # ── Execute ──
    start = time.time()
    try:
        with open(output_path, "w", encoding="utf-8") as fout, \
             open(error_path, "w", encoding="utf-8") as ferr:

            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=work_dir,
                stdin=asyncio.subprocess.PIPE,
                stdout=fout,
                stderr=ferr,
            )

            try:
                # Write stdin and wait for completion
                if input_data:
                    proc.stdin.write(input_data.encode("utf-8"))
                    await proc.stdin.drain()
                proc.stdin.close()
                await asyncio.wait_for(
                    proc.wait(),
                    timeout=time_limit + 2,
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                await proc.wait()
                raise subprocess.TimeoutExpired(cmd_label, time_limit)

        runtime = time.time() - start

        # ── Read output files ──
        try:
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                output = f.read(settings.OUTPUT_SIZE_LIMIT)
        except FileNotFoundError:
            output = ""

        try:
            with open(error_path, "r", encoding="utf-8", errors="replace") as f:
                stderr = f.read(2048)
        except FileNotFoundError:
            stderr = ""

        # ── Output size check ──
        # Check actual file size (not just what we read, which is capped)
        try:
            actual_size = os.path.getsize(output_path)
            if actual_size > settings.OUTPUT_SIZE_LIMIT:
                return "OLE", output, runtime, stderr
        except OSError:
            pass

        if len(output) >= settings.OUTPUT_SIZE_LIMIT:
            return "OLE", output, runtime, stderr

        # ── Verdict from exit code ──
        if proc.returncode != 0:
            if proc.returncode == 137:
                # SIGKILL (likely OOM from ulimit/prlimit)
                return "MLE", output, runtime, f"Memory limit exceeded ({memory_limit_mb}MB)"
            return "RTE", output, runtime, f"Exit code: {proc.returncode}\n{stderr[:300]}"

        # Normal exit — caller compares output
        return None, output, runtime, stderr

    except subprocess.TimeoutExpired:
        # Try to read partial output
        try:
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                partial_output = f.read(settings.OUTPUT_SIZE_LIMIT)
        except Exception:
            partial_output = ""
        return "TLE", partial_output, time_limit, "Time limit exceeded"
    except Exception as e:
        return "RTE", "", 0.0, str(e)
