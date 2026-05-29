# `src/components/DefaultPanel.jsx` 与 `DefaultPanel.css` — 模块说明（含用户白名单）

## 1. 组件职责总览

`DefaultPanel` 在 **`contentType === 'default'`** 时由 `App.jsx` 渲染，位于左栏「智慧助手空间」内、示例图表与摄像头入口之下。承担：

1. **语音状态指示**：识别中 / 唤醒待机 / 监听关闭。
2. **用户应用白名单（Windows）**：浏览本机 `.exe`、起名、确认写入后端；展示已添加列表与移除。
3. **示例指令卡片**：点击后由 `onExampleClick` 交给 `App`（多数走 `autoSendTask`，摄像头示例仅滚动定位）。

样式由 **`DefaultPanel.css`** 中 `dp-*` 与 **`dp-add-app*`**、**`dp-modal-*`**、**`dp-user-apps*`** 等类名承担。

---

## 2. `DefaultPanel.jsx` — 文件头与导入（约 1–19 行）

| 行号 | 说明 |
|------|------|
| 1–18 | 块注释：功能列表与 **全部 Props** 说明（含白名单相关）。 |
| 19 | `import './DefaultPanel.css'`：挂载组件样式。 |

---

## 3. 函数参数解构（约 21–35 行）

| Prop | 类型/默认 | 含义 |
|------|-----------|------|
| `isCmdActive` | boolean | 指令识别进行中 → 红点「识别指令中」。 |
| `isWakeActive` | boolean | 唤醒监听开 → 绿点「待机中…」。 |
| `onExampleClick` | function | `(example) => void`，`example` 含 `text`、`type`。 |
| `userExePickSupported` | boolean，默认 `true` | **`false`** 时整块「浏览添加」不渲染（后端非 Windows 时 `capabilities.userExePick` 为 false）。 |
| `pickBrowseBusy` | boolean | 为 `true` 时按钮禁用且文案变为「正在等待你选择程序…」。 |
| `userAppList` | 数组，默认 `[]` | 元素 `{ name, path }`，来自 `GET /api/user-apps`。 |
| `addAppDraft` | object 或 `null` | 非空时显示确认弹层；含 `path`、`suggestedName`（选文件后由 App 写入）。 |
| `addAppNameInput` | string | 弹层内受控输入，最大 24 字符与后端校验一致。 |
| `onAddAppNameChange` | function | `(value: string) => void`，一般为 `setAddAppNameInput`。 |
| `onBrowsePickExe` | function | 触发 `POST /api/user-apps/pick`。 |
| `onCancelAddApp` | function | 关闭弹层并清空草稿。 |
| `onConfirmAddApp` | function | `POST /api/user-apps` 提交 `{ name, path }`。 |
| `onRemoveUserApp` | function | `(name) => void`，`DELETE /api/user-apps?name=`。 |

---

## 4. 示例数据 `examples`（约 36–43 行）

静态数组，每项 `icon`、`text`、`type`。与原先一致；`face_camera` 类型在 `App.handleDefaultExample` 中特殊处理为滚动到锚点而非发后端。

---

## 5. JSX 结构（约 45–138 行）

### 5.1 根与状态行（约 46–55 行）

- 根容器 `className="dp"`。
- `dp-status`：三元嵌套渲染三种 `dp-dot` 变体。

### 5.2 白名单区域（约 57–88 行）

- **条件**：`userExePickSupported && (...)`。
- **`dp-add-app`** 容器：
  - 按钮 **`dp-add-app-btn`**：`disabled={pickBrowseBusy}`，`onClick` 调 `onBrowsePickExe?.()`（可选链避免未传 props 报错）。
  - 文案根据 `pickBrowseBusy` 切换。
  - **`dp-add-app-hint`**：说明系统弹框与语音用法。
- **列表**：`userAppList.length > 0` 时渲染 **`ul.dp-user-apps`**：
  - 每项 **`li.dp-user-apps-item`**：`key={row.name}`。
  - **`span.dp-user-apps-name`**：`title={row.path}` 悬停可看完整路径。
  - **`button.dp-user-apps-remove`**：`onClick` 调 `onRemoveUserApp?.(row.name)`，`aria-label` 无障碍。

