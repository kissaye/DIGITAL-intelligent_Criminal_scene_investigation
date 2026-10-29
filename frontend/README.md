# 数智刑勘前端工程

M0 阶段仅提供认证、角色路由和三类空白首页；不包含点云、三维浏览、案例、脱敏或教学业务模块。

M1 已增加仅管理员可访问的案例导入与转换状态页面。创建流程为：创建案例、以 multipart 字段 `upload` 上传 LAS/LAZ 文件、使用上传响应中的 `fileId` 创建转换版本。

## 环境要求

- Node.js 20 LTS 或更高版本
- npm 10 或更高版本

## 安装与运行

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

浏览器访问终端输出的地址，通常为 `http://localhost:5173`。

Mock 默认开启。用户名中含 `admin`、`teacher` 时分别模拟管理员和教师；其他用户名模拟学生。密码可填写任意非空值。

## 后端联调

启动后端服务后，在 `.env` 中保持 API 地址为空并关闭 Mock：

```env
VITE_API_BASE_URL=
VITE_USE_MOCK=false
```

不要填写 `http://localhost:8000`。Vite 开发服务器会将浏览器发往 `http://localhost:5173/api/...` 的请求代理到 `http://127.0.0.1:8000`，因此 HttpOnly Viewer Cookie 会在同源 `/api` 链路上正确写入和发送。启动流程：

```bash
npm run dev
```

在浏览器开发者工具的 Network 面板确认请求 URL 保持为 `http://localhost:5173/api/...`，包括 `viewer-config` 返回的 `/api/v1/viewer-assets/.../metadata.json` 与其相对瓦片资源；不应出现直接发往 `localhost:8000` 的浏览器请求。

接口契约：

- `POST /api/v1/auth/login`，请求体 `{ username, password }`，响应 `data` 包含 `accessToken`、`tokenType`。
- `GET /api/v1/auth/me`，响应 `data` 包含 `id`、`username`、`displayName`、`roles`。

请求会自动追加 `Authorization: <tokenType> <accessToken>`、携带同源 Cookie；收到 401 会清除本地认证信息并转到登录页。

## 构建

```bash
npm run build
```
