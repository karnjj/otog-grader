from dataclasses import dataclass
from typing import List
from DTO.verdictTestcase import VerdictTestcase
from constants.Enums import SubmissionStatus


@dataclass
class GroupResult:
    score: float
    fullScore: float
    verdicts: List[VerdictTestcase]


@dataclass
class ResultDTO:
    id: int
    result: str
    score: int
    sumTime: int
    memUse: int
    errmsg: str
    status: SubmissionStatus
    fullResult: List[GroupResult]
