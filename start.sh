#!/bin/bash
# ==================================================
#  social-auto-upload 一键重启脚本 (macOS/Linux)
#  同时启动后端(Flask) 和前端(Vue/Vite)
# ==================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=5409
FRONTEND_PORT=5173
VENV_DIR="$SCRIPT_DIR/.venv"

# --------------- 颜色 ---------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --------------- 清理旧进程 ---------------
cleanup_old() {
    echo -e "${YELLOW}[清理] 检查端口 $BACKEND_PORT 和 $FRONTEND_PORT 上的旧进程...${NC}"

    # 后端端口
    local backend_pid=$(lsof -ti :$BACKEND_PORT 2>/dev/null || true)
    if [ -n "$backend_pid" ]; then
        echo -e "${YELLOW}  → 发现后端进程 PID: $backend_pid，正在终止...${NC}"
        kill -9 $backend_pid 2>/dev/null || true
        echo -e "${GREEN}  ✓ 后端进程已终止${NC}"
    fi

    # 前端端口
    local frontend_pid=$(lsof -ti :$FRONTEND_PORT 2>/dev/null || true)
    if [ -n "$frontend_pid" ]; then
        echo -e "${YELLOW}  → 发现前端进程 PID: $frontend_pid，正在终止...${NC}"
        kill -9 $frontend_pid 2>/dev/null || true
        echo -e "${GREEN}  ✓ 前端进程已终止${NC}"
    fi

    echo ""
}

# --------------- 检查虚拟环境 ---------------
check_venv() {
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${RED}[错误] 未找到虚拟环境: $VENV_DIR${NC}"
        echo -e "${YELLOW}  请先运行: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
        exit 1
    fi
    echo -e "${GREEN}[venv] 激活虚拟环境${NC}"
    source "$VENV_DIR/bin/activate"
    echo ""
}

# --------------- 检查前端依赖 ---------------
check_frontend() {
    if [ ! -d "$SCRIPT_DIR/sau_frontend/node_modules" ]; then
        echo -e "${YELLOW}[前端] node_modules 不存在，正在安装依赖...${NC}"
        cd "$SCRIPT_DIR/sau_frontend"
        npm install
        cd "$SCRIPT_DIR"
        echo -e "${GREEN}[前端] 依赖安装完成${NC}"
    fi
}

# --------------- 清理函数 ---------------
pids_to_kill=""
cleanup() {
    echo ""
    echo -e "${YELLOW}[退出] 正在停止所有服务...${NC}"
    if [ -n "$pids_to_kill" ]; then
        kill $pids_to_kill 2>/dev/null || true
        wait $pids_to_kill 2>/dev/null || true
    fi
    echo -e "${GREEN}[退出] 所有服务已停止${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# =============== 主流程 ===============
echo ""
echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}  social-auto-upload 一键启动${NC}"
echo -e "${CYAN}==================================================${NC}"
echo ""

cleanup_old
check_venv
check_frontend

# --- 启动后端 ---
echo -e "${GREEN}[后端] 启动 Flask 服务 (端口 $BACKEND_PORT)...${NC}"
cd "$SCRIPT_DIR"
python sau_backend.py &
backend_pid=$!
pids_to_kill="$pids_to_kill $backend_pid"
echo -e "${GREEN}  → 后端 PID: $backend_pid${NC}"

# 等待后端就绪
sleep 2

# --- 启动前端 ---
echo -e "${GREEN}[前端] 启动 Vite 开发服务器 (端口 $FRONTEND_PORT)...${NC}"
cd "$SCRIPT_DIR/sau_frontend"
npm run dev -- --host 0.0.0.0 &
frontend_pid=$!
pids_to_kill="$pids_to_kill $frontend_pid"
echo -e "${GREEN}  → 前端 PID: $frontend_pid${NC}"

cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}==================================================${NC}"
echo -e "${GREEN}  后端:  http://localhost:$BACKEND_PORT${NC}"
echo -e "${GREEN}  前端:  http://localhost:$FRONTEND_PORT${NC}"
echo -e "${YELLOW}  按 Ctrl+C 停止所有服务${NC}"
echo -e "${CYAN}==================================================${NC}"
echo ""

# 等待任意子进程退出或被信号终止
wait
