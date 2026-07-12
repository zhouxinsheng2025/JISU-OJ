# JISU OJ 前端重设计规格

## 概述

吉林外国语大学 ACM 集训队判题系统前端翻新。仅改动 `app/templates/` 和 `app/static/`，不动后端逻辑。

## 设计方向

- **风格**: 学术稳重 (LeetCode / 洛谷风格)，信息层级清晰，可读性优先
- **配色**: 深色 + 浅色双主题，一键切换
- **布局**: 统一侧边栏导航 (可折叠)
- **图标**: Heroicons SVG 内联
- **登录页**: `app/static/photos/` 中随机背景图

---

## 文件结构变更

```
app/
├── static/
│   ├── emblem.webp          # 校徽 (保留)
│   ├── photos/              # 登录页背景图 (新增)
│   │   ├── 1.jpg            # 用户自行放入 .jpg/.png/.webp
│   │   ├── 2.jpg
│   │   └── ...
│   └── icons/               # (不创建，SVG 内联在模板中)
├── templates/
│   ├── base.html            # ★ 核心重构: 侧边栏 + 主题系统
│   ├── auth/
│   │   └── login.html       # ★ 重构: 全屏背景 + 随机图
│   ├── team/                # 选手端 7 个页面翻新
│   ├── jury/                # 裁判端 12 个页面翻新
│   └── public/
│       └── scoreboard.html  # 大屏计分板翻新
```

---

## 配色系统 (CSS 变量)

### 深色主题 (默认)

```css
:root {
  --bg-primary: #0f172a;       /* slate-900 */
  --bg-secondary: #1e293b;     /* slate-800 */
  --bg-card: #1e293b;
  --bg-hover: #334155;         /* slate-700 */
  --border: #334155;
  --text-primary: #f1f5f9;     /* slate-100 */
  --text-secondary: #94a3b8;   /* slate-400 */
  --text-muted: #64748b;       /* slate-500 */
  --accent: #3b82f6;           /* blue-500 */
  --accent-hover: #2563eb;     /* blue-600 */
  --success: #22c55e;          /* green-500 */
  --danger: #ef4444;           /* red-500 */
  --warning: #f59e0b;          /* amber-500 */
  --sidebar-bg: #0f172a;
  --sidebar-width: 240px;
}
```

### 浅色主题

```css
[data-theme="light"] {
  --bg-primary: #f8fafc;       /* slate-50 */
  --bg-secondary: #ffffff;
  --bg-card: #ffffff;
  --bg-hover: #f1f5f9;         /* slate-100 */
  --border: #e2e8f0;           /* slate-200 */
  --text-primary: #0f172a;     /* slate-900 */
  --text-secondary: #475569;   /* slate-600 */
  --text-muted: #94a3b8;       /* slate-400 */
  --sidebar-bg: #1e293b;        /* 侧边栏保持深色 */
}
```

---

## 布局规格

### base.html — 侧边栏 + 主内容区

```
┌──────────┬──────────────────────────────────────┐
│ Sidebar  │  Header bar                          │
│          │  (面包屑 + 主题切换 + 用户名 + 退出)   │
│ Logo     ├──────────────────────────────────────┤
│ ──────── │                                      │
│ Nav Item │  Content Area                        │
│ Nav Item │                                      │
│ Nav Item │                                      │
│ ...      │                                      │
│          │                                      │
│ Collapse │                                      │
│ Button   │                                      │
└──────────┴──────────────────────────────────────┘
```

- 侧边栏宽度: 240px (展开) / 64px (折叠)
- 侧边栏始终深色（浅色主题下也保持深色，形成对比）
- 折叠时只显示图标，悬停展开 tooltip
- 顶部栏: 面包屑 (左) + 主题切换按钮 + 用户名 + 退出 (右)
- 移动端 (<768px): 侧边栏变为底部汉堡菜单弹出

### login.html — 全屏登录

