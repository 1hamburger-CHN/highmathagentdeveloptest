@echo off
chcp 65001 >nul
echo ============================================
echo   苏格拉底教练 2.0 — 复变函数辅导系统
echo ============================================
echo.

docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Docker，请先安装 Docker Desktop
    echo 下载: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

if not exist "backend\.env" (
    echo [提示] 从 .env.example 创建配置文件...
    copy "backend\.env.example" "backend\.env"
    echo 请编辑 backend\.env 填入 API 密钥后重新运行
    pause
    exit /b 1
)

echo 构建并启动服务...
docker compose up -d --build

echo.
echo 启动完成！访问 http://localhost
echo 停止服务: docker compose down
pause
