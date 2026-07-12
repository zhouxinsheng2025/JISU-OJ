import subprocess
import os
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

COMPILE_COMMANDS = {
    "c":     ["gcc",   "-O2", "-Wall", "-std=c11",  "-o", "{output}", "{source}", "-lm"],
    "cpp":   ["g++",   "-O2", "-Wall", "-std=c++17","-o", "{output}", "{source}", "-lm"],
    "java":  ["javac", "-d", "{work_dir}", "{source}"],
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
    work_dir = os.path.abspath(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    if language not in COMPILE_COMMANDS:
        return False, "", f"不支持的语言类型: {language}"

    if language == "python":
        # Python 不需要编译，直接写入文件
        src_path = os.path.join(work_dir, "solution.py")
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(source_code)
        return True, src_path, ""

    ext = LANGUAGE_EXT[language]
    src_path = os.path.join(work_dir, f"solution.{ext}")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(source_code)

    if language == "java":
        exe_path = os.path.join(work_dir, "Main.class")
    else:
        exe_path = os.path.join(work_dir, "solution")

    cmd_template = COMPILE_COMMANDS[language]
    cmd = [arg.format(source=src_path, output=exe_path, work_dir=work_dir) for arg in cmd_template]

    try:
        proc = await asyncio.to_thread(
            lambda: subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=settings.COMPILE_TIME_LIMIT,
            )
        )
        if proc.returncode != 0:
            return False, proc.stderr, proc.stderr
        return True, exe_path, ""
    except subprocess.TimeoutExpired:
        return False, "", "Compilation timed out"
    except FileNotFoundError:
        return False, "", f"编译器未安装或不可用: {cmd[0]}"
