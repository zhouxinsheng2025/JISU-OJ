import zipfile, io, re
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import TestCase


def parse_testdata_zip(zip_bytes: bytes) -> list[dict]:
    """解析ZIP文件，提取测试数据对 (.in/.out 或 .in/.ans)
    支持DOMjudge格式: sample/目录=样例, secret/目录或根目录=隐藏数据
    返回: [{"input": str, "output": str, "is_sample": bool}, ...]
    """
    testcases = []
    inputs = {}  # key -> input content
    outputs = {}  # key -> output content

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith('/'):
                continue  # skip directories
            basename = name.split('/')[-1]
            if not basename:
                continue
            # Determine if sample or secret
            is_sample = name.startswith('sample/') or name.startswith('sample\\')
            # Extract key: remove extension and path
            key = basename.rsplit('.', 1)[0]
            content = zf.read(name).decode('utf-8', errors='replace').replace('\r\n', '\n')

            if basename.endswith('.in'):
                inputs[key] = (content, is_sample)
            elif basename.endswith('.out') or basename.endswith('.ans'):
                outputs[key] = (content, is_sample)

    # Pair inputs with outputs by key
    for key, (in_content, in_sample) in inputs.items():
        out_data = outputs.get(key)
        if out_data is None:
            # try without leading zeros: "01" matches "1"
            for ok in outputs:
                if ok.lstrip('0') == key.lstrip('0'):
                    out_data = outputs[ok]
                    break
        if out_data:
            out_content, out_sample = out_data
            testcases.append({
                "input": in_content.strip(),
                "output": out_content.strip(),
                "is_sample": in_sample or out_sample,
            })

    # Sort by numeric key
    def sort_key(tc):
        try:
            # Extract numeric part from key
            key = list(inputs.keys())[list(inputs.values()).index((tc["input"], tc["is_sample"]))] if (tc["input"], tc["is_sample"]) in inputs.values() else "0"
            return int(re.sub(r'\D', '', key) or "0")
        except:
            return 0

    return testcases


async def import_testcases_from_zip(
    db: AsyncSession,
    problem_id: int,
    zip_bytes: bytes,
    replace: bool = False,
) -> int:
    """从ZIP导入测试数据到指定题目
    replace=True时先删除旧数据
    返回导入数量
    """
    if replace:
        from sqlalchemy import select, delete
        await db.execute(delete(TestCase).where(TestCase.problem_id == problem_id))
        await db.commit()

    data = parse_testdata_zip(zip_bytes)
    count = 0
    for i, tc_data in enumerate(data):
        tc = TestCase(
            problem_id=problem_id,
            input=tc_data["input"],
            output=tc_data["output"],
            is_sample=tc_data["is_sample"],
            order=i + 1,
        )
        db.add(tc)
        count += 1
    await db.commit()
    return count
