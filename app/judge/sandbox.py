"""
Docker Sandbox — isolated code execution based on antares-oj architecture.

Architecture:
  - Source code mounted READ-ONLY to /input
  - Writable tmpfs /work for compilation and execution
  - mem_monitor.sh for memory usage tracking
  - Separate strategies for compiled vs interpreted languages

Security (antares-oj inspired):
  - Drop all Linux capabilities
  - No network access
  - Memory + CPU hard limits
  - Process count limits (anti fork-bomb)
  - Read-only root filesystem
  - Run as unprivileged user 'sandbox'

Return code convention:
  - None  → normal exit, output comparison needed
  - "CE"  → compilation error
  - "TLE" → time limit exceeded
  - "MLE" → memory limit exceeded
  - "RTE" → runtime error
  - "OLE" → output limit exceeded
"""
import asyncio
import logging
import os
import shutil
import tempfile
import time

from app.config import settings

logger = logging.getLogger(__name__)

# ── Language configurations (antares-oj style) ──────────────────────────
LANG_CONFIG = {
    "python": {
        "ext": "py",
        "source_file": "solution.py",
        "needs_compile": False,
        "compile_cmd": "",
        "run_cmd": "python3 /input/solution.py < /input/stdin.txt",
    },
    "c": {
        "ext": "c",
        "source_file": "solution.c",
        "needs_compile": True,
        "compile_cmd": "gcc -O2 -Wall -std=c11 -o /work/solution /work/solution.c -lm 2>/work/ce.txt",
        "run_cmd": "/work/solution < /work/stdin.txt",
    },
    "cpp": {
        "ext": "cpp",
        "source_file": "solution.cpp",
        "needs_compile": True,
        "compile_cmd": "g++ -O2 -Wall -std=c++17 -o /work/solution /work/solution.cpp -lm 2>/work/ce.txt",
        "run_cmd": "/work/solution < /work/stdin.txt",
    },
    "java": {
        "ext": "java",
        "source_file": "Main.java",
        "needs_compile": True,
        "compile_cmd": "javac -d /work /work/Main.java 2>/work/ce.txt",
        "run_cmd": "java -cp /work Main < /work/stdin.txt",
    },
}

SANDBOX_IMAGE = "jisu-sandbox:latest"

# Marker string in stderr that signals a compilation error
CE_MARKER = "[JISU_CE]"


def _is_docker_available() -> bool:
    """Check if Docker is available on this system."""
    return shutil.which("docker") is not None