### 5.3 确认弹层（约 90–120 行）

- **条件**：`addAppDraft && (...)`。
- **遮罩 `dp-modal-overlay`**：
  - `role="presentation"`。
  - **`onClick`**：若 `e.target === e.currentTarget`（点到遮罩未点到对话框）则 `onCancelAddApp?.()`，实现点击外部关闭。
- **对话框 `dp-modal`**：
  - `role="dialog"`、`aria-modal="true"`、`aria-labelledby="dp-modal-title"`。
  - **`onClick={(e) => e.stopPropagation()`**：防止点击对话框内部冒泡到遮罩被误判为「点外部」。
  - 标题、完整路径 `dp-modal-path`（`title` 同路径）、标签、`input#dp-add-app-name`（`maxLength={24}`、`autoComplete="off"`）。
  - **`dp-modal-actions`**：取消（ghost）、确认添加（primary）。

### 5.4 原有示例区（约 122–137 行）

- `dp-heading`、`dp-grid`、`dp-card` 映射 `examples` 不变。
- `dp-hint` 底部提示。

---

## 6. `DefaultPanel.css` — 类名与职责

### 6.1 原有（空状态 / 卡片）

| 选择器 | 作用 |
|--------|------|
| `.dp` | 纵向 flex、居中、间距。 |
| `.dp-status` / `.dp-status-label` / `.dp-dot*` | 状态行与三色圆点动画 `blink`。 |
| `.dp-heading` / `.dp-grid` / `.dp-card*` | 示例网格与卡片悬停。 |
| `.dp-hint` | 底部灰色提示。 |

### 6.2 白名单与弹层（新增）

| 选择器 | 作用 |
|--------|------|
| `.dp-add-app` | 白名单整块卡片容器，边框与 `var(--card-bg)`。 |
| `.dp-add-app-btn` | 主按钮：字重、圆角、描边、渐变背景；`:disabled` 降低透明度、`cursor: wait`。 |
| `.dp-add-app-hint` | 说明文字小号、次要色、居中。 |
| `.dp-user-apps` | 无列表符号、纵向列表间距。 |
| `.dp-user-apps-item` | 每行 flex 两端对齐、浅底圆角。 |
| `.dp-user-apps-name` | 单行省略号，`flex:1`。 |
| `.dp-user-apps-remove` | 小按钮，悬停变红提示删除。 |
| `.dp-modal-overlay` | `position: fixed; inset: 0` 全屏遮罩，`z-index: 1200`，半透明 + `backdrop-filter`。 |
| `.dp-modal` | 居中卡片最大宽度 420px、圆角、阴影。 |
| `.dp-modal-title` / `.dp-modal-path` / `.dp-modal-label` / `.dp-modal-input` | 标题、等宽路径预览、表单标签与输入框。 |
| `.dp-modal-actions` | 右对齐按钮组。 |
| `.dp-modal-btn--ghost` / `--primary` | 取消与确认样式。 |

---

## 7. 与 `App.jsx` 的数据流

1. 挂载时 `App` 的 `useEffect` 调用 **`refreshUserApps`**（`GET /api/user-apps`）与 **`GET /api/capabilities`**，设置 `userAppList` 与 `userExePickSupported`。
2. 用户点「浏览电脑…」→ **`handleBrowsePickExe`** → `POST /api/user-apps/pick` → 成功则 **`setAddAppDraft`** + **`setAddAppNameInput`**。
3. 用户确认 → **`handleConfirmAddApp`** → `POST /api/user-apps` → 成功清空 draft 并 **`refreshUserApps`**。
4. 移除 → **`handleRemoveUserApp`** → `DELETE` → **`refreshUserApps`**。

详见 [App.jsx-模块说明.md](./App.jsx-模块说明.md) 中的「用户应用白名单状态与回调」一节。

---

## 8. 无障碍与交互细节

- 弹层使用 `role="dialog"` 与 `aria-labelledby` 关联标题。
- 移除按钮提供 `aria-label`。
- 遮罩点击关闭依赖事件目标比较，避免误关。
