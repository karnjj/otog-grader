from pathlib import Path
import tabulate
from DTO.result import ResultDTO

from message import *
from handle import *
from DTO.submission import SubmissionDTO
from evaluate.main import getJudgeType
from evaluate.main import start as startEvaluate
from constants.Enums import *
from constants.osDotEnv import *
from errorLogging import writeTestcaseErrorLog

from typing import Callable
from datetime import datetime


def startJudge(submission: SubmissionDTO,
               onSubmitResult: Callable[[ResultDTO], None],
               onUpdateRuningInCase: Callable[[int, int], None]):
    """
    Start judge is a BIG function that will judge and evaluate participant code
    Attributes
    ----------
    queueData : submissionDTO
    onSubmitResult : function (ResultDTO) -> None
        is the function that will call when finishing judge
        you have to define 1 parameter
            [result : ResultDTO]
    onUpdateRuningInCase : function (int, int) -> None
        is the function that will call everytime when runing each case
        you have to define 2 parameters
            [resultId]
            [current number of testcase : int]
    """

    # If there is new payload
    printOKCyan("GRADER", "Receive New Submission.")
    print(f"[ {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')} ]")
    print(
        tabulate.tabulate(
            [
                ["id", submission.id],
                ["userId", submission.userId],
                ["problemId", submission.problemId],
                ["language", submission.language],
                ["case", submission.testcase],
            ],
            headers=["info", "value"],
            tablefmt="orgtbl",
        )
    )

    prepareLoging(submission)

    # If does not specify number of testcase
    if not submission.testcase:
        printFail("GRADER", "Number of testcase does not specified.")
        submitResult = ResultDTO(
            id=submission.id,
            result="No nCase",
            score=0,
            sumTime=0,
            memUse=0,
            errmsg="Number of testcase does not specified. Flame admins, kiddos. :(",
            status=SubmissionStatus.judgeError,
            fullResult=[]
        )
        onSubmitResult(submitResult)
        resultLoging(submission, submitResult)
        writeTestcaseErrorLog(submission, "Number of testcase does not specified. Flame Problem author, kiddos. :(")
        return

    # Check if testcases actually exist
    if not Path(submission.problemPath).is_dir():
        printFail("GRADER", "No testcase. Aborted.")
        submitResult = ResultDTO(
            id=submission.id,
            result="No Testcase",
            score=0,
            sumTime=0,
            memUse=0,
            errmsg="Admins have not yet upload the testcases. Go ahead and flame them.",
            status=SubmissionStatus.judgeError,
            fullResult=[]
        )
        onSubmitResult(submitResult)
        resultLoging(submission, submitResult)
        writeTestcaseErrorLog(submission, f"Author have not yet upload the testcases. Go ahead and flame them.")
        return

    # ? Check is .in are ready to use
    missingIn = getMissingSeqNumberFile(
        submission.problemPath, "in", int(submission.testcase))
    if missingIn:
        printFail("TESTCASE", f"Testcase {missingIn[0]}.in is missing")
        submitResult = ResultDTO(
            id=submission.id,
            result="Input missing",
            score=0,
            sumTime=0,
            memUse=0,
            errmsg="Admins have not yet upload the testcases. Go ahead and flame them.",
            status=SubmissionStatus.judgeError,
            fullResult=[]
        )
        onSubmitResult(submitResult)
        resultLoging(submission, submitResult)
        writeTestcaseErrorLog(submission, f"Testcase {missingIn[0]}.in is missing\n go ahead and flame the author.")
        return

    missingSol = getMissingSeqNumberFile(
        submission.problemPath, "sol", int(submission.testcase))
    # ? to check .sol It depend on type of judge
    judgeType = getJudgeType(submission.problemId)
    if judgeType == JudgeType.standard:
        # ? if it standard, It must have all .sol file
        if missingSol:
            printFail("TESTCASE", f"Testcase {missingSol[0]}.sol is missing")
            submitResult = ResultDTO(
                id=submission.id,
                result="Solution missing",
                score=0,
                sumTime=0,
                memUse=0,
                errmsg="Admins have not yet upload the testcases. Go ahead and flame them.",
                status=SubmissionStatus.judgeError,
                fullResult=[]
            )
            onSubmitResult(submitResult)
            resultLoging(submission, submitResult)
            writeTestcaseErrorLog(submission, f"Testcase {missingSol[0]}.sol is missing\n go ahead and flame the author.")
            return
    else:
        # ? otherwise, just warn.
        for e in missingSol:
            printWarning("TESTCASE", f"Testcase {e}.sol is missing")

    printHeader("GRADER", "Compiling process...")

    # try:
    #     sourceCode = submission.sourceCode.decode("UTF-8")
    # except:
    #     printFail("GRADER", "Cannot decode received source string. Aborted.")
    #     onSubmitResult(
    #         submission.id,
    #         "Undecodable",
    #         0,
    #         0,
    #         69,
    #         "Cannot decode your submitted code. Check your submission.",
    #     )
    #     return

    # ? check and init isolate
    isolateEnvPath = None  # ! None means didn't use isolate
    isolateUseControlGroup = strToBool(osEnv.USE_CONTROL_GROUP)
    if strToBool(osEnv.USE_ISOLATE):
        isolateEnvPath = initIsolate(isolateUseControlGroup)

    prepareEnv(submission.problemPath, isolateEnvPath)

    # Write source string to file
    srcCodePath = createSourceCode(
        submission.sourceCode, submission.language, isolateEnvPath)

    # Compile
    err = create(submission.userId, submission.language,
                 srcCodePath, submission.problemPath, isolateEnvPath)

    # If compile error
    if err == "Compilation Error":
        printOKCyan("GRADER", "Compile error.")
        try:
            if isolateEnvPath != None:
                errmsg = fileRead(f"{isolateEnvPath}/error.txt") or None
            else:
                errmsg = fileRead("env/error.txt") or None

        except:
            errmsg = "Someting went wrong."

        if errmsg:
            errmsg = errMsgHandle(errmsg)
        else:
            errmsg = "Someting went wrong.\nContact admin immediately :( !!"
            # TODO : also send this to discord

        submitResult = ResultDTO(
            id=submission.id,
            result=err,
            score=0,
            sumTime=0,
            memUse=0,
            errmsg=errmsg,
            status=SubmissionStatus.compileError,
            fullResult=[]
        )
        onSubmitResult(submitResult)
        resultLoging(submission, submitResult)
        return
    elif err == "Compilation TLE":
        printWarning("GRADER", "Compile Time Limit Exceeded.")
        submitResult = ResultDTO(
            id=submission.id,
            result="Compilation Error",
            score=0,
            sumTime=0,
            memUse=0,
            errmsg="Compilation Time Limit Exceeded",
            status=SubmissionStatus.compileError,
            fullResult=[]
        )
        onSubmitResult(submitResult)
        resultLoging(submission, submitResult)
        return

    submitResult = startEvaluate(
        submission, srcCodePath, isolateEnvPath, isolateUseControlGroup, onUpdateRuningInCase)

    print()
    onSubmitResult(submitResult)
    resultLoging(submission, submitResult)

    if not err:
        print(f"\n\t-> Time used: {int(submitResult.sumTime)} ms.")
        print(f"\t-> Mem  used: {int(submitResult.memUse or -1)} kb??")
