const express = require("express");
const cors = require("cors");
const bodyParser = require("body-parser");
const axios = require("axios");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const { Server } = require("socket.io");
const fs = require("fs");
const crypto = require("crypto");
const util = require("util");

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: process.env.FRONTEND_URL || "http://localhost:8000",
        methods: ["GET", "POST"],
        credentials: true,
    },
});

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, "../../frontend/dist")));

// 解析器路径
const PARSER_PATH = path.join(__dirname, "../python/parse_deepwiki.py");
const PYTHON_PATH = process.env.CONDA_PYTHON_PATH || "python";
const TEMP_DIR = path.join(__dirname, "../../temp");

// 确保临时目录存在
if (!fs.existsSync(TEMP_DIR)) {
    fs.mkdirSync(TEMP_DIR, { recursive: true });
}

// 活跃的解析任务
const activeTasks = new Map();

// 生成唯一的任务ID
function generateTaskId() {
    return crypto.randomBytes(16).toString("hex");
}

// 解析DeepWiki并返回Markdown
async function parseDeepWiki(url, taskId, socketId) {
    return new Promise((resolve, reject) => {
        console.log(`[Task: ${taskId}] 开始解析: ${url}`);

        // 创建输出文件路径
        const outputPath = path.join(TEMP_DIR, `${taskId}.md`);

        // 启动Python解析器进程
        const pythonProcess = spawn(PYTHON_PATH, [PARSER_PATH, url]);

        // 保存进程引用以便可以终止
        activeTasks.set(taskId, {
            process: pythonProcess,
            status: "running",
            url: url,
            socketId: socketId,
            stage: "启动",
            progress: 0,
            startTime: Date.now(),
            outputPath: outputPath,
        });

        let markdown = "";
        let errorOutput = "";

        // 处理标准输出
        let isCollectingMarkdown = false;
        let stdoutBuffer = "";
        let markdownLines = [];

        pythonProcess.stdout.on("data", (data) => {
            // 添加到缓冲区
            stdoutBuffer += data.toString();

            // 检查是否有完整的行
            let lines = stdoutBuffer.split("\n");
            // 最后一行可能不完整，保留在缓冲区
            stdoutBuffer = lines.pop() || "";

            // 处理每一行
            for (const line of lines) {
                try {
                    // 检查是否是Markdown内容的开始
                    if (line.includes("--------- Markdown 内容 ---------")) {
                        isCollectingMarkdown = true;
                        markdownLines = []; // 初始化Markdown收集数组
                        console.log(`[Task: ${taskId}] 开始收集Markdown内容`);
                        continue; // 跳过此行
                    }

                    // 检查是否是Markdown内容的结束
                    if (line.includes("--------- Markdown 结束 ---------")) {
                        isCollectingMarkdown = false;
                        markdown = markdownLines.join("\n");
                        console.log(
                            `[Task: ${taskId}] Markdown内容收集完成，共 ${markdown.length} 字符`
                        );
                        continue; // 跳过此行
                    }

                    // 如果正在收集Markdown内容
                    if (isCollectingMarkdown) {
                        markdownLines.push(line);
                        continue;
                    }

                    console.log(`[Python] ${line}`);

                    // 检查是否是 [stage] percentage%: message 格式的进度信息
                    const progressMatch = line.match(
                        /\[(.*?)\]\s*(\d+)%:\s*(.*)/
                    );
                    if (progressMatch) {
                        const stage = progressMatch[1];
                        const progress = parseInt(progressMatch[2], 10);
                        const message = progressMatch[3];

                        // 更新任务状态
                        const task = activeTasks.get(taskId);
                        if (task) {
                            task.stage = stage;
                            task.progress = progress;
                            task.message = message;

                            // 通过Socket.IO发送进度更新
                            io.to(socketId).emit(`task:${taskId}:progress`, {
                                stage: stage,
                                progress: progress,
                                message: message,
                            });
                        }
                    }
                } catch (err) {
                    console.error(`[Task: ${taskId}] 解析进度信息出错:`, err);
                }
            }
        });

        // 处理标准错误
        pythonProcess.stderr.on("data", (data) => {
            errorOutput += data.toString();
            console.error(`[Python Error] ${data.toString()}`);
        });

        // 处理进程结束
        pythonProcess.on("close", (code) => {
            const task = activeTasks.get(taskId);
            if (task) {
                task.status = code === 0 ? "completed" : "failed";
                task.endTime = Date.now();
                task.error = code !== 0 ? errorOutput : null;
            }

            if (code === 0) {
                // 解析成功
                console.log(`[Task: ${taskId}] 解析成功`);

                // 检查markdown内容是否有效
                if (!markdown || markdown.trim() === "") {
                    console.error(
                        `[Task: ${taskId}] 警告：收集到的Markdown内容为空!`
                    );
                    task.error = "解析成功，但Markdown内容为空";
                    io.to(socketId).emit(`task:${taskId}:failed`, {
                        error: "解析成功，但Markdown内容为空，请重试",
                    });
                    reject(new Error("解析成功，但Markdown内容为空"));
                    return;
                }

                console.log(
                    `[Task: ${taskId}] 写入Markdown到文件，内容长度: ${markdown.length}`
                );

                try {
                    // 保存Markdown到文件
                    fs.writeFileSync(outputPath, markdown, {
                        encoding: "utf8",
                    });

                    // 检查文件是否成功写入并有内容
                    const fileStats = fs.statSync(outputPath);
                    console.log(
                        `[Task: ${taskId}] 文件写入完成，大小: ${fileStats.size} 字节`
                    );

                    if (fileStats.size === 0) {
                        throw new Error("文件写入失败，文件大小为0");
                    }

                    // 通知前端解析完成
                    io.to(socketId).emit(`task:${taskId}:completed`, {
                        message: "解析成功",
                    });

                    resolve(markdown);
                } catch (err) {
                    console.error(`[Task: ${taskId}] 文件写入错误:`, err);
                    task.error = `文件写入错误: ${err.message}`;
                    io.to(socketId).emit(`task:${taskId}:failed`, {
                        error: `文件写入错误: ${err.message}`,
                    });
                    reject(err);
                }
            } else {
                // 解析失败
                console.error(`[Task: ${taskId}] 解析失败，错误码: ${code}`);
                console.error(errorOutput);

                // 通知前端解析失败
                io.to(socketId).emit(`task:${taskId}:failed`, {
                    error: `解析失败: ${errorOutput || "未知错误"}`,
                });

                reject(new Error(`解析失败: ${errorOutput || "未知错误"}`));
            }
        });
    });
}

