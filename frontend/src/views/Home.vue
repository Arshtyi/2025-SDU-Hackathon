<template>
    <div class="home-container">
        <header class="header">
            <h1>GitHub DeepWiki 解析器</h1>
            <p>输入 GitHub 仓库链接，获取 DeepWiki 解析结果</p>
        </header>

        <div class="repo-input">
            <input
                v-model="repoUrl"
                type="text"
                placeholder="例如: https://github.com/microsoft/vscode"
                @keyup.enter="parseRepo" />
            <button
                @click="parseRepo"
                :disabled="isLoading">
                {{ isLoading ? "解析中..." : "开始解析" }}
            </button>
            <button
                @click="demoParseRepo"
                :disabled="isLoading"
                class="demo-button">
                演示解析
            </button>
        </div>

        <div
            v-if="isLoading"
            class="progress-container">
            <div class="stage-indicator">
                <span>当前阶段: </span>
                <span :class="['stage-badge', stage.toLowerCase()]">{{
                    stage
                }}</span>
            </div>
            <div class="progress-bar">
                <div
                    class="progress-fill"
                    :style="{ width: `${progress}%` }"></div>
            </div>
            <div class="progress-info">
                <div class="progress-percentage">{{ progress }}%</div>
                <div class="progress-text">{{ progressText }}</div>
            </div>
        </div>

        <div
            v-if="deepWikiUrl"
            class="deepwiki-url-info">
            <p>
                实际请求 URL:
                <a
                    :href="deepWikiUrl"
                    target="_blank"
                    >{{ deepWikiUrl }}</a
                >
            </p>
        </div>

        <div
            v-if="error"
            class="error-message">
            {{ error }}
        </div>

        <div
            v-if="markdownContent"
            class="result-container">
            <div class="result-header">
                <h2>解析结果</h2>
                <button
                    class="copy-button"
                    @click="copyMarkdown">
                    复制Markdown
                </button>
                <button
                    class="download-button"
                    @click="downloadMarkdown">
                    下载Markdown
                </button>
                <button
                    class="debug-button"
                    @click="toggleDebug">
                    {{ showDebug ? "隐藏调试信息" : "显示调试信息" }}
                </button>
            </div>
            <div
                class="markdown-content"
                v-html="renderedMarkdown"></div>
        </div>

        <!-- 调试面板 -->
        <div
            v-if="showDebug"
            class="debug-panel">
            <h3>调试信息</h3>
            <div class="debug-info">
                <p><strong>任务ID:</strong> {{ currentTask }}</p>
                <p><strong>阶段:</strong> {{ stage }}</p>
                <p><strong>进度:</strong> {{ progress }}%</p>
                <p>
                    <strong>Markdown内容长度:</strong>
                    {{ markdownContent ? markdownContent.length : 0 }} 字符
                </p>
                <p><strong>Markdown内容预览:</strong></p>
                <pre class="markdown-preview">{{
                    markdownContent
                        ? markdownContent.substring(0, 200) + "..."
                        : "无内容"
                }}</pre>
            </div>
            <div class="file-explorer">
                <h4>文件浏览器</h4>
                <button
                    @click="loadFiles"
                    class="refresh-button">
                    刷新文件列表
                </button>
                <table
                    class="files-table"
                    v-if="files.length > 0">
                    <thead>
                        <tr>
                            <th>文件名</th>
                            <th>大小</th>
                            <th>修改时间</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="file in files"
                            :key="file.name">
                            <td>{{ file.name }}</td>
                            <td>{{ file.size }} bytes</td>
                            <td>
                                {{ new Date(file.modified).toLocaleString() }}
                            </td>
                            <td>
                                <button
                                    @click="viewFile(file.name)"
                                    class="view-button">
                                    查看
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p v-else>没有文件</p>
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { marked } from "marked";
import io from "socket.io-client";
import hljs from "highlight.js";
import "highlight.js/styles/github-dark.css";

