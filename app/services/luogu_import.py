"""
洛谷 / Hydro / CCP 题目格式导入

支持的格式:
1. Hydro 导出格式: problem_zh.md + testdata/ + problem.yaml
2. 洛谷题单导出: problem.md + testcases/
3. 通用 .in/.out 文件对（自动配对）
"""
import zipfile
import io
import re
import yaml
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Problem, TestCase, Difficulty


def parse_luogu_zip(zip_bytes: bytes) -> dict | None:
    """解析洛谷/Hydro格式的题目ZIP，返回题目数据 + 测试数据列表"""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()

        # 1. 解析题目描述
        description = ""
        title = ""
        time_limit = 1.0
        memory_limit = 256
        difficulty = Difficulty.EASY

        # 找题目描述文件
        desc_files = [n for n in namelist if n.endswith(('problem_zh.md', 'problem.md', 'statement.md', 'README.md'))]
        for desc_file in desc_files:
            content = zf.read(desc_file).decode('utf-8', errors='replace')
            if not description or 'zh' in desc_file:
                description = content
            # 从 Markdown 标题提取题目名
            if not title:
                m = re.search(r'^#\s*(.+)', content, re.MULTILINE)
                if m:
                    title = m.group(1).strip()

        # 找 YAML 配置
        yaml_files = [n for n in namelist if n.endswith(('problem.yaml', 'config.yaml', 'problem.yml'))]
        for yf in yaml_files:
            try:
                config = yaml.safe_load(zf.read(yf).decode('utf-8'))
                if config:
                    if 'title' in config:
                        title = config['title']
                    if 'time' in config:
                        t_str = str(config['time']).strip().lower()
                        if 'ms' in t_str:
                            time_limit = float(t_str.replace('ms', '')) / 1000
                        elif 's' in t_str:
                            time_limit = float(t_str.replace('s', ''))
                        else:
                            time_limit = float(t_str)
                    elif 'timeLimit' in config:
                        time_limit = float(config['timeLimit']) / 1000 if config['timeLimit'] > 100 else float(config['timeLimit'])
                    if 'memory' in config:
                        memory_limit = int(str(config['memory']).replace('MB', '').replace('M', '').replace('mb', '').strip())
                    elif 'memoryLimit' in config:
                        mem = int(config['memoryLimit'])
                        memory_limit = mem if mem > 100 else mem
                    if 'difficulty' in config:
                        diff_map = {1: Difficulty.EASY, 2: Difficulty.EASY, 3: Difficulty.MEDIUM,
                                    4: Difficulty.MEDIUM, 5: Difficulty.HARD, 6: Difficulty.HARD, 7: Difficulty.HARD}
                        difficulty = diff_map.get(config['difficulty'], Difficulty.EASY)
            except Exception:
                pass

        # 如果没有找到标题，用 ZIP 中第一个目录名
        if not title:
            for n in namelist:
                parts = n.split('/')
                if len(parts) > 1 and parts[0]:
                    title = parts[0]
                    break
            if not title:
                title = "Imported Problem"

        # 2. 解析测试数据
        testcases = []
        inputs = {}
        outputs = {}

        for name in namelist:
            if name.endswith('/'):
                continue
            basename = name.split('/')[-1]
            parent = name.split('/')[0] if '/' in name else ''

            content = zf.read(name).decode('utf-8', errors='replace').replace('\r\n', '\n')

            if basename.endswith('.in'):
                key = basename[:-3]
                # 判断是否是样例
                is_sample = 'sample' in name.lower() or 'example' in name.lower() or parent == 'sample'
                # Hydro: testdata/ 下可能有 config.yaml
                inputs[key] = (content.strip(), is_sample)
            elif basename.endswith('.out') or basename.endswith('.ans'):
                key = basename[:-4] if basename.endswith('.out') else basename[:-4]
                outputs[key] = (content.strip(), False)

        # 配对
        for key, (in_content, in_sample) in inputs.items():
            out_data = outputs.get(key)
            if out_data is None:
                # 尝试去掉前导零
                stripped_key = key.lstrip('0') or '0'
                out_data = outputs.get(stripped_key)
            if out_data:
                out_content, _ = out_data
                testcases.append({
                    "input": in_content,
                    "output": out_content,
                    "is_sample": in_sample,
                })

        # 按数字排序
        def sort_key(tc):
            for k, (content, _) in inputs.items():
                if content == tc["input"]:
                    try:
                        return int(re.sub(r'\D', '', k) or '0')
                    except ValueError:
                        return 0
            return 0

        testcases.sort(key=sort_key, reverse=False)

        return {
            "title": title,
            "description": description,
            "time_limit": time_limit,
            "memory_limit": memory_limit,
            "difficulty": difficulty,
            "testcases": testcases,
        }


async def import_from_luogu_zip(db: AsyncSession, zip_bytes: bytes) -> Problem | None:
    """从洛谷ZIP导入题目（含测试数据）"""
    data = parse_luogu_zip(zip_bytes)
    if data is None or not data.get("testcases"):
        return None

    # 生成 PID
    from sqlalchemy import select, func
    result = await db.execute(select(func.max(Problem.id)))
    max_id = result.scalar() or 0
    pid = f"P{max_id + 1001}"

    from app.models import Difficulty as DiffEnum
    diff_map = {"easy": DiffEnum.EASY, "medium": DiffEnum.MEDIUM, "hard": DiffEnum.HARD}
    difficulty = diff_map.get(data["difficulty"], DiffEnum.EASY) if isinstance(data["difficulty"], str) else data["difficulty"]

    problem = Problem(
        pid=pid,
        title=data["title"],
        description=data["description"],
        difficulty=difficulty,
        time_limit=data["time_limit"],
        memory_limit=data["memory_limit"],
    )
    db.add(problem)
    await db.flush()

    for i, tc_data in enumerate(data["testcases"]):
        tc = TestCase(
            problem_id=problem.id,
            input=tc_data["input"],
            output=tc_data["output"],
            is_sample=tc_data.get("is_sample", False),
            order=i + 1,
        )
        db.add(tc)

    await db.commit()
    await db.refresh(problem)
    return problem
