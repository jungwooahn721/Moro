from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from pathlib import Path
import json


KST = timezone(timedelta(hours=9))


def _parse_dt(dt_str: str) -> datetime:
    """Parse ISO 8601 datetime strings like '2025-09-30T21:00:00+09:00'.
    Fallback: naive strings without tz will be treated as KST.
    """
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KST)
    return dt


def _event_window(event: Dict[str, Any]) -> Tuple[datetime, datetime]:
    start = _parse_dt(event["date_start"])  # required
    finish = _parse_dt(event.get("date_finish", event["date_start"]))
    return start, finish


def _matches_date(d: datetime, date_str: str) -> bool:
    # date_str: 'YYYY-MM-DD'
    return d.strftime("%Y-%m-%d") == date_str


def _matches_weekday(d: datetime, weekday: Any) -> bool:
    # weekday: 0(Mon)~6(Sun) or str name in ko/en
    # date_start에서 자동으로 요일을 계산해서 매칭
    if isinstance(weekday, int):
        return d.weekday() == weekday
    if isinstance(weekday, str):
        # 요일 이름으로 매칭 (date_start에서 자동 계산된 요일과 비교)
        ko = ["월", "화", "수", "목", "금", "토", "일"]
        en = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        w = weekday.strip().lower()
        
        # 영어 요일명 처리
        if w in en:
            return d.weekday() == en.index(w)
        
        # 한국어 요일명 처리 (원본 weekday 사용)
        if weekday in ko:
            return d.weekday() == ko.index(weekday)
        
        # 한 글자 한국어 요일명 처리
        if len(weekday) == 1 and weekday in "월화수목금토일":
            return d.weekday() == ko.index(weekday)
            
    return False




def _matches_hour(d: datetime, hour: Any) -> bool:
    # hour: int (0-23) or 'HH' or 'HH:MM'
    if isinstance(hour, int):
        return d.hour == hour
    if isinstance(hour, str):
        h = hour.strip()
        try:
            if ":" in h:
                hh, mm = h.split(":")
                return d.hour == int(hh) and d.minute == int(mm)
            return d.hour == int(h)
        except Exception:
            return False
    return False


def _matches_year(d: datetime, year: Any) -> bool:
    # year: int (e.g., 2025) or str (e.g., "2025")
    if isinstance(year, int):
        return d.year == year
    if isinstance(year, str):
        try:
            return d.year == int(year.strip())
        except Exception:
            return False
    return False


def _matches_month(d: datetime, month: Any) -> bool:
    # month: int (1-12) or str (e.g., "1", "01", "January", "1월")
    if isinstance(month, int):
        return d.month == month
    if isinstance(month, str):
        m = month.strip()
        try:
            # Try parsing as integer
            return d.month == int(m)
        except Exception:
            # Try parsing as month name
            month_names = {
                "january": 1, "jan": 1, "1월": 1,
                "february": 2, "feb": 2, "2월": 2,
                "march": 3, "mar": 3, "3월": 3,
                "april": 4, "apr": 4, "4월": 4,
                "may": 5, "5월": 5,
                "june": 6, "jun": 6, "6월": 6,
                "july": 7, "jul": 7, "7월": 7,
                "august": 8, "aug": 8, "8월": 8,
                "september": 9, "sep": 9, "9월": 9,
                "october": 10, "oct": 10, "10월": 10,
                "november": 11, "nov": 11, "11월": 11,
                "december": 12, "dec": 12, "12월": 12
            }
            return d.month == month_names.get(m.lower(), 0)
    return False


