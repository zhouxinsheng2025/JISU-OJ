import subprocess
import os
import asyncio
import psutil
from app.config import settings


async def run_program(
    exe_path: str,
    language: str,
    work_dir: str,
    input_data: str,
    time_limit: float,
    memory_limit_mb: int,
) -> tuple[str | None, str, float, str]:
    """
    运行编译后的程序，返回 (verdict, stdout, runtime_seconds, stderr)
    verdict 为 None 表示正常退出，需要比对输出
    """
    output_path = os.path.join(work_dir, "output.txt")
    error_path = os.path.join(work_dir, "error.txt")

    if language == "python":
        cmd = f"python {exe_path}"
    elif language == "java":
        class_dir = os.path.dirname(exe_path)
        cmd = f"java -cp {class_dir} Main"
    else:
        cmd = f"./{exe_path}"

    try:
        runtime = await _run_with_limits(
            cmd, work_dir, input_data, output_path, error_path,
            time_limit, memory_limit_mb,
        )
        with open(output_path, "r", encoding="utf-8", errors="replace") as f:
            output = f.read(settings.OUTPUT_SIZE_LIMIT)
        with open(error_path, "r", encoding="utf-8", errors="replace") as f:
            stderr = f.read(1024)
        # 检查输出是否被截断
        if len(output) >= settings.OUTPUT_SIZE_LIMIT:
            return "OLE", output, runtime, stderr
        return None, output, runtime, stderr

    except subprocess.TimeoutExpired:
        return "TLE", "", time_limit, "Time limit exceeded"
    except MemoryError:
        return "MLE", "", 0.0, "Memory limit exceeded"
    except RuntimeError as e:
        return "RTE", "", 0.0, str(e)
    except Exception as e:
        return "RTE", "", 0.0, str(e)


async def _run_with_limits(
    cmd: str,
    cwd: str,
    stdin_data: str,
    stdout_path: str,
    stderr_path: str,
    time_limit: float,
    memory_limit_mb: int,
) -> float:
    """执行命令并施加资源限制"""
    import time
    start = time.time()

    with open(stdout_path, "w") as fout, open(stderr_path, "w") as ferr:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=fout,
            stderr=ferr,
        )
        try:
            await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=time_limit + 2,  # 额外2秒缓冲
            )
        except asyncio.TimeoutError:
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
            except psutil.NoSuchProcess:
                pass
            await proc.wait()
            raise subprocess.TimeoutExpired(cmd, time_limit)

    runtime = time.time() - start
    if proc.returncode != 0 and proc.returncode is not None:
        raise RuntimeError(f"Exit code: {proc.returncode}")

    return runtime
