import asyncio
import json
import uuid
import shutil
from fastapi import Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from deepagents.backends.local_shell import LocalShellBackend
from biziness.skill_service import SkillService
from biziness.agent_service import AgentService
from dataaccess.database import SessionLocal
from dataaccess.chat_repo import ChatRepo
from pathlib import Path
from config.schemas.chat_schemas import ChatRequest
from utils.logger import logger
from utils.auth_decorator import require_auth
from utils.temp_file_cleaner import clean_temp_files

# 项目根目录
PROJECT_DIR = Path(__file__).parent.parent
logger.info(f"项目根目录: {PROJECT_DIR}")

# 技能目录根路径
SKILLS_DIR = PROJECT_DIR / "skills"
logger.info(f"Skills目录路径: {SKILLS_DIR}")


# 创建LocalShellBackend，root_dir指向项目根目录，使uploads和skills都能访问
# LocalShellBackend 继承 FilesystemBackend，额外支持 execute（执行命令）
filesystem_backend = LocalShellBackend(
    root_dir=str(PROJECT_DIR),
    virtual_mode=True,  # 启用虚拟路径模式，必须使用以/开头的虚拟路径
    inherit_env=True    # 继承父进程环境变量（使 conda python 可用）
)


def get_uploaded_files_accessible_path(uploaded_files):
    """
    将上传的文件路径转换为 Skill 可访问的虚拟路径
    返回文件路径列表（相对于 PROJECT_DIR 的虚拟路径）
    """
    accessible_files = []
    for file_info in uploaded_files:
        try:
            original_path = Path(file_info.path)
            if not original_path.exists():
                logger.warning(f"原始文件不存在: {original_path}")
                continue
            
            # 返回相对于 PROJECT_DIR 的虚拟路径，这样 Skill 可以通过 FilesystemBackend 访问
            # 上传文件保存在 uploads/ 目录下
            relative_path = f"/uploads/{original_path.name}"
            accessible_files.append({
                "name": file_info.name,
                "path": relative_path,
                "size": file_info.size,
                "original_path": str(original_path)
            })
            logger.info(f"文件路径转换: {original_path} -> {relative_path}")
        except Exception as e:
            logger.exception(f"处理文件路径失败: {file_info.path}, 错误: {e}")
    return accessible_files