def build_sandbox_image() -> bool:
    """Build the sandbox Docker image. Called once at startup."""
    import subprocess

    sandbox_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sandbox")
    sandbox_dir = os.path.abspath(sandbox_dir)

    if not os.path.isdir(sandbox_dir):
        logger.warning("Sandbox directory not found: %s", sandbox_dir)
        return False

    try:
        result = subprocess.run(
            ["docker", "build", "-t", SANDBOX_IMAGE, "."],
            cwd=sandbox_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info("Sandbox Docker image built successfully")
            return True
        else:
            logger.warning("Sandbox image build failed: %s", result.stderr[:200])
            return False
    except Exception as e:
        logger.warning("Docker not available, using subprocess sandbox: %s", e)
        return False


# ── Shell script generators (antares-oj template-method style) ─────────

def _build_container_script(language: str) -> str:
    """
    Build the shell script that runs inside the Docker container.

    For compiled languages:
      1. Copy input files from /input (read-only) to /work (tmpfs)
      2. Compile → if fails, print CE marker to stderr and exit 1
      3. Run the compiled binary with stdin redirected

    For interpreted languages (Python):
      1. Run directly from /input (no compilation needed, no write needed)
    """
    config = LANG_CONFIG.get(language)
    if config is None:
        return "echo 'Unsupported language' >&2; exit 1"

    if not config["needs_compile"]:
        # Interpreted: run directly, no copy needed
        return config["run_cmd"]

    # Compiled: copy → compile → run
    return f"""# Copy source and input to writable /work
cp /input/* /work/ 2>/dev/null

# Compile
{config["compile_cmd"]}
if [ $? -ne 0 ]; then
    # Output compile errors to stderr with a marker
    cat /work/ce.txt >&2
    echo '{CE_MARKER}' >&2
    exit 1
fi

# Run the compiled program
{config["run_cmd"]}
"""


# ── Public API ──────────────────────────────────────────────────────────

async def run_in_container(
    language: str,
    source_code: str,
    input_data: str,
    time_limit: float,
    memory_limit_mb: int,
) -> tuple[str | None, str, float, str]:
    """
    Execute code in an isolated Docker container.

    Returns (verdict, stdout, runtime_seconds, stderr).
    verdict=None means normal exit — caller should compare output.
    """
    if not _is_docker_available():
        raise RuntimeError(
            "Docker not available. Set USE_DOCKER_SANDBOX=false for subprocess fallback."
        )

    config = LANG_CONFIG.get(language)
    if config is None:
        return "RTE", "", 0.0, f"Unsupported language: {language}"

    # Create temp directory for this submission
    work_dir = tempfile.mkdtemp(dir=settings.RUNS_DIR, prefix="sandbox_")
    work_dir = os.path.abspath(work_dir)

    try:
        # Write source code
        source_path = os.path.join(work_dir, config["source_file"])
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        # Write stdin file
        stdin_path = os.path.join(work_dir, "stdin.txt")
        with open(stdin_path, "w", encoding="utf-8") as f:
            f.write(input_data)

        # Build the container command script
        container_script = _build_container_script(language)

        # Build Docker run command
        # Security model (antares-oj inspired):
        #   - /input mounted read-only → source code + input data
        #   - /work as writable tmpfs → compilation artifacts + execution
        #   - CPU/Memory/PIDs capped
        docker_cmd = [
            "docker", "run", "--rm",
            # ── Security ──
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--network=none",
            # ── Resource limits ──
            f"--memory={memory_limit_mb}m",
            f"--memory-swap={memory_limit_mb}m",
            "--cpus=1",
            "--pids-limit=64",
            # ── Filesystem ──
            "--read-only",
            f"--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
            f"--tmpfs=/work:rw,exec,nosuid,size=256m",
            # ── Mount source + input (read-only) ──
            f"-v={work_dir}:/input:ro",
            # ── Work dir ──
            "-w=/work",
            # ── Run as sandbox user ──
            "--user=sandbox",
            # ── Image + command ──
            SANDBOX_IMAGE,
            "/bin/sh", "-c", container_script,
        ]

        logger.debug("Docker cmd: %s", " ".join(docker_cmd[:12]) + "...")

        start = time.time()
        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=time_limit + 10,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            await proc.wait()
            return "TLE", "", time_limit, "Time limit exceeded"

        runtime = time.time() - start
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # ── Output limit check ──
        if len(stdout) > settings.OUTPUT_SIZE_LIMIT:
            stdout = stdout[:settings.OUTPUT_SIZE_LIMIT]
            return "OLE", stdout, runtime, stderr

        # ── Return code → verdict mapping (antares-oj convention) ──
        if proc.returncode == 0:
            # Check for compilation error marker in stderr
            if CE_MARKER in stderr:
                # Strip the marker for clean error display
                stderr_clean = stderr.replace(CE_MARKER, "").strip()
                return "CE", "", runtime, stderr_clean
            return None, stdout, runtime, stderr
        elif proc.returncode == 124:
            # `timeout` command sent SIGTERM
            return "TLE", stdout, time_limit, "Time limit exceeded"
        elif proc.returncode == 137:
            # SIGKILL — typically Docker OOM killer
            return "MLE", stdout, runtime, f"Memory limit exceeded ({memory_limit_mb}MB)"
        else:
            # Check for CE marker (compile error with non-zero exit)
            if CE_MARKER in stderr:
                stderr_clean = stderr.replace(CE_MARKER, "").strip()
                return "CE", "", runtime, stderr_clean
            # Runtime error with exit code
            exit_msg = stderr[:500] if stderr else f"Exit code: {proc.returncode}"
            return "RTE", stdout, runtime, exit_msg

    except asyncio.TimeoutError:
        return "TLE", "", time_limit, "Time limit exceeded"
    except Exception as e:
        logger.error("Sandbox execution failed: %s", e, exc_info=True)
        return "RTE", "", 0.0, str(e)
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
