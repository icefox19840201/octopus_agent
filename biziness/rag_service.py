from config.octopus_enum.status import RagServiceEnum
class RagService:
    @staticmethod
    def know2db(markdown_path: str):
        if isinstance(markdown_path, str):
            return RagServiceEnum.type_error.value
        pass