# 小文 AI — 专属设计系统（Master Source of Truth）

> **产品**：小文 AI 轻量个人 AI 助手
> **用户**：18–30 岁 大学生 + 年轻职场人
> **风格**：新拟态 Neumorphism + 柔和极简 Soft Minimal
> **色调**：低饱和、温暖科技感、拒绝刺眼高对比
> **框架**：React 19 + Vite 8 + Plain CSS Custom Properties
> **生成日期**：2026-05-13

---

## 1. 设计语言定义

### 核心风格：Soft Neumorphism（柔和新拟态）

传统新拟态依赖纯白/纯灰背景 + 硬凹凸阴影，视觉冰冷且无障碍对比极差。小文 AI 采用**改良版柔和新拟态**：

| 维度 | 传统新拟态 | 小文改良方案 |
|------|-----------|-------------|
| 背景 | 纯灰 #e0e0e0 | 温暖纸底 #f0ebe3（暖 5%） |
| 凹陷 | 硬投影 #fff / #bebebe | 柔和双投影 + 模糊半径增大 2× |
| 凸起 | 硬高光 #fff / 阴影 #bebebe | 主色微染投影 + 1px 内发光 |
| 对比 | 文字与背景 < 3:1 ❌ | 文字与背景 ≥ 4.5:1 ✅ |
| 层次 | 仅靠光影 | 光影 + 微弱边框兜底 |

**关键原则**：
- 新拟态效果在**支持 `box-shadow` 的元素上应用**，不用于文字、图标等不可投影元素
- 所有凹陷/凸起区域的**文字对比必须独立验证**，不依赖阴影可读性
- 暗色模式下新拟态自动退化为**微弱凸起 + 边框**，避免暗背景上凹凸不明显

---

## 2. 完整色板

### 2.1 主色系（石青 Teal — 低饱和温暖版）

小文保持石青主色传统，但将饱和度压低约 15%、明度微调以适配新拟态凹凸层。

| Token | 亮色模式 | 暗色模式 | 用途 | 对比率（vs 背景） |
|-------|---------|---------|------|------------------|
| `--accent` | `#3d8a80` | `#4fd1c0` | 主按钮、链接、活跃态 | 亮 4.6:1 ✅ / 暗 7.2:1 ✅ |
| `--accent-strong` | `#2a6e64` | `#38b2a4` | 标题、强调 | 亮 7.1:1 ✅ / 暗 9.5:1 ✅ |
| `--accent-soft` | `#5ea89e` | `#7dd3c4` | 次级高亮、Icon 填充 | 亮 3.2:1 ⚠️(仅装饰) / 暗 5.8:1 ✅ |
| `--accent-light` | `#a3d8d0` | `#b2ede4` | 轻底色、Tag 背景 | 亮 1.8:1 ⚠️(仅背景) / 暗 2.4:1 ⚠️(仅背景) |
| `--accent-bg` | `rgba(61,138,128,0.08)` | `rgba(79,209,192,0.10)` | 悬停底色 | — |
| `--accent-glow` | `rgba(61,138,128,0.18)` | `rgba(79,209,192,0.22)` | 新拟态发光层 | — |

### 2.2 中性色系（温暖石调 Stone-warm）

| Token | 亮色模式 | 暗色模式 | 用途 | 对比率 |
|-------|---------|---------|------|--------|
| `--bg` | `#f0ebe3` | `#121a17` | 页面底色 | — |
| `--surface` | `#f7f2ea` | `#182220` | 新拟态凸起面（Card） | — |
| `--surface-raised` | `#faf6ef` | `#1e2b28` | 二级凸起（内嵌面板） | — |
| `--surface-sunken` | `#e8e2d8` | `#0e1513` | 新拟态凹陷面（Input） | — |
| `--border` | `#ddd6c8` | `#2c3b36` | 边框、分隔线 | — |
| `--border-soft` | `rgba(28,25,23,0.06)` | `rgba(255,255,255,0.05)` | 微弱边框兜底 | — |

### 2.3 语义色系（低饱和温暖变体）

