import datetime
import os
import json
import ast
import asyncio
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from dataaccess.models import LLMModel
from dotenv import load_dotenv
from utils.logger import logger
from langchain_core.tools import StructuredTool, BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel, create_model
from dataaccess.mcp_repo import MCPToolRepo
from dataaccess.database import SessionLocal
from dataaccess.mcp_repo import MCPRepo
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Any, Iterator

load_dotenv('.env')

# 创建回调处理器 - 使用环境变量配置
langfuse_handler = CallbackHandler()
# 创建 Langfuse 客户端（用于 flush）
langfuse = Langfuse( environment="local",release="langfuse-auto-trace-test",debug=False)
#langfuse.auth_check()


class _FilteredChatModel(BaseChatModel):
    """BaseChatModel 包装器，用于适配 deepagents 框架。
    deepagents 需要模型是 BaseChatModel 实例。
    """

    model: BaseChatModel

    def _generate(
        self,
        messages,
        stop,
        run_manager,
        **kwargs,
    ) -> ChatResult:
        return self.model._generate(messages, stop, run_manager, **kwargs)

    def _stream(
        self,
        messages,
        stop,
        run_manager,
        **kwargs,
    ) -> Iterator[ChatGeneration]:
        return self.model._stream(messages, stop, run_manager, **kwargs)

    async def _agenerate(
        self,
        messages,
        stop,
        run_manager,
        **kwargs,
    ) -> ChatResult:
        return await self.model._agenerate(messages, stop, run_manager, **kwargs)

    async def _astream(
        self,
        messages,
        stop,
        run_manager,
        **kwargs,
    ):
        async for chunk in self.model._astream(messages, stop, run_manager, **kwargs):
            yield chunk

    def bind_tools(
        self,
        tools: Any,
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ):
        """委托 bind_tools 到底层模型"""
        bound = self.model.bind_tools(tools, tool_choice=tool_choice, **kwargs)
        if isinstance(bound, BaseChatModel):
            return _FilteredChatModel(model=bound)
        return bound

    @property
    def _llm_type(self) -> str:
        return self.model._llm_type

    @property
    def model_name(self) -> str:
        return getattr(self.model, 'model_name', 'unknown')

    def invoke(self, input, config=None, **kwargs):
        """重写 invoke 方法"""
        return self.model.invoke(input, config=config, **kwargs)

    async def ainvoke(self, input, config=None, **kwargs):
        """重写异步 invoke 方法"""
        return await self.model.ainvoke(input, config=config, **kwargs)

    async def astream(self, input, config=None, **kwargs):
        """重写异步 stream 方法"""
        async for chunk in self.model.astream(input, config=config, **kwargs):
            yield chunk


def _wrap_model(llm):
    """包装模型为 deepagents 兼容的 BaseChatModel 实例"""
    return _FilteredChatModel(model=llm)

def get_llm(temperature=0.6, top_p=0.9, model_id=None):
    """获取配置好的LLM实例"""
    # 如果指定了 model_id，从数据库获取模型配置
    if model_id:
        try:
            db = SessionLocal()
            try:
                model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
                if model:
                    return _wrap_model(ChatOpenAI(
                        model=model.model_name,
                        temperature=temperature,
                        top_p=top_p,
                        streaming=True,
                        base_url=model.base_url,
                        api_key=model.api_key,
                        callbacks=[langfuse_handler]
                    ))
            finally:
                db.close()
        except Exception as e:
            logger.error(f"根据 model_id 获取模型失败: {e}")
    
    # 默认返回 deepseek-chat
    return _wrap_model(ChatOpenAI(
        model='deepseek-chat',
        temperature=temperature,
        top_p=top_p,
        streaming=True,
        callbacks=[langfuse_handler]
    ))

def get_llm_with_config(model_name, base_url, api_key, temperature=0.6, top_p=0.9):
    """根据配置获取LLM实例"""
    return _wrap_model(ChatOpenAI(
        model=model_name,
        temperature=temperature,
        top_p=top_p,
        streaming=True,
        base_url=base_url,
        api_key=api_key
    ))