export default {
    name: "Home",
    data() {
        return {
            repoUrl: "",
            markdownContent: "",
            isLoading: false,
            error: null,
            socket: null,
            progress: 0,
            progressText: "准备中...",
            deepWikiUrl: null,
            currentTask: null,
            stage: "初始化",
            showDebug: false,
            files: [],
        };
    },
    computed: {
        renderedMarkdown() {
            if (!this.markdownContent) return "";

            // 配置marked以使用highlight.js进行代码高亮
            marked.setOptions({
                highlight: function (code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(code, { language: lang })
                                .value;
                        } catch (e) {
                            console.error(e);
                        }
                    }
                    return hljs.highlightAuto(code).value;
                },
                breaks: true,
                gfm: true,
                headerIds: true,
                mangle: false,
            });

            return marked(this.markdownContent);
        },
    },
    mounted() {
        // 连接Socket.IO用于实时进度更新，使用相对路径自动适应当前域名和端口
        const backendUrl =
            process.env.VUE_APP_BACKEND_URL ||
            (window.location.hostname === "localhost"
                ? "http://localhost:3000"
                : window.location.origin);

        this.socket = io(backendUrl);

        // 监听一般的进度更新
        this.socket.on("connect", () => {
            console.log("Socket.io连接成功");
        });

        this.socket.on("connect_error", (error) => {
            console.error("Socket.io连接失败:", error);
        });
    },
    beforeUnmount() {
        // 清理定时器
        if (this.progressCheckInterval) {
            clearInterval(this.progressCheckInterval);
        }

        // 清理Socket连接
        if (this.currentTask) {
            this.socket.off(`task:${this.currentTask}:progress`);
            this.socket.off(`task:${this.currentTask}:completed`);
            this.socket.off(`task:${this.currentTask}:failed`);
        }

        if (this.socket) {
            this.socket.disconnect();
        }
    },
    methods: {
        async parseRepo() {
            if (!this.repoUrl) {
                this.error = "请输入GitHub仓库URL";
                return;
            }

            this.isLoading = true;
            this.error = null;
            this.markdownContent = "";
            this.deepWikiUrl = null;
            this.progress = 0;
            this.progressText = "开始解析...";
            this.stage = "初始化";

            // 设置 DeepWiki URL
            if (this.repoUrl.includes("github.com")) {
                this.deepWikiUrl = this.repoUrl.replace(
                    "github.com",
                    "deepwiki.com"
                );
            } else if (this.repoUrl.includes("deepwiki.io")) {
                this.deepWikiUrl = this.repoUrl.replace(
                    "deepwiki.io",
                    "deepwiki.com"
                );
            } else if (this.repoUrl.includes("deepwiki.bb7.ai")) {
                this.deepWikiUrl = this.repoUrl.replace(
                    "deepwiki.bb7.ai",
                    "deepwiki.com"
                );
            } else {
                this.deepWikiUrl = this.repoUrl;
            }

            // 取消之前的任务监听
            if (this.currentTask) {
                this.socket.off(`task:${this.currentTask}:progress`);
                this.socket.off(`task:${this.currentTask}:completed`);
                this.socket.off(`task:${this.currentTask}:failed`);
            }

            try {
                const apiUrl = process.env.VUE_APP_API_URL || "/api";

                // 启动解析任务
                const response = await axios.post(`${apiUrl}/parse`, {
                    url: this.deepWikiUrl || this.repoUrl,
                });

                if (!response.data || !response.data.taskId) {
                    throw new Error("服务器返回的数据格式不正确");
                }

                this.currentTask = response.data.taskId;

                // 监听任务进度
                this.socket.on(`task:${this.currentTask}:progress`, (data) => {
                    this.progress = data.progress;
                    this.progressText = data.message;
                    this.stage = data.stage;
                    console.log(
                        `进度更新: [${data.stage}] ${data.progress}% - ${data.message}`
                    );
                });

                // 监听任务完成
                this.socket.on(
                    `task:${this.currentTask}:completed`,
                    async (data) => {
                        console.log("任务完成:", data);
                        // 获取Markdown内容
                        try {
                            const markdownResponse = await axios.get(
                                `${apiUrl}/markdown/${this.currentTask}`
                            );

                            // 检查响应数据是否有效
                            if (
                                markdownResponse.data &&
                                markdownResponse.data.markdown
                            ) {
                                this.markdownContent =
                                    markdownResponse.data.markdown;
                                console.log(
                                    `成功获取Markdown内容，长度: ${this.markdownContent.length}`
                                );

                                // 只显示前100个字符用于调试
                                if (this.markdownContent.length > 0) {
                                    console.log(
                                        `Markdown内容开头: ${this.markdownContent.substring(
                                            0,
                                            100
                                        )}...`
                                    );
                                }

                                this.isLoading = false;
                            } else {
                                console.error("Markdown内容为空或格式不正确");
                                this.error = "获取的Markdown内容为空，请重试";
                                this.isLoading = false;
                            }
                        } catch (err) {
                            console.error("获取Markdown内容失败:", err);
                            this.error = `解析完成，但获取内容失败: ${
                                err.response?.data?.error || err.message
                            }`;
                            this.isLoading = false;
                        }
                    }
                );

                // 监听任务失败
                this.socket.on(`task:${this.currentTask}:failed`, (data) => {
                    console.error("任务失败:", data);
                    this.error = data.error || "解析失败，请稍后重试";
                    this.isLoading = false;
                });

                // 如果30秒内没有任何进度更新，则定时查询任务状态
                this.progressCheckInterval = setInterval(async () => {
                    try {
                        const statusResponse = await axios.get(
                            `${apiUrl}/task/${this.currentTask}`
                        );
                        const taskInfo = statusResponse.data;

                        if (taskInfo.status === "completed") {
                            clearInterval(this.progressCheckInterval);
                            // 获取Markdown内容
                            const markdownResponse = await axios.get(
                                `${apiUrl}/markdown/${this.currentTask}`
                            );
                            this.markdownContent =
                                markdownResponse.data.markdown;
                            this.isLoading = false;
                        } else if (taskInfo.status === "failed") {
                            clearInterval(this.progressCheckInterval);
                            this.error =
                                taskInfo.error || "解析失败，请稍后重试";
                            this.isLoading = false;
                        } else {
                            // 更新进度信息
                            this.progress = taskInfo.progress;
                            this.stage = taskInfo.stage;
                        }
                    } catch (err) {
                        console.error("获取任务状态失败:", err);
                    }
                }, 3000);
            } catch (error) {
                console.error("解析失败:", error);
                this.error =
                    error.response?.data?.error || "解析过程中发生错误，请重试";
                this.isLoading = false;
            }
        },
        copyMarkdown() {
            if (!this.markdownContent) return;

            navigator.clipboard
                .writeText(this.markdownContent)
                .then(() => {
                    alert("Markdown内容已复制到剪贴板!");
                })
                .catch((err) => {
                    console.error("复制失败:", err);
                    alert("复制失败，请手动选择内容并复制");
                });
        },

        downloadMarkdown() {
            if (!this.markdownContent) return;

            // 创建Blob
            const blob = new Blob([this.markdownContent], {
                type: "text/markdown",
            });

            // 创建一个临时链接
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");

            // 设置链接属性
            const repoName = this.extractRepoName(this.repoUrl);
            a.href = url;
            a.download = `${repoName || "deepwiki"}-${new Date()
                .toISOString()
                .slice(0, 10)}.md`;

            // 模拟点击链接下载文件
            document.body.appendChild(a);
            a.click();

            // 清理
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 0);
        },

        extractRepoName(url) {
            if (!url) return "";

            try {
                // 尝试提取仓库名称
                const urlObj = new URL(url);
                const pathParts = urlObj.pathname.split("/").filter(Boolean);

                // 如果路径至少有两部分 (用户名/仓库名)
                if (pathParts.length >= 2) {
                    return pathParts[1]; // 返回仓库名称
                }

                return "";
            } catch (e) {
                return "";
            }
        },

        toggleDebug() {
            this.showDebug = !this.showDebug;
            if (this.showDebug) {
                this.loadFiles();
            }
        },

        async loadFiles() {
            try {
                const apiUrl = process.env.VUE_APP_API_URL || "/api";
                const response = await axios.get(`${apiUrl}/files`);
                this.files = response.data.files || [];
            } catch (error) {
                console.error("加载文件列表失败:", error);
            }
        },

        async viewFile(fileName) {
            try {
                const apiUrl = process.env.VUE_APP_API_URL || "/api";
                const response = await axios.get(`${apiUrl}/file/${fileName}`);
                alert(`文件内容:\n\n${response.data.content}`);
            } catch (error) {
                console.error("查看文件失败:", error);
            }
        },

        async demoParseRepo() {
            // 使用演示URL
            const demoUrl = "https://github.com/Arshtyi/LaTeX-Templates";
            this.repoUrl = demoUrl;

            this.isLoading = true;
            this.error = null;
            this.markdownContent = "";
            this.progress = 0;
            this.progressText = "开始演示解析...";
            this.stage = "测试";

            try {
                const apiUrl = process.env.VUE_APP_API_URL || "/api";

                // 直接调用测试端点
                this.progressText = "正在解析演示存储库...";
                this.progress = 50;

                const response = await axios.get(`${apiUrl}/test-parse`, {
                    params: { url: demoUrl },
                });

                if (response.data && response.data.markdown) {
                    this.markdownContent = response.data.markdown;
                    this.isLoading = false;

                    // 模拟DeepWiki URL
                    if (demoUrl.includes("github.com")) {
                        this.deepWikiUrl = demoUrl.replace(
                            "github.com",
                            "deepwiki.com"
                        );
                    }
                } else {
                    this.error = "演示解析返回了空内容";
                    this.isLoading = false;
                }
            } catch (error) {
                console.error("演示解析失败:", error);
                this.error = `演示解析失败: ${
                    error.response?.data?.error || error.message
                }`;
                this.isLoading = false;
            }
        },

        toggleDebug() {
            this.showDebug = !this.showDebug;
        },

        async loadFiles() {
            try {
                const apiUrl = process.env.VUE_APP_API_URL || "/api";
                const response = await axios.get(`${apiUrl}/files`);
                this.files = response.data.files || [];
            } catch (error) {
                console.error("加载文件列表失败:", error);
            }
        },

        async viewFile(fileName) {
            try {
                const apiUrl = process.env.VUE_APP_API_URL || "/api";
                const response = await axios.get(`${apiUrl}/files/${fileName}`);
                alert(`文件内容:\n\n${response.data.content}`);
            } catch (error) {
                console.error("查看文件失败:", error);
            }
        },

        async demoParseRepo() {
            this.repoUrl = "https://github.com/microsoft/vscode";
            await this.parseRepo();
        },
    },
};
</script>

