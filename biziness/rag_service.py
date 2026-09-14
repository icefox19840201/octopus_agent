from utils.logger import logger
from typing import List,Optional
from pathlib import Path
from mineru.cli.common import do_parse , read_fn
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llama_index.core import Document,VectorStoreIndex,StorageContext,load_index_from_storage
from llama_index.core import settings as llamaindex_settings
from llama_index.core.schema import TextNode
from llama_index.core.retrievers import VectorIndexRetriever,QueryFusionRetriever
from llama_index.core.schema import NodeWithScore,QueryBundle
from llama_index.llms.openai import OpenAI
from llama_index.core.schema import RelatedNodeInfo, NodeRelationship
#pip install llama-index-vector-stores-milvus
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
#pip install llama-index-retrievers-bm25
from pymilvus import DataType
from llama_index.retrievers.bm25 import BM25Retriever
#pip install sentence-transformers torch torchvision torchaudio
from sentence_transformers import CrossEncoder
import settings
import os
import re
import uuid

class BGEReranker:
    """BGE Cross-Encoder Reranker"""

    def __init__(self, model, top_k=5):
        self._model = model
        self._top_k = top_k

    def rerank(self, query: str, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """
        使用 BGE Cross-Encoder 对节点进行重排序
        """
        if not nodes:
            return []

        # 构建 query-document pairs
        pairs = [[query, node.text] for node in nodes]

        # 使用 Cross-Encoder 预测相关性分数
        scores = self._model.predict(pairs)

        # 创建新的节点列表，使用 rerank 分数
        reranked_nodes = []
        for i, node in enumerate(nodes):
            new_node = NodeWithScore(
                node=node.node,
                score=float(scores[i])
            )
            reranked_nodes.append(new_node)

        # 按分数降序排序
        reranked_nodes.sort(key=lambda x: x.score, reverse=True)

        return reranked_nodes[:self._top_k]

class RagService:
    #----------------------------rag入库部分-----------------------------
    @classmethod
    def know2db(cls, filepath: str, download_url: str,kb_id:str):
        """
        将文档转换为向量并存储到数据库
        
        Args:
            filepath: 文档文件路径
            download_url: 文档下载地址
            doc_id: 文档唯一标识（必须传入）
            
        Returns:

        """
        # 文件扩展名
        file_ex_name_with_mineru = ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.pdf']
        file_ex_name_without_mineru = ['.txt', '.md']
        file_ex_with_audio = ['wav', 'mp3']
        file_ex = Path(filepath).suffix
        doc_id = str(uuid.uuid4())
        logger.info(f'kb_id====>{kb_id}')
        if file_ex in file_ex_name_with_mineru or file_ex in file_ex_name_without_mineru:
            markdown_path = cls.docs2_markdown(filepath)
            
            # 传递完整的 metadata，包括 category 和 doc_id
            metadata = {
                'source': download_url,
                'doc_id': doc_id,
                'file_name': Path(filepath).name,
                'file_type': file_ex
            }
            
            logger.info(f'开始切分文档: {Path(filepath).name}')
            logger.info(f'  - source: {download_url}')
            
            nodes = cls.split_markdown_file(
                markdown_path, 
                chunk_size=800, 
                chunk_overlap=200, 
                remove_images=True, 
                metadata=metadata
            )
            
            logger.info(f'切分完成，生成 {len(nodes)} 个节点')
            logger.info(f'开始向量化并入库...')
            
            cls.embeddingdoc2db(nodes,collection_name=kb_id)
            logger.info('入库完成...')

        elif file_ex in file_ex_with_audio:
            logger.warning(f'音频文件暂不支持: {filepath}')
            pass
        else:
            logger.error(f'不支持的文件类型: {file_ex}')
            return None
    @classmethod
    def docs2_markdown(cls,doc_path: str):
        '''
        将文档转为markdown文档（word/excel/pdf/ppt）
        '''
        os.environ.setdefault("MODELSCOPE_CACHE", settings.mineru_model_path)
        doc_obj = Path(doc_path)
        doc_bin = read_fn(doc_obj)
        do_parse(
            output_dir=settings.out_dir,
            pdf_file_names=[doc_obj.stem],
            pdf_bytes_list=[doc_bin],
            p_lang_list=["ch"],
            backend="pipeline",
            parse_method="auto",
            formula_enable=True,
            table_enable=True,
            start_page_id=0,
            end_page_id=None,
        )

        result_root = Path(settings.out_dir) / doc_obj.stem / "auto"
        markdown_path = str(result_root / f"{doc_obj.stem}.md")
        logger.info('markdown_path===={}'.format(markdown_path))
        return markdown_path

    @classmethod
    def audio2text(cls,markdown_path: str):
        '''
        音频转文本
        需要安装ffmpeg
        '''
        # model = AutoModel(
        #     model=r"E:\bigmodel\modelscope_model\asr\SenseVoiceSmall",
        #     vad_model="./asr_models/iic/fsmn-vad",
        #     device="cpu"
        # )

        #res = model.generate(input="offline_audio.wav", language="zh")
        pass
    @classmethod
    def get_milvus(cls,collection_name):
        vector_store = MilvusVectorStore(
            uri=settings.MILVUS_URI,
            collection_name=collection_name,
            dim=settings.VECTOR_DIM,
            overwrite=True,

            # 向量索引配置
            index_config={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200}
            },

            # 搜索配置
            search_config={
                "metric_type": "COSINE",
                "params": {"ef": 64}
            },

            scalar_field_names=["file_name", "file_type", "source"],
            scalar_field_types=[
                DataType.VARCHAR,  # file_name
                DataType.VARCHAR,  # file_type
                DataType.VARCHAR  # source
            ],
            output_fields=["doc_id", "file_name", "file_type", "source"],
            user=settings.MILVUS_USER,
            password=settings.DB_PASSWORD,
            db_name=settings.rag_db_name
        )
        return vector_store

    @classmethod
    def get_embed_model(cls):
        '''
        获取embedding模型
        '''
        embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu",
            normalize=True
        )
        llamaindex_settings.Settings.embed_model = embed_model
        return embed_model

    @classmethod
    def embeddingdoc2db(cls, node, collection_name='test'):
        '''
        文档入库 - 确保 category 和其他自定义字段作为独立标量字段
        注意：doc_id 字段已由 MilvusVectorStore 自动创建，不需要在 scalar_field_names 中重复定义
        '''
        logger.info('准备入库')
        cls.get_embed_model()
        vector_store=cls.get_milvus(collection_name=collection_name)
        storage_content = StorageContext.from_defaults(vector_store=vector_store)
        vector_index = VectorStoreIndex(nodes=node, storage_context=storage_content)
        os.makedirs(settings.INDEX_DIR, exist_ok=True)
        vector_index.storage_context.persist(os.path.join(settings.EMBEDINDEX_DIR,collection_name))
        print(f"✓ Milvus 向量索引创建成功: {collection_name}")
        print(f"  - 向量维度: {settings.VECTOR_DIM}")
        print(f"  - 节点数量: {len(node)}")
        print(f"  - 索引类型: HNSW (COSINE)")
        
        # bm25索引创建
        print('创建bm25索引')
        bm25_retriever = BM25Retriever.from_defaults(
            nodes=node,
            similarity_top_k=20,
            verbose=False
        )
        os.makedirs(os.path.join(settings.BM25_INDEX_DIR,collection_name), exist_ok=True)
        bm25_retriever.persist(os.path.join(settings.BM25_INDEX_DIR,collection_name))
        print('bm25索引创建完成')


    @classmethod
    def _remove_image_references(cls, text: str) -> str:
        """去除 Markdown 图片引用和 HTML <img> 标签。"""
        before_len = len(text)
        # 逐行过滤：任何包含图片引用特征的行直接删除
        lines = text.splitlines()
        filtered = []
        for line in lines:
            stripped = line.strip()
            # 匹配 ![...](...) 形式的 Markdown 图片
            if re.search(r"!\[.*?\]\(", stripped):
                continue
            # 匹配 <img 标签
            if re.search(r"<img\b", stripped, re.IGNORECASE):
                continue
            filtered.append(line)
        text = "\n".join(filtered)
        # 清理连续空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()
        logger.info(f"_remove_image_references: 原长度 {before_len}, 新长度 {len(text)}")
        return text


    @classmethod
    def _extract_html_tables(cls,text: str) -> tuple[List[str], str]:
        """提取 HTML ``<table>...</table>`` 表格，返回 (表格列表, 替换后的文本)。
           提取出的表格会用 ``__TABLE_BLOCK_{idx}__`` 占位符代替，
        """
        pattern = re.compile(r"<table[\s\S]*?</table>", re.IGNORECASE)
        tables: List[str] = []
        def replacer(match: re.Match) -> str:
            tables.append(match.group(0))
            return f"\n__TABLE_BLOCK_{len(tables) - 1}__\n"
        replaced = pattern.sub(replacer, text)
        return tables, replaced

    @classmethod
    def _extract_markdown_tables(cls,text: str) -> tuple[List[str], str]:
        """提取 Markdown ``|`` 表格，返回 (表格列表, 替换后的文本)。

        识别规则：
        1. 连续多行以 ``|`` 开头；
        2. 至少包含表头和分隔行；
        3. 分隔行符合 ``|---|---|`` 形式（允许 ``:`` 对齐标记和空格）。
        """
        lines = text.splitlines(keepends=True)
        tables: List[str] = []
        output: List[str] = []
        i = 0
        n = len(lines)

        while i < n:
            stripped = lines[i].strip()
            # 行首为 | 表示可能进入表格区域
            if stripped.startswith("|"):
                table_lines: List[str] = []
                while i < n and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                # 至少包含表头和分隔行，且分隔行符合 |---|---| 形式
                if (
                        len(table_lines) >= 2
                        and re.match(r"^\|[-:\|\s]+\|$", table_lines[1].strip())
                ):
                    tables.append("".join(table_lines))
                    output.append(f"\n__TABLE_BLOCK_{len(tables) - 1}__\n")
                else:
                    # 不满足表格结构，按普通文本原样保留
                    output.extend(table_lines)
            else:
                output.append(lines[i])
                i += 1

        return tables, "".join(output)

    @classmethod
    def _extract_tables(cls,text: str) -> tuple[List[str], str]:
        """提取文本中的所有表格（HTML 表格优先，再识别 Markdown 表格）。"""
        # 先提取 HTML 表格，避免 HTML 表格内部出现 | 字符时被误判为 Markdown 表格
        html_tables, text_after_html = cls._extract_html_tables(text)
        # 再提取 Markdown 表格
        md_tables, text_after_md = cls._extract_markdown_tables(text_after_html)
        return html_tables + md_tables, text_after_md

    @classmethod
    def split_documents_preserve_tables(cls,
            text: str,
            chunk_size: int = 800,
            chunk_overlap: int = 100,
            separators: Optional[List[str]] = None,
            metadata: Optional[dict] = None,
            remove_images: bool = True,
            base_dir: Optional[str] = None,
            **kwargs,
    ) -> List[Document]:
        """对 Markdown / HTML 混排文本进行切割，确保表格完整不被截断。

            text: 待切分的文本。
            chunk_size: 非表格文本的目标块大小（表格本身会作为整体保留，可能超出此大小）。
            chunk_overlap: 块间重叠字符数。
            separators: 切分分隔符，默认按段落、句子、词语逐级切分。
            metadata: 附加到每个 Document 的元数据（包含 doc_id 等）。
            remove_images: 是否去除 Markdown 图片引用，默认为 True。
        """

        # 提取表格并用占位符替换，防止表格被截断
        tables, placeholder_text = cls._extract_tables(text)

        # 使用 LangChain 递归字符切分器切分非表格文本
        if separators is None:
            # 默认分隔符按“语义粒度从大到小”排列，优先在段落边界切分，
            # 必要时再拆到句子、词语、单个字符
            separators = ["\n\n", "\n", "。", "；", "，", " ", ""]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False,
        )
        print(f'metadata的数据----->{metadata}')
        docs = splitter.create_documents([placeholder_text], metadatas=[metadata or {}])

        nodes = []
        
        for idx, doc in enumerate(docs):
            content = doc.page_content
            # 还原表格
            for table_idx, table in enumerate(tables):
                placeholder = f"__TABLE_BLOCK_{table_idx}__"
                if placeholder in content:
                    content = content.replace(placeholder, table)
            # 表格还原后清除图片引用（表格内部可能包含图片）
            if remove_images:
                content = cls._remove_image_references(content)

            node_metadata = doc.metadata or {}
            doc_id_value = node_metadata.get('doc_id')
            print(f'node_metadata的数据---->{node_metadata}')
            print(f'node_metadata数据中的doc_id的值------》{doc_id_value}')
            
            node = TextNode(
                text=content,
                metadata=node_metadata
            )
            # 通过 relationships 设置 ref_doc_id
            if doc_id_value:
                node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id=doc_id_value)
            print(f'创建node后的relationships: {node.relationships}')
            
            nodes.append(node)

        return nodes

    @classmethod
    def split_markdown_file(cls,
            markdown_path: str,
            chunk_size: int = 800,
            chunk_overlap: int = 150,
            remove_images: bool = True,
            metadata:dict= {},
            **kwargs,
    ) -> List[Document]:
        """读取 Markdown 文件并切分，保留表格完整。
            markdown_path: Markdown 文件路径。
            chunk_size: 块大小，
            chunk_overlap: 块间重叠，
            remove_images: 是否去除图片引用。

        """
        text = Path(markdown_path).read_text(encoding="utf-8")
        base_dir = str(Path(markdown_path).parent)
        return cls.split_documents_preserve_tables(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            remove_images=remove_images,
            metadata=metadata,
            base_dir=base_dir,
            **kwargs,
        )

    #------------------------rag查询部分-------------------------

    @classmethod
    def get_reranker(cls, top_k: int = 20):
        '''
        获取 BGE 重排模型（惰性加载并缓存，避免每次请求重复加载）
        '''
        if getattr(cls, '_reranker', None) is None:
            cross_encoder = CrossEncoder(settings.rerank_model, device="cpu")
            cls._reranker = BGEReranker(cross_encoder, top_k=top_k)
            logger.info('BGE 重排模型加载完成并缓存')
        return cls._reranker

    @classmethod
    def hit_test(cls,query,kb_id:str):
        '''
        rag查询命中测试
        '''
        logger.info(f'kb_id:{kb_id}')
        cls.get_embed_model()
        vector_store=cls.get_milvus(collection_name=kb_id)
        #加载向量索引
        index_dir=os.path.join(settings.EMBEDINDEX_DIR,kb_id)
        storage_context = StorageContext.from_defaults(
            persist_dir=index_dir,
            vector_store=vector_store
        )
        vector_index = load_index_from_storage(storage_context)
        #向量检索
        vector_retriever = VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=20
        )
        logger.info("向量索引加载成功!")
        bm25_index_dir=os.path.join(settings.BM25_INDEX_DIR,kb_id)
        #bm25检索
        bm25_retriever = BM25Retriever.from_persist_dir(bm25_index_dir)
        logger.info('bm25索引加载完成')
        #权重设置，向量 60%, BM25 40%
        RETRIEVER_WEIGHTS = [0.6, 0.4]
        #向量检索器召回10个 + BM25检索器召回20个 → RRF融合后输出20个
        FUSION_TOP_K= 20

        fusion_retriever = QueryFusionRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            similarity_top_k=FUSION_TOP_K,  # 融合后输出数量
            num_queries=1,
            mode="reciprocal_rerank",
            retriever_weights=RETRIEVER_WEIGHTS,  # 设置权重
            use_async=False,
            verbose=False
        )
        reranker = cls.get_reranker(top_k=20)
        # RRF 混合检索 + BGE Reranker 精排
        query_bundle = QueryBundle(query)
        print(query_bundle)
        logger.info('rrf融合完成')
        logger.info('混合检索开始执行')
        rrf_nodes = fusion_retriever.retrieve(query_bundle)
        logger.info('结果重排')
        reranked_nodes = reranker.rerank(query, rrf_nodes)
        # 过滤：只保留 >= 0.6 的结果用于回答
        filtered_nodes = [n for n in reranked_nodes if n.score >= 0.6]
        if not filtered_nodes:
            logger.info('未找到满足条件的结果 (score >= 0.6)')
        # 组装命中结果，附带每条数据的引用源（文件名/文件类型/下载地址）
        results = []
        for node in filtered_nodes:
            meta = node.metadata or {}
            results.append({
                "content": node.text,
                "score": float(node.score) if node.score is not None else None,
                "file_name": meta.get("file_name"),
                "file_type": meta.get("file_type"),
                "source": meta.get("source"),
            })
        source_files = sorted({r["file_name"] for r in results if r.get("file_name")})
        logger.info(f'命中测试返回 {len(results)} 条结果，引用源: {source_files}')
        return results


    def hybrid_search(question:str):
        '''
        rag查询
        '''
        rerank_model = settings.rerank_model
        reranker_model = CrossEncoder(rerank_model, device="cpu")
        print("BGE Reranker 模型加载完成")
        pass

