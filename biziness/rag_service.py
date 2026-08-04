from utils.logger import logger
from typing import List,Optional
from pathlib import Path
from mineru.cli.common import do_parse , read_fn
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import settings
import os
import re
class RagService:

    @classmethod
    def know2db(cls,filepath: str):
        #文件扩展名
        file_ex_name_with_mineru=['.doc','.docx','.ppt','.pptx','.xls','.xlsx','.pdf']
        file_ex_name_without_mineru=['.txt','.md']
        file_ex_with_audio=['wav','mp3']
        file_ex=Path(filepath).suffix
        if file_ex in file_ex_name_with_mineru or file_ex in file_ex_name_without_mineru:
            markdown_path=cls.docs2_markdown(filepath)
            chunks=cls.split_markdown_file(markdown_path,800,200,True)
            for i, chunk in enumerate(chunks):
                print(f"\n========== Chunk {i + 1} ==========\n")
                print(chunk.page_content)
                print("\n")
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
        '''
        pass



    @classmethod
    def embeddingdoc2db(cls,doc):
        pass

    @classmethod
    def _remove_image_references(cls,text: str) -> str:
        """去除 Markdown 图片引用，如 ``![alt](images/xxx.jpg)``。
        Markdown 图片语法：![可选描述](图片路径)

        """
        return re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)

    @classmethod
    def _extract_html_tables(cls,text: str) -> tuple[List[str], str]:
        """提取 HTML ``<table>...</table>`` 表格，返回 (表格列表, 替换后的文本)。
           提取出的表格会用 ``__TABLE_BLOCK_{idx}__`` 占位符代替，
           保证后续切分步骤不会在表格中间断开。
           [\s\S]*? 表示跨行非贪婪匹配，re.IGNORECASE 忽略 table 标签大小写
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
    ) -> List[Document]:
        """对 Markdown / HTML 混排文本进行切割，确保表格完整不被截断。

        实现思路：
        1. 可选去除 Markdown 图片引用，减少无意义内容；
        2. 识别出所有 HTML ``<table>`` 和 Markdown ``|`` 表格，并用占位符替换；
        3. 使用 LangChain 的 ``RecursiveCharacterTextSplitter`` 对替换后的文本切分；
        4. 切分完成后把占位符还原为完整表格。

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
        # 步骤 1：按需去除图片引用
        if remove_images:
            text = cls._remove_image_references(text)

        # 步骤 2：提取表格并用占位符替换，防止表格被截断
        tables, placeholder_text = cls._extract_tables(text)

        # 步骤 3：使用 LangChain 递归字符切分器切分非表格文本
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

        # 步骤 4：将占位符还原为完整表格
        result: List[Document] = []
        for doc in docs:
            content = doc.page_content
            for idx, table in enumerate(tables):
                placeholder = f"__TABLE_BLOCK_{idx}__"
                if placeholder in content:
                    content = content.replace(placeholder, table)
            result.append(Document(page_content=content, metadata=doc.metadata))

        return result

    @classmethod
    def split_markdown_file(cls,
            markdown_path: str,
            chunk_size: int = 800,
            chunk_overlap: int = 100,
            remove_images: bool = True,
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
        return cls.split_documents_preserve_tables(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            remove_images=remove_images,
            **kwargs,
        )