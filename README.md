# Github 项目简析

这个项目用于解析 GitHub 仓库的 DeepWiki 内容，并将其转换为 Markdown 格式进行展示。项目采用前后端分离的架构，前端使用 Vue.js，后端使用 Node.js 和 Python。设计简洁清爽，使用便捷。

## 功能特点

-   输入 GitHub 仓库链接，自动转换为 DeepWiki 链接
-   解析 DeepWiki 页面内容并转换为 Markdown 格式
-   实时显示解析进度
-   支持复制和下载解析结果
-   美观简洁的用户界面
-   代码高亮显示、行号标注和一键复制功能
-   支持多种编程语言的语法高亮

## 技术栈

-   **前端**：Vue.js、Axios、Socket.io、Marked、Highlight.js
-   **后端**：
    -   Node.js (Express)：处理 API 请求、Socket.io 通信
    -   Python：网页内容抓取和解析
-   **环境**：
    -   Node.js 包管理：npm
    -   Python 虚拟环境：Conda

## 安装和运行

### 前置条件

-   Node.js (v14+)
-   npm (v6+)
-   Python (v3.8+)
-   Conda 或 Miniconda

### 启动项目

我们提供了一个便捷的启动脚本，可以一键启动整个项目：

```bash
# 添加执行权限
chmod +x start.sh

# 启动项目
./start.sh start
```

启动脚本会自动：

1. 检查端口占用并释放（前端 8080 端口，后端 3000 端口）
2. 设置 Python Conda 环境并安装依赖
3. 安装 Node.js 依赖
4. 启动后端 API 服务
5. 启动前端开发服务器

### 其他脚本命令

```bash
# 停止所有服务
./start.sh stop

# 重启所有服务
./start.sh restart

# 查看服务状态
./start.sh status

# 构建前端项目
./start.sh build
```

## 项目结构

```
/
├── frontend/               # 前端Vue项目
│   ├── public/             # 静态资源
│   └── src/                # 源代码
│       ├── assets/         # 资源文件
│       ├── components/     # Vue组件
│       ├── views/          # 页面
│       └── App.vue         # 主应用组件
├── backend/                # 后端
│   ├── nodejs/             # Node.js API服务
│   │   └── server.js       # 主服务器
│   └── python/             # Python解析器
│       └── parse_deepwiki.py  # DeepWiki解析器
├── .conda/                 # Python虚拟环境
├── start.sh                # 启动脚本
└── README.md               # 项目文档
```

## 使用方法

1. 启动项目后，打开浏览器访问 `http://localhost:8000`
2. 在输入框中输入 GitHub 仓库链接，例如：`https://github.com/username/repo`
3. 点击"开始解析"按钮
4. 等待解析完成，查看结果
5. 在解析结果中，代码块支持：
    - 语法高亮显示
    - 显示编程语言标识
    - 自动行号
    - 鼠标悬停时显示复制按钮
    - 点击复制按钮一键复制代码内容
6. 可以复制或下载解析后的全部 Markdown 内容

## 注意事项

-   启动脚本会检查并自动处理端口占用问题
-   所有依赖项会在首次启动时自动安装
-   启动时会提示配置网络代理，用于访问 DeepWiki 网站
-   系统会自动将 GitHub 链接转换为正确的 DeepWiki 链接 (deepwiki.com)

## URL 转换规则

系统会自动将以下 URL 格式转换为标准的 DeepWiki URL：

-   `https://github.com/user/repo` → `https://deepwiki.com/user/repo`
-   `https://deepwiki.io/user/repo` → `https://deepwiki.com/user/repo`
-   `https://deepwiki.bb7.ai/user/repo` → `https://deepwiki.com/user/repo`

## 网络配置

在启动脚本运行时，系统会提示您配置网络设置：

1. 询问是否使用代理 - 默认为"是"

    - 如果使用代理，需要输入：
        - 代理主机地址（默认：127.0.0.1）
        - 代理端口（默认：7897）

2. 询问是否验证 SSL 证书 - 默认为"是"

    - 不验证 SSL 证书可以解决一些 SSL 连接错误，但会降低安全性

3. HTTP 请求超时时间 - 默认为 30 秒

    - 可以设置更大的值来处理网络较慢的情况

4. 最大重试次数 - 默认为 3 次
    - 遇到连接错误时会自动重试的次数

您也可以通过环境变量手动设置网络配置：

```bash
# 代理设置
export HTTP_PROXY_HOST=127.0.0.1
export HTTP_PROXY_PORT=7897
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897

# SSL证书验证设置（1=启用验证，0=禁用验证）
export SSL_VERIFY=0

# HTTP连接设置
export HTTP_TIMEOUT=60   # 超时时间（秒）
export HTTP_MAX_RETRIES=5   # 最大重试次数

# 禁用代理
export NO_PROXY=1

# SSL和连接设置
export SSL_VERIFY=0     # 0为禁用SSL验证，1为启用
export HTTP_MAX_RETRIES=3  # 连接失败时的重试次数
export HTTP_TIMEOUT=60     # 连接超时时间（秒）
```

### 解决常见连接问题

如果遇到以下问题，可以尝试：

1. **SSL 证书错误**：禁用 SSL 验证（启动时选择不验证 SSL 证书）
2. **连接超时**：确保代理正确配置，或尝试不使用代理
3. **DNS 解析失败**：检查网络连接和 DNS 设置
4. **EOF 错误**：可能是代理问题，尝试不使用代理或使用其他代理