@require_auth
async def chat(request: Request, chat_data: ChatRequest):
    """
    智能体聊天接口（SSE流式返回）
    """
    logger.info(f"收到聊天请求: message={chat_data.message}, agent_id={chat_data.agent_id}, conversation_id={chat_data.conversation_id}")
    
    # 处理上传的文件信息
    uploaded_files = chat_data.files or []
    if uploaded_files:
        logger.info(f"用户上传了 {len(uploaded_files)} 个文件: {[f.name for f in uploaded_files]}")

    # 从request.state.user获取当前用户ID
    user = getattr(request.state, 'user', None)
    user_id = user.get('user_id') if user else None

    async def generate():
        """SSE事件生成器"""
        try:
            # 获取智能体配置
            agent_config = AgentService.get_agent_config(chat_data.agent_id)
            if not agent_config:
                yield f"data: {json.dumps({'type': 'error', 'content': f'智能体不存在: {chat_data.agent_id}'}, ensure_ascii=False)}\n\n"
                return

            logger.info(f"智能体配置: agent_id={chat_data.agent_id}")

            # 获取智能体配置的技能ID列表
            agent_skill_ids = agent_config.get("skills", [])
            logger.info(f"智能体技能列表: {agent_skill_ids}")

            # 获取智能体配置的工具ID列表
            agent_tool_ids = agent_config.get("tools", [])
            logger.info(f"智能体工具列表: {agent_tool_ids}")

            # 获取智能体配置的模型ID
            agent_model_id = agent_config.get("model_id")
            logger.info(f"智能体模型ID: {agent_model_id}")

            # 使用传入的 conversation_id 或生成新的
            conversation_id = chat_data.conversation_id
            if not conversation_id:
                conversation_id = f"conv_{uuid.uuid4().hex}"
                logger.info(f"生成新的 conversation_id: {conversation_id}")

            # 通过 SkillService 解析技能并生成路径
            agent_skills = SkillService.get_skills_by_ids(agent_skill_ids)
            skill_sources = SkillService.get_skill_source_paths(agent_skill_ids)
            logger.info(f"加载了 {len(agent_skills)} 个技能: {skill_sources}")
            logger.info(skill_sources)

            # 调试：检查技能目录是否存在
            for skill_path in skill_sources:
                # skill_path 是虚拟路径（如 /skills/excel-data-analyse/）
                # 映射到实际路径：项目根目录 + skill_path
                full_path = PROJECT_DIR / skill_path.strip("/")
                logger.info(f"检查技能路径: 虚拟路径={skill_path}, 实际路径={full_path}, 存在: {full_path.exists()}")
                if full_path.exists():
                    skill_md = full_path / "SKILL.md"
                    logger.info(f"SKILL.md 路径: {skill_md}, 存在: {skill_md.exists()}")

            # 将上传的文件复制到Skill可访问的目录
            accessible_files = get_uploaded_files_accessible_path(uploaded_files)
            logger.info(f"Skill可访问的文件: {accessible_files}")

            # 构建消息内容，包含文件信息（使用Skill可访问的路径）
            message_content = chat_data.message
            if accessible_files:
                file_paths = "\n".join([f["path"] for f in accessible_files])
                file_names = ", ".join([f["name"] for f in accessible_files])
                message_content = f"{chat_data.message}\n\n[上传文件]: {file_names}\n[文件路径]:\n{file_paths}\n\n请使用Excel数据分析技能分析这些文件。"

            # 异步流式输出（传入agent_id和user_id用于保存记录）
            async for event in AgentService.chat_stream_async(
                skill_sources=skill_sources,
                filesystem_backend=filesystem_backend,
                content=message_content,
                conversation=conversation_id,
                agent_id=chat_data.agent_id,
                user_id=user_id,
                tool_ids=agent_tool_ids,
                model_id=agent_model_id,
                uploaded_files=accessible_files
            ):
                yield event

        except asyncio.CancelledError:
            logger.info(f"聊天请求被用户终止: agent_id={chat_data.agent_id}, conversation={chat_data.conversation_id}")
            yield f"data: {json.dumps({'type': 'error', 'content': '对话已终止'}, ensure_ascii=False)}\n\n"
            raise
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"聊天流式接口错误: agent_id={chat_data.agent_id}")

            # 检查是否是 LangGraph Redis 序列化器错误
            if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
                logger.error(f"chat_view 捕获到 LangGraph Redis 序列化器错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': '会话存储出现兼容性问题，请使用新的会话 ID 重试'}, ensure_ascii=False)}\n\n"
                return

            # 检查是否是 DeepSeek 推理模式错误
            if "reasoning_content" in error_msg or "thinking mode" in error_msg:
                logger.error(f"chat_view 捕获到 DeepSeek 推理模式错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': '当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"
        finally:
            # 对话结束后清理临时文件
            try:
                cleaned = clean_temp_files()
                if cleaned > 0:
                    logger.info(f"对话结束后清理了 {cleaned} 个临时文件")
            except Exception as e:
                logger.warning(f"清理临时文件时出错: {e}")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@require_auth
async def get_chat_history(
    request: Request,
    agent_id: str = Query(..., description="智能体ID"),
    conversation_id: str = Query(None, description="会话ID（可选，不传则返回该智能体的所有对话）")
):
    """
    获取用户与指定智能体的对话历史（最近100轮，从早到晚）
    如果传入 conversation_id，则只返回该会话的对话
    """
    user = getattr(request.state, 'user', None)
    user_id = user.get('user_id') if user else None

    if not user_id:
        return JSONResponse({"success": False, "message": "未登录或登录已过期"}, status_code=401)

    try:
        db = SessionLocal()
        messages = ChatRepo.get_by_user_agent_and_conversation(db, user_id, agent_id, conversation_id, limit=100)
        db.close()

        # 转换为前端需要的格式（与正常提问回复格式一致）
        history = []
        for msg in messages:
            # 用户消息
            history.append({
                "role": "user",
                "content": msg.user_message,
                "time": msg.created_at.strftime("%H:%M:%S") if msg.created_at else ""
            })
            # AI回复
            history.append({
                "role": "agent",
                "content": msg.ai_message,
                "time": msg.created_at.strftime("%H:%M:%S") if msg.created_at else ""
            })

        return JSONResponse({
            "success": True,
            "data": history,
            "conversation_id": conversation_id or (messages[-1].conversation_id if messages else None)
        })
    except Exception as e:
        logger.exception(f"获取对话历史失败: user_id={user_id}, agent_id={agent_id}, conversation_id={conversation_id}")
        return JSONResponse({"success": False, "message": f"获取对话历史失败: {str(e)}"}, status_code=500)
