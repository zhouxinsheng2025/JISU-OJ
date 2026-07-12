# Website Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all 26 frontend templates with sidebar layout, dark/light theme toggle, SVG icons, and randomized login backgrounds.

**Architecture:** New `base.html` provides sidebar + header + CSS variable theme system. All page templates extend it with consistent card/table/form components. Login page is standalone with fullscreen random background.

**Tech Stack:** Jinja2 templates, Tailwind CSS (CDN), Heroicons SVG inline, vanilla JS for theme toggle and login background

## Global Constraints

- Modify files in `app/templates/` and `app/static/` only
- Minimal backend change: only add photos list to login route in `app/routers/auth.py`
- Zero new Python/JS dependencies
- Preserve all existing functionality (submit, judge, scoreboard, WebSocket, export)
- Use CSS variables for theming (not Tailwind's `dark:` prefix)

---

### Task 1: Foundation — base.html + Login Page

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/templates/auth/login.html`
- Modify: `app/routers/auth.py` (minimal: pass photos list to template)
- Create: `app/static/photos/` (already exists, empty)
- Create: sample photo placeholder note

- [ ] **Step 1: Build the new base.html**

Write `app/templates/base.html` with:
- CSS variables in `<style>` block for dark/light theme
- Sidebar (240px, collapsible to 64px) with school emblem + nav links
- Top header bar with breadcrumb (left), theme toggle + username + logout (right)
- Mobile hamburger menu for <768px
- `localStorage` theme persistence + system preference detection

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}JISU裁判系统{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --border: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --sidebar-bg: #0f172a;
            --sidebar-width: 240px;
        }
        [data-theme="light"] {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-card: #ffffff;
            --bg-hover: #f1f5f9;
            --border: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --sidebar-bg: #1e293b;
        }
        body { background: var(--bg-primary); color: var(--text-primary); }
        .sidebar { width: var(--sidebar-width); background: var(--sidebar-bg); }
        .sidebar.collapsed { width: 64px; }
        .sidebar.collapsed .nav-label { display: none; }
        .sidebar.collapsed .nav-icon { margin: 0 auto; }
        @media (max-width: 767px) {
            .sidebar { display: none; }
            .sidebar.open { display: flex; position: fixed; z-index: 50; height: 100vh; width: 240px; }
        }
    </style>
</head>
<body class="min-h-screen flex">
    {% if user %}
    <!-- Sidebar -->
    <aside id="sidebar" class="sidebar flex flex-col border-r border-[var(--border)] transition-all duration-200 shrink-0">
        <div class="h-14 flex items-center gap-2 px-4 border-b border-[var(--border)]">
            <img src="/static/emblem.webp" alt="校徽" class="w-7 h-7 rounded" style="object-fit:contain">
            <span class="font-bold text-base text-blue-400 nav-label whitespace-nowrap">JISU裁判系统</span>
        </div>
        <nav class="flex-1 py-2 overflow-y-auto">
            {% block sidebar %}{% endblock %}
        </nav>
        <button onclick="toggleSidebar()" class="h-10 flex items-center justify-center border-t border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/></svg>
        </button>
    </aside>
    <!-- Main -->
    <div class="flex-1 flex flex-col min-w-0">
        <header class="h-14 flex items-center justify-between px-6 border-b border-[var(--border)] bg-[var(--bg-secondary)] shrink-0">
            <div id="breadcrumb" class="text-sm text-[var(--text-muted)]">
                {% block breadcrumb %}{% endblock %}
            </div>
            <div class="flex items-center gap-3 text-sm">
                <button onclick="toggleTheme()" class="p-1.5 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-secondary)]" title="切换主题">
                    <svg id="theme-icon-light" class="w-5 h-5 hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    <svg id="theme-icon-dark" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
                </button>
                <span class="text-[var(--text-secondary)]">{{ user.teamname }}</span>
                <a href="/auth/logout" class="text-red-400 hover:text-red-300 transition-colors">退出</a>
            </div>
        </header>
        <main class="flex-1 p-6 overflow-y-auto">
            {% block content %}{% endblock %}
        </main>
    </div>
    {% else %}
    <main class="flex-1">
        {% block content %}{% endblock %}
    </main>
    {% endif %}
    <script>
    // Theme toggle
    (function() {
        const html = document.documentElement;
        const saved = localStorage.getItem('theme');
        if (saved) { html.setAttribute('data-theme', saved); }
        else if (window.matchMedia('(prefers-color-scheme: light)').matches) { html.setAttribute('data-theme', 'light'); }
        updateThemeIcons();
    })();
    function toggleTheme() {
        const html = document.documentElement;
        const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcons();
    }
    function updateThemeIcons() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        document.getElementById('theme-icon-dark').style.display = isDark ? 'none' : '';
        document.getElementById('theme-icon-light').style.display = isDark ? '' : 'none';
    }
    // Sidebar toggle
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('collapsed');
        localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
    }
    // Restore sidebar state
    (function() {
        if (localStorage.getItem('sidebar-collapsed') === 'true') {
            document.getElementById('sidebar')?.classList.add('collapsed');
        }
    })();
    // Mobile menu
    function toggleMobileMenu() {
        document.getElementById('sidebar').classList.toggle('open');
    }
    </script>
</body>
</html>
```

- [ ] **Step 2: Add mobile hamburger button to header**

Add a hamburger button that only shows on mobile:
```html
<button onclick="toggleMobileMenu()" class="md:hidden p-1.5 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-muted)]">
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
</button>
```

Place it inside the `<header>` before the breadcrumb div.

- [ ] **Step 3: Add sidebar nav item macro**

Add a reusable Jinja2 macro pattern for nav items. Each template's `{% block sidebar %}` will contain nav items like:
```html
{% block sidebar %}
<a href="/jury/" class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors rounded-lg mx-2 {{ 'bg-blue-500/10 text-blue-400 border-l-2 border-blue-500' if request.url.path == '/jury/' else 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]' }}">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>
    <span class="nav-label">仪表盘</span>
</a>
{% endblock %}
```

- [ ] **Step 4: Rebuild login.html**

Write `app/templates/auth/login.html` with:
- Fullscreen layout with random background image from `/static/photos/`
- Dark overlay + glass-morphism login card
- School emblem + system name
- Username/password form + login button
- Fallback gradient background when no photos exist

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - JISU裁判系统</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --danger: #ef4444;
            --border: #334155;
        }
        body { background: var(--bg-primary); }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(148, 163, 184, 0.1); }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center bg-cover bg-center bg-no-repeat p-4" id="login-body" style="background-image: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);">
    <div class="glass rounded-2xl p-8 w-full max-w-sm shadow-2xl">
        <div class="text-center mb-6">
            <img src="/static/emblem.webp" alt="校徽" class="w-16 h-16 mx-auto rounded-xl mb-3" style="object-fit:contain">
            <h1 class="text-xl font-bold text-[var(--text-primary)]">JISU程序设计裁判系统</h1>
            <p class="text-sm text-[var(--text-muted)] mt-1">吉林外国语大学 ACM 集训队</p>
        </div>
        {% if error %}
        <div class="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2.5 rounded-lg mb-4 text-sm">{{ error }}</div>
        {% endif %}
        <form method="post" action="/auth/login" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-[var(--text-secondary)] mb-1">用户名</label>
                <input type="text" name="username" required autofocus
                    class="w-full bg-slate-800/50 border border-[var(--border)] rounded-lg px-4 py-2.5 text-[var(--text-primary)] text-sm focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent outline-none transition-all">
            </div>
            <div>
                <label class="block text-sm font-medium text-[var(--text-secondary)] mb-1">密码</label>
                <input type="password" name="password" required
                    class="w-full bg-slate-800/50 border border-[var(--border)] rounded-lg px-4 py-2.5 text-[var(--text-primary)] text-sm focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent outline-none transition-all">
            </div>
            <button type="submit"
                class="w-full bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white font-medium py-2.5 rounded-lg transition-colors">
                登录
            </button>
        </form>
    </div>
    <script>
    const photos = {{ photos | tojson }};
    if (photos.length > 0) {
        const pick = photos[Math.floor(Math.random() * photos.length)];
        document.getElementById('login-body').style.backgroundImage = `url('/static/photos/${pick}')`;
    }
    </script>