```
┌─────────────────────────────────────────────────┐
│                                                 │
│           [随机背景图 + 半透明遮罩]                │
│                                                 │
│                    ┌─────────┐                   │
│                    │ 校徽    │                   │
│                    │ JISU OJ │                   │
│                    │         │                   │
│                    │ [表单]  │                   │
│                    │         │                   │
│                    └─────────┘                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

- 背景: `/static/photos/` 随机选取，每次刷新变化
- 遮罩: 深色半透明 `bg-black/50`
- 登录卡片: 毛玻璃效果 `backdrop-blur`
- 实现: 后端传照片列表到模板，JS 随机选一张或模板随机选

### 选手端页面

| 页面 | 核心内容 |
|------|---------|
| 仪表盘 | 比赛倒计时(大字) + 快捷入口卡片(题目/提交/计分板) |
| 题目列表 | 表格: 状态图标(AC/WA/-) + 题号 + 标题 + 难度标签 |
| 题目详情 | 题目描述 + 样例(可切换tab) + 代码提交区(语言选择+文本框+提交按钮) |
| 提交记录 | 表格: ID + 题目 + 语言 + 时间 + 状态 + 结果徽章 + 分数 |
| 提交详情 | 代码展示(语法高亮) + 判题结果 + 逐测试点表格 |
| 计分板 | 表格: 排名 + 队伍 + 每题状态 + 解题数 + 罚时 |
| 练习 | 题目卡片网格 + 进度指示 |

### 裁判端页面

| 页面 | 核心内容 |
|------|---------|
| 仪表盘 | 统计卡片(总题目/比赛/队伍/提交数) + 快捷入口网格 |
| 题库 | 表格 + 筛选栏(难度/标签下拉) + 新建/导入按钮 |
| 题目表单 | 表单: PID + 标题 + 描述 + 难度 + 标签 + 时限 + 内存 |
| 比赛列表 | 表格 + 状态徽章(进行中/已结束) + 切换启用按钮 |
| 比赛表单 | 表单: 标题 + 时间 + 计分模式 + 封榜时间 |
| 添加题目 | 双栏: 题库列表(左) + 已选题目(右) |
| 测试数据 | 题目信息 + 样例/隐藏数据双tab + ZIP上传区 + 单个添加表单 |
| 队伍列表 | 表格 + CSV导入按钮 |
| 队伍表单 | 表单: 用户名 + 密码 + 队伍名 |
| 提交记录 | 同选手端, 额外操作列(重判按钮) |
| 提交详情 | 代码 + 判题结果 + 测试点 + 重判按钮 |
| 问答 | 问题列表(展开式) + 回复表单 |
| 计分板 | 同选手端, 额外导出按钮, 不封榜 |

### 公共大屏计分板

- 无导航栏, 纯展示
- 更大字号, 更多留白
- AC 绿色呼吸动画
- 顶部: 比赛标题 + 实时时钟
- 底部: 状态指示器 (实时/封榜/离线)

---

## 组件库

### 表格
- 圆角表头 `rounded-t-lg`
- 斑马纹行
- 悬停高亮
- 数据行 `border-b border-[var(--border)]`
- 等宽字体列使用 `font-mono`

### 卡片
- `bg-[var(--bg-card)] rounded-xl border border-[var(--border)]`
- 可选阴影: `shadow-sm`
- 内边距: `p-6`

### 按钮
- 主按钮: `bg-[var(--accent)] text-white px-4 py-2 rounded-lg font-medium`
- 次按钮: `border border-[var(--border)] text-[var(--text-primary)] px-4 py-2 rounded-lg`
- 危险按钮: `bg-[var(--danger)] text-white px-4 py-2 rounded-lg`
- 小按钮: `px-3 py-1.5 text-sm`

### 徽章 (Badge)
用于判题结果/难度/状态标签:
- AC: 绿色
- WA: 红色
- TLE/MLE: 黄色
- CE: 紫色
- 难度 easy: 绿色, medium: 黄色, hard: 红色

### 表单
- `bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-4 py-2.5`
- focus: `ring-2 ring-[var(--accent)] border-transparent`
- 标签: `text-sm font-medium text-[var(--text-secondary)] mb-1`

### 侧边栏菜单项
- 展开: `图标(20px) + 文字` 
- 折叠: `图标(20px)` 居中
- 当前页: 左侧蓝色竖线 + 蓝色背景
- 悬停: 背景色变化

---

## 响应式断点

| 断点 | 布局调整 |
|------|---------|
| >=1024px | 完整侧边栏 + 内容区 |
| 768-1023px | 折叠侧边栏 |
| <768px | 侧边栏隐藏, 顶部汉堡菜单, 内容区全宽 |

---

## 主题切换实现

- `localStorage` 存储用户选择
- 默认跟随系统 `prefers-color-scheme`
- `<html data-theme="dark|light">` 控制
- 切换按钮: 太阳/月亮图标, 点击即切换
- 过渡动画: `transition-colors duration-300` 防止闪烁

---

## 登录页背景实现

### 后端 (app/main.py 或 templates_helpers.py)
```python
# 在 startup 或 template global 中注册
import os, random
def get_login_photos():
    photo_dir = os.path.join(os.path.dirname(__file__), "static", "photos")
    if not os.path.isdir(photo_dir):
        return []
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    photos = [f for f in os.listdir(photo_dir) if os.path.splitext(f)[1].lower() in exts]
    return photos
```

### 前端 (Jinja2 + JS)
```html
<!-- 后端传入 photos 列表 -->
<script>
const photos = {{ photos | tojson }};
if (photos.length > 0) {
    const pick = photos[Math.floor(Math.random() * photos.length)];
    document.body.style.backgroundImage = `url('/static/photos/${pick}')`;
}
</script>
```

如果 `photos/` 为空，降级为纯色渐变背景。

---

## 实施顺序

1. **base.html** — 侧边栏 + 主题系统 + CSS 变量
2. **login.html** — 随机背景 + 毛玻璃卡片
3. **team/dashboard.html** — 仪表盘 (以此建立选手端模板)
4. **team/ 其余6页** — 依序翻新
5. **jury/dashboard.html** — 仪表盘 (以此建立裁判端模板)
6. **jury/ 其余11页** — 依序翻新
7. **public/scoreboard.html** — 大屏计分板
8. **整体打磨** — 过渡动画、响应式、细节调整

---

## 验证

- [ ] 深色/浅色切换正常，刷新后保持
- [ ] 侧边栏折叠/展开正常
- [ ] 移动端汉堡菜单可用
- [ ] 登录页背景随机切换
- [ ] 所有后端功能不受影响 (提交/判题/计分板/问答/导出)
- [ ] 所有 26 个页面无布局错乱
- [ ] WebSocket 实时刷新仍正常
