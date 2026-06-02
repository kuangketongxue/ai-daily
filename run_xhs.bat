@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   AI日报 x 小红书 — 一键生成
echo ========================================
echo.

echo [1/4] 采集数据...
python scripts/collect.py
if errorlevel 1 (
    echo [WARN] 采集出错，尝试使用已有数据继续
)

echo.
echo [2/4] AI筛选...
python scripts/process.py
if errorlevel 1 (
    echo [WARN] AI筛选出错，尝试使用原始数据继续
)

echo.
echo [3/4] 生成图片卡片...
python xhs/generate_cards.py

echo.
echo [4/4] 生成文案...
python xhs/generate_caption.py

echo.
echo ========================================
echo   全部完成！
echo ========================================
echo.
echo 查看 output\xhs\%date:~0,4%-%date:~5,2%-%date:~8,2%\ 文件夹
echo 确认内容后运行: python xhs/publish.py
echo.
pause