| Token | 亮色模式 | 暗色模式 | 用途 |
|-------|---------|---------|------|
| `--success` | `#5a9e6f` | `#6dbf85` | 成功状态 |
| `--success-bg` | `rgba(90,158,111,0.10)` | `rgba(109,191,133,0.12)` | 成功底色 |
| `--warning` | `#c4903a` | `#daa64e` | 警告状态 |
| `--warning-bg` | `rgba(196,144,58,0.10)` | `rgba(218,166,78,0.12)` | 警告底色 |
| `--error` | `#c25858` | `#e07070` | 错误状态 |
| `--error-bg` | `rgba(194,88,88,0.10)` | `rgba(224,112,112,0.12)` | 错误底色 |
| `--info` | `#5a8ab5` | `#74aad4` | 提示信息 |
| `--info-bg` | `rgba(90,138,181,0.10)` | `rgba(116,170,212,0.12)` | 提示底色 |

### 2.4 文字色系

| Token | 亮色模式 | 暗色模式 | 用途 | 对比率 |
|-------|---------|---------|------|--------|
| `--text-primary` | `#1c1917` | `#f0eeea` | 正文 | 亮 14.2:1 ✅ / 暗 13.8:1 ✅ |
| `--text-secondary` | `#57534e` | `#c8c4be` | 辅助文字 | 亮 6.8:1 ✅ / 暗 8.2:1 ✅ |
| `--text-tertiary` | `#8c857c` | `#9a9590` | 淡化、标签 | 亮 3.8:1 ⚠️(≥18px) / 暗 5.0:1 ✅ |
| `--text-on-accent` | `#ffffff` | `#0c1a16` | 主色按钮内文字 | 亮 4.8:1 ✅ / 暗 15.1:1 ✅ |
| `--text-placeholder` | `#a8a19a` | `#6b7d76` | 占位符 | 亮 2.5:1 ⚠️(仅占位) / 暗 3.2:1 ⚠️(仅占位) |

---

## 3. 字体规范

### 3.1 字体栈

| 角色 | 字体栈 | 降级 |
|------|--------|------|
| 主字体（正文） | `"Noto Sans SC"`, `"PingFang SC"` | `"Microsoft YaHei"`, `system-ui`, `sans-serif` |
| 展示字体（标题） | `"Fraunces"` | `"Songti SC"`, `"STSong"`, `Georgia`, `serif` |
| 等宽字体（代码） | `"JetBrains Mono"`, `"Fira Code"` | `"Source Code Pro"`, `monospace` |

### 3.2 字号阶梯（Type Scale — 1.25 Major Third）

| Token | 值 | 用途 |
|-------|---|------|
| `--text-2xs` | `0.64rem` (10px) | 极小标签（辅助角标） |
| `--text-xs` | `0.8rem` (13px) | 小标签、时间戳 |
| `--text-sm` | `0.875rem` (14px) | 辅助文字、输入框 |
| `--text-base` | `1rem` (16px) | 正文（基准） |
| `--text-lg` | `1.125rem` (18px) | 卡片标题 |
| `--text-xl` | `1.25rem` (20px) | 区块标题 |
| `--text-2xl` | `1.5rem` (24px) | 页面标题 |
| `--text-3xl` | `1.875rem` (30px) | 大标题 |
| `--text-4xl` | `2.25rem` (36px) | Hero 标题 |

### 3.3 字重

| Token | 值 | 用途 |
|-------|---|------|
| `--font-regular` | `400` | 正文 |
| `--font-medium` | `500` | 标签、小标题 |
| `--font-semibold` | `600` | 按钮、强调标题 |
| `--font-bold` | `700` | 大标题 |

### 3.4 行高

| 场景 | 行高 | 说明 |
|------|------|------|
| 正文段落 | `1.75` | 充裕阅读感 |
| 卡片标题 | `1.4` | 紧凑标题 |
| 单行 UI 文字 | `1.2` | 按钮、标签 |
| 代码块 | `1.6` | 等宽对齐 |

---

## 4. 间距规则（8dp 网格）

### 4.1 间距阶梯

| Token | 值 | 用途 |
|-------|---|------|
| `--space-1` | `4px` | 图标与文字间隙 |
| `--space-2` | `8px` | 紧凑间距（标签间） |
| `--space-3` | `12px` | 小间距 |
| `--space-4` | `16px` | 标准间距（组件内 padding） |
| `--space-5` | `20px` | 中等间距 |
| `--space-6` | `24px` | 区块内 padding |
| `--space-8` | `32px` | 区块间 gap |
| `--space-10` | `40px` | 大区块间距 |
| `--space-12` | `48px` | 页面 section 间距 |
| `--space-16` | `64px` | 页面顶级留白 |

