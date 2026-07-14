@echo off
echo === 搜索 Python ===

REM 常见 Python 安装位置
for %%p in (
    "C:\Users\%USERNAME%\anaconda3\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Python313\python.exe"
) do (
    if exist %%p (
        echo 找到: %%p
        %%p --version
    )
)

echo.
echo Node:
node --version
echo.
pause
