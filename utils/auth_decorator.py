"""
认证装饰器模块
用于保护需要登录才能访问的API接口
"""
from functools import wraps
from fastapi import Request, HTTPException
from biziness.auth_service import AuthService
from utils.logger import logger


def require_auth(func):
    """
    认证装饰器
    要求请求必须携带有效的token才能访问

    使用方式:
        @require_auth
        async def my_api(request: Request):
            ...

    或带参数:
        @require_auth
        async def my_api(request: Request, some_id: str):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = None

        # 从参数中查找 Request 对象
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if request is None:
            request = kwargs.get('request')

        if request is None:
            logger.error(f"认证装饰器无法获取Request对象: {func.__name__}")
            raise HTTPException(status_code=500, detail="服务器内部错误")

        # 从请求头中获取token
        auth_header = request.headers.get('Authorization', '')
        token = None

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif auth_header:
            token = auth_header

        if not token:
            logger.warning(f"未提供认证JWT token: {func.__name__}")
            raise HTTPException(status_code=401, detail="未登录或登录已过期")

        # 验证JWT token
        verify_result = AuthService.verify(token)
        if not verify_result['success']:
            logger.warning(f"JWT token验证失败或已过期: {func.__name__}")
            raise HTTPException(status_code=401, detail="未登录或登录已过期")

        # 将用户信息存入request.state，供后续使用
        request.state.user = verify_result['data']
        request.state.token = token

        return await func(*args, **kwargs)

    return wrapper


def get_current_user(request: Request) -> dict:
    """
    从请求中获取当前登录用户信息
    需要在被 @require_auth 装饰的函数中使用

    Args:
        request: FastAPI Request对象

    Returns:
        用户信息字典，包含 username, role, email
    """
    return getattr(request.state, 'user', None)