// API 路由
app.post("/api/parse", async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                error: "请提供URL参数",
            });
        }

        // 获取Socket.io客户端ID
        const socketId = req.headers["x-socket-id"] || "unknown";

        // 生成任务ID
        const taskId = generateTaskId();

        console.log(`[API] 收到解析请求: ${url}, 任务ID: ${taskId}`);

        // 异步启动解析任务
        parseDeepWiki(url, taskId, socketId).catch((err) => {
            console.error(`[Task: ${taskId}] 解析出错:`, err);
        });

        // 立即返回任务ID
        res.json({
            taskId: taskId,
            message: "解析任务已启动",
        });
    } catch (err) {
        console.error("[API Error] 解析请求失败:", err);
        res.status(500).json({
            error: "服务器内部错误",
        });
    }
});

// 获取任务状态
app.get("/api/task/:taskId", (req, res) => {
    const { taskId } = req.params;

    const task = activeTasks.get(taskId);

    if (!task) {
        return res.status(404).json({
            error: "找不到指定的任务",
        });
    }

    // 返回任务信息（不包含进程对象）
    const { process, ...taskInfo } = task;
    res.json(taskInfo);
});

// 获取解析后的Markdown
app.get("/api/markdown/:taskId", (req, res) => {
    const { taskId } = req.params;

    console.log(`[API] 收到获取Markdown请求，任务ID: ${taskId}`);

    const task = activeTasks.get(taskId);

    if (!task) {
        console.warn(`[API] 找不到任务: ${taskId}`);
        return res.status(404).json({
            error: "找不到指定的任务",
        });
    }

    if (task.status !== "completed") {
        console.warn(`[API] 任务尚未完成: ${taskId}，当前状态: ${task.status}`);
        return res.status(400).json({
            error: "任务尚未完成",
            status: task.status,
        });
    }

    // 读取保存的Markdown文件
    try {
        console.log(`[API] 读取Markdown文件: ${task.outputPath}`);

        // 检查文件是否存在
        if (!fs.existsSync(task.outputPath)) {
            throw new Error(`文件不存在: ${task.outputPath}`);
        }

        // 检查文件大小
        const fileStats = fs.statSync(task.outputPath);
        console.log(`[API] Markdown文件大小: ${fileStats.size} 字节`);

        if (fileStats.size === 0) {
            throw new Error("Markdown文件为空");
        }

        const markdown = fs.readFileSync(task.outputPath, "utf-8");
        console.log(`[API] 成功读取Markdown内容，长度: ${markdown.length}`);

        if (!markdown || markdown.trim() === "") {
            throw new Error("读取的Markdown内容为空");
        }

        res.json({
            markdown: markdown,
        });
    } catch (err) {
        console.error(`[API Error] 读取Markdown文件失败: ${err.message}`);
        res.status(500).json({
            error: `读取Markdown内容失败: ${err.message}`,
        });
    }
});

