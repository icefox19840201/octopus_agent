import settings
import json
import redis
import os
import traceback
import requests
from urllib.parse import quote, urlparse, urlunparse
from utils.logger import logger
import asyncio
from pathlib import Path
from biziness.rag_service import RagService

redis_client=redis.Redis(host=settings.redis_mq_host, port=settings.redis_mq_port,
                         db=settings.redis_mq_db, decode_responses=settings.redis_mq_decode_responses)
async def producer(filepath,kb_id):
    '''
    redis生产端
    '''
    try:
        task = {
            "file_path": filepath,
            "kb_id":kb_id
        }

        redis_client.lpush(settings.redis_mq_queue_key, json.dumps(task))
        print("任务已入队")
        return True
    except:
        msg=traceback.format_exc()
        logger.exception(msg)
        return False

def get_kb_queue_tasks(kb_id):
    '''
    查询指定知识库在 redis 队列中排队中的上传任务

    队列使用 lpush 入队、brpop 出队，队列中可能同时存在多个知识库的任务，
    这里按 kb_id 严格过滤，确保只返回当前知识库的排队信息，避免不同知识库混淆。

    :param kb_id: 知识库ID
    :return: 该知识库排队中的任务列表（按出队处理顺序排列）
    '''
    try:
        if not kb_id:
            logger.warning('[队列查询] kb_id 为空，无法查询排队信息')
            return []

        queue_key = settings.redis_mq_queue_key
        raw_items = redis_client.lrange(queue_key, 0, -1)
        logger.info(f'[队列查询] 知识库 {kb_id} 开始查询，队列键={queue_key}，队列总任务数={len(raw_items)}')

        tasks = []
        for raw in raw_items:
            try:
                task = json.loads(raw)
            except Exception:
                logger.warning(f'[队列查询] 知识库 {kb_id} 发现无法解析的队列数据，已跳过: {raw}')
                continue
            # 严格校验 kb_id，只收集当前知识库的任务
            if task.get('kb_id') == kb_id:
                tasks.append(task)

        # lrange 返回头→尾（新→旧），reverse 后为最早入队在前，符合出队处理顺序
        tasks.reverse()
        file_paths = [t.get('file_path') for t in tasks]
        logger.info(f'[队列查询] 知识库 {kb_id} 命中排队任务数={len(tasks)}，文件列表={file_paths}')
        return tasks
    except Exception:
        logger.exception(f'[队列查询] 查询知识库 {kb_id} 排队信息失败: {traceback.format_exc()}')
        return []


async def consumer():
    '''
    redis 消费端
    '''
    while True:
        try:
            pop_res= redis_client.brpop(settings.redis_mq_queue_key, timeout=1)
            if pop_res is None:
                logger.info('队列为空，消费端正常运行')
                await asyncio.sleep(3)
                continue
            _, data = pop_res
            task = json.loads(data)
            print("收到上传任务：", task.get("file_path", "未知文件"))
            #下载文件到临时目录
            download_temp_dir=settings.rag_download_temp_dir
            os.makedirs(download_temp_dir, exist_ok=True)

            #下载
            file_url = task.get("file_path")
            kb_id=task.get('kb_id')
            parsed = urlparse(file_url)
            encoded_path = quote(parsed.path)
            encoded_url = urlunparse(parsed._replace(path=encoded_path))
            file_name = Path(parsed.path).name
            local_file_path = os.path.join(download_temp_dir, file_name)
            response = requests.get(encoded_url, timeout=60)
            response.raise_for_status()

            with open(local_file_path, 'wb') as f:
                f.write(response.content)
            doc_file_path = local_file_path
            RagService.know2db(doc_file_path, encoded_url,kb_id)
            os.remove(local_file_path)

        except:
            msg=traceback.format_exc()
            logger.exception(msg)