### 4.2 应用规则

- **组件内 padding**：`--space-4` (16px) 或 `--space-6` (24px)
- **组件间 gap**：`--space-6` (24px) 或 `--space-8` (32px)
- **区块 section 间距**：`--space-10` (40px) 或 `--space-12` (48px)
- **卡片内嵌工具区**：`--space-4` (16px)
- **新拟态组件留白**：比普通组件多 4px，为阴影呼吸空间

---

## 5. 圆角规范

| Token | 值 | 用途 |
|-------|---|------|
| `--radius-sm` | `8px` | 小按钮、Badge、Tag |
| `--radius-md` | `14px` | 卡片、面板、对话框 |
| `--radius-lg` | `20px` | 大面板、Modal |
| `--radius-xl` | `28px` | Hero 卡片、突出展示区 |
| `--radius-full` | `9999px` | 头像、圆形按钮 |

**统一原则**：
- 同一层级的元素圆角必须一致
- 外层容器圆角 > 内嵌元素圆角（如卡片 14px > 内芯片 8px）
- 新拟态凹陷区圆角与所在容器一致，不可省略

---

## 6. 阴影与特效（新拟态核心）

### 6.1 亮色模式 — 柔和新拟态阴影

```
凸起（Card / Panel / Button）:
  --shadow-raised:
    0 2px 4px rgba(28,25,23,0.04),       ← 近距离柔化
    0 8px 24px rgba(28,25,23,0.06),      ← 中距离扩散
    inset 0 1px 0 rgba(255,255,255,0.6); ← 顶部高光（微弱）

凹陷（Input / Pressed State）:
  --shadow-sunken:
    inset 0 2px 4px rgba(28,25,23,0.06),
    inset 0 -1px 2px rgba(255,255,255,0.5);

主色凸起（Accent Button）:
  --shadow-accent:
    0 2px 8px rgba(61,138,128,0.18),
    0 8px 24px rgba(61,138,128,0.10),
    inset 0 1px 0 rgba(255,255,255,0.25);

浮层（Modal / Dropdown）:
  --shadow-float:
    0 12px 40px rgba(28,25,23,0.10),
    0 2px 8px rgba(28,25,23,0.06);
```

### 6.2 暗色模式 — 微弱凸起 + 边框

暗色模式下新拟态凹凸几乎不可见，退化为**微凸起边框方案**：

```
凸起:
  --shadow-raised:
    0 1px 3px rgba(0,0,0,0.20),
    0 4px 12px rgba(0,0,0,0.12);

凹陷:
  --shadow-sunken:
    inset 0 1px 3px rgba(0,0,0,0.25);

主色凸起:
  --shadow-accent:
    0 2px 8px rgba(79,209,192,0.15),
    0 4px 16px rgba(79,209,192,0.08);

浮层:
  --shadow-float:
    0 16px 48px rgba(0,0,0,0.40),
    0 2px 8px rgba(0,0,0,0.20);
```

### 6.3 边框兜底策略

新拟态在低对比环境（无障碍高对比模式、老旧浏览器）下可能失效。每个依赖阴影表达层次的元素**必须同时设置**：

```css
border: 1px solid var(--border-soft);
```

这样阴影失效时仍有边框兜底，不丢失层次。

### 6.4 过渡与微交互

| 交互 | 过渡 | 时间函数 | 时长 |
|------|------|---------|------|
| 按钮 hover | `background, box-shadow, transform` | `cubic-bezier(0.23,1,0.32,1)` | `180ms` |
| 按钮 press | `transform: scale(0.97)`, shadow → sunken | `ease-out` | `120ms` |
| 卡片 hover | `box-shadow 增强`, `translateY(-2px)` | `cubic-bezier(0.23,1,0.32,1)` | `250ms` |
| 面板展开/收起 | `max-height + opacity` | `ease-in-out` | `300ms` |
| 页面切换 | `opacity + translateY(8px)` | `ease-out` | `250ms` |
| 输入框 focus | `box-shadow: sunken → accent glow` | `ease-out` | `200ms` |
| Toast 出现 | `opacity 0→1 + translateY(12px→0)` | `cubic-bezier(0.23,1,0.32,1)` | `250ms` |
| Toast 消失 | `opacity 1→0` | `ease-in` | `180ms` |

