import os
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Optional
from fastapi import Request, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from utils.auth_decorator import require_auth
from utils.logger import logger
import settings
from biziness.redis_mq import producer
from minio import Minio
from minio.error import S3Error
import io
from biziness.knowledge_base_service import KnowledgeBaseService
# 确保上传目录存在
UPLOAD_DIR = Path(os.path.join(settings.uploads_dir_path,'analysis_report'))
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
async def upload_multiple_files(
    request: Request,
    files: list[UploadFile] = File(...),
    kb_id: Optional[str] = Form(None, description="知识库ID")
):
    """
    批量上传文件接口,用于知识库上传文档使用，上传文档后，直接解析文档并入库
    """
    results = []
    uploaded_files = []  # 存储成功上传的文件信息

    # 校验知识库ID
    if not kb_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "缺少知识库ID参数(kb_id)"}
        )

    # 验证知识库是否存在（业务层处理）
    if not KnowledgeBaseService.check_knowledge_base_exists(kb_id):
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "知识库不存在"}
        )

    for file in files:
        try:
            if not file.filename:
                results.append({"success": False, "message": "文件名不能为空", "filename": None})
                continue
            file_ext = Path(file.filename).suffix
            print('扩展名{}'.format(file_ext))
            unique_filename = file.filename.strip(file_ext)+'_'+f"{uuid.uuid4().hex}{file_ext}"
            contents = await file.read()
            logger.info('等待解析')
            #上传到minio
            minio_client=Minio(
                endpoint=settings.minio_remote_addr,
                access_key=settings.mino_access_key,
                secret_key=settings.minio_secret_key,
                secure=False
            )
            bucket_name=settings.minio_bucket_name
            if not minio_client.bucket_exists(bucket_name):
                minio_client.make_bucket(bucket_name)

            public_read_policy = (
                '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", '
                '"Principal": "*", "Action": ["s3:GetObject"], '
                '"Resource": ["arn:aws:s3:::%s/*"]}]}' % bucket_name
            )
            minio_client.set_bucket_policy(bucket_name, public_read_policy)
            data=io.BytesIO(contents)
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=unique_filename,
                data=data,
                length=len(contents)
            )
            download_url=f'http://{settings.minio_remote_addr}/rag/{unique_filename}'
            logger.info(f'文件下载url: {download_url}')
            await producer(download_url)
            results.append({
                "success": True,
                "message": "上传成功",
                "filename": file.filename,
                "path": download_url,
                "size": len(contents)
            })
            # 记录成功上传的文件信息
            uploaded_files.append({
                "filename": file.filename,
                "path": download_url,
                "size": len(contents)
            })

        except Exception as e:
            logger.exception(f"文件上传失败: {file.filename}")
            results.append({
                "success": False,
                "message": f"上传失败: {str(e)}",
                "filename": file.filename
            })

    # 有文件上传成功时，通过业务层更新知识库的 file_path 字段（JSON格式，多文件一起更新）
    if uploaded_files:
        result = KnowledgeBaseService.update_knowledge_base_file_path(kb_id, uploaded_files)
        if result["success"]:
            logger.info(f"知识库 {kb_id} file_path 已更新: {result.get('data')}")
        else:
            logger.warning(f"更新知识库 file_path 失败: {result.get('message')}")

    return {
        "success": all(r.get("success") for r in results),
        "message": f"上传完成: {sum(1 for r in results if r.get('success'))}/{len(results)} 个文件成功",
        "results": results
    }
