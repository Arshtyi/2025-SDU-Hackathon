#!/bin/bash

# GitHub DeepWiki Analyzer 启动脚本
# 作用：启动前端和后端服务，并处理端口占用问题

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 前端和后端目录
FRONTEND_DIR="$PROJECT_ROOT/frontend"
NODEJS_DIR="$PROJECT_ROOT/backend/nodejs"
PYTHON_DIR="$PROJECT_ROOT/backend/python"
PYTHON_ENV="$PROJECT_ROOT/.conda"

# 前端和后端端口
FRONTEND_PORT=8000
BACKEND_PORT=3000

# 检查端口是否被占用并释放
check_and_free_port() {
    local port=$1
    local service_name=$2
    
    echo -e "${BLUE}检查端口 $port 是否被占用...${NC}"
    
    if lsof -i:$port > /dev/null 2>&1; then
        echo -e "${YELLOW}端口 $port 已被占用. 尝试释放...${NC}"
        
        # 查找占用端口的PID
        local pid=$(lsof -ti:$port)
        
        # 显示进程信息
        echo -e "${YELLOW}占用端口的进程信息:${NC}"
        ps -p $pid -o pid,ppid,cmd
        
        # 询问用户是否要终止进程
        echo -ne "${YELLOW}是否终止占用端口 $port 的进程? [Y/n] ${NC}"
        read -r kill_process
        
        if [[ $kill_process =~ ^[Nn]$ ]]; then
            echo -e "${RED}无法启动 $service_name，端口 $port 被占用.${NC}"
            return 1
        else
            echo -e "${YELLOW}正在终止进程 (PID: $pid)...${NC}"
            kill -15 $pid
            
            # 等待端口释放
            local counter=0
            while lsof -i:$port > /dev/null 2>&1; do
                if [ $counter -ge 10 ]; then
                    echo -e "${RED}无法释放端口 $port，尝试强制终止进程...${NC}"
                    kill -9 $pid
                    sleep 1
                    if lsof -i:$port > /dev/null 2>&1; then
                        echo -e "${RED}无法释放端口 $port，请手动终止占用的进程.${NC}"
                        return 1
                    else
                        break
                    fi
                fi
                
                echo -e "${YELLOW}等待端口释放...${NC}"
                sleep 1
                ((counter++))
            done
            
            echo -e "${GREEN}端口 $port 已成功释放.${NC}"
        fi
    else
        echo -e "${GREEN}端口 $port 可用.${NC}"
    fi
    
    return 0
}

# 确保Python环境已创建
setup_conda_env() {
    echo -e "${BLUE}检查Conda环境...${NC}"
    
    # 检查conda是否已安装
    if ! command -v conda &> /dev/null; then
        echo -e "${RED}未检测到conda，请安装Miniconda或Anaconda.${NC}"
        exit 1
    fi
    
    # 确定环境名称
    local env_name=".conda"
    
    # 检查conda环境是否存在
    if ! conda env list | grep -q "^$env_name"; then
        echo -e "${YELLOW}创建新的conda环境 '$env_name'...${NC}"
        conda create -y -p "$PYTHON_ENV" python=3.10
    fi
    
    # 安装必要的Python包
    echo -e "${BLUE}安装Python依赖...${NC}"
    
    # 激活conda环境并安装依赖
    eval "$(conda shell.bash hook)"
    conda activate "$PYTHON_ENV"
    
    # 安装依赖
    pip install requests beautifulsoup4 urllib3 lxml
    
    echo -e "${GREEN}Python环境设置完成.${NC}"
}

# 安装Node.js依赖
setup_node_dependencies() {
    echo -e "${BLUE}安装Node.js后端依赖...${NC}"
    cd "$NODEJS_DIR"
    npm install
    
    echo -e "${BLUE}安装前端依赖...${NC}"
    cd "$FRONTEND_DIR"
    npm install
    
    echo -e "${GREEN}Node.js依赖安装完成.${NC}"
}

# 构建前端
build_frontend() {
    echo -e "${BLUE}构建前端应用...${NC}"
    cd "$FRONTEND_DIR"
    npm run build
    
    echo -e "${GREEN}前端构建完成.${NC}"
}