def get_llm_sync(temperature=0.6, top_p=0.9, model_id=None):
    """获取用于同步调用的LLM实例（不带Langfuse回调，避免流式追踪问题）
    
    适用于简单的同步调用场景，如生成英文名称、生成技能描述等。
    使用方式与 get_llm() 相同，但不会触发 Langfuse 追踪。
    """
    # 如果指定了 model_id，从数据库获取模型配置
    if model_id:
        try:
            db = SessionLocal()
            try:
                model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
                if model:
                    return ChatOpenAI(
                        model=model.model_name,
                        temperature=temperature,
                        top_p=top_p,
                        streaming=False,  # 同步调用不使用流式
                        base_url=model.base_url,
                        api_key=model.api_key
                    )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"根据 model_id 获取同步模型失败: {e}")
    
    # 默认返回 deepseek-chat（不带回调）
    return ChatOpenAI(
        model='deepseek-chat',
        temperature=temperature,
        top_p=top_p,
        streaming=False  # 同步调用不使用流式
    )

def test_llm_connection(model_name, base_url, api_key, temperature=0.6, top_p=0.9):
    """
    测试LLM连接
    返回 (success: bool, message: str)
    """
    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            top_p=top_p,
            streaming=False,
            base_url=base_url,
            api_key=api_key
        )
        # 发送一个简单的测试消息
        response = llm.invoke("Hello")
        if response and hasattr(response, 'content') and response.content:
            return True, "连接成功"
        else:
            return False, "连接失败：无法获取响应"
    except Exception as e:
        logger.exception("LLM连接测试失败")
        # 提取友好的错误信息，避免返回HTML内容
        error_msg = str(e)
        # 如果错误信息包含HTML，提取关键信息
        if '<html>' in error_msg.lower() or '<!doctype' in error_msg.lower():
            # 尝试提取HTTP状态码
            import re
            # 匹配类似 "405 Not Allowed" 的模式
            http_match = re.search(r'(\d{3})\s+([^<\n]+)', error_msg)
            if http_match:
                code, status = http_match.groups()
                error_msg = f"HTTP {code} {status.strip()}"
            else:
                error_msg = "连接失败：服务器返回错误页面"
        # 限制错误信息长度
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        return False, f"连接失败: {error_msg}"





def create_agent_with_skills(llm, skill_sources, filesystem_backend, checkpointer, system_prompt=None, tools=None):
    """创建带技能的DeepAgent"""
    # 构建可用技能列表
    available_skills = ", ".join([s.strip("/") for s in skill_sources]) if skill_sources else "无"
    
    # 如果提供了自定义系统提示词，需要确保包含技能信息
    # 因为当 system_prompt 不为 None 时，deepagents 不会自动生成技能相关的提示词
    if system_prompt:
        # 检查提示词是否包含技能信息标记
        if "{available_skills}" in system_prompt:
            # 用户自己在提示词中使用了变量，进行替换
            system_prompt = system_prompt.replace("{available_skills}", available_skills)
            logger.info(f"使用自定义系统提示词，已替换技能列表变量")
    today=datetime.datetime.now().strftime("%Y%m%d")
    today_desc='当前日期为：'+today
    system_prompt+=today_desc
    # 如果 tools 已经是 LangChain BaseTool 对象（来自 MCP 工具），直接使用
    if tools and isinstance(tools[0], BaseTool):
        logger.info(f"tools 已经是 BaseTool 对象，直接使用 {len(tools)} 个工具")
        return create_deep_agent(
            model=llm,
            skills=skill_sources,
            backend=filesystem_backend,
            checkpointer=checkpointer,
            system_prompt=system_prompt,
            tools=tools
        )
    
    # 如果 tools 是字符串列表，尝试从数据库重新查询
    if tools and isinstance(tools[0], str):
        logger.warning(f"tools 是字符串列表，尝试从数据库重新查询")

        db = SessionLocal()
        try:
            new_tools = []
            for tool_name in tools:
                all_tools = MCPToolRepo.get_all(db)
                for t in all_tools:
                    if t.name == tool_name:
                        new_tools.append({
                            'id': t.id,
                            'name': t.name,
                            'description': t.description,
                            'parameters': t.parameters,
                            'mcp_id': t.mcp_id
                        })
                        logger.info(f"按名称找到工具: {t.name} (ID: {t.id})")
                        break
            tools = new_tools
        finally:
            db.close()
    
    # 转换 MCP 工具为 LangChain 工具
    langchain_tools = []
    if tools:
        logger.info(f"开始转换 {len(tools)} 个工具")
        for i, tool in enumerate(tools):
            try:
                logger.info(f"转换工具 {i+1}/{len(tools)}: {tool}, 类型: {type(tool)}")
                if isinstance(tool, str):
                    logger.error(f"工具是字符串而不是字典: {tool}")
                    continue
                lc_tool = convert_mcp_tool_to_langchain(tool)
                if lc_tool:
                    langchain_tools.append(lc_tool)
                    logger.info(f"工具转换成功: {lc_tool.name}")
            except Exception as e:
                tool_name = tool if isinstance(tool, str) else tool.get('name', 'unknown') if isinstance(tool, dict) else 'unknown'
                logger.error(f"转换工具失败: {tool_name}, 错误: {e}")
        logger.info(f"成功转换 {len(langchain_tools)} 个工具")
    
    # 如果没有 MCP 工具，不传 tools 参数，让 deepagents 使用内置工具
    return create_deep_agent(
        model=llm,
        skills=skill_sources,
        backend=filesystem_backend,
        checkpointer=checkpointer,
        system_prompt=system_prompt,
        tools=langchain_tools if langchain_tools else None
    )


