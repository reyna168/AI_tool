## 技术栈
- 框架：Next.js 14 App Router
- 语言：TypeScript 严格模式
- 样式：Tailwind CSS v3+
- 包管理：npm
- 运行环境：Node.js 18+

## 项目架构
- `/app` - Next.js App Router 页面和布局
- `/components` - 可复用 UI 组件
- `/lib` - 工具函数和配置
- `/types` - TypeScript 类型定义
- `/public` - 静态资源

## 开发命令
- 启动开发服务器：`npm run dev`
- 构建生产版本：`npm run build`
- 运行类型检查：`npm run type-check`
- 运行测试：`npm test`
- 代码格式化：`npm run format`

## 代码风格规范

### React 组件
- 使用函数组件配合 TypeScript
- 组件名使用 PascalCase
- 文件名使用 PascalCase：`UserCard.tsx`
- 使用命名导出，避免默认导出
- Props 接口名称：组件名 + Props（如 `ButtonProps`）

### Tailwind CSS 使用
- 只使用 Tailwind 工具类，不写自定义 CSS
- 类名顺序：布局 → 间距 → 颜色 → 状态
- 响应式前缀使用：`sm:` `md:` `lg:` `xl:`
- 示例格式：`flex items-center justify-between p-4 bg-white rounded-lg hover:shadow-md`

### TypeScript 规范
- 所有函数参数和返回值必须有类型注解
- 接口定义优先使用 `interface` 而非 `type`
- 严格模式下不允许 `any` 类型
- 组件 Props 必须定义接口

### Next.js App Router 规范
- 页面文件：`page.tsx`
- 布局文件：`layout.tsx`
- 加载状态：`loading.tsx`
- 错误处理：`error.tsx`
- 默认使用 Server Components
- 需要客户端交互时添加 `'use client'`

### 文件命名约定
- 组件文件：`UserProfile.tsx`
- 页面路由：`user-profile/page.tsx`
- 工具函数：`formatDate.ts`
- 类型定义：`UserTypes.ts`

## 测试规范
- 测试文件命名：`ComponentName.test.tsx`
- 测试位置：与组件文件同目录或 `__tests__` 文件夹
- 运行单个测试：`npm test -- ComponentName`
- 测试覆盖率：`npm run test:coverage`

## Git 工作流
- 分支命名：`feature/功能描述` 或 `fix/修复描述`
- 提交信息：使用 conventional commits 格式
- 提交前必须通过类型检查和测试
- 每个 PR 需要通过所有检查

## 重要提醒
- 优先使用 Server Components 提升性能
- 组件保持单一职责，避免过于复杂
- 遵循 Tailwind 设计系统的一致性
- 始终处理加载和错误状态
- 代码提交前运行 `npm run type-check`