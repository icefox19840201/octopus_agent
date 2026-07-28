from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
import os
import tempfile
import urllib.parse
from biziness.skill_service import SkillService
from config.schemas.skills_schemas import SkillCreate, SkillUpdate
from utils.logger import logger
from utils.auth_decorator import require_auth, get_current_user


@require_auth
async def create_skill(request: Request, skill: SkillCreate):
    """
    创建新Skill
    """
    try:
        import uuid

        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        # 使用LLM将中文名称转换为英文格式（符合Agent Skills规范）
        skill_name =SkillService.generate_english_name(skill.name, skill.description)

        # 构建skill数据，生成唯一ID
        skill_data = {
            "id": f"skill_{uuid.uuid4().hex}",
            "name": skill_name,
            "description": skill.description,
            "code": skill.code,
            "skill_space": skill.skill_space if hasattr(skill, 'skill_space') else 'private',
            "created_by": user_id,
            "department_id": department_id,
            "createdAt": os.popen('date /t').read().strip(),
            "updatedAt": os.popen('date /t').read().strip()
        }

        # 保存skill配置
        success = SkillService.save_skill_config(skill_data)

        if success:
            return {
                "success": True,
                "data": skill_data,
                "message": "Skill创建成功"
            }
        else:
            raise HTTPException(status_code=500, detail="Skill创建失败")
    except Exception as e:
        logger.exception("创建Skill失败")
        raise HTTPException(status_code=500, detail=str(e))

@require_auth
async def list_skills(request: Request, page: int = 1, page_size: int = 10):
    """
    获取Skill列表（分页，带空间过滤）
    """
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        result = SkillService.paginate_skills(page, page_size, user_id, department_id)
        return {
            "success": True,
            "data": result,
            "message": "获取Skill列表成功"
        }
    except Exception as e:
        logger.exception("获取Skill列表失败")
        raise HTTPException(status_code=500, detail=str(e))

@require_auth
async def get_skill(request: Request, skill_id: str):
    """
    获取Skill详情
    """
    try:
        skill = SkillService.get_skill_config(skill_id)
        if skill:
            return {
                "success": True,
                "data": skill,
                "message": "获取Skill详情成功"
            }
        else:
            raise HTTPException(status_code=404, detail="Skill不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取Skill详情失败: skill_id={skill_id}")
        raise HTTPException(status_code=500, detail=str(e))


@require_auth
async def export_skills(request: Request):
    """导出所有Skills为ZIP文件"""
    try:
        zip_path = SkillService.export_skills_zip()
        return FileResponse(
            zip_path,
            media_type='application/zip',
            filename='skills_export.zip',
            headers={"Content-Disposition": "attachment; filename=skills_export.zip"}
        )
    except Exception as e:
        logger.exception("导出Skills失败")
        raise HTTPException(status_code=500, detail=f"导出Skills失败: {str(e)}")


@require_auth
async def export_single_skill(request: Request, skill_id: str):
    """导出单个Skill为ZIP文件（扁平结构：根目录下SKILL.md + _skills_meta.json）"""
    try:
        result = SkillService.export_single_skill_zip(skill_id)
        if not result:
            raise HTTPException(status_code=404, detail="Skill不存在")
        return FileResponse(
            result["zip_path"],
            media_type='application/zip',
            filename=result["filename"],
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(result['filename'])}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"导出单个Skill失败: skill_id={skill_id}")
        raise HTTPException(status_code=500, detail=f"导出Skill失败: {str(e)}")


@require_auth
async def import_skills(request: Request, file: UploadFile = File(...)):
    """从ZIP文件导入Skills"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        tmp_path = tmp.name
        tmp.close()
        content = await file.read()
        with open(tmp_path, 'wb') as f:
            f.write(content)
            logger.info(f"临时导入文件: {tmp_path}")
        result = SkillService.import_skills_zip(tmp_path, file.filename, user_id, department_id)

        try:
            os.unlink(tmp_path)
        except Exception:
            logger.warning(f"删除临时文件失败: {tmp_path}")

        has_errors = bool(result.get("errors"))
        success_count = result.get("success", 0)
        msg_parts = [f"成功{success_count}个", f"跳过{result.get('skipped', 0)}个"]
        if has_errors:
            errors = result["errors"]
            msg_parts.append(f"错误{'；'.join(errors[:3])}")
            if len(errors) > 3:
                msg_parts[-1] += f"…（共{len(errors)}个错误）"
        return {
            "success": success_count > 0,
            "data": result,
            "message": "导入完成：" + "，".join(msg_parts)
        }
    except Exception as e:
        logger.exception("导入Skills失败")
        raise HTTPException(status_code=500, detail=f"导入Skills失败: {str(e)}")

@require_auth
async def update_skill(request: Request, skill_id: str, skill: SkillUpdate):
    """
    更新Skill，同时修改数据库信息和SKILL.md文件内容
    """
    try:
        update_data = skill.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="没有要更新的数据")

        success = SkillService.update_skill_with_file(skill_id, update_data)

        if success:
            updated_skill = SkillService.get_skill_config(skill_id)
            return {
                "success": True,
                "data": updated_skill,
                "message": "Skill更新成功"
            }
        else:
            raise HTTPException(status_code=500, detail="Skill更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"更新Skill失败: skill_id={skill_id}")
        raise HTTPException(status_code=500, detail=str(e))

@require_auth
async def delete_skill(request: Request, skill_id: str):
    """
    删除Skill
    """
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None

        result = SkillService.delete_skill_config(skill_id, user_id)
        if result.get("success"):
            return {
                "success": True,
                "message": "Skill删除成功"
            }
        else:
            msg = result.get("message", "Skill不存在")
            if "无权" in msg:
                raise HTTPException(status_code=403, detail=msg)
            if "被" in msg and "引用" in msg:
                raise HTTPException(status_code=409, detail=msg)
            raise HTTPException(status_code=404, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除Skill失败: skill_id={skill_id}")
        raise HTTPException(status_code=500, detail=str(e))