</body>
</html>
```

- [ ] **Step 5: Update auth.py login route to pass photos**

Modify `app/routers/auth.py`, the `login_page` GET handler:
```python
@router.get("/login")
async def login_page(request: Request):
    import os
    photo_dir = os.path.join(os.path.dirname(__file__), "..", "static", "photos")
    photos = []
    if os.path.isdir(photo_dir):
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        photos = [f for f in os.listdir(photo_dir) if os.path.splitext(f)[1].lower() in exts]
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/login.html",
        {"request": request, "photos": photos}
    )
```

And the `login` POST handler's error response also needs `"photos": []`:
```python
return templates.TemplateResponse(
    f"{TEMPLATE_DIR}/login.html",
    {"request": request, "error": "用户名或密码错误", "photos": []},
    status_code=401,
)
```

- [ ] **Step 6: Verify login page works**

Run: `python -c "from app.main import app; print('OK')"` — should import cleanly.
Start the dev server: `python run.py`
Open http://localhost:8000/auth/login — verify the login page renders with the new design.
Place sample images in `app/static/photos/` and verify random background works on refresh.

---

### Task 2: Team Templates (7 pages)

**Files:**
- Modify: `app/templates/team/dashboard.html`
- Modify: `app/templates/team/problems.html`
- Modify: `app/templates/team/problem_detail.html`
- Modify: `app/templates/team/submissions.html`
- Modify: `app/templates/team/submission_detail.html`
- Modify: `app/templates/team/scoreboard.html`
- Modify: `app/templates/team/practice.html`
- Modify: `app/templates/team/clarifications.html`

**Interfaces:**
- Consumes: `base.html` sidebar + theme system from Task 1
- Produces: Team sidebar nav block with icons for dashboard, problems, practice, submissions, scoreboard, clarifications

- [ ] **Step 1: Team sidebar nav block**

Each team template uses this sidebar block:
```html
{% block sidebar %}
<!-- 仪表盘 -->
<a href="/team/" class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors rounded-lg mx-2 mb-0.5 {{ 'bg-blue-500/10 text-blue-400 border-l-2 border-blue-500' if request.url.path == '/team/' else 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]' }}">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>
    <span class="nav-label">仪表盘</span>
</a>
<!-- 题目 -->
<a href="/team/problems" class="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors rounded-lg mx-2 mb-0.5 {{ 'bg-blue-500/10 text-blue-400 border-l-2 border-blue-500' if '/team/problems' in request.url.path else 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]' }}">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
    <span class="nav-label">题目列表</span>
</a>
<!-- 练习 -->
<a href="/team/practice" class="...">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
    <span class="nav-label">开放练习</span>
</a>
<!-- 提交记录 -->
<a href="/team/submissions" class="...">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"/></svg>
    <span class="nav-label">提交记录</span>
</a>
<!-- 计分板 -->
<a href="/team/scoreboard" class="...">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
    <span class="nav-label">计分板</span>
</a>
<!-- 问答 -->
<a href="/team/clarifications" class="...">
    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
    <span class="nav-label">问答</span>
</a>
{% endblock %}
```

Also add `{% block breadcrumb %}` with appropriate path for each page. For example in dashboard:
```html
{% block breadcrumb %}仪表盘{% endblock %}
```
In problems:
```html
{% block breadcrumb %}<a href="/team/" class="hover:text-[var(--text-primary)]">仪表盘</a> / 题目列表{% endblock %}
```

- [ ] **Step 2: Rewrite team/dashboard.html**

Key components:
- Contest info card with styled countdown timer
- Quick action grid (Problems / Submissions / Scoreboard / Practice)
- Practice mode prompt if no active contest

Maintain the existing countdown JavaScript, wrap content in new card/button styles.

- [ ] **Step 3: Rewrite team/problems.html**

Styled table with:
- Status column: green check circle (AC), red X (attempted), gray dot (untouched)
- Problem ID + title link
- Difficulty badge (easy=green, medium=yellow, hard=red)
- Use the status_map from existing template data

- [ ] **Step 4: Rewrite team/problem_detail.html**

- Problem description section (prose, well-formatted)
- Sample test cases in tab-style cards (input/output toggles)
- Code submission form: language select dropdown + textarea + submit button
- Error messages styled as alert banners

- [ ] **Step 5: Rewrite team/submissions.html + submission_detail.html**

Submissions table with verdict badges. Keep the WebSocket auto-refresh script. Submission detail with code display area + per-testcase results table.

- [ ] **Step 6: Rewrite team/scoreboard.html**

Same table structure as before, new styling. Keep WebSocket real-time refresh. Add freeze warning banner.

- [ ] **Step 7: Rewrite team/practice.html + clarifications.html**

Practice: problem card grid with progress bars.
Clarifications: expandable Q&A list + ask question form.

- [ ] **Step 8: Verify team pages**

Run dev server, log in as a team user, navigate all 7 pages. Verify layout, theme toggle, sidebar collapse, mobile responsive.

---

### Task 3: Jury Templates (12 pages)

**Files:**
- Modify: `app/templates/jury/dashboard.html`
- Modify: `app/templates/jury/bank.html`
- Modify: `app/templates/jury/bank_form.html`
- Modify: `app/templates/jury/contests.html`
- Modify: `app/templates/jury/contest_form.html`
- Modify: `app/templates/jury/add_problem.html`
- Modify: `app/templates/jury/problems.html`
- Modify: `app/templates/jury/testcases.html`
- Modify: `app/templates/jury/teams.html`
- Modify: `app/templates/jury/team_form.html`
- Modify: `app/templates/jury/submissions.html`
- Modify: `app/templates/jury/submission_detail.html`
- Modify: `app/templates/jury/clarifications.html`
- Modify: `app/templates/jury/scoreboard.html`

- [ ] **Step 1: Jury sidebar nav block**

7 nav items: 仪表盘, 题库, 比赛管理, 队伍管理, 提交记录, 问答, 计分板

Icons:
- 仪表盘: grid squares (same as team)
- 题库: `M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10` (archive/book)
- 比赛: `M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2` (clipboard)
- 队伍: `M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z` (users)
- 提交: same as team
- 问答: same as team
- 计分板: same as team

- [ ] **Step 2: Rewrite jury/dashboard.html**

Stats cards (total problems, contests, teams, submissions) in a 4-column grid. Each card shows count + label + icon. Below: quick action buttons grid.

- [ ] **Step 3: Rewrite jury/bank.html + bank_form.html**

Bank: filter bar (difficulty dropdown, tag input) + problem table + "新建题目" and "导入洛谷" buttons.
Bank form: styled form with PID auto-generation info, description textarea, difficulty/tag/time/memory fields.

- [ ] **Step 4: Rewrite jury/contests.html + contest_form.html**

Contests: table with title, time range, type badge, status badge, toggle enable button, edit/delete actions.
Contest form: datetime-local inputs, score mode radio, freeze time field.

- [ ] **Step 5: Rewrite jury/problems.html + add_problem.html + testcases.html**

Problems: contest title header + problem table with remove button + "添加题目" button.
Add problem: dual-column layout — left column lists all bank problems with checkboxes, right column shows already-added problems.
Testcases: problem info header + sample/secret tab toggle + ZIP upload dropzone + inline add form + testcase list.

- [ ] **Step 6: Rewrite jury/teams.html + team_form.html**

Teams: CSV upload button + team table (username, teamname, enabled toggle, edit/delete).
Team form: username, password (optional on edit), teamname, enabled checkbox.

- [ ] **Step 7: Rewrite jury/submissions.html + submission_detail.html**

Same as team but with extra "重判" (rejudge) button column. Keep existing rejudge form.

- [ ] **Step 8: Rewrite jury/clarifications.html + scoreboard.html**

Clarifications: filterable by contest, accordion-style Q&A with reply form.
Scoreboard: same as team but with export button, always shows real data.

- [ ] **Step 9: Verify jury pages**

Log in as admin, navigate all 12 pages. Verify layout, actions, forms, theme toggle.

---

### Task 4: Public Scoreboard

**Files:**
- Modify: `app/templates/public/scoreboard.html`

- [ ] **Step 1: Redesign public scoreboard for big screen display**

Key design changes:
- No sidebar/header (standalone page)
- Larger font sizes, more whitespace
- AC cells: green background with subtle pulse animation
- Top bar: contest title + real-time clock
- Bottom status bar: connection status indicator
- Keep WebSocket auto-refresh
- Print-friendly layout

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% if contest %}{{ contest.title }} - {% endif %}计分板</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --bg-primary: #0a0f1a;
            --bg-secondary: #111827;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #3b82f6;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
        }
        body { background: var(--bg-primary); color: var(--text-primary); }
        @keyframes pulse-green {
            0%, 100% { background-color: rgba(34, 197, 94, 0.15); }
            50% { background-color: rgba(34, 197, 94, 0.3); }
        }
        .ac-cell { animation: pulse-green 3s ease-in-out infinite; }
    </style>
</head>
<body class="min-h-screen p-6">
    {% if contest %}
    <div class="max-w-7xl mx-auto">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold mb-2">{{ contest.title }}</h1>
            <div class="flex items-center justify-center gap-4 text-sm">
                <span class="text-[var(--text-secondary)]">
                    {{ contest.start_time.strftime('%Y-%m-%d %H:%M') }} ~ {{ contest.end_time.strftime('%Y-%m-%d %H:%M') }}
                </span>
                <span id="clock" class="font-mono text-lg text-[var(--accent)]"></span>
            </div>
            {% if freeze %}
            <div class="mt-2 inline-block bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 px-3 py-1 rounded-full text-sm">已封榜</div>
            {% endif %}
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b border-gray-700 text-[var(--text-secondary)] text-xs uppercase tracking-wider">
                        <th class="px-3 py-3 text-center w-10">#</th>
                        <th class="px-4 py-3 text-left">队伍</th>
                        {% for problem in problems %}
                        <th class="px-2 py-3 text-center w-12">{{ problem.title[:8] }}</th>
                        {% endfor %}
                        <th class="px-3 py-3 text-center w-14">解题</th>
                        <th class="px-4 py-3 text-center w-16">罚时</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in board %}
                    <tr class="border-b border-gray-800 hover:bg-white/5 transition-colors">
                        <td class="px-3 py-3 text-center text-[var(--text-secondary)] font-mono">{{ loop.index }}</td>
                        <td class="px-4 py-3 font-semibold">{{ item.teamname }}</td>
                        {% for problem in problems %}
                        {% set cache = item.problems.get(problem.id) %}
                        <td class="px-2 py-3 text-center font-mono text-xs">
                            {% if cache and cache.is_correct %}
                            <span class="ac-cell inline-flex items-center justify-center w-9 h-7 rounded font-bold text-[var(--success)]">
                                +{% if cache.submissions > 1 %}{{ cache.submissions - 1 }}{% endif %}
                            </span>
                            {% elif cache and not cache.is_correct %}
                            <span class="text-[var(--danger)]">-{{ cache.submissions }}</span>
                            {% else %}
                            <span class="text-gray-600">.</span>
                            {% endif %}
                        </td>
                        {% endfor %}
                        <td class="px-3 py-3 text-center font-bold text-[var(--accent)] font-mono">{{ item.solved }}</td>
                        <td class="px-4 py-3 text-center font-mono text-sm">{{ item.total_time if contest.score_mode != 'ioi' else item.total_score }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="text-center mt-4 text-xs text-[var(--text-secondary)]">
            <span id="ws-status">实时更新中</span>
        </div>
    </div>
    <script>
    // Real-time clock
    function updateClock() {
        document.getElementById('clock').textContent = new Date().toLocaleTimeString('zh-CN', {hour12: false});
    }
    updateClock();
    setInterval(updateClock, 1000);
    // WebSocket auto-refresh (same as before)
    (function() {
        var statusEl = document.getElementById('ws-status');
        var reloadTimer = null;
        function refresh() { location.reload(); }
        setInterval(refresh, 60000);
        try {
            var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            var ws = new WebSocket(proto + '//' + location.host + '/ws/judge-updates');
            ws.onopen = function() { statusEl.textContent = '实时更新中'; };
            ws.onmessage = function(event) {
                var data = JSON.parse(event.data);
                if (data.type === 'judging_done') {
                    if (reloadTimer) clearTimeout(reloadTimer);
                    reloadTimer = setTimeout(refresh, 1500);
                }
            };
            ws.onclose = function() { statusEl.textContent = '连接断开'; };
        } catch(e) { statusEl.textContent = '轮询模式'; }
    })();
    </script>
    {% else %}
    <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
            <div class="text-6xl mb-4 text-gray-700">/</div>
            <h1 class="text-2xl font-bold text-gray-500 mb-2">暂无进行中的比赛</h1>
            <p class="text-gray-600">请等待比赛开始</p>
        </div>
    </div>
    {% endif %}
</body>
</html>
```

- [ ] **Step 2: Verify public scoreboard**

Open http://localhost:8000/public/scoreboard — verify layout, clock, AC animation, WebSocket.

---

### Task 5: Final Polish

**Files:**
- All modified templates (add `transition-colors duration-200` to body)
- `app/templates/base.html` (fix any remaining hardcoded colors)

- [ ] **Step 1: Add transition to theme change**

Add `transition-colors duration-300` to `<body>` and all major containers in base.html.

- [ ] **Step 2: Consistent component audit**

Check all 26 pages for:
- Consistent card border radius (rounded-xl)
- Consistent button styles
- Consistent form input styles
- Proper verdict/difficulty badge colors
- Proper font-mono usage for data columns

- [ ] **Step 3: Full verification**

Run full test suite and check the app:
```bash
python -m pytest tests/ -v
python -c "from app.main import app; print('OK')"
python run.py
```

Then manually test:
- Login with random background
- Theme toggle (persists across refresh)
- Sidebar collapse/expand
- Mobile responsive (<768px hamburger menu)
- All team pages (7)
- All jury pages (12)
- Public scoreboard
- Submit code and verify WebSocket refresh
- Scoreboard real-time update

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: complete website redesign with sidebar layout, dark/light theme, and login backgrounds

- New base.html with sidebar layout, CSS variable theming, collapsible sidebar
- Dark/light theme toggle with localStorage persistence
- Random photo backgrounds on login page from /static/photos/
- All 26 templates redesigned with consistent card/table/form components
- Heroicons SVG inline icons throughout
- Public scoreboard with real-time clock and AC animation
- Mobile responsive with hamburger menu
- All existing functionality preserved (submit, judge, scoreboard, WebSocket, export)

Co-Authored-By: Claude <noreply@anthropic.com>"
```
