import datetime
from typing import List
from backend.parser.base_parser import ParsedEntry

class TimelineMerger:
    def __init__(self):
        pass

    def merge(self, all_entries: List[ParsedEntry]) -> List[ParsedEntry]:
        # Filter out entries with invalid timestamps
        valid_entries = [e for e in all_entries if e.timestamp is not None]
        
        # Sort chronologically by timestamp
        # In python, datetime object comparisons are supported as long as they are naive or all aware.
        # We will ensure all timestamps are parsed consistently as UTC naive datetimes.
        # Our parsers strip timezone suffix and parse as naive, which effectively assumes a unified base.
        valid_entries.sort(key=lambda x: x.timestamp)
        return valid_entries

    def get_time_bounds(self, entries: List[ParsedEntry]) -> dict:
        if not entries:
            return {"start": None, "end": None}
        return {
            "start": entries[0].timestamp,
            "end": entries[-1].timestamp
        }

    def filter_time_window(self, entries: List[ParsedEntry], start_time: datetime.datetime, end_time: datetime.datetime) -> List[ParsedEntry]:
        return [e for e in entries if start_time <= e.timestamp <= end_time]
