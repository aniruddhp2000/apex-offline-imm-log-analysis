import datetime

class ParsedEntry:
    def __init__(self, timestamp: datetime.datetime, log_level: str, message: str, source_file: str, raw: str, metadata: dict = None):
        self.timestamp = timestamp
        self.log_level = log_level.upper() if log_level else "INFO"
        self.message = message
        self.source_file = source_file
        self.raw = raw
        self.metadata = metadata if metadata is not None else {}

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "log_level": self.log_level,
            "message": self.message,
            "source_file": self.source_file,
            "metadata": self.metadata,
            "raw": self.raw
        }

class BaseLogParser:
    def parse(self, filepath: str, relative_path: str) -> list:
        raise NotImplementedError("Each parser must implement the 'parse' method.")