def _nearest_key(d: datetime, now: Optional[datetime]) -> timedelta:
    if now is None:
        now = datetime.now(tz=KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    return abs(d - now)


def filter_out_by_criteria(
    events: Iterable[Dict[str, Any]],
    *,
    date: Optional[str] = None,  # YYYY-MM-DD
    weekday: Optional[Any] = None,  # 0-6 or '월'~'일'
    hour: Optional[Any] = None,  # HH or HH:MM
    year: Optional[Any] = None,  # 2025 or "2025"
    month: Optional[Any] = None,  # 1-12 or "1월", "January", etc.
    time_window_hours: Optional[float] = None,  # ±N hours from reference_time
    reference_time: Optional[datetime] = None,  # reference point for time filtering
    nearest_n: Optional[int] = None,  # exclude N nearest to reference_time
    sort_by: Optional[str] = None,  # 'nearest'|'start'|None
) -> List[Dict[str, Any]]:
    """Return events that DO NOT match the given criteria.

    Criteria semantics (if provided):
    - date: keep only events whose start date equals 'YYYY-MM-DD' (others excluded)
    - weekday: keep only events on given weekday (0=Mon..6=Sun or name). Others excluded.
    - hour: keep only events starting at given hour ('HH' or 'HH:MM'). Others excluded.
    - year: keep only events in given year (e.g., 2025 or "2025"). Others excluded.
    - month: keep only events in given month (1-12, "1월", "January", etc.). Others excluded.
    - time_window_hours: keep only events within N hours of 'reference_time' (both before and after). Others excluded.
    - reference_time: reference point for time-based filtering (defaults to current time if not provided)
    - nearest_n: keep only the N nearest to 'reference_time'. Others excluded.

    This function returns the complement set: items NOT matching all provided filters.
    """

    events_list = list(events)

    # Build the set of indices that match all provided filters
    matched_indices: List[int] = []

    # Set up reference time for time-based filtering
    ref_time = reference_time if reference_time is not None else datetime.now(tz=KST)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=KST)

    # Compute matching for standard filters
    for idx, ev in enumerate(events_list):
        start, finish = _event_window(ev)

        ok = True
        if date is not None:
            ok = ok and _matches_date(start, date)
        if weekday is not None:
            ok = ok and _matches_weekday(start, weekday)
        if hour is not None:
            ok = ok and _matches_hour(start, hour)
        if year is not None:
            ok = ok and _matches_year(start, year)
        if month is not None:
            ok = ok and _matches_month(start, month)
        if time_window_hours is not None:
            # Event starts within N hours of reference_time (both before and after)
            time_diff = abs((start - ref_time).total_seconds()) / 3600  # hours
            ok = ok and (time_diff <= time_window_hours)

        if ok:
            matched_indices.append(idx)

    # If nearest_n is provided, further intersect with nearest constraint
    if nearest_n is not None:
        # rank all events by |start - reference_time|
        ranked = sorted(
            [(idx, _nearest_key(_event_window(events_list[idx])[0], ref_time)) for idx in matched_indices],
            key=lambda x: x[1],
        )
        matched_indices = [idx for idx, _ in ranked[: max(0, nearest_n)]]

    # Complement indices => those NOT matched
    exclude_indices = {i for i in range(len(events_list))} - set(matched_indices)
    result = [events_list[i] for i in sorted(exclude_indices)]

    # Optional sorting for result presentation
    if sort_by is not None and result:
        if sort_by == "nearest":
            result.sort(key=lambda e: _nearest_key(_event_window(e)[0], ref_time))
        elif sort_by == "start":
            result.sort(key=lambda e: _event_window(e)[0])

    return result


def parse_with_criteria(
    vector_dir: str = "Database/[user]",
    criteria: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Public API: return events that match given criteria.
    """
    vector_dir = Path(vector_dir)
    if not vector_dir.exists():
        return []
    
    # Find all JSON files (monthly files, not event_*.json)
    json_files = list(vector_dir.glob("*.json"))
    if not json_files:
        return []
    # Load all events from JSON files
    # Support both schemas:
    # - Array of events per file
    # - Single event object per file (e.g., Database/[user]/0001.json)
    events_list = []
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                file_events = json.load(f)
                if isinstance(file_events, list):
                    events_list.extend(file_events)
                elif isinstance(file_events, dict):
                    events_list.append(file_events)
                else:
                    # Unknown shape; skip
                    continue
        except Exception as e:
            print(f"Failed to load {json_file}: {e}")
            continue
    
    if not events_list:
        return []
    merged = {**(criteria or {}), **kwargs}
    excluded = filter_out_by_criteria(events_list, **merged)
    excluded_ids = set(map(id, excluded))
    included = [ev for ev in events_list if id(ev) not in excluded_ids]
    return included