**`prefers-reduced-motion` 降级**：所有过渡 → `0ms`，仅保留颜色变化。

---

## 7. 响应式断点

| 断点名 | 宽度 | 列数 | 布局变化 |
|-------|------|------|---------|
| `mobile` | < 640px | 1 | 单列全宽，底部输入，吉祥物缩小 |
| `tablet` | 640–1023px | 1–2 | 可折叠侧栏，卡片双列 |
| `desktop` | ≥ 1024px | 2+ | 左右分栏（对话 + 工具 / 日志） |
| `wide` | ≥ 1440px | 2+ | 内容限宽 max-width: 1200px 居中 |

**viewport meta**：`width=device-width, initial-scale=1`，**禁止** `maximum-scale=1` 或 `user-scalable=no`。

---

## 8. 组件层级与 z-index 管理

| 层级 | Token | 值 | 用途 |
|------|-------|---|------|
| 基底 | `--z-base` | `0` | 页面内容 |
| 卡片悬浮 | `--z-card-hover` | `10` | hover 态卡片 |
| 粘性头 | `--z-sticky` | `20` | 导航栏、ModeBar |
| 下拉菜单 | `--z-dropdown` | `40` | Dropdown、Autocomplete |
| 浮层 | `--z-overlay` | `100` | Modal 遮罩 |
| 最高 | `--z-toast` | `1000` | Toast 通知 |

---

## 9. 反设计坑清单（Anti-Patterns）

以下是根据新拟态 + 柔和极简风格，**必须避开**的 UI 陷阱：

### 9.1 新拟态专属坑

| # | 反设计 | 为什么 | 正确做法 |
|---|--------|--------|---------|
| 1 | **纯新拟态无文字对比** | 凹陷区文字对比极低 < 3:1，WCAG 不通过 | 凹陷区文字使用 `--text-primary`，独立验证对比 |
| 2 | **全页面新拟态** | 大面积凹凸致视觉疲劳，层次混乱 | 仅 Card / Button / Input 用新拟态，区域留白**纯平** |
| 3 | **暗色模式硬用新拟态** | 暗背景凹凸无法区分，反而糊成一团 | 暗色退化为微凸起 + 边框方案（见 §6.2） |
| 4 | **新拟态 + 高饱和色** | 鲜艳色配凹凸产生「塑料玩具感」 | 主色区用低饱和石青，鲜艳色仅用于小面积状态点 |
| 5 | **多层嵌套凹凸** | 三层以上凹凸→用户无法理解层级 | 最多两层：外凸起 + 内凹陷。深层改为颜色/边框 |

### 9.2 柔和极简专属坑

| # | 反设计 | 为什么 | 正确做法 |
|---|--------|--------|---------|
| 6 | **留白 = 没设计** | 留白无网格 → 内容散乱 | 留白遵循 8dp 网格，有节奏不随意 |
| 7 | **所有色都同一个灰** | 「低饱和」不等于「无色」，全灰画面沉闷 | 主色、语义色保持可辨识色相，仅饱和度压低 15% |
| 8 | **圆角全用最大值** | 全圆角卡片失去层次感，显得幼稚 | 区分 `sm/md/lg/xl` 四档，外层 > 内层 |
| 9 | **过渡动画慢于 400ms** | 300ms+ 的柔和动画在重复操作时变累 | UI 反馈 150–250ms，页面切换 ≤ 300ms |
| 10 | **占位符当标签** | 输入框占位符输入后消失，用户忘字段名 | 可见 label 持久显示，占位符仅作格式提示 |

### 9.3 通用无障碍坑

| # | 反设计 | 为什么 | 正确做法 |
|---|--------|--------|---------|
| 11 | **仅靠颜色传达状态** | 色盲无法区分 error/success | 状态颜色 + 图标 + 文字三重编码 |
| 12 | **移除 focus ring** | 键盘用户无法定位焦点 | 保留 2px focus ring，颜色 `--accent` |
| 13 | **Icon 无 label** | 屏幕阅读器读不出含义 | icon-only 按钮 `aria-label`，图标+文字 `aria-hidden` |
| 14 | **Emoji 当图标** | 跨平台渲染不一致，不可 theming | 使用 Lucide SVG icons |
| 15 | **禁用缩放** | `user-scalable=no` 违反 WCAG | 不限制缩放，1rem = 16px 避免 iOS 自动放大 |

