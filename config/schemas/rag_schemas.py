from pydantic import BaseModel
class Rag_Docs_Path(BaseModel):
    doc_path: list[str]