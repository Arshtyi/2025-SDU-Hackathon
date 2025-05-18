<template>
    <div class="home-container">
        <header class="header">
            <h1>Github项目简析</h1>
            <p>输入 GitHub 仓库链接，获取项目详细解析</p>
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
import mermaid from "mermaid";
// 引入更现代的代码高亮样式
import "highlight.js/styles/github-dark-dimmed.css";
// 引入常用语言
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import python from "highlight.js/lib/languages/python";
import java from "highlight.js/lib/languages/java";
import cpp from "highlight.js/lib/languages/cpp";
import csharp from "highlight.js/lib/languages/csharp";
import php from "highlight.js/lib/languages/php";
import ruby from "highlight.js/lib/languages/ruby";
import go from "highlight.js/lib/languages/go";
import rust from "highlight.js/lib/languages/rust";
import bash from "highlight.js/lib/languages/bash";
import shell from "highlight.js/lib/languages/shell";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";
import markdown from "highlight.js/lib/languages/markdown";
import sql from "highlight.js/lib/languages/sql";
import css from "highlight.js/lib/languages/css";
import scss from "highlight.js/lib/languages/scss";
import less from "highlight.js/lib/languages/less";
import powershell from "highlight.js/lib/languages/powershell";

// 注册语言
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("java", java);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("csharp", csharp);
hljs.registerLanguage("php", php);
hljs.registerLanguage("ruby", ruby);
hljs.registerLanguage("go", go);
hljs.registerLanguage("rust", rust);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("shell", shell);
hljs.registerLanguage("json", json);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("css", css);
hljs.registerLanguage("scss", scss);
hljs.registerLanguage("less", less);
hljs.registerLanguage("powershell", powershell);

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

            // 预处理Markdown内容，过滤掉包含特殊标记的代码块
            let processedContent = this.markdownContent;

            // 查找并移除包含特殊标记的代码块
            // 匹配 ```mermaid ... $!/$ ... ``` 形式的代码块
            processedContent = processedContent.replace(
                /```mermaid[\s\S]*?\$!\/?[\s\S]*?```/g,
                "[特殊内容已跳过 - 请访问原始DeepWiki查看完整内容]"
            );

            // 移除空的代码块或只包含空白字符的代码块
            processedContent = processedContent.replace(
                /```(?:mermaid|[a-z]*)\s*[\r\n]*\s*```/g,
                ""
            );

            // 如果只是普通的 $!/$ 标记（不在代码块中），也移除它们
            processedContent = processedContent.replace(/\$!\/\$/g, "");

            // 配置marked以使用highlight.js进行代码高亮
            marked.setOptions({
                highlight: function (code, lang) {
                    // 检查代码内容中是否包含特殊标记
                    if (
                        code.includes("$!/$") ||
                        code.includes("$!$") ||
                        code.includes("$/$")
                    ) {
                        // 跳过包含特殊标记的代码块，返回空字符串让它不渲染
                        return "";
                    }

                    const language = lang || "";
                    let highlighted;

                    // 尝试使用指定的语言进行高亮
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            highlighted = hljs.highlight(code, {
                                language: lang,
                            }).value;
                        } catch (e) {
                            console.error("代码高亮错误:", e);
                            // 回退到自动检测语言
                            try {
                                highlighted = hljs.highlightAuto(code).value;
                            } catch (e2) {
                                console.error("自动高亮失败:", e2);
                                // 最终回退：转义HTML并原样返回
                                highlighted = code
                                    .replace(/&/g, "&amp;")
                                    .replace(/</g, "&lt;")
                                    .replace(/>/g, "&gt;")
                                    .replace(/"/g, "&quot;")
                                    .replace(/'/g, "&#039;");
                            }
                        }
                    } else {
                        // 如果没有指定语言或不支持该语言，尝试自动检测
                        try {
                            highlighted = hljs.highlightAuto(code).value;
                        } catch (e) {
                            console.error("自动高亮失败:", e);
                            // 转义HTML并原样返回
                            highlighted = code
                                .replace(/&/g, "&amp;")
                                .replace(/</g, "&lt;")
                                .replace(/>/g, "&gt;")
                                .replace(/"/g, "&quot;")
                                .replace(/'/g, "&#039;");
                        }
                    }

                    // 添加行号和复制按钮
                    const lines = highlighted.split("\n");
                    let lineNumbersHtml = "";

                    // 创建行号
                    for (let i = 0; i < lines.length; i++) {
                        lineNumbersHtml += `<span class="hljs-line-number">${
                            i + 1
                        }</span>`;
                    }

                    // 创建包含行号和复制按钮的完整代码块
                    return `<div class="hljs-code-container">
                            <div class="hljs-line-numbers">${lineNumbersHtml}</div>
                            <div class="hljs-code">${highlighted}</div>
                            <button class="hljs-copy-button" onclick="copyCode(this)">复制</button>
                        </div>`;
                },
                breaks: true,
                gfm: true,
                headerIds: true,
                mangle: false,
                smartLists: true,
            });

            // 渲染Markdown
            const html = marked(processedContent);

            // 移除空的代码块（那些包含特殊标记被过滤掉的或空白代码块）
            const cleanedHtml = html
                // 移除完全空的代码块
                .replace(
                    /<pre><code class="language-[a-zA-Z0-9]+">\s*<\/code><\/pre>/g,
                    ""
                )
                // 移除只包含空白字符的代码块
                .replace(
                    /<pre[^>]*><code[^>]*>(\s|\n|\r|\t)*<\/code><\/pre>/g,
                    ""
                )
                // 移除空的<pre>标签（可能是由于其他过滤导致的）
                .replace(/<pre[^>]*>\s*<\/pre>/g, "")
                // 处理包含空div的代码块（hljs渲染后的结构）
                .replace(
                    /<div class="hljs-code-container">\s*<div class="hljs-line-numbers">[^<]*<\/div>\s*<div class="hljs-code">\s*<\/div>[\s\n\r]*<button[^>]*>[^<]*<\/button>\s*<\/div>/g,
                    ""
                )
                // 替换特殊内容提示为通知组件
                .replace(
                    /<p>\[特殊内容已跳过 - 请访问原始DeepWiki查看完整内容\]<\/p>/g,
                    `<div class="skip-special-marker-notice">
                        <div class="skip-icon">&#9888;</div>
                        <div class="skip-notice-text">
                            <p class="skip-title">已跳过特殊标记内容 ($!/$)</p>
                            <p>根据当前解析策略，包含特殊标记的内容不进行处理。</p>
                            <p>如需查看完整内容，请访问<a href="${
                                this.deepWikiUrl || "#"
                            }" target="_blank">原始页面</a>。</p>
                        </div>
                    </div>`
                );

            // 在返回HTML之前添加代码块的数据属性用于显示语言标识
            return cleanedHtml.replace(
                /<pre><code class="language-([a-zA-Z0-9]+)">/g,
                '<pre data-language="$1"><code class="language-$1">'
            );
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

        // 初始化Mermaid
        mermaid.initialize({
            startOnLoad: false,
            theme: "dark",
            securityLevel: "loose",
            fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif',
            logLevel: 3, // 减少日志输出
            flowchart: {
                htmlLabels: true,
                curve: "linear",
                useMaxWidth: true,
            },
            sequence: {
                mirrorActors: false,
                diagramMarginX: 50,
                diagramMarginY: 10,
                actorMargin: 80,
            },
            gantt: {
                titleTopMargin: 25,
                barHeight: 20,
                barGap: 4,
                topPadding: 50,
            },
            pie: {
                textPosition: 0.75,
            },
            er: {
                useMaxWidth: true,
            },
            gitGraph: {
                mainBranchName: "main",
                showCommitLabel: false,
            },
            journey: {
                diagramMarginX: 50,
                diagramMarginY: 10,
            },
        });

        // 全局添加复制代码的函数
        window.copyCode = (button) => {
            const codeContainer = button.parentElement;
            const codeElement = codeContainer.querySelector(".hljs-code");

            // 获取纯文本代码（去除HTML标记）
            const textToCopy = codeElement.textContent || codeElement.innerText;

            // 使用剪贴板API
            navigator.clipboard
                .writeText(textToCopy)
                .then(() => {
                    // 显示复制成功的反馈
                    button.textContent = "已复制!";
                    button.classList.add("copied");

                    // 3秒后恢复按钮状态
                    setTimeout(() => {
                        button.textContent = "复制";
                        button.classList.remove("copied");
                    }, 3000);
                })
                .catch((err) => {
                    console.error("复制失败:", err);
                    button.textContent = "复制失败";

                    // 3秒后恢复按钮状态
                    setTimeout(() => {
                        button.textContent = "复制";
                    }, 3000);
                });
        };
    },

    // 监视渲染的Markdown内容，处理代码块
    updated() {
        this.$nextTick(() => {
            this.enhanceCodeBlocks();
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
        // 移除空的代码块
        removeEmptyCodeBlocks() {
            // 获取所有代码块
            const codeBlocks = document.querySelectorAll(
                ".markdown-content pre"
            );

            codeBlocks.forEach((pre) => {
                const code = pre.querySelector("code");

                // 检查是否为空代码块（无内容或只有空白字符）
                if (
                    !code ||
                    !code.textContent ||
                    code.textContent.trim() === "" ||
                    code.textContent.trim() === "$!/$" ||
                    code.textContent.match(/^\s*\$!\/?[\s\n]*\$\s*$/)
                ) {
                    console.log("检测到空代码块，移除中...");

                    // 检查是否有父元素
                    if (pre.parentElement) {
                        // 移除整个代码块
                        pre.remove();
                    }
                }
            });

            // 移除可能的空容器（由于移除代码块后留下的）
            const emptyContainers = document.querySelectorAll(
                ".markdown-content div:empty"
            );
            emptyContainers.forEach((container) => {
                if (container.parentElement) {
                    container.remove();
                }
            });
        },

        // 增强已渲染的代码块
        enhanceCodeBlocks() {
            if (!this.markdownContent) return;

            // 首先移除空的代码块
            this.removeEmptyCodeBlocks();

            // 为所有代码块添加语言标识和复制按钮
            const codeBlocks = document.querySelectorAll(
                ".markdown-content pre"
            );

            codeBlocks.forEach((pre) => {
                // 获取语言
                const lang = pre.getAttribute("data-language") || "";
                const code = pre.querySelector("code");

                // 处理mermaid图表块
                if (lang === "mermaid" && code) {
                    try {
                        const id = `mermaid-${Date.now()}-${Math.floor(
                            Math.random() * 1000
                        )}`;
                        let mermaidText = code.textContent || code.innerText;

                        // 检查是否为空代码块
                        if (!mermaidText || mermaidText.trim() === "") {
                            console.log("检测到空mermaid代码块，跳过处理");
                            // 尝试移除空代码块
                            try {
                                pre.remove();
                            } catch (e) {
                                console.error("移除空代码块失败:", e);
                            }
                            return; // 跳过后续处理
                        }

                        // 检查是否包含$!/$ 标记，如果有则可能是特殊代码块标记
                        const isSpecialBlock =
                            mermaidText.includes("$!/$") ||
                            mermaidText.includes("$!$") ||
                            mermaidText.includes("$/$") ||
                            // 如果代码块内容仅为特殊标记或非常接近特殊标记（可能有空格等），也视为特殊块
                            mermaidText.trim() === "$!/$" ||
                            /^\s*\$!\/?[\s\n]*\$\s*$/.test(mermaidText);

                        if (isSpecialBlock) {
                            console.log(
                                "检测到特殊代码块标记: $!/$ - 根据新策略跳过处理"
                            );

                            // 这里需要检查父级容器是否存在
                            const parentElement = pre.parentElement;
                            if (parentElement) {
                                // 如果只是一个只包含特殊标记的代码块，尝试移除整个父容器
                                if (
                                    mermaidText.trim() === "$!/$" ||
                                    /^\s*\$!\/?[\s\n]*\$\s*$/.test(mermaidText)
                                ) {
                                    try {
                                        pre.remove(); // 直接移除pre元素
                                        return; // 直接返回，不执行后续的图表处理逻辑
                                    } catch (e) {
                                        console.error("移除特殊标记块失败:", e);
                                        // 如果移除失败，回退到显示通知的方式
                                    }
                                }
                            }

                            // 创建特殊标记通知容器，替换原来的渲染逻辑
                            const skipNoticeContainer =
                                document.createElement("div");
                            skipNoticeContainer.className =
                                "skip-special-marker-notice";

                            // 创建通知图标
                            const skipIcon = document.createElement("div");
                            skipIcon.className = "skip-icon";
                            skipIcon.innerHTML = "&#9888;"; // 警告符号
                            skipNoticeContainer.appendChild(skipIcon);

                            // 创建通知文本
                            const skipNotice = document.createElement("div");
                            skipNotice.className = "skip-notice-text";
                            skipNotice.innerHTML = `
                                <p class="skip-title">已跳过特殊标记内容 ($!/$)</p>
                                <p>根据当前解析策略，包含特殊标记的内容不进行处理。</p>
                                <p>如需查看完整内容，请访问<a href="${
                                    this.deepWikiUrl || "#"
                                }" target="_blank">原始页面</a>。</p>
                            `;
                            skipNoticeContainer.appendChild(skipNotice);

                            // 替换pre元素内容
                            pre.innerHTML = "";
                            pre.appendChild(skipNoticeContainer);
                            pre.className = "special-marker-skipped";

                            return; // 直接返回，不执行后续的图表处理逻辑
                        }

                        // 清理特殊标记，更智能地处理不同位置的标记
                        // 注意：下面的代码只会在特殊情况下执行，比如特殊标记被错误地传递到这里
                        // 正常情况下，上面的检查应该已经处理了所有特殊标记的情况
                        if (
                            mermaidText.includes("$!") ||
                            mermaidText.includes("/$")
                        ) {
                            console.log("检测到可能的特殊标记变体，尝试清理");

                            // 增强的特殊标记清理，支持更多变体和格式
                            mermaidText = mermaidText
                                .replace(
                                    /\$!\/?\$|\$[\s\n]*!\/?[\s\n]*\$|\$![\s\n]*\/\$|\$[\s\n]*![\s\n]*\/[\s\n]*\$/g,
                                    ""
                                )
                                .replace(
                                    /\s*[\n\r]*\s*\$!.*?\$\s*[\n\r]*\s*/g,
                                    ""
                                )
                                .trim();
                        }

                        // 创建图表容器
                        const mermaidContainer = document.createElement("div");
                        mermaidContainer.className = "mermaid-container";

                        // 创建一个用于mermaid渲染的div
                        const mermaidDiv = document.createElement("div");
                        mermaidDiv.className = "mermaid";
                        mermaidDiv.id = id;

                        // 添加图表类型标识
                        const chartTypeLabel = document.createElement("div");
                        chartTypeLabel.className = "chart-type-label";

                        // 检测图表类型并设置相应标签
                        let chartType = "图表";
                        if (
                            mermaidText.includes("graph") ||
                            mermaidText.includes("flowchart")
                        ) {
                            chartType = "流程图";
                        } else if (mermaidText.includes("sequenceDiagram")) {
                            chartType = "序列图";
                        } else if (mermaidText.includes("classDiagram")) {
                            chartType = "类图";
                        } else if (mermaidText.includes("gantt")) {
                            chartType = "甘特图";
                        } else if (mermaidText.includes("pie")) {
                            chartType = "饼图";
                        } else if (mermaidText.includes("mindmap")) {
                            chartType = "思维导图";
                        } else if (mermaidText.includes("gitGraph")) {
                            chartType = "Git图";
                        } else if (mermaidText.includes("timeline")) {
                            chartType = "时间线";
                        } else if (mermaidText.includes("erDiagram")) {
                            chartType = "E-R图";
                        } else if (mermaidText.includes("journey")) {
                            chartType = "用户旅程图";
                        }

                        chartTypeLabel.textContent = chartType;

                        // 创建加载指示器
                        const loadingDiv = document.createElement("div");
                        loadingDiv.className = "mermaid-loading";
                        loadingDiv.textContent = "图表加载中...";

                        // 添加到容器
                        mermaidContainer.appendChild(chartTypeLabel);
                        mermaidContainer.appendChild(loadingDiv);

                        // 替换pre元素内容
                        pre.innerHTML = "";
                        pre.appendChild(mermaidContainer);
                        pre.classList.add("mermaid-pre");

                        console.log(
                            "尝试渲染mermaid图表",
                            isSpecialBlock ? "(特殊代码块)" : ""
                        );

                        // 添加图表类型指示器和原始代码查看按钮
                        const toolbarDiv = document.createElement("div");
                        toolbarDiv.className = "mermaid-toolbar";

                        // 图表类型标签
                        let diagramType = "未知图表";
                        let typeCssClass = "mermaid-type";

                        if (
                            mermaidText.startsWith("graph ") ||
                            mermaidText.startsWith("flowchart ")
                        ) {
                            diagramType = "流程图";
                            typeCssClass += " flowchart";
                        } else if (mermaidText.includes("sequenceDiagram")) {
                            diagramType = "序列图";
                            typeCssClass += " sequence";
                        } else if (mermaidText.includes("classDiagram")) {
                            diagramType = "类图";
                            typeCssClass += " class";
                        } else if (mermaidText.includes("gantt")) {
                            diagramType = "甘特图";
                            typeCssClass += " gantt";
                        } else if (mermaidText.includes("pie")) {
                            diagramType = "饼图";
                            typeCssClass += " pie";
                        } else if (mermaidText.includes("gitGraph")) {
                            diagramType = "Git图";
                            typeCssClass += " git";
                        } else if (mermaidText.includes("mindmap")) {
                            diagramType = "思维导图";
                            typeCssClass += " mindmap";
                        } else if (mermaidText.includes("timeline")) {
                            diagramType = "时间线";
                            typeCssClass += " timeline";
                        } else if (mermaidText.includes("erDiagram")) {
                            diagramType = "实体关系图";
                            typeCssClass += " er";
                        } else if (mermaidText.includes("journey")) {
                            diagramType = "用户旅程图";
                            typeCssClass += " journey";
                        }

                        const typeLabel = document.createElement("span");
                        typeLabel.className = typeCssClass;
                        typeLabel.textContent = diagramType;
                        toolbarDiv.appendChild(typeLabel);

                        // 特殊标记指示器
                        if (isSpecialBlock) {
                            const specialLabel = document.createElement("span");
                            specialLabel.className = "mermaid-special-marker";
                            specialLabel.textContent = "特殊代码块";
                            specialLabel.title = "此图表来自特殊代码块标记";
                            toolbarDiv.appendChild(specialLabel);
                        }

                        // 查看源码按钮
                        const sourceBtn = document.createElement("button");
                        sourceBtn.className = "mermaid-source-btn";
                        sourceBtn.textContent = "查看代码";
                        sourceBtn.onclick = function () {
                            // 切换显示源代码/图表
                            const sourceView =
                                mermaidContainer.querySelector(
                                    ".mermaid-source"
                                );
                            const diagramView =
                                mermaidContainer.querySelector(".mermaid");

                            if (sourceView) {
                                // 如果已经存在源代码视图，则切换显示状态
                                const isVisible =
                                    sourceView.style.display !== "none";
                                sourceView.style.display = isVisible
                                    ? "none"
                                    : "block";
                                diagramView.style.display = isVisible
                                    ? "block"
                                    : "none";
                                sourceBtn.textContent = isVisible
                                    ? "查看代码"
                                    : "查看图表";
                            } else {
                                // 创建源代码视图
                                const codeView = document.createElement("pre");
                                codeView.className = "mermaid-source";
                                codeView.textContent = mermaidText;
                                mermaidContainer.appendChild(codeView);

                                diagramView.style.display = "none";
                                sourceBtn.textContent = "查看图表";
                            }
                        };
                        toolbarDiv.appendChild(sourceBtn);

                        // 添加工具栏到容器
                        mermaidContainer.appendChild(toolbarDiv);
                        mermaidContainer.appendChild(mermaidDiv);

                        // 异步渲染mermaid图表
                        mermaid
                            .render(id, mermaidText)
                            .then((result) => {
                                // 移除加载指示器
                                loadingDiv.remove();

                                // 设置渲染结果
                                mermaidDiv.innerHTML = result.svg;
                                console.log("mermaid图表渲染成功");

                                // 为SVG添加样式
                                const svg = mermaidDiv.querySelector("svg");
                                if (svg) {
                                    svg.style.maxWidth = "100%";
                                    svg.style.height = "auto";
                                    svg.style.display = "block";
                                    svg.style.margin = "0 auto";
                                }
                            })
                            .catch((error) => {
                                console.error("mermaid图表渲染失败:", error);

                                // 移除加载指示器
                                loadingDiv.remove();

                                // 显示错误信息和代码
                                const errorDiv = document.createElement("div");
                                errorDiv.className = "mermaid-error";
                                errorDiv.innerHTML = `
                                <p>图表渲染失败，可能的原因：</p>
                                <ul>
                                    <li>语法错误</li>
                                    <li>未能完整提取图表内容</li>
                                    <li>图表类型暂不支持</li>
                                </ul>
                                <p>您可以尝试查看原始页面或检查图表代码：</p>
                            `;

                                // 尝试自动修复常见的语法错误
                                let fixedText = mermaidText;
                                // 修复1: 缺少方向
                                if (fixedText.match(/^graph\s*$/m)) {
                                    fixedText = fixedText.replace(
                                        /^graph\s*$/m,
                                        "graph TD"
                                    );
                                }
                                // 修复2: 缺少分隔符
                                fixedText = fixedText.replace(
                                    /([A-Z][0-9]*)([A-Z][0-9]*)/g,
                                    "$1-->$2"
                                );

                                if (fixedText !== mermaidText) {
                                    // 如果进行了修复，尝试再次渲染
                                    const fixedDiv =
                                        document.createElement("div");
                                    fixedDiv.className = "mermaid-fixed";
                                    fixedDiv.id = `fixed-${id}`;
                                    mermaidContainer.appendChild(fixedDiv);

                                    const fixingNote =
                                        document.createElement("div");
                                    fixingNote.className =
                                        "mermaid-fixing-note";
                                    fixingNote.textContent = "尝试自动修复...";
                                    mermaidContainer.appendChild(fixingNote);

                                    mermaid
                                        .render(`fixed-${id}`, fixedText)
                                        .then((result) => {
                                            fixingNote.textContent =
                                                "图表已自动修复:";
                                            fixedDiv.innerHTML = result.svg;

                                            const svg =
                                                fixedDiv.querySelector("svg");
                                            if (svg) {
                                                svg.style.maxWidth = "100%";
                                                svg.style.height = "auto";
                                            }
                                        })
                                        .catch(() => {
                                            // 如果修复失败，移除修复相关元素
                                            fixingNote.remove();
                                            fixedDiv.remove();

                                            // 显示原始错误代码
                                            const codeView =
                                                document.createElement("pre");
                                            codeView.className =
                                                "mermaid-error-code";
                                            codeView.textContent = mermaidText;
                                            mermaidContainer.appendChild(
                                                errorDiv
                                            );
                                            mermaidContainer.appendChild(
                                                codeView
                                            );
                                        });
                                } else {
                                    // 显示源代码
                                    const codeView =
                                        document.createElement("pre");
                                    codeView.className = "mermaid-error-code";
                                    codeView.textContent = mermaidText;
                                    mermaidContainer.appendChild(errorDiv);
                                    mermaidContainer.appendChild(codeView);
                                }
                            });

                        return; // 不需要添加复制按钮和行号
                    } catch (e) {
                        console.error("处理mermaid图表出错:", e);
                    }
                }

                // 如果没有复制按钮，添加一个
                if (!pre.querySelector(".hljs-copy-button")) {
                    const copyBtn = document.createElement("button");
                    copyBtn.className = "hljs-copy-button";
                    copyBtn.textContent = "复制";
                    copyBtn.onclick = function () {
                        // 获取代码文本
                        const code = pre.querySelector("code");
                        const text = code.textContent || code.innerText;

                        // 复制到剪贴板
                        navigator.clipboard
                            .writeText(text)
                            .then(() => {
                                copyBtn.textContent = "已复制!";
                                copyBtn.classList.add("copied");

                                // 3秒后恢复按钮文本
                                setTimeout(() => {
                                    copyBtn.textContent = "复制";
                                    copyBtn.classList.remove("copied");
                                }, 3000);
                            })
                            .catch((err) => {
                                console.error("复制失败:", err);
                                copyBtn.textContent = "复制失败";
                                setTimeout(() => {
                                    copyBtn.textContent = "复制";
                                }, 3000);
                            });
                    };
                    pre.appendChild(copyBtn);
                }

                // 添加行号，如果还没有添加的话
                if (code && !pre.querySelector(".hljs-line-numbers")) {
                    const lines = code.innerHTML.split("\n");
                    const lineNumbers = document.createElement("div");
                    lineNumbers.className = "hljs-line-numbers";

                    for (let i = 0; i < lines.length; i++) {
                        const span = document.createElement("span");
                        span.className = "hljs-line-number";
                        span.textContent = i + 1;
                        lineNumbers.appendChild(span);
                    }

                    // 在pre内部添加行号
                    pre.classList.add("with-line-numbers");
                    pre.insertBefore(lineNumbers, code);
                }
            });
        },

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

        // 增强代码块显示
        enhanceCodeBlocks() {
            if (!this.markdownContent) return;

            // 查找所有代码块
            const codeBlocks = document.querySelectorAll(
                ".markdown-content pre code"
            );
            codeBlocks.forEach((block, index) => {
                const parentPre = block.parentNode;
                if (!parentPre) return;

                // 1. 添加语言标识
                const langMatch = block.className.match(/language-(\w+)/);
                const language = langMatch ? langMatch[1] : "文本";
                parentPre.setAttribute("data-language", language);

                // 2. 添加复制按钮
                if (!parentPre.querySelector(".code-copy-btn")) {
                    const copyBtn = document.createElement("button");
                    copyBtn.className = "code-copy-btn";
                    copyBtn.innerHTML = "复制";
                    copyBtn.onclick = () => {
                        const codeText = block.textContent;
                        navigator.clipboard.writeText(codeText).then(
                            () => {
                                copyBtn.innerHTML = "已复制!";
                                setTimeout(() => {
                                    copyBtn.innerHTML = "复制";
                                }, 2000);
                            },
                            (err) => {
                                console.error("复制失败:", err);
                                copyBtn.innerHTML = "复制失败";
                                setTimeout(() => {
                                    copyBtn.innerHTML = "复制";
                                }, 2000);
                            }
                        );
                    };
                    parentPre.appendChild(copyBtn);
                }

                // 3. 添加行号（如果行数超过3行）
                const lines = block.textContent
                    .split("\n")
                    .filter((line) => line.trim());
                if (
                    lines.length > 3 &&
                    !parentPre.querySelector(".line-numbers")
                ) {
                    parentPre.classList.add("line-numbers");

                    // 创建行号容器
                    const lineNumbers = document.createElement("div");
                    lineNumbers.className = "line-numbers";

                    // 为每行创建行号
                    for (let i = 1; i <= lines.length; i++) {
                        const lineNumber = document.createElement("span");
                        lineNumber.className = "line-number";
                        lineNumber.textContent = i;
                        lineNumbers.appendChild(lineNumber);
                    }

                    // 插入行号容器
                    parentPre.insertBefore(lineNumbers, block);
                    parentPre.classList.add("has-line-numbers");
                }
            });
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
    margin-bottom: 2.5rem;
    background: linear-gradient(135deg, #2c3e50, #3498db);
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.8rem;
    color: #ffffff;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.header p {
    color: #ecf0f1;
    font-size: 1.2rem;
}

.repo-input {
    display: flex;
    gap: 0.75rem;
    max-width: 800px;
    margin: 0 auto 2rem;
    width: 100%;
}

.repo-input input {
    flex: 1;
    padding: 14px 18px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 1rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    transition: all 0.3s;
}

.repo-input input:focus {
    border-color: #3498db;
    box-shadow: 0 2px 12px rgba(52, 152, 219, 0.2);
    outline: none;
}

.repo-input button {
    padding: 0 24px;
    background-color: #4caf50;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.repo-input button:hover:not(:disabled) {
    background-color: #45a049;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
}

.repo-input button:disabled {
    background-color: #9e9e9e;
    cursor: not-allowed;
}

.repo-input .demo-button {
    background-color: #3498db;
    box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
}

.repo-input .demo-button:hover:not(:disabled) {
    background-color: #2980b9;
    box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4);
}

.progress-container {
    margin-top: 2rem;
    margin-bottom: 2rem;
    padding: 1.8rem;
    border: none;
    border-radius: 12px;
    background-color: #ffffff;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    width: 100%;
}

.stage-indicator {
    display: flex;
    align-items: center;
    margin-bottom: 1.2rem;
    font-size: 1rem;
}

.stage-badge {
    padding: 0.35rem 0.85rem;
    border-radius: 20px;
    color: white;
    font-weight: 600;
    margin-left: 0.5rem;
    text-transform: capitalize;
    letter-spacing: 0.5px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.stage-badge.初始化 {
    background-color: #9c27b0;
}

.stage-badge.fetch {
    background-color: #3498db;
}

.stage-badge.parse {
    background-color: #e67e22;
}

.stage-badge.convert {
    background-color: #4caf50;
}

.stage-badge.测试 {
    background-color: #3f51b5;
}

.progress-bar {
    height: 14px;
    background-color: #e0e0e0;
    border-radius: 7px;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4caf50, #8bc34a);
    width: 0%;
    transition: width 0.3s ease;
    border-radius: 7px;
    box-shadow: 0 2px 4px rgba(76, 175, 80, 0.2);
}

.progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.75rem;
}

.progress-percentage {
    font-weight: bold;
    color: #333;
    font-size: 1.1rem;
}

.progress-text {
    color: #555;
    font-size: 0.95rem;
}

.error-message {
    color: #e53935;
    background-color: #ffebee;
    border-left: 4px solid #e53935;
    padding: 16px;
    border-radius: 8px;
    max-width: 800px;
    margin: 1.5rem auto;
    width: 100%;
    box-shadow: 0 2px 8px rgba(229, 57, 53, 0.15);
}

.deepwiki-url-info {
    margin: 1.5rem auto;
    padding: 1rem 1.25rem;
    background-color: #e3f2fd;
    border-left: 4px solid #2196f3;
    border-radius: 8px;
    max-width: 800px;
    font-size: 0.95rem;
    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
}

.deepwiki-url-info a {
    color: #1976d2;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
}

.deepwiki-url-info a:hover {
    color: #0d47a1;
    text-decoration: underline;
}

.result-container {
    background-color: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    width: 100%;
    margin-top: 2.5rem;
}

.result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.8rem;
    padding-bottom: 1.2rem;
    border-bottom: 1px solid #eee;
}

.result-header h2 {
    font-size: 1.8rem;
    color: #2c3e50;
    margin: 0;
    position: relative;
}

.result-header h2:after {
    content: "";
    position: absolute;
    bottom: -0.5rem;
    left: 0;
    width: 50px;
    height: 3px;
    background-color: #3498db;
    border-radius: 3px;
}

.copy-button,
.download-button,
.debug-button {
    padding: 0.6rem 1.2rem;
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    margin-left: 0.75rem;
    transition: all 0.3s;
}

.copy-button {
    background-color: #e3f2fd;
    color: #1976d2;
    border-color: #bbdefb;
}

.download-button {
    background-color: #e8f5e9;
    color: #388e3c;
    border-color: #c8e6c9;
}

.debug-button {
    background-color: #f3e5f5;
    color: #7b1fa2;
    border-color: #e1bee7;
}

.copy-button:hover,
.download-button:hover,
.debug-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.copy-button:hover {
    background-color: #bbdefb;
}

.download-button:hover {
    background-color: #c8e6c9;
}

.debug-button:hover {
    background-color: #e1bee7;
}

.markdown-content {
    line-height: 1.8;
}

/* Markdown样式 */
.markdown-content :deep(h1) {
    font-size: 2.2rem;
    margin: 2rem 0 1.2rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid #eee;
    color: #2c3e50;
}

.markdown-content :deep(h2) {
    font-size: 1.8rem;
    margin: 1.8rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #f0f0f0;
    color: #34495e;
}

.markdown-content :deep(h3) {
    font-size: 1.5rem;
    margin: 1.5rem 0 0.8rem;
    color: #3a3a3a;
}

.markdown-content :deep(h4) {
    font-size: 1.3rem;
    margin: 1.2rem 0 0.6rem;
    color: #444;
}

.markdown-content :deep(p) {
    margin-bottom: 1.2rem;
    line-height: 1.8;
    color: #333;
}

.markdown-content :deep(pre) {
    background-color: #2d333b;
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1.5rem 0;
    position: relative;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* 语言标签 */
.markdown-content :deep(pre)::before {
    content: attr(data-language);
    position: absolute;
    top: 0;
    right: 0;
    color: #c9d1d9;
    font-size: 0.75rem;
    background: #444c56;
    padding: 0.15rem 0.5rem;
    border-radius: 0 8px 0 4px;
    z-index: 2;
    opacity: 0.8;
}

/* 添加复制按钮 */
.markdown-content :deep(.hljs-copy-button) {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background-color: #444c56;
    border: none;
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    color: #c9d1d9;
    font-size: 0.8rem;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.3s;
}

.markdown-content :deep(pre:hover .hljs-copy-button) {
    opacity: 1;
}

.markdown-content :deep(.hljs-copy-button):hover {
    background-color: #545d68;
}

.markdown-content :deep(.hljs-copy-button.copied) {
    background-color: #388e3c;
}

.markdown-content :deep(code) {
    font-family: "JetBrains Mono", "Fira Code", Consolas, Monaco, "Courier New",
        monospace;
    font-size: 0.95em;
    padding: 0.15em 0.3em;
    border-radius: 3px;
    background-color: #f0f0f0;
}

.markdown-content :deep(pre code) {
    padding: 0;
    background-color: transparent;
    color: #e1e4e8;
    line-height: 1.5;
    border-radius: 0;
}

.markdown-content :deep(a) {
    color: #3498db;
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: all 0.2s;
}

.markdown-content :deep(a:hover) {
    color: #2980b9;
    border-bottom-color: #2980b9;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
    padding-left: 2rem;
    margin-bottom: 1.5rem;
}

.markdown-content :deep(li) {
    margin-bottom: 0.5rem;
}

.markdown-content :deep(blockquote) {
    border-left: 4px solid #3498db;
    padding-left: 1.2rem;
    color: #5a6a7a;
    margin: 1.5rem 0;
    background-color: #f8f9fa;
    padding: 0.8rem 1.2rem;
    border-radius: 0 4px 4px 0;
}

.markdown-content :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5rem 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    overflow: hidden;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
    border: 1px solid #e0e0e0;
    padding: 0.8rem;
    text-align: left;
}

.markdown-content :deep(th) {
    background-color: #f5f5f5;
    font-weight: 600;
    color: #333;
}

.markdown-content :deep(tr:nth-child(even)) {
    background-color: #f9f9f9;
}

.markdown-content :deep(tr:hover) {
    background-color: #f0f7ff;
}

.markdown-content :deep(img) {
    max-width: 100%;
    height: auto;
    margin: 1.5rem 0;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

/* 代码块头部语言标识 */
.markdown-content :deep(pre)::before {
    content: attr(data-language);
    position: absolute;
    top: 0;
    right: 0;
    color: #999;
    background-color: #373b43;
    padding: 0.2em 0.5em;
    border-bottom-left-radius: 4px;
    font-size: 0.75em;
    font-family: sans-serif;
}

.markdown-content :deep(.hljs-comment),
.markdown-content :deep(.hljs-quote) {
    color: #7e848a;
    font-style: italic;
}

.markdown-content :deep(.hljs-keyword),
.markdown-content :deep(.hljs-selector-tag) {
    color: #c678dd;
}

.markdown-content :deep(.hljs-string),
.markdown-content :deep(.hljs-doctag) {
    color: #98c379;
}

.markdown-content :deep(.hljs-number),
.markdown-content :deep(.hljs-literal) {
    color: #d19a66;
}

.markdown-content :deep(.hljs-variable),
.markdown-content :deep(.hljs-template-variable) {
    color: #d79b7b;
}

.markdown-content :deep(.hljs-title),
.markdown-content :deep(.hljs-function) {
    color: #61afef;
}

.error-rendering {
    color: #e83e8c;
    background-color: #fff1f2;
    padding: 1rem;
    border-radius: 6px;
    border-left: 4px solid #e83e8c;
    margin: 1rem 0;
}

/* 代码块复制按钮样式 */
.markdown-content :deep(.code-copy-btn) {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: #373b43;
    color: #ccc;
    border: none;
    border-radius: 4px;
    padding: 0.3em 0.6em;
    font-size: 0.75em;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
}

.markdown-content :deep(pre:hover .code-copy-btn) {
    opacity: 1;
}

.markdown-content :deep(.code-copy-btn:hover) {
    background: #4c5058;
    color: #fff;
}

/* 代码块行号样式 */
.markdown-content :deep(pre.with-line-numbers) {
    padding-left: 3.5rem; /* 为行号腾出空间 */
    position: relative;
}

.markdown-content :deep(.hljs-line-numbers) {
    position: absolute;
    top: 0;
    left: 0;
    width: 3rem;
    height: 100%;
    border-right: 1px solid #3e4c5a;
    background-color: #252d36;
    padding: 1rem 0.5rem;
    text-align: right;
    user-select: none;
    display: flex;
    flex-direction: column;
    z-index: 1;
}

.markdown-content :deep(.hljs-line-number) {
    font-family: monospace;
    font-size: 0.85em;
    color: #6e7681;
    display: block;
    line-height: 1.5;
    margin-bottom: 0;
}

/* 代码容器样式 */
.markdown-content :deep(.hljs-code-container) {
    position: relative;
    margin: 1.5rem 0;
}

.markdown-content :deep(.hljs-code) {
    font-family: "JetBrains Mono", "Fira Code", Consolas, Monaco, "Courier New",
        monospace;
    line-height: 1.5;
    padding: 0;
}

/* Mermaid图表样式 */
.mermaid-pre {
    padding: 0 !important;
    overflow: visible !important;
    background-color: transparent !important;
    margin: 2rem 0;
}

.mermaid-container {
    position: relative;
    min-height: 100px;
    width: 100%;
    margin: 1rem 0;
    overflow: auto;
    background: #f8f8f8;
    border-radius: 4px;
}

.chart-type-label {
    position: absolute;
    top: 4px;
    right: 4px;
    padding: 2px 6px;
    background: rgba(0, 0, 0, 0.6);
    color: white;
    font-size: 12px;
    border-radius: 3px;
    z-index: 10;
}

.mermaid {
    display: block;
    width: 100%;
    background-color: #1e1e2e;
    overflow: auto;
    padding: 1rem 0;
    text-align: center;
}

.mermaid svg {
    max-width: 100% !important;
    height: auto !important;
    display: inline-block !important;
    margin: 0 auto;
}

.mermaid-fixed {
    margin-top: 0.5rem;
    padding: 1rem;
    border: 1px dashed #4a5568;
    border-radius: 8px;
}

.mermaid-fixing-note {
    color: #68d391;
    font-style: italic;
    margin-bottom: 0.5rem;
    padding: 0.25rem 0.5rem;
    background-color: rgba(104, 211, 145, 0.1);
    border-radius: 4px;
}

.mermaid-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    background-color: #252b37;
    border-radius: 4px 4px 0 0;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #3e4c5a;
}

.mermaid-type {
    font-size: 0.85rem;
    color: #87a8d0;
    background-color: #304765;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-weight: 500;
}

.mermaid-type.flowchart {
    background-color: #304765;
    color: #87a8d0;
}
.mermaid-type.sequence {
    background-color: #2c503d;
    color: #8bd5b2;
}
.mermaid-type.class {
    background-color: #4b3c63;
    color: #c6b8e0;
}
.mermaid-type.gantt {
    background-color: #5f4339;
    color: #e2b9a8;
}
.mermaid-type.pie {
    background-color: #43596a;
    color: #a0c6df;
}
.mermaid-type.git {
    background-color: #53433a;
    color: #dfc4b3;
}
.mermaid-type.mindmap {
    background-color: #3d5a3a;
    color: #b4ddb1;
}
.mermaid-type.timeline {
    background-color: #524b31;
    color: #e2d8a7;
}
.mermaid-type.er {
    background-color: #523a50;
    color: #e3b3dc;
}
.mermaid-type.journey {
    background-color: #354858;
    color: #a9c7de;
}

.mermaid-special-marker {
    font-size: 0.75rem;
    color: #f8f9fa;
    background-color: #6d28d9;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    margin-left: 0.5rem;
    font-weight: 500;
}

.mermaid-source-btn {
    background-color: #384860;
    border: none;
    color: #c9d1d9;
    padding: 0.25rem 0.75rem;
    font-size: 0.85rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.mermaid-source-btn:hover {
    background-color: #455b79;
}

.mermaid-loading {
    color: #87a8d0;
    text-align: center;
    padding: 2rem 0;
    font-style: italic;
    background-color: #1e1e2e;
}

.mermaid-error {
    background-color: rgba(220, 53, 69, 0.1);
    color: #ff6b6b;
    padding: 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    border-left: 4px solid #ff6b6b;
}

.mermaid-error-code {
    background-color: #272935 !important;
    padding: 1rem !important;
    border-radius: 8px !important;
    margin: 0.5rem 0 !important;
    overflow-x: auto !important;
    color: #e0e0e0 !important;
    font-size: 0.9rem;
}

.mermaid-source {
    background-color: #272935;
    color: #e0e0e0;
    padding: 1rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    overflow-x: auto;
    font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
    font-size: 0.9rem;
    line-height: 1.5;
    white-space: pre-wrap;
}

/* SVG元素样式优化 */
.mermaid svg .label {
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
    font-size: 14px !important;
}

.mermaid svg .node rect,
.mermaid svg .node circle,
.mermaid svg .node polygon,
.mermaid svg .node path {
    stroke-width: 2px !important;
}

.mermaid svg .cluster rect {
    stroke-width: 1px !important;
    stroke-dasharray: 5 !important;
}

/* 特殊标记跳过通知样式 */
.special-marker-skipped {
    background-color: #f8f9fa !important;
    padding: 0 !important;
    border-radius: 8px;
    margin: 1.5rem 0;
    border: none !important;
}

.skip-special-marker-notice {
    display: flex;
    align-items: flex-start;
    padding: 1.5rem;
    background-color: #fff8e6;
    border: 1px solid #ffe58f;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.skip-icon {
    font-size: 2rem;
    color: #faad14;
    margin-right: 1rem;
    line-height: 1;
}

.skip-notice-text {
    flex: 1;
}

.skip-title {
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #d46b08;
    font-size: 1.1rem;
}

.skip-notice-text p {
    margin-bottom: 0.5rem;
    color: #5c5c5c;
}

.skip-notice-text a {
    color: #1890ff;
    text-decoration: none;
    font-weight: 500;
}

.skip-notice-text a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    .header {
        padding: 1.5rem;
    }

    .header h1 {
        font-size: 2rem;
    }

    .repo-input {
        flex-direction: column;
        gap: 0.8rem;
    }

    .repo-input button {
        width: 100%;
        padding: 14px;
    }

    .result-header {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
    }

    .result-header div {
        display: flex;
        width: 100%;
        gap: 0.5rem;
    }

    .copy-button,
    .download-button,
    .debug-button {
        flex: 1;
        margin-left: 0;
        text-align: center;
        padding: 0.6rem 0;
    }
}
</style>
