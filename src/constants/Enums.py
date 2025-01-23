from enum import Enum


class EvaluateMode(Enum):
    classic = "classic"
    codeforces = "codeforces"


class JudgeType(Enum):
    ogogi = "ogogi"
    cppCheck = "check.cpp"
    standard = "standard"

    thaco = "thaco"  # ? https://thaco.tech


class VerdictStatus(Enum):
    accept = "ACCEPTED"
    partial = "PARTIAL"
    reject = "REJECTED"

    timeExceed = "TIME_LIMIT_EXCEEDED"
    runtimeErr = "RUNTIME_ERROR"

    skip = "SKIPPED"

    problemErr = "PROBLEM_ERROR"
    internalErr = "INTERNAL_ERROR"

class SubmissionStatus(Enum):
    accept = "accept"
    reject = "reject"
    waiting = "waiting"
    grading = "grading"
    compileError = "compileError"
    judgeError = "judgeError"
