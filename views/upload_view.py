import os
import uuid
from pathlib import Path
from fastapi import Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from utils.auth_decorator import require_auth
from utils.logger import logger
import settings
from biziness.redis_mq import producer
# 确保上传目录存在
UPLOAD_DIR = Path(settings.uploads_dir_path)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@require_auth
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    上传文件接口
    文件保存到 settings.uploads_dir_path 指定的目录
    返回文件的完整路径
    """
    try:
        # 检查文件是否为空
        if not file.filename:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "文件名不能为空"}
            )

        # 生成唯一文件名
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # 保存文件
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # 返回完整路径
        full_path = str(file_path.absolute())
        
        logger.info(f"文件上传成功: {file.filename} -> {full_path}")

        return {
            "success": True,
            "message": "上传成功",
            "filename": file.filename,
            "path": full_path,
            "size": len(contents)
        }

    except Exception as e:
        logger.exception(f"文件上传失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"上传失败: {str(e)}"}
        )


@require_auth
async def upload_multiple_files(request: Request, files: list[UploadFile] = File(...)):
    """
    批量上传文件接口,用于知识库上传文档使用，上传文档后，直接解析文档并入库
    """
    results = []
    
    for file in files:
        try:
            if not file.filename:
                results.append({"success": False, "message": "文件名不能为空", "filename": None})
                continue

            file_ext = Path(file.filename).suffix
            unique_filename = file.filename.strip(file_ext)+'_'+f"{uuid.uuid4().hex}{file_ext}"
            rag_file_path = os.path.join(UPLOAD_DIR, 'rags')
            os.makedirs(rag_file_path, exist_ok=True)
            file_path = os.path.join(rag_file_path, unique_filename)

            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            full_path = str(file_path)
            
            logger.info(f"文件上传成功: {file.filename} -> {full_path}")
            logger.info('等待解析')
            await producer(full_path)
            results.append({
                "success": True,
                "message": "上传成功",
                "filename": file.filename,
                "path": full_path,
                "size": len(contents)
            })

        except Exception as e:
            logger.exception(f"文件上传失败: {file.filename}")
            results.append({
                "success": False,
                "message": f"上传失败: {str(e)}",
                "filename": file.filename
            })

    return {
        "success": all(r.get("success") for r in results),
        "message": f"上传完成: {sum(1 for r in results if r.get('success'))}/{len(results)} 个文件成功",
        "results": results
    }
