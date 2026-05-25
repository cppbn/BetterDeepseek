# Frontend

Vue 3 + TypeScript + Vite 前端 SPA。开发时独立启动，生产构建后由后端托管。

## 命令

```bash
npm run dev          # Vite 开发服务器
npm run build        # 生产构建（vue-tsc + vite build）
npm run type-check   # TypeScript 类型检查
npm run lint         # oxlint + eslint
npm run format       # prettier
```

## 环境变量

| 变量 | 开发 | 生产 |
|------|------|------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8010/api` | `/api` |

## 目录结构

```
Frontend/src/
├── main.ts               # Vue 应用入口（Pinia + Router）
├── App.vue               # 根组件（<router-view />）
├── style.css             # Tailwind 指令 + 自定义样式
├── types/index.ts        # TypeScript 类型定义（Message, StreamEvent, ModelInfo 等）
├── router/index.ts       # 路由配置（/chat, /login, /register, /admin）
├── api/                  # API 层
│   ├── client.ts         # Axios 实例（baseURL, auth 拦截器, 401 跳转）
│   ├── auth.ts           # 登录/注册
│   ├── sessions.ts       # 会话 CRUD
│   ├── messages.ts       # 消息历史
│   ├── stream.ts         # SSE 流式对话（fetch ReadableStream）
│   ├── files.ts          # 文件上传/下载/预览
│   ├── models.ts         # 获取可用模型列表
│   └── admin.ts          # 管理面板 API
├── stores/               # Pinia 状态管理
│   ├── auth.ts           # 用户认证状态（token, login, logout）
│   └── session.ts        # 会话/消息状态（sessions, messagesMap, reasoning合并）
├── composables/          # Vue 组合式函数
│   └── useChatStream.ts  # 流式对话逻辑（发送/停止/重新生成、SSE 事件处理）
├── views/                # 页面组件
│   ├── LoginView.vue     # 登录页
│   ├── RegisterView.vue  # 注册页
│   ├── ChatView.vue      # 主对话页面
│   └── AdminView.vue     # 管理员面板
└── components/           # 子组件
    ├── layout/
    │   └── AppLayout.vue # 应用布局（侧边栏 + 顶部栏）
    ├── chat/
    │   ├── SessionSidebar.vue   # 会话列表侧边栏
    │   ├── MessageList.vue      # 消息滚动列表
    │   ├── MessageItem.vue      # 单条消息（推理步骤/工具调用/附件）
    │   ├── MarkdownRenderer.vue # Markdown 渲染（KaTeX 数学公式、代码高亮）
    │   ├── ChatInput.vue        # 输入区（文本、文件拖拽、搜索/代码开关）
    │   ├── ModelSelector.vue    # 模型选择下拉框
    │   └── FileUploadButton.vue # 文件上传按钮
    └── common/
        └── LoadingSpinner.vue   # 加载动画
```

## 路由

| 路径 | 页面 | 鉴权 |
|------|------|------|
| `/` | 重定向到 `/chat` | - |
| `/chat/:sessionId?` | ChatView（对话主页） | 需登录 |
| `/login` | LoginView | 仅未登录 |
| `/register` | RegisterView | 仅未登录 |
| `/admin` | AdminView | Admin-Key 验证 |

## 状态流

```
auth store
  ├─> token (localStorage)
  ├─> login() / register() → 保存 token
  ├─> logout() → 清除 token，跳转 /login
  └─> axios 拦截器自动附加 Authorization header

session store
  ├─> sessions[]            # 所有会话
  ├─> currentSessionId      # 当前会话
  ├─> messagesMap           # sessionId → Message[]
  └─> mergeReasoningMessages()  # 合并推理步骤

useChatStream (composable)
  ├─> sendMessage()         # 发送消息 → SSE 流 → 更新 messagesMap
  ├─> stop()               # 中止流
  └─> regenerate()          # 重新生成（删除最后一条，重发）
```

## 对话数据流

```
ChatInput.vue
  └─> useChatStream.sendMessage()
       ├─> 创建虚拟用户消息 + 助手消息（负 ID）
       ├─> stream.ts POST /chat/stream (SSE fetch)
       ├─> 处理 SSE 事件:
       │    ├─ content           → 追加到助手消息
       │    ├─ reasoning_content → 追加推理内容
       │    ├─ tool_call         → 追加工具调用状态
       │    ├─ tool_result       → 追加工具结果
       │    ├─ file              → 追加导出文件
       │    ├─ error             → 显示错误
       │    └─ title             → 更新会话标题
       └─> syncAfterStream() → 从 DB 同步最终消息列表
```

## 技术栈

| 类别 | 库 |
|------|-----|
| 框架 | Vue 3 (Composition API) |
| 语言 | TypeScript |
| 构建 | Vite |
| 状态 | Pinia |
| 路由 | Vue Router |
| HTTP | Axios |
| 样式 | Tailwind CSS |
| 渲染 | markdown-it + highlight.js + KaTeX |
