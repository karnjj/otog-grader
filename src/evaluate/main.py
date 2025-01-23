import os

from DTO.submission import SubmissionDTO
from DTO.evaluate import EvaluateData
from DTO.result import ResultDTO

from constants.osDotEnv import osEnv
from constants.Enums import EvaluateMode, SubmissionStatus

from evaluate import classic, codeforces
from evaluate.verdict.main import getJudgeType

from handle import fileRead
from message import *
import subtask
import errorLogging


def evaModeFromStr(mode: str) -> EvaluateMode:
    if mode == "codeforces":
        return EvaluateMode.codeforces

    return EvaluateMode.classic


def start(submission: SubmissionDTO, srcPath: str, isoPath, useControlGroup:bool, onUpdateRuningInCase) -> ResultDTO:
    if osEnv.GRADER_FORCE_TO_MODE != "none":
        evaMode = evaModeFromStr(osEnv.GRADER_FORCE_TO_MODE)
    else:
        evaMode = evaModeFromStr(submission.mode)

    judgeType = getJudgeType(submission.problemPath)
    evaData = EvaluateData(submission, srcPath, evaMode, judgeType)

    # ? read substask first
    if os.path.exists(f"{evaData.submission.problemPath}/subtask.json"):
        subContent = fileRead(
            f"{evaData.submission.problemPath}/subtask.json")
        printHeader("SUBTASK", f"Found custom subtask")
    else:
        subContent = evaData.submission.testcase
    
    try:
        problemTaskData = subtask.compile(subContent)
    except Exception as e:
        errorLogging.writeSubtaskErrorLog(submission, str(e))
        return ResultDTO(evaData.submission.id, "Subtask Error", 0, 0, 0, str(e), SubmissionStatus.judgeError, [])

    # ? start evaluate
    if evaMode == EvaluateMode.codeforces:
        evaResult = codeforces.evaluate(evaData, isoPath, useControlGroup, onUpdateRuningInCase, problemTaskData.maxCase)
    else:
        evaResult = classic.evaluate(evaData, isoPath, useControlGroup, onUpdateRuningInCase, problemTaskData)
    
    if evaResult.result in ["Problem Error", "Judge Error", "Subtask Error"]:
        errorLogging.writeInternalErrorLog(submission, evaResult, evaResult.result)
    
    return evaResult
