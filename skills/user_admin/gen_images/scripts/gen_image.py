#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像生成脚本 - 通过命令行传参生成图片，返回 HTML img 标签
图片默认保存到 static/images 目录
"""

import argparse
import base64
import requests
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# API 配置
API_KEY = 'sk-JxuWh9wMvX8VTqjMbZJ1Xg48mu3MLiZMNviO7VuVn1O8cYyH'
BASE_URL = 'https://aiyiwei.vip/v1'

# 默认输出目录（项目根目录下的 static/images）
# 脚本路径: skills/{user_id}/gen_images/scripts/gen_image.py
# 需要找到项目根目录（包含 static 文件夹的目录）
def get_project_root():
    """获取项目根目录（包含 static 文件夹的目录）"""
    current = Path(__file__).resolve()
    # 向上查找，直到找到包含 static 文件夹的目录，或者到达根目录
    for parent in current.parents:
        if (parent / "static").exists():
            return parent
        # 如果找到 manager.py 或 settings.py，也认为是项目根目录
        if (parent / "manager.py").exists() or (parent / "settings.py").exists():
            return parent
    # 默认返回脚本的上三级目录（skills/{user_id}/gen_images/ -> skills/{user_id}/ -> skills/ -> 项目根目录）
    return Path(__file__).resolve().parent.parent.parent.parent

PROJECT_ROOT = get_project_root()
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "static" / "images"

# 调试信息（输出到 stderr，不会污染 stdout 的 img 标签）
print(f"[DEBUG] 项目根目录: {PROJECT_ROOT}", file=sys.stderr)
print(f"[DEBUG] 图片输出目录: {DEFAULT_OUTPUT_DIR}", file=sys.stderr)


def optimize_prompt(description):
    """使用文本模型优化提示词"""
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import PromptTemplate
        
        # llm = ChatOpenAI(
        #     model_name="gpt-4o-mini",
        #     temperature=0.7,
        #     api_key=API_KEY,
        #     base_url=BASE_URL
        # )

        llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.7,
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        prompt = PromptTemplate(
            input_variables=["description"],
            template="请把下面的描述优化成适合生成高质量图像的提示词，要求详细、具体、画面感强：{description}"
        )
        
        chain = prompt | llm
        result = chain.invoke({"description": description})
        return result.content
    except Exception as e:
        print(f"提示词优化失败，使用原始描述: {e}", file=sys.stderr)
        return description


def generate_image(description, size="2K", output_dir=None, optimize=True, return_base64=False):
    """
    生成图像并返回 HTML img 标签
    
    Args:
        description: 图像描述
        size: 图像尺寸 (2K, 1024x1024, 1024x1536, 1536x1024)
        output_dir: 输出目录（可选，默认 static/images）
        optimize: 是否优化提示词
        return_base64: 是否返回 base64 编码的图片（否则返回文件路径）
    
    Returns:
        HTML img 标签字符串
    """
    # 优化提示词
    if optimize:
        print(f"正在优化提示词...", file=sys.stderr)
        optimized_prompt = optimize_prompt(description)
        print(f"优化后的提示词: {optimized_prompt}", file=sys.stderr)
    else:
        optimized_prompt = description
    
    # 调用图像生成 API
    api_url = f"{BASE_URL}/images/generations"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "doubao-seedream-3-0-t2i-250415",
        "prompt": optimized_prompt,
        "size": size,
        "output_format": "png",
        "response_format": "url",
        "watermark": False
    }
    
    try:
        print(f"正在生成图像...", file=sys.stderr)
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data or len(data['data']) == 0:
            error_msg = f"API 响应异常: {json.dumps(data, ensure_ascii=False)}"
            print(error_msg, file=sys.stderr)
            return f"<p style='color:red'>图像生成失败: {error_msg}</p>"
        
        image_data = data['data'][0]
        
        if 'url' in image_data:
            # 获取图片 URL
            image_url = image_data['url'].strip()
            print(f"获取图片 URL: {image_url}", file=sys.stderr)
            
            # 下载图片
            image_response = requests.get(image_url, timeout=60)
            image_response.raise_for_status()
            image_bytes = image_response.content
            
            # 使用PIL检查并调整图片尺寸
            try:
                from PIL import Image
                from io import BytesIO
                
                # 从字节加载图片
                img = Image.open(BytesIO(image_bytes))
                original_size = img.size
                print(f"API返回图片尺寸: {original_size}", file=sys.stderr)
                
                # 解析目标尺寸
                target_width, target_height = map(int, size.split('x'))
                target_size = (target_width, target_height)
                
                # 如果尺寸不匹配，强制调整
                if img.size != target_size:
                    print(f"尺寸不匹配，强制调整为: {target_size}", file=sys.stderr)
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                    # 转换回字节
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    image_bytes = buffer.getvalue()
                    print(f"图片已调整为: {img.size}", file=sys.stderr)
                else:
                    print(f"图片尺寸正确: {img.size}", file=sys.stderr)
                    
            except ImportError:
                print("PIL未安装，无法检查图片尺寸", file=sys.stderr)
            except Exception as e:
                print(f"调整图片尺寸时出错: {e}", file=sys.stderr)
            
            # 确定输出目录
            if output_dir is None:
                output_dir = DEFAULT_OUTPUT_DIR
            else:
                output_dir = Path(output_dir)
            
            # 创建目录
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名（使用时间戳+描述）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in description[:15] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_') or 'image'
            filename = f"{timestamp}_{safe_name}.png"
            output_file = output_dir / filename
            
            # 保存图片
            with open(output_file, "wb") as f:
                f.write(image_bytes)
            print(f"图片已保存: {output_file}", file=sys.stderr)
            
            # 计算相对于项目根目录的路径，用于 img src
            try:
                relative_path = output_file.relative_to(PROJECT_ROOT)
                src_path = f"/{relative_path.as_posix()}"
            except ValueError:
                # 如果无法计算相对路径，使用默认路径
                src_path = f"/static/images/{filename}"
            
            if return_base64:
                # 返回 base64 编码的图片
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                img_tag = f'<img src="data:image/png;base64,{image_base64}" alt="{description}" style="max-width:100%;height:auto;" />'
            else:
                # 返回文件路径
                img_tag = f'<img src="{src_path}" alt="{description}" style="max-width:100%;height:auto;" />'
            
            return img_tag
            
        elif 'b64_json' in image_data:
            # 直接返回 base64
            image_base64 = image_data['b64_json']
            image_bytes = base64.b64decode(image_base64)
            
            # 使用PIL检查并调整图片尺寸
            try:
                from PIL import Image
                from io import BytesIO
                
                img = Image.open(BytesIO(image_bytes))
                original_size = img.size
                print(f"API返回图片尺寸: {original_size}", file=sys.stderr)
                
                # 解析目标尺寸
                target_width, target_height = map(int, size.split('x'))
                target_size = (target_width, target_height)
                
                # 如果尺寸不匹配，强制调整
                if img.size != target_size:
                    print(f"尺寸不匹配，强制调整为: {target_size}", file=sys.stderr)
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    image_bytes = buffer.getvalue()
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    print(f"图片已调整为: {img.size}", file=sys.stderr)
                else:
                    print(f"图片尺寸正确: {img.size}", file=sys.stderr)
                    
            except ImportError:
                print("PIL未安装，无法检查图片尺寸", file=sys.stderr)
            except Exception as e:
                print(f"调整图片尺寸时出错: {e}", file=sys.stderr)
            
            if return_base64:
                img_tag = f'<img src="data:image/png;base64,{image_base64}" alt="{description}" style="max-width:100%;height:auto;" />'
            else:
                # 保存到文件
                if output_dir is None:
                    output_dir = DEFAULT_OUTPUT_DIR
                else:
                    output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in description[:15] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_') or 'image'
                filename = f"{timestamp}_{safe_name}.png"
                output_file = output_dir / filename
                
                with open(output_file, "wb") as f:
                    f.write(image_bytes)
                
                src_path = f"/static/images/{filename}"
                img_tag = f'<img src="{src_path}" alt="{description}" style="max-width:100%;height:auto;" />'
            return img_tag
        else:
            error_msg = f"未知的响应格式: {image_data}"
            print(error_msg, file=sys.stderr)
            return f"<p style='color:red'>图像生成失败: {error_msg}</p>"
            
    except requests.exceptions.Timeout:
        error_msg = "请求超时，请稍后重试"
        print(error_msg, file=sys.stderr)
        return f"<p style='color:red'>图像生成失败: {error_msg}</p>"
    except Exception as e:
        error_msg = f"图像生成出错: {str(e)}"
        print(error_msg, file=sys.stderr)
        return f"<p style='color:red'>图像生成失败: {error_msg}</p>"


# 豆包Seedream模型支持的尺寸
SUPPORTED_SIZES = {
    '1024x1024': '1024x1024',  # 正方形 1:1
    '1024x1536': '1024x1536',  # 竖屏 2:3
    '1536x1024': '1536x1024',  # 横屏 3:2
    '1:1': '1024x1024',
    '2:3': '1024x1536',
    '3:2': '1536x1024',
}


def main():
    parser = argparse.ArgumentParser(description='图像生成工具')
    parser.add_argument('description', help='图像描述文本')
    parser.add_argument('--size', default='1024x1024', 
                        choices=list(SUPPORTED_SIZES.keys()),
                        help='图像尺寸 (默认: 1024x1024, 支持: 1024x1024, 1024x1536, 1536x1024, 1:1, 2:3, 3:2)')
    parser.add_argument('--output-dir', '-o', 
                        help=f'图片保存目录（默认: {DEFAULT_OUTPUT_DIR}）')
    parser.add_argument('--no-optimize', action='store_true',
                        help='禁用提示词优化')
    parser.add_argument('--base64', action='store_true',
                        help='返回 base64 编码的图片（默认返回文件路径）')
    
    args = parser.parse_args()
    
    # 转换尺寸参数
    api_size = SUPPORTED_SIZES.get(args.size, '1024x1024')
    print(f"使用尺寸: {api_size}", file=sys.stderr)
    
    # 生成图像
    result = generate_image(
        description=args.description,
        size=api_size,
        output_dir=args.output_dir,
        optimize=not args.no_optimize,
        return_base64=args.base64
    )
    
    # 输出结果（HTML img 标签）
    print(result)


if __name__ == '__main__':
    main()
