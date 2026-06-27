import subprocess
import os
import asyncio
from app.config import settings

COMPILE_COMMANDS = {
    "c": "gcc {source} -o {output} -O2 -Wall -lm",
    "cpp": "g++ {source} -o {output} -O2 -Wall -lm",
    "java": "javac {source}",
    "python": None,  # 无需编译
}


LANGUAGE_EXT = {
    "c": "c",
    "cpp": "cpp",
    "java": "java",
    "python": "py",
}


async def compile_code(source_code: str, language: str, work_dir: str) -> tuple[bool, str, str]:
    """编译源代码，返回 (成功, 可执行路径或错误, 编译器输出)"""
    os.makedirs(work_dir, exist_ok=True)

    if language == "python":
        # Python 不需要编译，直接写入文件
        src_path = os.path.join(work_dir, "solution.py")
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source_code)
        return True, src_path, ""

    ext = LANGUAGE_EXT.get(language, "txt")
    src_path = os.path.join(work_dir, f"solution.{ext}")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    if language == "java":
        exe_path = os.path.join(work_dir, "Main.class")
    else:
        exe_path = os.path.join(work_dir, "solution")

    cmd = COMPILE_COMMANDS[language].format(source=src_path, output=exe_path)

    try:
        proc = await _run_async(cmd, work_dir)
        if proc.returncode != 0:
            return False, proc.stderr, proc.stderr
        return True, exe_path, ""
    except subprocess.TimeoutExpired:
        return False, "", "Compilation timed out"


async def _run_async(cmd: str, cwd: str) -> subprocess.CompletedProcess:
    return await asyncio.to_thread(asyncio_to_thread_run, cmd, cwd)


def asyncio_to_thread_run(cmd: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True,
        timeout=settings.COMPILE_TIME_LIMIT,
    )