<style scoped>
.home-container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem 1rem;
}

.header {
    text-align: center;
    margin-bottom: 2rem;
}

.header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    color: #2c3e50;
}

.header p {
    color: #666;
    font-size: 1.1rem;
}

.repo-input {
    display: flex;
    gap: 0.5rem;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
}

.repo-input input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

.repo-input button {
    padding: 0 24px;
    background-color: #4caf50;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
}

.repo-input button:hover:not(:disabled) {
    background-color: #45a049;
}

.repo-input button:disabled {
    background-color: #9e9e9e;
    cursor: not-allowed;
}

.repo-input .demo-button {
    background-color: #2196f3;
}

.repo-input .demo-button:hover:not(:disabled) {
    background-color: #1976d2;
}

.demo-button {
    background-color: #2196f3;
    color: white;
}

.demo-button:hover:not(:disabled) {
    background-color: #1976d2;
}

.progress-container {
    margin-top: 2rem;
    margin-bottom: 2rem;
    padding: 1.5rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #f9f9f9;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    width: 100%;
}

.stage-indicator {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    font-size: 1rem;
}

.stage-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 16px;
    color: white;
    font-weight: 500;
    margin-left: 0.5rem;
    text-transform: capitalize;
}

.stage-badge.初始化 {
    background-color: #9c27b0;
}

