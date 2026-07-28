from fastapi import Request, HTTPException
from biziness.auth_service import AuthService
from utils.logger import logger


async def login(request: Request):
    try:
        body = await request.json()
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()

        if not username or not password:
            raise HTTPException(status_code=400, detail="用户名和密码不能为空")

        result = AuthService.login(username, password)

        if not result["success"]:
            error_code = result.get("error_code")
            if error_code == "INVALID_CREDENTIALS":
                logger.warning(f"登录失败: 用户名或密码错误, username={username}")
                raise HTTPException(status_code=401, detail=result["message"])
            elif error_code == "ACCOUNT_DISABLED":
                logger.warning(f"登录失败: 账户已停用, username={username}")
                raise HTTPException(status_code=403, detail=result["message"])
            else:
                raise HTTPException(status_code=400, detail=result["message"])

        logger.info(f"登录成功: username={username}, role={result.get('data', {}).get('role')}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"登录接口异常")
        raise HTTPException(status_code=500, detail="登录失败，服务器内部错误")


async def logout(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    return AuthService.logout(token)


async def verify(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    return AuthService.verify(token)


def get_current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    return AuthService.get_current_user(token)


async def change_password(request: Request):
    """修改密码接口"""
    try:
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "").strip()

        body = await request.json()
        old_password = body.get("old_password", "").strip()
        new_password = body.get("new_password", "").strip()

        result = AuthService.change_password(token, old_password, new_password)

        if not result["success"]:
            error_code = result.get("error_code")
            if error_code == "UNAUTHORIZED":
                raise HTTPException(status_code=401, detail=result["message"])
            elif error_code == "INVALID_PASSWORD":
                logger.warning("修改密码失败: 原密码错误")
                raise HTTPException(status_code=400, detail=result["message"])
            else:
                raise HTTPException(status_code=400, detail=result["message"])

        logger.info("密码修改成功")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("修改密码接口异常")
        raise HTTPException(status_code=500, detail="修改密码失败，服务器内部错误")
