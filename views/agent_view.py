from fastapi import HTTPException, Request, UploadFile, File
from fastapi.responses import  Response
from biziness.agent_service import AgentService
from pathlib import Path
import uuid
from datetime import datetime
from utils.logger import logger
from utils.auth_decorator import require_auth, get_current_user


@require_auth
async def create_agent(request: Request):
    """创建Agent并保存到数据库"""
    try:
        data = await request.json()
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        agent_id = f"agent_{uuid.uuid4().hex}"

        agent_data = {
            "id": agent_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "skills": data.get("skills", []),
            "tools": data.get("tools", []),
            "model_id": data.get("model_id"),
            "prompt_id": data.get("prompt_id"),
            "agent_space": data.get("agent_space", "private"),
            "status": "active",
            "config": data.get("config", {}),
            "temperature": data.get("temperature", 0.7),
            "top_p": data.get("top_p", 0.9),
            "enable_memory": data.get("enable_memory", True),
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat()
        }

        success = AgentService.save_agent_config(agent_id, agent_data, user_id, department_id)

        if success:
            return {
                "success": True,
                "message": "Agent创建成功",
                "data": agent_data
            }
        else:
            raise HTTPException(status_code=500, detail="保存Agent配置失败")

    except Exception as e:
        logger.exception(f"创建Agent失败")
        raise HTTPException(status_code=500, detail=f"创建Agent失败: {str(e)}")


@require_auth
async def list_agents(request: Request, page: int = 1, page_size: int = 10, keyword: str = None):
    """获取Agent列表（分页，带空间过滤，支持搜索）"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        # 如果有搜索关键词，使用搜索方法
        if keyword:
            result = AgentService.search_agents(page, page_size, user_id, department_id, keyword)
        else:
            result = AgentService.paginate_agents(page, page_size, user_id, department_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.exception("获取Agent列表失败")
        raise HTTPException(status_code=500, detail=f"获取Agent列表失败: {str(e)}")


@require_auth
async def get_agent(request: Request, agent_id: str):
    """获取单个Agent配置"""
    try:
        agent = AgentService.get_agent_config(agent_id)

        if agent is None:
            raise HTTPException(status_code=404, detail="Agent不存在")

        return {
            "success": True,
            "data": agent
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取Agent详情失败: agent_id={agent_id}")
        raise HTTPException(status_code=500, detail=f"获取Agent失败: {str(e)}")


@require_auth
async def update_agent(request: Request, agent_id: str):
    """更新Agent配置"""
    try:
        data = await request.json()
        
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None

        existing = AgentService.get_agent_config(agent_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Agent不存在")

        data["updatedAt"] = datetime.now().isoformat()

        result = AgentService.update_agent_config(agent_id, data, user_id)

        if result.get("success"):
            return {
                "success": True,
                "message": "Agent更新成功"
            }
        else:
            msg = result.get("message", "更新Agent配置失败")
            if "无权" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=500, detail=msg)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"更新Agent失败: agent_id={agent_id}")
        raise HTTPException(status_code=500, detail=f"更新Agent失败: {str(e)}")


@require_auth
async def delete_agent(request: Request, agent_id: str):
    """删除Agent"""
    try:
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None

        result = AgentService.delete_agent_config(agent_id, user_id)

        if result.get("success"):
            return {
                "success": True,
                "message": "Agent删除成功"
            }
        else:
            msg = result.get("message", "Agent不存在或删除失败")
            if "无权" in msg:
                raise HTTPException(status_code=403, detail=msg)
            raise HTTPException(status_code=404, detail=msg)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除Agent失败: agent_id={agent_id}")
        raise HTTPException(status_code=500, detail=f"删除Agent失败: {str(e)}")


@require_auth
async def export_agents(request: Request):
    """导出所有Agents为JSON文件"""
    try:
        json_str = AgentService.export_agents_json()
        return Response(
            content=json_str,
            media_type='application/json',
            headers={"Content-Disposition": "attachment; filename=agents_export.json"}
        )
    except Exception as e:
        logger.exception("导出Agents失败")
        raise HTTPException(status_code=500, detail=f"导出Agents失败: {str(e)}")


@require_auth
async def export_single_agent(request: Request, agent_id: str):
    """导出单个Agent为JSON文件"""
    try:
        json_str = AgentService.export_single_agent_json(agent_id)
        return Response(
            content=json_str,
            media_type='application/json',
            headers={"Content-Disposition": f"attachment; filename=agent_{agent_id}.json"}
        )
    except Exception as e:
        logger.exception(f"导出单个Agent失败: agent_id={agent_id}")
        raise HTTPException(status_code=500, detail=f"导出Agent失败: {str(e)}")


@require_auth
async def import_agents(request: Request, file: UploadFile = File(...)):
    """从JSON文件导入Agents"""
    try:
        content = await file.read()
        json_str = content.decode('utf-8')

        # 获取当前用户信息
        user = get_current_user(request)
        user_id = user.get('user_id') if user else None
        department_id = user.get('department_id') if user else None

        # 先保存上传文件到config/agent_config/目录（保留原始文件名）
        agent_config_dir = Path(__file__).parent.parent / "config" / "agent_config"
        agent_config_dir.mkdir(parents=True, exist_ok=True)
        save_path = agent_config_dir / (file.filename or f"agents_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        save_path.write_bytes(content)
        logger.info(f"Agent导入文件已保存: {save_path}")
        # 读取保存的文件内容进行导入
        saved_content = save_path.read_text(encoding='utf-8')
        result = AgentService.import_agents_json(saved_content, user_id, department_id)
        return {
            "success": True,
            "data": result,
            "message": f"导入完成：成功{result['success']}个，跳过{result['skipped']}个"
        }
    except Exception as e:
        logger.exception("导入Agents失败")
        raise HTTPException(status_code=500, detail=f"导入Agents失败: {str(e)}")