.stage-badge.fetch {
    background-color: #2196f3;
}

.stage-badge.parse {
    background-color: #ff9800;
}

.stage-badge.convert {
    background-color: #4caf50;
}

.progress-bar {
    height: 12px;
    background-color: #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4caf50, #8bc34a);
    width: 0%;
    transition: width 0.3s ease;
    border-radius: 6px;
}

.progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.5rem;
}

.progress-percentage {
    font-weight: bold;
    color: #333;
}

.progress-text {
    color: #555;
    font-size: 0.9rem;
}

.error-message {
    color: #e53935;
    background-color: #ffebee;
    border: 1px solid #ffcdd2;
    padding: 12px;
    border-radius: 4px;
    max-width: 800px;
    margin: 0 auto;
    width: 100%;
}

.deepwiki-url-info {
    margin: 1rem auto;
    padding: 0.75rem 1rem;
    background-color: #e3f2fd;
    border-left: 4px solid #2196f3;
    border-radius: 4px;
    max-width: 800px;
    font-size: 0.9rem;
}

.deepwiki-url-info a {
    color: #1976d2;
    text-decoration: none;
    font-weight: 500;
}

.result-container {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    width: 100%;
    margin-top: 2rem;
}

.result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
}

.result-header h2 {
    font-size: 1.5rem;
    color: #2c3e50;
    margin: 0;
}

