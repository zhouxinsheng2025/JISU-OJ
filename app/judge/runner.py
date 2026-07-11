import asyncio
import logging
import os
import subprocess
import time

import psutil

from app.config import settings

logger = logging.getLogger(__name__)


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
    """执行命令并施加时间和内存限制。"""
    memory_limit_bytes = memory_limit_mb * 1024 * 1024
    # 为 Java/Python 虚拟机预留 64MB 额外开销
    memory_limit_bytes += 64 * 1024 * 1024

    start = time.time()
    oom_event = asyncio.Event()

    # Unix: 通过 preexec_fn 设置进程资源限制
    preexec_fn = _make_preexec_fn(time_limit + 5, memory_limit_bytes + 128 * 1024 * 1024)

    with open(stdout_path, "w") as fout, open(stderr_path, "w") as ferr:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=fout,
            stderr=ferr,
            preexec_fn=preexec_fn,
        )

        # 启动内存监控任务
        monitor_task = asyncio.create_task(
            _monitor_memory(proc.pid, memory_limit_bytes, oom_event)
        )

        try:
            await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=time_limit + 2,
            )
        except asyncio.TimeoutError:
            _kill_process_tree(proc.pid)
            await proc.wait()
            raise subprocess.TimeoutExpired(cmd, time_limit)
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    # 检查是否触发内存超限
    if oom_event.is_set():
        raise MemoryError(f"Memory limit {memory_limit_mb}MB exceeded")

    runtime = time.time() - start
    if proc.returncode != 0 and proc.returncode is not None:
        raise RuntimeError(f"Exit code: {proc.returncode}")

    return runtime


async def _monitor_memory(
    pid: int,
    memory_limit_bytes: int,
    oom_event: asyncio.Event,
    interval: float = 0.1,
) -> None:
    """后台协程：每 interval 秒检查一次进程树总内存。"""
    try:
        proc = psutil.Process(pid)
        while True:
            try:
                total_rss = _process_tree_rss(proc)
                if total_rss > memory_limit_bytes:
                    logger.warning(
                        "内存超限: PID=%d RSS=%d MB 限制=%d MB",
                        pid,
                        total_rss // (1024 * 1024),
                        memory_limit_bytes // (1024 * 1024),
                    )
                    oom_event.set()
                    _kill_process_tree(pid)
                    return
            except (psutil.NoSuchProcess, ProcessLookupError):
                # 进程已正常退出
                return
            await asyncio.sleep(interval)
    except (psutil.NoSuchProcess, ProcessLookupError):
        pass


def _process_tree_rss(root: psutil.Process) -> int:
    """计算进程树的总 RSS（物理内存）。"""
    try:
        total = root.memory_info().rss
        for child in root.children(recursive=True):
            try:
                total += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def _kill_process_tree(pid: int) -> None:
    """递归杀死进程树。"""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def _make_preexec_fn(time_limit_sec: float, memory_limit_bytes: int):
    """Unix: 返回一个 preexec_fn 用于设置子进程资源限制。"""
    if os.name == "nt":
        return None  # Windows 不支持 preexec_fn

    def _set_limits():
        import resource
        try:
            # 虚拟内存限制
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        except (ValueError, resource.error) as e:
            logger.debug("RLIMIT_AS 设置失败: %s", e)

        try:
            # CPU 时间硬限制
            cpu_limit = int(time_limit_sec) + 5
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
        except (ValueError, resource.error) as e:
            logger.debug("RLIMIT_CPU 设置失败: %s", e)

        try:
            # 限制子进程数，防止 fork 炸弹
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        except (ValueError, resource.error, AttributeError):
            pass

        try:
            # 限制文件大小 (防止写满磁盘)
            resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 * 1024, 64 * 1024 * 1024))
        except (ValueError, resource.error):
            pass

    return _set_limits
