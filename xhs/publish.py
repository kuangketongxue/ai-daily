"""
AI日报 × 小红书 — 半自动发布脚本
调用 social-auto-upload 发布到小红书
首次使用需扫码登录，之后自动填入内容，人工确认后发布
"""
import os
import sys
import glob
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'xhs')


def publish(date_str=None):
    """半自动发布到小红书"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    output_dir = os.path.join(OUTPUT_DIR, date_str)

    # 检查输出目录
    if not os.path.exists(output_dir):
        print(f"[ERR] 未找到 {date_str} 的内容，请先运行 generate_cards.py 和 generate_caption.py")
        return False

    # 收集图片（按文件名排序）
    images = sorted(glob.glob(os.path.join(output_dir, 'card_*.png')))
    if not images:
        print("[ERR] 未找到卡片图片")
        return False

    # 读取文案
    caption_path = os.path.join(output_dir, 'caption.txt')
    if os.path.exists(caption_path):
        with open(caption_path, 'r', encoding='utf-8') as f:
            caption = f.read()
    else:
        caption = f"AI日报 | {date_str}"

    # 提取标题（文案第一行）
    title = caption.split('\n')[0].strip()

    print(f"=== 小红书发布 {date_str} ===")
    print(f"  标题: {title}")
    print(f"  图片: {len(images)} 张")
    print(f"  文案: {len(caption)} 字")

    # 方案1: 使用 social-auto-upload（如果已安装）
    try:
        from social_auto_upload.auto_upload import upload_image

        print("\n  正在打开小红书...")
        print("  ⚠️ 首次使用需要扫码登录，请关注浏览器窗口")

        result = upload_image(
            title=title,
            content=caption,
            images=images,
            account_type='xhs',  # 小红书
        )

        if result:
            print("\n  ✅ 发布成功！")
            return True
        else:
            print("\n  ❌ 发布失败或已取消")
            return False

    except ImportError:
        print("\n  ⚠️ social-auto-upload 未安装")
        print("  安装命令: pip install social-auto-upload && playwright install chromium")
        print("\n  手动发布步骤:")
        print(f"  1. 打开小红书创作中心")
        print(f"  2. 新建图文笔记")
        print(f"  3. 标题: {title}")
        print(f"  4. 上传图片: {output_dir}/card_*.png")
        print(f"  5. 粘贴文案: {caption_path}")

        # 打开输出目录
        os.startfile(output_dir)
        print(f"\n  📂 已打开文件夹: {output_dir}")
        return False

    except Exception as e:
        print(f"\n  [ERR] 发布出错: {e}")
        return False


if __name__ == '__main__':
    date = sys.argv[1] if len(sys.argv) > 1 else None
    publish(date)
