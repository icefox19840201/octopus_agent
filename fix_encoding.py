#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 编码修复模块
在导入 deepagents 之前调用
"""

import os
import sys
import subprocess

# 在 Windows 上修复编码问题
def fix_windows_encoding():
    """修复 Windows 子进程编码问题"""
    if sys.platform != 'win32':
        return
    
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['LC_ALL'] = 'en_US.UTF-8'
    os.environ['LANG'] = 'en_US.UTF-8'
    
    # 修改 subprocess 默认编码
    # 这会影响所有新创建的子进程
    original_popen = subprocess.Popen
    
    class FixedPopen(original_popen):
        def __init__(self, *args, **kwargs):
            # 强制使用 UTF-8 编码
            if 'encoding' not in kwargs:
                kwargs['encoding'] = 'utf-8'
            if 'errors' not in kwargs:
                kwargs['errors'] = 'replace'
            super().__init__(*args, **kwargs)
    
    subprocess.Popen = FixedPopen
    
    # 同时修复 run 函数
    original_run = subprocess.run
    
    def fixed_run(*args, **kwargs):
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
        if 'errors' not in kwargs:
            kwargs['errors'] = 'replace'
        return original_run(*args, **kwargs)
    
    subprocess.run = fixed_run
    
    print("[fix_encoding] Windows 编码修复已应用")

# 立即执行修复
fix_windows_encoding()
