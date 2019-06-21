import typing
from dataclasses import dataclass


@dataclass
class Talk:
    title: str
    id: str
    starred: bool
    selected: bool
    tracks: typing.List[str]
    start: str
    end: str
    slug: typing.Optional[str]
    language: typing.Optional[str]
    level: typing.Optional[str]
    speakers: typing.List[str]
    can_be_starred: bool
    start_column: int
    end_column: int
    start_row: int
    end_row: int


@dataclass
class GridTime:
    time: str
    start_row: int
    end_row: int


@dataclass
class Grid:
    times: str  # TODO: correct type
    rows: int
    cols: int


@dataclass
class ScheduleGrid:
    day: str
    tracks: typing.List[str]
    talks: typing.List[Talk]
    grid: Grid
