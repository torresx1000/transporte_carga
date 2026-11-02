from app.repositories.records import RecordRepository


class RecordService:
    def __init__(self, repository: RecordRepository):
        self.repository = repository

    def list(self, page: int, page_size: int, filters: dict):
        total, items = self.repository.list(page, page_size, filters)
        return {
            "total": total,
            "items": items,
            "page": page,
            "pages": (total + page_size - 1) // page_size,
        }