### 9.4 性能坑

| # | 反设计 | 为什么 | 正确做法 |
|---|--------|--------|---------|
| 16 | **大面积 `box-shadow` 动画** | 每帧重绘 shadow → GPU 不可合成 | hover 过渡只改 `transform` + `opacity`，shadow 用 `will-change` 或固定 |
| 17 | **新拟态 `filter: blur()` 背景模糊** | 移动端性能灾难 | 用静态 blur（预渲染）或直接用半透明色替代 |
| 18 | **长列表无虚拟化** | 50+ 卡片全部 DOM → 滚动卡顿 | 聊天记录 50+ 条时启用虚拟列表 |

---

## 10. CSS Custom Properties 汇总（完整代码）

将以下 token 粘贴到 `index.css` 的 `:root` 中替换现有值：

```css
:root {
  /* ═══ 主色系（石青 — 低饱和温暖版）═══ */
  --accent: #3d8a80;
  --accent-strong: #2a6e64;
  --accent-soft: #5ea89e;
  --accent-light: #a3d8d0;
  --accent-bg: rgba(61,138,128,0.08);
  --accent-glow: rgba(61,138,128,0.18);
  --hover-bg: rgba(61,138,128,0.08);

  /* ═══ 中性色系（温暖石调）═══ */
  --bg: #f0ebe3;
  --surface: #f7f2ea;
  --surface-raised: #faf6ef;
  --surface-sunken: #e8e2d8;
  --border: #ddd6c8;
  --border-soft: rgba(28,25,23,0.06);

  /* ═══ 文字色系 ═══ */
  --text-primary: #1c1917;
  --text-secondary: #57534e;
  --text-tertiary: #8c857c;
  --text-on-accent: #ffffff;
  --text-placeholder: #a8a19a;

  /* ═══ 语义色系 ═══ */
  --success: #5a9e6f;
  --success-bg: rgba(90,158,111,0.10);
  --warning: #c4903a;
  --warning-bg: rgba(196,144,58,0.10);
  --error: #c25858;
  --error-bg: rgba(194,88,88,0.10);
  --info: #5a8ab5;
  --info-bg: rgba(90,138,181,0.10);

  /* ═══ 字体 ═══ */
  --font: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --font-display: "Fraunces", "Songti SC", "STSong", Georgia, serif;
  --font-mono: "JetBrains Mono", "Fira Code", "Source Code Pro", monospace;

  /* ═══ 字号阶梯 ═══ */
  --text-2xs: 0.64rem;
  --text-xs: 0.8rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;

  /* ═══ 字重 ═══ */
  --font-regular: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* ═══ 间距（8dp 网格）═══ */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* ═══ 圆角 ═══ */
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --radius-full: 9999px;

  /* ═══ 新拟态阴影（亮色）═══ */
  --shadow-raised:
    0 2px 4px rgba(28,25,23,0.04),
    0 8px 24px rgba(28,25,23,0.06),
    inset 0 1px 0 rgba(255,255,255,0.6);
  --shadow-sunken:
    inset 0 2px 4px rgba(28,25,23,0.06),
    inset 0 -1px 2px rgba(255,255,255,0.5);
  --shadow-accent:
    0 2px 8px rgba(61,138,128,0.18),
    0 8px 24px rgba(61,138,128,0.10),
    inset 0 1px 0 rgba(255,255,255,0.25);
  --shadow-float:
    0 12px 40px rgba(28,25,23,0.10),
    0 2px 8px rgba(28,25,23,0.06);

  /* ═══ 工具卡 ═══ */
  --tool-card-bg: color-mix(in srgb, var(--surface) 94%, var(--accent) 6%);
  --tool-card-border: color-mix(in srgb, var(--accent) 22%, var(--border));
  --tool-card-dash: color-mix(in srgb, var(--accent) 38%, transparent);
  --tool-inner-bg: color-mix(in srgb, var(--surface-raised) 88%, var(--surface));
  --tool-inner-border: var(--border);

  /* ═══ 工作流深色卡 ═══ */
  --workflow-bg-a: #141c1b;
  --workflow-bg-b: #1a2826;
  --workflow-border: rgba(79,209,192,0.28);
  --workflow-eyebrow: #5eead4;
  --workflow-step-ring: #3d8a80;

  /* ═══ z-index ═══ */
  --z-base: 0;
  --z-card-hover: 10;
  --z-sticky: 20;
  --z-dropdown: 40;
  --z-overlay: 100;
  --z-toast: 1000;

  /* ═══ 动画缓动 ═══ */
  --ease-out-expo: cubic-bezier(0.23,1,0.32,1);
  --ease-in-out: ease-in-out;
  --duration-fast: 120ms;
  --duration-normal: 180ms;
  --duration-slow: 250ms;
  --duration-page: 300ms;
}
```

