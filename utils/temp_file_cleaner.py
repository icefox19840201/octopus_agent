#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时文件清理工具
用于清理 deepagents 自动生成的临时脚本文件
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from utils.logger import logger
from views.default_viewer import env


class TempFileCleaner:
    """临时文件清理器"""
    
    # 默认清理的目录模式
    DEFAULT_PATTERNS = [
        "tmp/*.py",
        "workspace/*.py",
        "*.py",  # 项目根目录下的临时脚本
    ]
    
    # 保留的文件（白名单）
    KEEP_FILES = [
        "manager.py",
        "settings.py",
        "urls.py",
        "fix_encoding.py",
        ".env"
    ]
    
    @staticmethod
    def clean_temp_files(base_dir: str = None, patterns: list = None, max_age_hours: int = 1):
        """
        清理临时文件
        
        Args:
            base_dir: 项目根目录，默认为当前工作目录
            patterns: 要清理的文件模式列表
            max_age_hours: 只清理超过指定小时数的文件（避免清理正在使用的文件）
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        else:
            base_dir = Path(base_dir)
        
        if patterns is None:
            patterns = TempFileCleaner.DEFAULT_PATTERNS
        
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for pattern in patterns:
            # 处理相对路径
            if pattern.startswith("tmp/"):
                search_dir = base_dir / "tmp"
                file_pattern = pattern.replace("tmp/", "")
            elif pattern.startswith("workspace/"):
                search_dir = base_dir / "workspace"
                file_pattern = pattern.replace("workspace/", "")
            else:
                search_dir = base_dir
                file_pattern = pattern
            
            if not search_dir.exists():
                continue
            
            # 查找匹配的文件
            for file_path in search_dir.glob(file_pattern):
                if not file_path.is_file():
                    continue
                
                # 检查是否在白名单中
                if file_path.name in TempFileCleaner.KEEP_FILES:
                    continue
                
                # 检查文件修改时间
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime > cutoff_time:
                        # 文件太新，可能正在使用，跳过
                        continue
                    
                    # 删除文件
                    file_path.unlink()
                    cleaned_count += 1
                    logger.info(f"已清理临时文件: {file_path}")
                except Exception as e:
                    logger.warning(f"清理文件失败 {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"共清理 {cleaned_count} 个临时文件")
        
        return cleaned_count
    
    @staticmethod
    def clean_all(base_dir: str = None):
        """清理所有临时文件（包括新创建的）"""
        return TempFileCleaner.clean_temp_files(base_dir, max_age_hours=0)


# 便捷的清理函数
def clean_temp_files():
    """清理临时文件（保留1小时内的文件）"""
    return TempFileCleaner.clean_temp_files()


def clean_all_temp_files():
    """清理所有临时文件"""
    return TempFileCleaner.clean_all()


if __name__ == "__main__":
    # 测试清理功能
    count = clean_temp_files()
    print(f"清理了 {count} 个临时文件")
