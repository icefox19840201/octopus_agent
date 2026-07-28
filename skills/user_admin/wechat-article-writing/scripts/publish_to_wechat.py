#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章发布脚本
将创作完成的文章发布到微信公众号草稿箱
"""
import os
import sys
import json
import re
import base64
import argparse
import requests
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import tempfile
# 微信公众号配置
APP_ID = "wx549261365212cb59"
APP_SECRET = "8f5f767c1421ed085e603c71169f3edb"

# 微信API接口
WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"


def get_access_token():
    """获取微信access_token"""
    url = f"{WECHAT_API_BASE}/token"
    params = {
        "grant_type": "client_credential",
        "appid": APP_ID,
        "secret": APP_SECRET
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if "access_token" in data:
            return data["access_token"]
        else:
            print(f"获取access_token失败: {data.get('errmsg', '未知错误')}")
            return None
    except Exception as e:
        print(f"请求access_token时出错: {str(e)}")
        return None


def upload_image(access_token, image_path):
    """上传图片到微信素材库"""
    url = f"{WECHAT_API_BASE}/media/uploadimg"
    params = {"access_token": access_token}
    
    try:
        with open(image_path, 'rb') as f:
            files = {'media': f}
            response = requests.post(url, params=params, files=files, timeout=30)
            data = response.json()
            
            if "url" in data:
                return data["url"]
            else:
                print(f"上传图片失败: {data.get('errmsg', '未知错误')}")
                return None
    except Exception as e:
        print(f"上传图片时出错: {str(e)}")
        return None


def check_and_resize_image(image_path, max_size=(900, 500), max_file_size=2*1024*1024, is_thumb=False):
    """
    检查并调整图片尺寸和大小
    
    参数:
        image_path: 图片路径
        max_size: 最大尺寸 (宽, 高)
        max_file_size: 最大文件大小（字节）
        is_thumb: 是否为缩略图（微信缩略图要求1:1正方形）
    
    返回:
        调整后的图片路径（如果调整了）或原路径
    """
    try:
        from PIL import Image
        import tempfile
        
        img = Image.open(image_path)
        original_size = img.size
        original_format = img.format
        
        # 如果是缩略图，需要裁剪为1:1正方形
        if is_thumb:
            # 微信缩略图建议尺寸 300x300 或 200x200
            target_size = (300, 300)
            
            # 计算裁剪区域（居中裁剪）
            width, height = img.size
            if width != height:
                min_dim = min(width, height)
                left = (width - min_dim) // 2
                top = (height - min_dim) // 2
                right = left + min_dim
                bottom = top + min_dim
                img = img.crop((left, top, right, bottom))
                print(f"封面图已裁剪为1:1正方形: {img.size}")
            
            # 调整尺寸
            if img.width > target_size[0]:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
        else:
            # 普通图片，使用thumbnail保持比例
            if img.width > max_size[0] or img.height > max_size[1]:
                print(f"图片尺寸 {original_size} 超过限制 {max_size}，正在调整...")
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 保存到临时文件
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"wechat_thumb_{os.path.basename(image_path)}")
        
        # 转换为RGB（如果是RGBA）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            original_format = 'JPEG'
        
        # 保存并检查大小
        quality = 95
        while quality > 50:
            if original_format in ['JPEG', 'JPG']:
                img.save(temp_path, 'JPEG', quality=quality)
            else:
                img.save(temp_path, 'JPEG', quality=quality)
            
            file_size = os.path.getsize(temp_path)
            if file_size <= max_file_size:
                print(f"图片已调整: {img.size}, 文件大小: {file_size} bytes")
                return temp_path
            
            quality -= 10
        
        print(f"警告: 无法将图片压缩到 {max_file_size} bytes 以下")
        return temp_path
        
    except ImportError:
        print("未安装PIL库，无法调整图片尺寸")
        return image_path
    except Exception as e:
        print(f"调整图片时出错: {str(e)}")
        return image_path


def upload_thumb_media(access_token, image_path):
    """上传缩略图到微信素材库（用于封面图）"""
    url = f"{WECHAT_API_BASE}/media/upload"
    params = {
        "access_token": access_token,
        "type": "thumb"
    }
    
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            print(f"封面图文件不存在: {image_path}")
            return None
        
        # 检查文件格式
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            print(f"封面图格式不支持: {ext}，仅支持jpg/jpeg/png/gif/bmp")
            return None
        
        # 检查并调整图片尺寸（微信缩略图要求1:1正方形，最大2MB）
        processed_path = check_and_resize_image(image_path, max_size=(300, 300), max_file_size=2*1024*1024, is_thumb=True)
        
        # 检查文件大小
        file_size = os.path.getsize(processed_path)
        if file_size > 2 * 1024 * 1024:
            print(f"封面图文件过大: {file_size} bytes，最大支持2MB")
            return None
        
        with open(processed_path, 'rb') as f:
            files = {'media': f}
            response = requests.post(url, params=params, files=files, timeout=30)
            data = response.json()
            
            print(f"封面图上传响应: {data}")
            
            # 微信返回的是 thumb_media_id
            if "thumb_media_id" in data:
                return data["thumb_media_id"]
            elif "media_id" in data:
                return data["media_id"]
            else:
                print(f"上传缩略图失败: {data.get('errmsg', '未知错误')}")
                return None
    except Exception as e:
        print(f"上传缩略图时出错: {str(e)}")
        return None


def create_draft(access_token, title, content, author="", digest="", thumb_media_id=""):
    """
    创建草稿箱文章
    
    参数:
        access_token: 微信access_token
        title: 文章标题
        content: 文章内容（HTML格式）
        author: 作者名
        digest: 文章摘要
        thumb_media_id: 封面图素材ID（可选）
    """
    url = f"{WECHAT_API_BASE}/draft/add"
    params = {"access_token": access_token}
    
    # 构建文章数据
    article = {
        "title": title,
        "content": content,
        "author": author,
        "digest": digest,
        "content_source_url": "",
        "need_open_comment": 1,
        "only_fans_can_comment": 0
    }
    
    # 只有在有有效的thumb_media_id时才添加
    if thumb_media_id and thumb_media_id.strip():
        article["thumb_media_id"] = thumb_media_id
        print(f"使用封面图 media_id: {thumb_media_id}")
    else:
        print("未使用封面图")
    
    data = {
        "articles": [article]
    }
    
    try:
        print(f"创建草稿请求数据: {json.dumps(data, ensure_ascii=False)[:500]}...")
        
        response = requests.post(
            url, 
            params=params, 
            json=data,
            timeout=30
        )
        result = response.json()
        
        print(f"创建草稿响应: {result}")
        
        if "media_id" in result:
            return result["media_id"]
        else:
            print(f"创建草稿失败: {result.get('errmsg', '未知错误')}")
            # 如果是因为封面图问题，尝试不带头图重新发布
            if thumb_media_id and "media_id" in result.get('errmsg', '').lower():
                print("尝试不带头图重新发布...")
                return create_draft(access_token, title, content, author, digest, "")
            return None
    except Exception as e:
        print(f"创建草稿时出错: {str(e)}")
        return None


def extract_first_image_from_content(content, image_dir=None):
    """
    从文章内容中提取第一张本地图片路径
    
    参数:
        content: 文章内容（HTML格式）
        image_dir: 图片所在目录
    
    返回:
        第一张图片的完整路径，如果没有则返回None
    """
    import re
    
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    matches = re.findall(img_pattern, content)
    
    print(f"  从HTML中提取到的图片路径: {matches}")
    
    for src in matches:
        # 清理路径（去除可能的引号问题）
        src = src.strip()
        
        # 只处理本地图片路径
        if not src.startswith(('http://', 'https://')):
            if image_dir:
                img_path = os.path.join(image_dir, src)
            else:
                img_path = src
            
            print(f"  检查图片路径: {img_path}, 存在: {os.path.exists(img_path)}")
            
            if os.path.exists(img_path):
                return img_path
    
    return None


def process_content_images(access_token, content, image_dir=None):
    """
    处理文章中的图片，上传到微信服务器
    
    参数:
        access_token: 微信access_token
        content: 文章内容（HTML格式）
        image_dir: 图片所在目录
    
    返回:
        (处理后的内容, 第一张图片路径)
    """
    import re
    
    first_image_path = None
    
    # 查找所有图片标签
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
    matches = re.findall(img_pattern, content)
    
    print(f"  发现 {len(matches)} 个图片标签")
    
    def replace_image(match):
        nonlocal first_image_path
        src = match.group(1)
        
        print(f"  处理图片: {src}")
        
        # 如果是本地图片路径
        if not src.startswith(('http://', 'https://')):
            if image_dir:
                img_path = os.path.join(image_dir, src)
            else:
                img_path = src
            
            print(f"    本地路径: {img_path}, 存在: {os.path.exists(img_path)}")
            
            if os.path.exists(img_path):
                # 记录第一张图片
                if first_image_path is None:
                    first_image_path = img_path
                    print(f"    记录为封面图候选")
                
                # 上传图片到微信
                new_url = upload_image(access_token, img_path)
                if new_url:
                    print(f"    上传成功: {new_url}")
                    return match.group(0).replace(src, new_url)
                else:
                    print(f"    上传失败")
        else:
            print(f"    已是远程URL，跳过")
        
        return match.group(0)
    
    # 替换所有图片地址
    processed_content = re.sub(img_pattern, replace_image, content)
    
    print(f"  第一张图片路径: {first_image_path}")
    
    return processed_content, first_image_path


def create_default_thumb_image():
    """创建一个默认的封面图（300x300正方形）"""
    try:
        # 创建300x300的默认封面图（微信缩略图要求1:1正方形）
        img = Image.new('RGB', (300, 300), color='#07C160')
        draw = ImageDraw.Draw(img)
        
        # 添加文字
        text = "微信"
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置（居中）
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (300 - text_width) // 2
        y = (300 - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # 保存到临时文件
        temp_path = os.path.join(tempfile.gettempdir(), "default_wechat_thumb.jpg")
        img.save(temp_path, 'JPEG', quality=90)
        
        print(f"创建默认封面图: 300x300")
        return temp_path
    except Exception as e:
        print(f"创建默认封面图失败: {str(e)}")
        return None


def publish_article(title, content, author="", digest="", cover_image_path=None):
    """
    发布文章到微信公众号草稿箱
    
    参数:
        title: 文章标题
        content: 文章内容（支持HTML格式）
        author: 作者名（可选）
        digest: 文章摘要（可选）
        cover_image_path: 封面图本地路径（可选）
    
    返回:
        成功返回media_id，失败返回None
    """
    print("=" * 50)
    print("开始发布文章到微信公众号草稿箱")
    print("=" * 50)
    
    # 1. 获取access_token
    print("\n[1/4] 正在获取access_token...")
    access_token = get_access_token()
    if not access_token:
        print("❌ 获取access_token失败")
        print("\n" + "=" * 50)
        print("❌ 文章发布失败")
        print("=" * 50)
        return None
    print("✓ 获取access_token成功")
    
    # 2. 处理文章内容中的图片
    print("\n[2/4] 正在处理文章图片...")
    processed_content, first_image_path = process_content_images(access_token, content)
    print(f"✓ 图片处理完成")
    if first_image_path:
        print(f"  发现正文中第一张图片: {first_image_path}")
    
    # 3. 上传封面图（微信要求必须有封面图）
    thumb_media_id = ""
    print("\n[3/4] 正在上传封面图...")
    print(f"  指定封面图: {cover_image_path}")
    print(f"  正文第一张图片: {first_image_path}")
    
    # 优先级1: 如果提供了封面图，使用提供的
    if cover_image_path and os.path.exists(cover_image_path):
        print(f"使用指定的封面图: {cover_image_path}")
        thumb_media_id = upload_thumb_media(access_token, cover_image_path)
        if thumb_media_id:
            print(f"✓ 封面图上传成功，media_id: {thumb_media_id}")
        else:
            print("⚠ 封面图上传失败，将尝试使用正文中的图片")
    else:
        if cover_image_path:
            print(f"⚠ 指定的封面图不存在: {cover_image_path}")
    
    # 优先级2: 如果指定封面图失败或没提供，使用正文中的第一张图片
    if not thumb_media_id and first_image_path:
        print(f"使用正文中的第一张图片作为封面: {first_image_path}")
        print(f"  检查文件是否存在: {os.path.exists(first_image_path)}")
        thumb_media_id = upload_thumb_media(access_token, first_image_path)
        if thumb_media_id:
            print(f"✓ 正文图片作为封面上传成功，media_id: {thumb_media_id}")
        else:
            print("⚠ 正文图片上传失败，将使用默认封面图")
    
    # 优先级3: 如果都失败了，创建默认封面图
    if not thumb_media_id:
        print("创建默认封面图...")
        default_thumb_path = create_default_thumb_image()
        if default_thumb_path:
            thumb_media_id = upload_thumb_media(access_token, default_thumb_path)
            if thumb_media_id:
                print(f"✓ 默认封面图上传成功，media_id: {thumb_media_id}")
            else:
                print("❌ 默认封面图上传失败")
        else:
            print("❌ 无法创建默认封面图")
    
    if not thumb_media_id:
        print("❌ 无法获取封面图media_id，发布失败")
        print("\n" + "=" * 50)
        print("❌ 文章发布失败")
        print("💡 原因: 无法上传封面图")
        print("   可能原因: 图片格式不支持、图片过大、或微信API限制")
        print("=" * 50)
        return None
    
    # 4. 创建草稿
    print("\n[4/4] 正在创建草稿...")
    media_id = create_draft(
        access_token=access_token,
        title=title,
        content=processed_content,
        author=author,
        digest=digest,
        thumb_media_id=thumb_media_id
    )
    
    if media_id:
        print("\n" + "=" * 50)
        print("✅ 文章发布成功！")
        print(f"📄 文章标题: {title}")
        print(f"🆔 Media ID: {media_id}")
        print("=" * 50)
        return media_id
    else:
        print("\n" + "=" * 50)
        print("❌ 文章发布失败")
        print("💡 原因: 创建草稿失败")
        print("   可能原因: 微信API限制、文章内容格式错误、或服务器问题")
        print("   建议: 请检查文章内容格式，或稍后重试")
        print("=" * 50)
        return None


def main():
    """主函数 - 从命令行参数接收文章信息"""

    
    parser = argparse.ArgumentParser(description='发布文章到微信公众号草稿箱')
    parser.add_argument('--title', '-t', required=True, help='文章标题')
    parser.add_argument('--content', '-c', required=True, help='文章内容（HTML格式）')
    parser.add_argument('--author', '-a', default='', help='作者名')
    parser.add_argument('--digest', '-d', default='', help='文章摘要')
    parser.add_argument('--cover', default=None, help='封面图路径')
    parser.add_argument('--file', '-f', default=None, help='从文件读取内容')
    
    args = parser.parse_args()
    
    # 如果从文件读取内容
    content = args.content
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    
    # 发布文章
    media_id = publish_article(
        title=args.title,
        content=content,
        author=args.author,
        digest=args.digest,
        cover_image_path=args.cover
    )
    
    if media_id:
        # 输出结果供调用方使用
        result = {
            "success": True,
            "media_id": media_id,
            "title": args.title,
            "message": "文章已成功发布到微信公众号草稿箱"
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    else:
        # 发布失败，返回详细错误信息
        result = {
            "success": False,
            "message": "文章发布失败",
            "reason": "由于微信公众号API配置问题（IP白名单限制），文章未能自动发布到草稿箱。请复制文章内容到微信公众号后台手动发布。",
            "title": args.title,
            "content_length": len(content),
            "suggestion": "请管理员登录微信公众平台，将服务器IP添加到IP白名单中"
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
