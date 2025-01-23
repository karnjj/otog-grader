import os

from DTO.evaluate import EvaluateData
from DTO.result import ResultDTO
from constants.Enums import VerdictStatus, SubmissionStatus
from handle import error
from constants.osDotEnv import *
import cmdManager as langCMD
from evaluate.verdict.main import excuteAndVerdict
from constants.verdict import verdictsColorSymbol, verdictCodeforces, verdictsColorCodeforces

from message import *
import errorLogging
import traceback


def evaluate(evaData: EvaluateData, isoPath: str, useControlGroup, onUpdateRuningInCase: str, mxCase: int) -> ResultDTO:

    submission = evaData.submission

    printHeader("Codeforces", f"Evaluate with Codeforces standard")
    printHeader("GRADER", f"use {evaData.judgeType.value} Judge...")
    printHeader("GRADER", f"Runtime process:")

    print("\t-> Result: ", end="", flush=True)
    result = "Accepted"
    resultTime = 0
    resultMem = 0

    realTimeFactor = langCMD.get(
        submission.language, "timeFactor") * float(osEnv.GRADER_TIME_FACTOR)
    testTimeLimit = submission.timeLimit * realTimeFactor

    for testcaseNum in range(1, mxCase+1):
        
        try:
            testcaseResult = excuteAndVerdict(
                submission.problemPath,
                testcaseNum,
                testTimeLimit,
                (submission.memoryLimit) * 1024,
                submission.language,
                evaData.srcPath,
                isoPath,
                evaData.judgeType
            )
        except Exception as e:
            errorStr = str(e)
            fullErrorStr = traceback.format_exc()
            print()
            if errorStr.startswith("WARNING"):
                printFail("WARNING", f"Something wrong but will treat as RUNTIME ERROR\n\n{errorStr}\n (See discord message for more information)")
                result = verdictCodeforces(VerdictStatus.runtimeErr).replace("%d", str(testcaseNum))
                errorLogging.writeInternalWarningLog(submission, errorStr, VerdictStatus.runtimeErr, "Ignorable Judge or Problem Error")
                return ResultDTO(submission.id,
                            result, 0, resultTime, resultMem, f"Something wrong but will treat as RUNTIME ERROR\n\n{errorStr}",
                            SubmissionStatus.reject, [])
            elif errorStr.startswith("PROBLEM\n"):
                errorStr = errorStr[8:]
                printFail("PROBLEM", f"Some thing wrong with {evaData.judgeType.value} judge\n\n{errorStr}\n (See discord message for more information)")
                return ResultDTO(submission.id,
                            "Problem Error", 0, 0, 0, f"It's the problem author's fault!\nGO BLAME THEM\n\n\n{evaData.judgeType.value} was explode during evaluate\n\n{fullErrorStr}",
                            SubmissionStatus.judgeError, [])
            else:
                printFail("INTERNAL", f"Some thing wrong in internal grading system or something...:(\n\n{errorStr}\n (See discord message for more information )")
                return ResultDTO(submission.id,
                            "Judge Error", 0, 0, 0, f"Something wrong in internal grading system...\nPlease contact admin AI.Tor!!\n\n{fullErrorStr}",
                            SubmissionStatus.judgeError, [])


        resultTime = max(resultTime, testcaseResult.timeUse *
                         1000 // realTimeFactor)
        resultMem = max(resultMem, testcaseResult.memUse)

        result = verdictCodeforces(
            testcaseResult.status).replace("%d", str(testcaseNum))

        if testcaseResult.status != VerdictStatus.accept:
            print(verdictsColorCodeforces(testcaseResult.status).replace(
                "%d", str(testcaseNum)), flush=True)
            return ResultDTO(submission.id, result, 0, resultTime, resultMem, None, SubmissionStatus.reject, [])

        onUpdateRuningInCase(submission.id, testcaseNum)

    # ? mean accept every testcase
    print(verdictsColorCodeforces(VerdictStatus.accept), flush=True)
    return ResultDTO(submission.id, result, submission.maxScore, resultTime, resultMem, None, SubmissionStatus.accept, [])