// 取消任务
app.delete("/api/task/:taskId", (req, res) => {
    const { taskId } = req.params;

    const task = activeTasks.get(taskId);

    if (!task) {
        return res.status(404).json({
            error: "找不到指定的任务",
        });
    }

    // 终止进程
    if (task.process && !task.process.killed) {
        task.process.kill();
        task.status = "cancelled";

        // 通知前端任务已取消
        io.to(task.socketId).emit(`task:${taskId}:failed`, {
            error: "任务已取消",
        });
    }

    res.json({
        message: "任务已取消",
    });
});

// Socket.io 连接处理
io.on("connection", (socket) => {
    console.log(`客户端连接: ${socket.id}`);

    // 保存socketId，以便后续API请求可以使用
    socket.on("register", (data) => {
        socket.data = { ...socket.data, ...data };
        console.log(`客户端 ${socket.id} 注册信息:`, socket.data);
    });

    socket.on("disconnect", () => {
        console.log(`客户端断开连接: ${socket.id}`);
        // 清理该socket的任务
        for (const [taskId, task] of activeTasks.entries()) {
            if (task.socketId === socket.id && task.status === "running") {
                // 终止相关进程
                if (task.process && !task.process.killed) {
                    task.process.kill();
                    task.status = "cancelled";
                }
                console.log(`清理任务: ${taskId}`);
            }
        }
    });
});

// 调试终端点 - 直接解析测试URL
app.get("/api/test-parse", async (req, res) => {
    try {
        const testUrl =
            req.query.url || "https://deepwiki.com/Arshtyi/LaTeX-Templates";

        console.log(`[API] 调试：直接解析 ${testUrl}`);

        // 直接使用子进程执行解析脚本
        const pythonProcess = spawn(PYTHON_PATH, [PARSER_PATH, testUrl]);

        let output = "";
        let markdown = "";
        let isCollectingMarkdown = false;
        let markdownLines = [];

        pythonProcess.stdout.on("data", (data) => {
            const text = data.toString();
            output += text;

            // 处理Markdown内容
            const lines = text.split("\n");

            for (const line of lines) {
                if (line.includes("--------- Markdown 内容 ---------")) {
                    isCollectingMarkdown = true;
                    continue;
                } else if (line.includes("--------- Markdown 结束 ---------")) {
                    isCollectingMarkdown = false;
                    continue;
                }

                if (isCollectingMarkdown) {
                    markdownLines.push(line);
                }
            }
        });

        pythonProcess.stderr.on("data", (data) => {
            output += `[ERROR] ${data.toString()}`;
        });

        pythonProcess.on("close", (code) => {
            markdown = markdownLines.join("\n");

            res.json({
                success: code === 0,
                exitCode: code,
                output,
                markdownLength: markdown.length,
                markdownFirstLine: markdown.split("\n")[0] || "无内容",
                markdown,
            });
        });
    } catch (err) {
        console.error("[API Error] 测试解析失败:", err);
        res.status(500).json({
            error: `测试解析失败: ${err.message}`,
        });
    }
});

// 文件查看和管理API
app.get("/api/files", (req, res) => {
    try {
        // 获取temp目录下所有文件
        const files = fs.readdirSync(TEMP_DIR);

        // 收集文件信息
        const fileInfos = files.map((filename) => {
            const filePath = path.join(TEMP_DIR, filename);
            const stats = fs.statSync(filePath);
            return {
                name: filename,
                size: stats.size,
                created: stats.birthtime,
                modified: stats.mtime,
            };
        });

        res.json({
            files: fileInfos,
        });
    } catch (err) {
        console.error("[API Error] 获取文件列表失败:", err);
        res.status(500).json({
            error: `获取文件列表失败: ${err.message}`,
        });
    }
});

app.get("/api/file/:filename", (req, res) => {
    try {
        const { filename } = req.params;
        const filePath = path.join(TEMP_DIR, filename);

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                error: "文件不存在",
            });
        }

        const content = fs.readFileSync(filePath, "utf-8");
        res.json({
            filename,
            content,
            size: content.length,
        });
    } catch (err) {
        console.error("[API Error] 读取文件失败:", err);
        res.status(500).json({
            error: `读取文件失败: ${err.message}`,
        });
    }
});

// 处理前端路由 - 确保这是最后一个路由处理器
app.get("/*", (req, res) => {
    res.sendFile(path.join(__dirname, "../../frontend/dist/index.html"));
});

// 启动服务器
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`服务器运行在端口 ${PORT}`);
});

// 优雅退出：清理所有活跃任务
process.on("SIGINT", () => {
    console.log("正在关闭服务器...");

    // 终止所有Python进程
    for (const [taskId, task] of activeTasks.entries()) {
        if (task.process && !task.process.killed) {
            console.log(`终止任务: ${taskId}`);
            task.process.kill();
        }
    }

    // 关闭服务器
    server.close(() => {
        console.log("服务器已关闭");
        process.exit(0);
    });
});
