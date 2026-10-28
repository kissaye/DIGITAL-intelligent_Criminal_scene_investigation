# 数智刑勘前端工程

M0 阶段仅提供认证、角色路由和三类空白首页；不包含点云、三维浏览、案例、脱敏或教学业务模块。

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

在 `.env` 中配置并关闭 Mock：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK=false
```

接口契约：

- `POST /api/v1/auth/login`，请求体 `{ username, password }`，响应 `data` 包含 `accessToken`、`tokenType`。
- `GET /api/v1/auth/me`，响应 `data` 包含 `id`、`username`、`displayName`、`roles`。

请求会自动追加 `Authorization: <tokenType> <accessToken>`；收到 401 会清除本地认证信息并转到登录页。

## 构建

```bash
npm run build
```