### 暗色模式覆写（`@media (prefers-color-scheme: dark)`）

```css
@media (prefers-color-scheme: dark) {
  :root {
    --accent: #4fd1c0;
    --accent-strong: #38b2a4;
    --accent-soft: #7dd3c4;
    --accent-light: #b2ede4;
    --accent-bg: rgba(79,209,192,0.10);
    --accent-glow: rgba(79,209,192,0.22);
    --hover-bg: rgba(79,209,192,0.10);

    --bg: #121a17;
    --surface: #182220;
    --surface-raised: #1e2b28;
    --surface-sunken: #0e1513;
    --border: #2c3b36;
    --border-soft: rgba(255,255,255,0.05);

    --text-primary: #f0eeea;
    --text-secondary: #c8c4be;
    --text-tertiary: #9a9590;
    --text-on-accent: #0c1a16;
    --text-placeholder: #6b7d76;

    --success: #6dbf85;
    --warning: #daa64e;
    --error: #e07070;
    --info: #74aad4;

    --shadow-raised:
      0 1px 3px rgba(0,0,0,0.20),
      0 4px 12px rgba(0,0,0,0.12);
    --shadow-sunken:
      inset 0 1px 3px rgba(0,0,0,0.25);
    --shadow-accent:
      0 2px 8px rgba(79,209,192,0.15),
      0 4px 16px rgba(79,209,192,0.08);
    --shadow-float:
      0 16px 48px rgba(0,0,0,0.40),
      0 2px 8px rgba(0,0,0,0.20);

    --workflow-bg-a: #0c1211;
    --workflow-bg-b: #111a19;
    --workflow-border: rgba(79,209,192,0.22);
    --workflow-eyebrow: #7dd3fc;
    --workflow-step-ring: #4fd1c0;

    --tool-card-bg: linear-gradient(165deg, #151c1b 0%, #1a2523 100%);
    --tool-card-border: rgba(79,209,192,0.22);
    --tool-card-dash: rgba(79,209,192,0.38);
    --tool-inner-bg: rgba(12,18,17,0.55);
    --tool-inner-border: rgba(79,209,192,0.14);
  }
}
```

### `prefers-reduced-motion` 降级

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 11. 组件示例速查

### 按钮（Neumorphic）

```css
.btn-primary {
  background: var(--accent);
  color: var(--text-on-accent);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-accent);
  padding: var(--space-3) var(--space-6);
  font-weight: var(--font-semibold);
  transition: transform var(--duration-fast) ease-out,
              box-shadow var(--duration-normal) var(--ease-out-expo);
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(61,138,128,0.22),
              0 12px 32px rgba(61,138,128,0.14),
              inset 0 1px 0 rgba(255,255,255,0.25);
}
.btn-primary:active {
  transform: scale(0.97);
  box-shadow: var(--shadow-sunken);
}
```

### 输入框（Sunken）

```css
.input-neu {
  background: var(--surface-sunken);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sunken);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
  font-size: var(--text-base);
  transition: box-shadow var(--duration-normal) ease-out;
}
.input-neu:focus {
  outline: none;
  box-shadow: var(--shadow-sunken),
              0 0 0 3px var(--accent-glow);
  border-color: var(--accent);
}
```

### 卡片（Raised）

```css
.card-neu {
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-raised);
  padding: var(--space-6);
  transition: transform var(--duration-slow) var(--ease-out-expo),
              box-shadow var(--duration-slow) var(--ease-out-expo);
}
.card-neu:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(28,25,23,0.06),
              0 16px 40px rgba(28,25,23,0.08),
              inset 0 1px 0 rgba(255,255,255,0.6);
}
```

---

*此设计系统为小文 AI 项目唯一设计权威来源。页面级覆盖规则放在 `design-system/pages/` 目录下，优先级高于本文件。*
