from utils.logger import logger
from typing import List,Optional
from pathlib import Path
from mineru.cli.common import do_parse , read_fn
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llama_index.core import Document,VectorStoreIndex,StorageContext,load_index_from_storage
from llama_index.core import settings as llamaindex_settings
from llama_index.core.schema import TextNode
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore,QueryBundle
from llama_index.llms.openai import OpenAI
#pip install llama-index-vector-stores-milvus
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
#pip install llama-index-retrievers-bm25
from llama_index.retrievers.bm25 import BM25Retriever
#pip install sentence-transformers torch torchvision torchaudio
from sentence_transformers import CrossEncoder
import settings
import os
import re
import uuid
#from funasr import AutoModel
class RagService:

    @classmethod
    def know2db(cls,filepath: str,download_url:str):
        #文件扩展名
        file_ex_name_with_mineru=['.doc','.docx','.ppt','.pptx','.xls','.xlsx','.pdf']
        file_ex_name_without_mineru=['.txt','.md']
        file_ex_with_audio=['wav','mp3']
        file_ex=Path(filepath).suffix
        if file_ex in file_ex_name_with_mineru or file_ex in file_ex_name_without_mineru:
            markdown_path=cls.docs2_markdown(filepath)
            nodes=cls.split_markdown_file(markdown_path,800,200,True,{'source':download_url})
            print('打印nodes')
            for item in nodes:
                print(item.text)
            print(nodes)

            cls.embeddingdoc2db(nodes)

        elif file_ex in file_ex_with_audio:
            pass
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
    def embeddingdoc2db(cls,node,collection_name='test'):
        '''
        文档入库
        '''
        logger.info('准备入库')
        embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            device="cpu",
            normalize=True
        )
        llamaindex_settings.Settings.embed_model=embed_model
        vector_store = MilvusVectorStore(
            uri=settings.MILVUS_URI,
            user=settings.MILVUS_USER,
            password=settings.DB_PASSWORD,
            collection_name=collection_name,
            token=f'{settings.MILVUS_USER}:{settings.DB_PASSWORD}@rag',
            dim=settings.VECTOR_DIM,
            overwrite=True,
            index_config={
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 200}
            },
            search_config={
                "metric_type": "COSINE",
                "params": {"ef": 64}
            },
            scalar_field_indexes=[
                {"field_name": "category", "index_type": "Trie", "index_name": "category_idx"},
                {"field_name": "doc_id", "index_type": "Trie", "index_name": "doc_id_idx"}
            ]
        )
        storage_content=StorageContext.from_defaults(vector_store=vector_store)
        vector_index=VectorStoreIndex(nodes=node,storage_context=storage_content)
        os.makedirs(settings.INDEX_DIR,exist_ok=True)
        vector_index.storage_context.persist(settings.EMBEDINDEX_DIR)
        print(f"✓ Milvus 向量索引创建成功: {collection_name}")
        print(f"  - 向量维度: {settings.VECTOR_DIM}")
        print(f"  - 节点数量: {len(node)}")
        print(f"  - 索引类型: HNSW (COSINE)")
        #bm25索引创建
        print('创建bm25索引')
        bm25_retriever=BM25Retriever.from_defaults(
            nodes=node,
            similarity_top_k=20,
            verbose=False
        )
        os.makedirs(settings.BM25_INDEX_DIR,exist_ok=True)
        bm25_retriever.persist(settings.BM25_INDEX_DIR)
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

        Args:
            text: 待切分的文本。
            chunk_size: 非表格文本的目标块大小（表格本身会作为整体保留，可能超出此大小）。
            chunk_overlap: 块间重叠字符数。
            separators: 切分分隔符，默认按段落、句子、词语逐级切分。
            metadata: 附加到每个 Document 的元数据。
            remove_images: 是否去除 Markdown 图片引用，默认为 True。

        Returns:
            切分后的 ``Document`` 列表，每个 Document 中的表格均完整。
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
            
            # 直接创建 TextNode，避免二次切分
            node = TextNode(
                text=content,
                metadata=doc.metadata or {},
                id_=f"node_{idx}"
            )
            nodes.append(node)
        
        print(f'切分后文档数量: {len(docs)}')
        print(f'生成的 nodes 数量: {len(nodes)}')
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

        Args:
            markdown_path: Markdown 文件路径。
            chunk_size: 块大小，参见 ``split_documents_preserve_tables``。
            chunk_overlap: 块间重叠，参见 ``split_documents_preserve_tables``。
            remove_images: 是否去除图片引用。
            **kwargs: 其他传递给 ``split_documents_preserve_tables`` 的参数。

        Returns:
            切分后的 ``Document`` 列表。
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
