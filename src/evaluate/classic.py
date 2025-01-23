import os

from DTO.evaluate import EvaluateData
from DTO.result import ResultDTO, GroupResult
from DTO.verdictTestcase import VerdictTestcase
from DTO.subtask import ProblemTaskDTO, SubtaskDTO, SubtaskOption
from handle import error
from checkType import *
import cmdManager as langCMD
from constants.osDotEnv import *
from constants.Enums import VerdictStatus, SubmissionStatus
from constants.verdict import verdictSymbol, verdictsColorSymbol

from evaluate.verdict.main import excuteAndVerdict
import errorLogging

import traceback
from message import *

import json


def evaluate(evaData: EvaluateData, isoPath: str, useControlGroup, onUpdateRuningInCase: str, subtaskData: ProblemTaskDTO) -> ResultDTO:

    submission = evaData.submission

    printHeader("GRADER", f"use {evaData.judgeType.value} Judge...")
    printHeader("GRADER", f"Runtime process:")

    print("\t-> Result (Unordered): ", end="", flush=True)
    isPass = [False for i in range(len(subtaskData.orderIndSubtask) + 5)]
    result = ["" for i in range(len(subtaskData.orderIndSubtask) + 5)]
    score = 0
    mxScore = 0
    mxTime = 0
    mxMem = None
    caseCount = 1
    fullResult = [GroupResult(0, subtask.score, []) for subtask in subtaskData.subtasks]

    realTimeFactor = langCMD.get(
        submission.language, "timeFactor") * float(osEnv.GRADER_TIME_FACTOR)
    testTimeLimit = submission.timeLimit * realTimeFactor
    
    for testInd in subtaskData.orderIndSubtask:

        cur_subtask = subtaskData.subtasks[testInd]

        if cur_subtask.group:
            result[testInd] += "["
            print("[", end="", flush=True)
        elif len(subtaskData.orderIndSubtask) != 1:
            result[testInd] += "("
            print("(", end="", flush=True)

        correct = 0
        percent_testcase_scores = []
        isSkiped = False

        # Check if it prerequisite when it it contest
        if (submission.contestId) and cur_subtask.require:
            for req in cur_subtask.require:
                if not isPass[req]:
                    isSkiped = True

            if isSkiped:
                allCrt = len(cur_subtask.cases)
                correct = 0
                percent_testcase_scores = [0]*allCrt
                caseCount += allCrt
                print("S"*allCrt, end="", flush=True)
                result[testInd] += "S"*allCrt
                fullResult[testInd].verdicts += [VerdictTestcase(VerdictStatus.skip, 0, 0, 0)]*allCrt
                isPass[testInd] = False

        for indTestNum, testcaseNum in enumerate(cur_subtask.cases):

            if isSkiped:
                break
            
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
                if errorStr[:7].lower() == "warning":
                    printFail("WARNING", f"Something wrong but will treat as RUNTIME ERROR\n\n{errorStr}\n (See discord message for more infomation)")
                    result[testInd] += verdictSymbol(VerdictStatus.runtimeErr)
                    fullResult[testInd].verdicts += [VerdictTestcase(VerdictStatus.runtimeErr, 0, 0, 0)]
                    errorLogging.writeInternalWarningLog(submission, errorStr, VerdictStatus.runtimeErr, "Ignorable Judge or Problem Error")
                elif errorStr.startswith("PROBLEM\n"):
                    errorStr = errorStr[8:]
                    printFail("PROBLEM", f"Something wrong with {evaData.judgeType.value} judge\n\n{errorStr}\n (See discord message for more infomation)")
                    return ResultDTO(submission.id,
                                "Problem Error", 0, 0, 0, f"It's the problem author's fault!\nGO BLAME THEM\n\n\n{evaData.judgeType.value} was explode during evaluate\n\n{fullErrorStr}",
                                SubmissionStatus.judgeError, [])
                else:
                    printFail("INTERNAL", f"Something wrong in internal grading system or something...:(\n\n{errorStr}\n (See discord message for more infomation)")
                    return ResultDTO(submission.id,
                                "Judge Error", 0, 0, 0, f"Something wrong in internal grading system...\nPlease contact admin AI.Tor!!\n\n{fullErrorStr}",
                                SubmissionStatus.judgeError, [])
            else:

                testcaseResult.timeUse = testcaseResult.timeUse * 1000 // realTimeFactor

                mxTime = max(mxTime, testcaseResult.timeUse)
                if testcaseResult.memUse != -1:
                    mxMem = max(mxMem or 0, testcaseResult.memUse)

                if testcaseResult.status == VerdictStatus.accept:
                    correct += 1
                    percent_testcase_scores.append(1)
                elif testcaseResult.status == VerdictStatus.partial:
                    percent_testcase_scores.append(testcaseResult.percent)
                else:
                    percent_testcase_scores.append(0)

                result[testInd] += verdictSymbol(testcaseResult.status)
                fullResult[testInd].verdicts += [testcaseResult]
                print(verdictsColorSymbol(testcaseResult.status), end="", flush=True)
                caseCount += 1

            #? skip the other testcase when it isn't accept and grouped subtask
            if cur_subtask.group and testcaseResult.status != VerdictStatus.accept:
                nRemain = len(cur_subtask.cases) - indTestNum - 1
                result[testInd] += "S"*nRemain
                fullResult[testInd].verdicts += [VerdictTestcase(VerdictStatus.skip, 0, 0, 0)]*nRemain
                print("S"*nRemain, end="", flush=True)
                caseCount += nRemain
                break


            onUpdateRuningInCase(submission.id, caseCount)

        # calculate score for each subtask here
        allCorrect = len(cur_subtask.cases)
        groupScore = 0
        if cur_subtask.group:
            if correct == allCorrect:
                groupScore = cur_subtask.score
            else:
                groupScore = 0
        else:
            if cur_subtask.option == SubtaskOption.max:
                groupScore = max(percent_testcase_scores) * cur_subtask.score
            elif cur_subtask.option == SubtaskOption.min:
                groupScore = min(percent_testcase_scores) * cur_subtask.score
            else: # just sum
                percentSumScore = sum(percent_testcase_scores)
                groupScore = percentSumScore / allCorrect * cur_subtask.score
        score += groupScore
        fullResult[testInd].score = groupScore
        mxScore += float(cur_subtask.score)
        isPass[testInd] = (correct == allCorrect)        

        if cur_subtask.group:
            result[testInd] += "]"
            print("]", end="", flush=True)
        elif len(subtaskData.orderIndSubtask) != 1:
            result[testInd] += ")"
            print(")", end="", flush=True)

    print()
    finalResult = "".join(result)
    finalScore = round(score * submission.maxScore / mxScore)
    print("\t-> Final Result: ", finalResult, flush=True)

    print(f"\t-> Full Result:")
    groupIndex = 0
    for  groupResult in fullResult:
        groupIndex += 1
        print(f"\t\tGroup #{groupIndex}: {groupResult.score}/{groupResult.fullScore}")
        for verdict in groupResult.verdicts:
            print(f"\t\t\tStatus: {verdict.status.value}, Percent: {verdict.percent}, Time Used: {verdict.timeUse} ms, Mem Used: {verdict.memUse} kb")

    status = SubmissionStatus.accept if all(c in "P[]()" for c in finalResult) else SubmissionStatus.reject
    
    return ResultDTO(submission.id,
                     finalResult, finalScore, mxTime, mxMem, None, status, fullResult)