def _parse_parameters(parameters_str) -> dict:
    """解析参数 schema，兼容 JSON 和 Python repr 两种格式"""
    if not parameters_str:
        return {}
    
    if isinstance(parameters_str, dict):
        return parameters_str
    
    if not isinstance(parameters_str, str):
        logger.warning(f"参数格式异常: {type(parameters_str)}")
        return {}
    
    try:
        result = json.loads(parameters_str)
        if isinstance(result, str):
            logger.info(f"参数是双重编码的字符串，尝试再次解析: {result[:100]}")
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.info(f"JSON 解析失败，尝试 ast.literal_eval")
                return ast.literal_eval(result)
        return result
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"JSON 解析失败: {e}")
        try:
            return ast.literal_eval(parameters_str)
        except Exception as e2:
            logger.error(f"ast.literal_eval 也失败: {e2}")
            return {}


def convert_mcp_tool_to_langchain(tool_data: dict) -> Any:
    """将 MCP 工具数据转换为 LangChain 工具"""
    
    if not isinstance(tool_data, dict):
        logger.error(f"工具数据格式错误: 期望字典，实际得到 {type(tool_data)}: {tool_data}")
        return None
    
    tool_name = tool_data.get('name', '')
    tool_description = tool_data.get('description', '')
    parameters = _parse_parameters(tool_data.get('parameters', '{}'))
    mcp_id = tool_data.get('mcp_id', '')
    
    logger.info(f"解析后的参数: {parameters}, 类型: {type(parameters)}")
    
    if not isinstance(parameters, dict):
        logger.warning(f"parameters 不是字典: {parameters}")
        parameters = {}
    
    properties = parameters.get('properties', {})
    required = parameters.get('required', [])
    
    fields = {}
    for param_name, param_info in properties.items():
        if isinstance(param_info, str):
            logger.warning(f"参数 {param_name} 的信息是字符串: {param_info}")
            param_info = {}
        
        param_type = param_info.get('type', 'string') if isinstance(param_info, dict) else 'string'
        
        type_map = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
        }
        field_type = type_map.get(param_type, str)
        
        fields[param_name] = (field_type, ... if param_name in required else None)
    
    ArgsModel = create_model(f'{tool_name}Args', **fields) if fields else create_model(f'{tool_name}Args', __base__=BaseModel)
    
    async def _async_tool_func(**kwargs):
        """异步执行 MCP 工具调用"""

        # 创建 Langfuse span 追踪工具执行
        # 创建独立的 span（observation），后续可以通过时间戳关联到 trace
        
        db = SessionLocal()
        try:
            mcp = MCPRepo.get_by_id(db, mcp_id)
            if not mcp:
                return f"错误: MCP 服务不存在"
            
            server_name = mcp.name or f"mcp_{mcp_id}"
            
            # 基础请求头 - 服务器需要这些头来接受请求
            base_headers = {
                "Accept": "application/json, text/event-stream",
                "Accept-Encoding": "identity"
            }
            
            if mcp.type == 'sse':
                connection_config = {server_name: {"transport": "sse", "url": mcp.endpoint, "headers": base_headers}}
            elif mcp.type == 'streamable-http':
                connection_config = {server_name: {"transport": "streamable_http", "url": mcp.endpoint, "headers": base_headers}}
            else:
                return f"错误: 不支持的 MCP 类型: {mcp.type}"
            
            client = MultiServerMCPClient(connection_config)
            tools = await client.get_tools()
            
            target_tool = next((t for t in tools if getattr(t, 'name', '') == tool_name), None)
            if not target_tool:
                return f"错误: 工具 {tool_name} 在 MCP 服务器上不存在"
            
            result = await target_tool.ainvoke(kwargs)

            return result
            
        except Exception as e:
            logger.exception(f"调用 MCP 工具失败: {tool_name}")

            return f"调用工具失败: {str(e)}"
        finally:
            db.close()
    
    def _sync_tool_func(**kwargs):
        """同步执行 MCP 工具调用（通过新事件循环包装异步函数）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_async_tool_func(**kwargs))
        finally:
            loop.close()
    
    return StructuredTool(
        name=tool_name,
        description=tool_description,
        func=_sync_tool_func,
        args_schema=ArgsModel,
        coroutine=_async_tool_func
    )


def create_agent_without_skills(llm, checkpointer):
    """创建不带技能的DeepAgent"""
    return create_deep_agent(
        model=llm,
        checkpointer=checkpointer
    )


def stream_chat_response(agent, content, conversation, checkpoint_limit=20, use_memory=True):
    """
    流式聊天响应生成器
    返回 SSE 格式的数据流
    use_memory: 是否使用记忆功能，为False时不设置thread_id，避免从checkpoint加载历史
    """

    if use_memory:
        config = {"configurable": {"thread_id": conversation, "checkpoint_limit": checkpoint_limit,"callbacks": [langfuse_handler]}}
    else:
        # 不使用记忆时，不设置 thread_id，避免从 checkpoint 加载历史
        config = {"configurable": {"callbacks": [langfuse_handler]}}
        logger.info(f"不使用记忆功能，不设置 thread_id: conversation={conversation}")
    
    ai_response_parts = []

    try:
        # 尝试流式输出，捕获检查点相关的序列化错误
        stream_iterator = agent.stream(
                {"messages": [{"role": "user", "content": content}]},
                config=config,
                stream_mode="messages"
        )

        for chunk, metadata in stream_iterator:
            # 检查是否被取消
            if asyncio.current_task() and asyncio.current_task().cancelled():
                logger.info("流式输出被取消")
                raise asyncio.CancelledError()

            # 只输出 AI 模型的文本 token，过滤工具返回结果消息（ToolMessage）
            if not isinstance(chunk, AIMessageChunk):
                continue
            if not chunk.content:
                continue
            # chunk.content 可能是 str 或 list（如 tool_calls 时的内容块列表）
            if isinstance(chunk.content, str):
                content_text = chunk.content
            elif isinstance(chunk.content, list):
                # 从内容块列表中提取文本
                text_parts = []
                for block in chunk.content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                content_text = ''.join(text_parts)
                if not content_text:
                    continue
            else:
                continue
            ai_response_parts.append(content_text)
            yield f"data: {json.dumps({'type': 'token', 'content': content_text}, ensure_ascii=False)}\n\n"

        langfuse.flush()

    except asyncio.CancelledError:
        logger.info("流式输出被取消，清理资源")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception("聊天流式输出错误")

        # 检查是否是 Redis 检查点序列化错误
        if "JSONDecodeError" in error_msg or "unexpected character" in error_msg:
            logger.error("检测到 Redis 检查点数据损坏，建议清理检查点数据")
            error_msg = "会话数据损坏，请使用新的会话 ID 重试"

        # 检查是否是 image_url 不支持的错误
        if "image_url" in error_msg or "unknown variant" in error_msg:
            logger.error(f"检测到模型不支持 image_url 类型的消息: {error_msg}")
            error_msg = "当前会话包含图像数据，但当前模型不支持图像输入。请使用新的会话 ID 重试。"

        # 检查是否是 LangGraph Redis 序列化器错误
        if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
            logger.error(f"检测到 LangGraph Redis 序列化器错误: {error_msg}")
            error_msg = "会话存储出现兼容性问题，请使用新的会话 ID 重试"

        # 检查是否是 DeepSeek 推理模式错误
        if "reasoning_content" in error_msg or "thinking mode" in error_msg:
            logger.error(f"检测到 DeepSeek 推理模式错误: {error_msg}")
            error_msg = "当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。"

        yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"
        return

    yield f"data: {json.dumps({'type': 'end', 'conversation_id': conversation}, ensure_ascii=False)}\n\n"


async def async_stream_chat_response(agent, content, conversation, checkpoint_limit=20, use_memory=True):
    """
    异步流式聊天响应生成器
    返回 SSE 格式的数据流
    use_memory: 是否使用记忆功能，为False时不设置thread_id，避免从checkpoint加载历史
    """

    if use_memory:
        config = {"configurable": {"thread_id": conversation, "checkpoint_limit": checkpoint_limit,"callbacks": [langfuse_handler]}}
    else:
        # 不使用记忆时，不设置 thread_id，避免从 checkpoint 加载历史
        config = {"configurable": {"callbacks": [langfuse_handler]}}
        logger.info(f"不使用记忆功能，不设置 thread_id: conversation={conversation}")
    
    ai_response_parts = []

    try:
        # 使用异步流式输出
        stream_iterator = agent.astream(
                {"messages": [{"role": "user", "content": content}]},
                config=config,
                stream_mode="messages"
        )

        async for chunk, metadata in stream_iterator:
            # 只输出 AI 模型的文本 token，过滤工具返回结果消息（ToolMessage）
            if not isinstance(chunk, AIMessageChunk):
                continue
            if not chunk.content:
                continue
            # chunk.content 可能是 str 或 list（如 tool_calls 时的内容块列表）
            if isinstance(chunk.content, str):
                content_text = chunk.content
            elif isinstance(chunk.content, list):
                # 从内容块列表中提取文本
                text_parts = []
                for block in chunk.content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                content_text = ''.join(text_parts)
                if not content_text:
                    continue
            else:
                continue
            ai_response_parts.append(content_text)
            yield f"data: {json.dumps({'type': 'token', 'content': content_text}, ensure_ascii=False)}\n\n"

        langfuse.flush()

    except asyncio.CancelledError:
        logger.info("异步流式输出被取消，清理资源")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.exception("异步聊天流式输出错误")

        # 检查是否是 Redis 检查点序列化错误
        if "JSONDecodeError" in error_msg or "unexpected character" in error_msg:
            logger.error("检测到 Redis 检查点数据损坏，建议清理检查点数据")
            error_msg = "会话数据损坏，请使用新的会话 ID 重试"

        # 检查是否是 image_url 不支持的错误
        if "image_url" in error_msg or "unknown variant" in error_msg:
            logger.error(f"检测到模型不支持 image_url 类型的消息: {error_msg}")
            error_msg = "当前会话包含图像数据，但当前模型不支持图像输入。请使用新的会话 ID 重试。"

        # 检查是否是 LangGraph Redis 序列化器错误
        if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
            logger.error(f"检测到 LangGraph Redis 序列化器错误: {error_msg}")
            error_msg = "会话存储出现兼容性问题，请使用新的会话 ID 重试"

        # 检查是否是 DeepSeek 推理模式错误
        if "reasoning_content" in error_msg or "thinking mode" in error_msg:
            logger.error(f"检测到 DeepSeek 推理模式错误: {error_msg}")
            error_msg = "当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。"

        yield f"data: {json.dumps({'type': 'error', 'content': error_msg}, ensure_ascii=False)}\n\n"
        return

    yield f"data: {json.dumps({'type': 'end', 'conversation_id': conversation}, ensure_ascii=False)}\n\n"


def get_deepagent_response_with_stream(skill_sources, filesystem_backend, checkpointer, conversation, content,
                                       temperature=0.7, top_p=0.9, tools=None, model_id=None, use_memory=True,
                                       system_prompt=None):
    """
    完整的流式响应接口：创建LLM -> 创建Agent -> 流式输出
    这是一个生成器函数，需要使用 for 或 yield from 来调用
    use_memory: 是否使用记忆功能
    system_prompt: 自定义系统提示词，如果为None则使用默认提示词
    """
    logger.info(f"get_deepagent_response_with_stream 接收到的 tools: {tools}, 类型: {type(tools)}, use_memory={use_memory}")
    if tools:
        for i, t in enumerate(tools):
            logger.info(f"  工具 {i}: {t}, 类型: {type(t)}")

    llm = get_llm(temperature=temperature, top_p=top_p, model_id=model_id)
    agent = create_agent_with_skills(llm, skill_sources, filesystem_backend, checkpointer, tools=tools, system_prompt=system_prompt)

    try:
        yield from stream_chat_response(agent, content, conversation, use_memory=use_memory)
    except Exception as e:
        error_msg = str(e)
        logger.exception("流式输出外层捕获错误")

        # 检查是否是 LangGraph Redis 序列化器错误
        if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
            logger.error(f"外层捕获到 LangGraph Redis 序列化器错误: {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'content': '会话存储出现兼容性问题，请使用新的会话 ID 重试'}, ensure_ascii=False)}\n\n"
            return

        # 检查是否是 DeepSeek 推理模式错误
        if "reasoning_content" in error_msg or "thinking mode" in error_msg:
            logger.error(f"外层捕获到 DeepSeek 推理模式错误: {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'content': '当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。'}, ensure_ascii=False)}\n\n"
            return

        # 其他错误重新抛出
        raise


async def get_deepagent_response_with_stream_async(skill_sources, filesystem_backend, checkpointer, conversation, content,
                                                   temperature=0.7, top_p=0.9, tools=None, model_id=None, use_memory=True,
                                                   system_prompt=None):
    """
    异步流式响应接口：创建LLM -> 创建Agent -> 异步流式输出
    这是一个异步生成器函数，需要使用 async for 来调用
    use_memory: 是否使用记忆功能
    system_prompt: 自定义系统提示词，如果为None则使用默认提示词
    """
    logger.info(f"get_deepagent_response_with_stream_async 接收到的 tools: {tools}, 类型: {type(tools)}, use_memory={use_memory}")
    if tools:
        for i, t in enumerate(tools):
            logger.info(f"  工具 {i}: {t}, 类型: {type(t)}")

    llm = get_llm(temperature=temperature, top_p=top_p, model_id=model_id)
    agent = create_agent_with_skills(llm, skill_sources, filesystem_backend, checkpointer, tools=tools, system_prompt=system_prompt)

    try:
        async for data in async_stream_chat_response(agent, content, conversation, use_memory=use_memory):
            yield data
    except Exception as e:
        error_msg = str(e)
        logger.exception("异步流式输出外层捕获错误")

        # 检查是否是 LangGraph Redis 序列化器错误
        if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
            logger.error(f"外层捕获到 LangGraph Redis 序列化器错误: {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'content': '会话存储出现兼容性问题，请使用新的会话 ID 重试'}, ensure_ascii=False)}\n\n"
            return

        # 检查是否是 DeepSeek 推理模式错误
        if "reasoning_content" in error_msg or "thinking mode" in error_msg:
            logger.error(f"外层捕获到 DeepSeek 推理模式错误: {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'content': '当前模型启用了推理模式，但会话不支持推理内容传递。请使用新的会话 ID 重试。'}, ensure_ascii=False)}\n\n"
            return

        # 其他错误重新抛出
        raise



def get_deepagent_response_sync(skill_sources, filesystem_backend, checkpointer, conversation, content,
                                temperature=0.7, top_p=0.9, system_prompt=None):
    """
    同步非流式响应接口
    返回完整的AI响应字符串
    system_prompt: 自定义系统提示词，如果为None则使用默认提示词
    """
    llm = get_llm(temperature=temperature, top_p=top_p)

    if skill_sources:
        agent = create_agent_with_skills(llm, skill_sources, filesystem_backend, checkpointer, system_prompt=system_prompt)
    else:
        agent = create_agent_without_skills(llm, checkpointer)

    config = {"configurable": {"thread_id": conversation, "checkpoint_limit": 20}}

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": content}]},
            config=config
        )
        langfuse.flush()
        # 提取响应内容
        if result and "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                return last_message.content
            elif isinstance(last_message, dict):
                return last_message.get("content", "抱歉，我无法处理您的请求。")
    except Exception as e:
        error_msg = str(e)
        logger.exception("同步聊天错误")
        
        # 检查是否是 LangGraph Redis 序列化器错误
        if "_encode_constructor_args" in error_msg or "JsonPlusRedisSerializer" in error_msg:
            logger.error(f"检测到 LangGraph Redis 序列化器错误: {error_msg}")
            return "会话存储出现兼容性问题，请使用新的会话 ID 重试"
        
        return f"抱歉，处理请求时出错: {error_msg}"

    return "抱歉，我无法处理您的请求。"
