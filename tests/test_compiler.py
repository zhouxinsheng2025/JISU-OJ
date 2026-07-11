import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from app.judge.compiler import compile_code


class TestCompile:
    def test_python_no_compile(self):
        """Python 不需要编译，直接返回源文件路径。"""
        ok, path, err = __import__('asyncio').run(
            compile_code("print('hello')", "python", "/tmp")
        )
        assert ok is True
        assert path.endswith(".py")

    @patch("app.judge.compiler.subprocess.run")
    def test_c_compile_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        ok, path, err = __import__('asyncio').run(
            compile_code('#include <stdio.h>\nint main(){return 0;}', "c", "/tmp")
        )
        assert ok is True
        assert "solution" in path

    @patch("app.judge.compiler.subprocess.run")
    def test_c_compile_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="syntax error")
        ok, path, err = __import__('asyncio').run(
            compile_code('broken code', "c", "/tmp")
        )
        assert ok is False
        assert "syntax error" in err