.copy-button,
.download-button,
.debug-button {
    padding: 0.5rem 1rem;
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
    cursor: pointer;
    margin-left: 0.5rem;
    transition: all 0.2s;
}

.copy-button:hover,
.download-button:hover,
.debug-button:hover {
    background-color: #e0e0e0;
}

.markdown-content {
    line-height: 1.8;
}

/* Markdown样式 */
.markdown-content :deep(h1) {
    font-size: 2rem;
    margin: 1.5rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #eee;
}

.markdown-content :deep(h2) {
    font-size: 1.5rem;
    margin: 1.2rem 0 0.8rem;
}

.markdown-content :deep(h3) {
    font-size: 1.25rem;
    margin: 1rem 0 0.7rem;
}

.markdown-content :deep(p) {
    margin-bottom: 1rem;
}

.markdown-content :deep(pre) {
    background-color: #282c34;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    margin: 1rem 0;
}

.markdown-content :deep(code) {
    font-family: "Consolas", "Monaco", "Courier New", monospace;
    font-size: 0.9em;
}

.markdown-content :deep(a) {
    color: #1976d2;
    text-decoration: none;
}

.markdown-content :deep(a:hover) {
    text-decoration: underline;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
    padding-left: 2rem;
    margin-bottom: 1rem;
}

.markdown-content :deep(blockquote) {
    border-left: 4px solid #bbdefb;
    padding-left: 1rem;
    color: #546e7a;
    margin: 1rem 0;
    background-color: #f5f5f5;
    padding: 0.5rem 1rem;
}

.markdown-content :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
    border: 1px solid #e0e0e0;
    padding: 0.5rem;
    text-align: left;
}

.markdown-content :deep(th) {
    background-color: #f5f5f5;
    font-weight: bold;
}

.markdown-content :deep(img) {
    max-width: 100%;
    height: auto;
    margin: 1rem 0;
    border-radius: 4px;
}

.debug-panel {
    margin-top: 2rem;
    padding: 1.5rem;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #f9f9f9;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.debug-panel h3 {
    font-size: 1.25rem;
    margin-bottom: 1rem;
    color: #2c3e50;
}

.debug-info p {
    margin: 0.5rem 0;
    font-size: 0.9rem;
    color: #333;
}

.debug-info pre {
    background-color: #f5f5f5;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.9rem;
    color: #333;
}

.file-explorer {
    margin-top: 1rem;
}

.file-explorer h4 {
    font-size: 1rem;
    margin-bottom: 0.5rem;
    color: #2c3e50;
}

.refresh-button {
    padding: 0.5rem 1rem;
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
    cursor: pointer;
    margin-bottom: 1rem;
    transition: all 0.2s;
}

.refresh-button:hover {
    background-color: #e0e0e0;
}

.files-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
}

.files-table th,
.files-table td {
    border: 1px solid #ddd;
    padding: 0.5rem;
    text-align: left;
}

.files-table th {
    background-color: #f5f5f5;
    font-weight: bold;
}

.view-button {
    padding: 0.5rem 1rem;
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;
}

.view-button:hover {
    background-color: #e0e0e0;
}

@media (max-width: 768px) {
    .header h1 {
        font-size: 2rem;
    }

    .repo-input {
        flex-direction: column;
    }

    .repo-input button {
        width: 100%;
        padding: 12px 16px;
    }

    .result-header {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
    }

    .result-header div {
        display: flex;
        width: 100%;
        justify-content: space-between;
    }

    .copy-button,
    .download-button,
    .debug-button {
        flex: 1;
        text-align: center;
    }
}
</style>