# 启动后端服务
start_backend() {
    echo -e "${BLUE}启动Node.js后端服务...${NC}"
    cd "$NODEJS_DIR"
    
    # 设置conda环境路径
    export CONDA_PYTHON_PATH="$PYTHON_ENV/bin/python"
    
    # 启动Node.js服务
    PORT="$BACKEND_PORT" nohup npm start > "$PROJECT_ROOT/backend.log" 2>&1 &
    BACKEND_PID=$!
    
    echo -e "${GREEN}后端服务已在端口 $BACKEND_PORT 启动，PID: $BACKEND_PID${NC}"
    echo "后端日志: $PROJECT_ROOT/backend.log"
}

# 启动前端服务（开发模式）
start_frontend_dev() {
    echo -e "${BLUE}启动前端开发服务器...${NC}"
    cd "$FRONTEND_DIR"
    
    # 设置后端API地址
    export VUE_APP_BACKEND_URL="http://localhost:$BACKEND_PORT"
    export VUE_APP_API_URL="http://localhost:$BACKEND_PORT/api"
    
    # 启动Vue开发服务器
    PORT="$FRONTEND_PORT" nohup npm run serve > "$PROJECT_ROOT/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}前端服务已在端口 $FRONTEND_PORT 启动，PID: $FRONTEND_PID${NC}"
    echo "前端日志: $PROJECT_ROOT/frontend.log"
}

# 提供停止服务函数
stop_services() {
    echo -e "${BLUE}停止所有服务...${NC}"
    
    # 停止后端
    if lsof -i:$BACKEND_PORT > /dev/null 2>&1; then
        local backend_pid=$(lsof -ti:$BACKEND_PORT)
        echo -e "${YELLOW}停止后端服务 (PID: $backend_pid)...${NC}"
        kill -15 $backend_pid
    fi
    
    # 停止前端
    if lsof -i:$FRONTEND_PORT > /dev/null 2>&1; then
        local frontend_pid=$(lsof -ti:$FRONTEND_PORT)
        echo -e "${YELLOW}停止前端服务 (PID: $frontend_pid)...${NC}"
        kill -15 $frontend_pid
    fi
    
    echo -e "${GREEN}所有服务已停止.${NC}"
}

# 显示项目状态
show_status() {
    echo -e "${BLUE}项目状态:${NC}"
    
    # 检查后端
    if lsof -i:$BACKEND_PORT > /dev/null 2>&1; then
        local backend_pid=$(lsof -ti:$BACKEND_PORT)
        echo -e "${GREEN}✓ 后端服务正在运行 (PID: $backend_pid)${NC}"
    else
        echo -e "${RED}✗ 后端服务未运行${NC}"
    fi
    
    # 检查前端
    if lsof -i:$FRONTEND_PORT > /dev/null 2>&1; then
        local frontend_pid=$(lsof -ti:$FRONTEND_PORT)
        echo -e "${GREEN}✓ 前端服务正在运行 (PID: $frontend_pid)${NC}"
    else
        echo -e "${RED}✗ 前端服务未运行${NC}"
    fi
    
    echo -e "\n${BLUE}访问地址:${NC}"
    echo -e "前端: ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "后端API: ${GREEN}http://localhost:$BACKEND_PORT/api${NC}"
}

# 处理命令行参数
case "$1" in
    start)
        # 检查并释放端口
        check_and_free_port $FRONTEND_PORT "前端" || exit 1
        check_and_free_port $BACKEND_PORT "后端" || exit 1
        
        # 设置环境
        setup_conda_env
        setup_node_dependencies
        
        # 启动服务
        start_backend
        start_frontend_dev
        
        # 显示状态
        echo ""
        show_status
        ;;
        
    stop)
        stop_services
        ;;
        
    restart)
        stop_services
        sleep 2
        
        # 检查并释放端口
        check_and_free_port $FRONTEND_PORT "前端" || exit 1
        check_and_free_port $BACKEND_PORT "后端" || exit 1
        
        # 启动服务
        start_backend
        start_frontend_dev
        
        # 显示状态
        echo ""
        show_status
        ;;
        
    status)
        show_status
        ;;
        
    build)
        setup_node_dependencies
        build_frontend
        echo -e "${GREEN}项目构建完成.${NC}"
        ;;
        
    *)
        echo -e "${BLUE}GitHub DeepWiki 解析器${NC} - 启动脚本"
        echo ""
        echo "用法: $0 [命令]"
        echo ""
        echo "命令:"
        echo "  start    - 启动前端和后端服务"
        echo "  stop     - 停止所有服务"
        echo "  restart  - 重启所有服务"
        echo "  status   - 显示服务状态"
        echo "  build    - 构建前端项目"
        echo ""
        echo "示例:"
        echo "  $0 start    # 启动所有服务"
        ;;
esac
