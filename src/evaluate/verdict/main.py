from DTO.verdictTestcase import VerdictTestcase
from DTO.testcaseData import TestcaseData
from constants.Enums import JudgeType, VerdictStatus
import cmdManager as langCMD
from message import *
from handle import isolateMetaReader, error

from evaluate.verdict import standard, cppCheck, ogogi, thaco

from pathlib import Path
import subprocess
import os
import time
import signal


def excute(problemPath: str, testcase: int, timeLimit: float, memoryLimit: int, language: str, sourcePath: str, isoPath, useControlGroup:bool = False):
    if isoPath != None:  # ? Use isolate to execute

        inputFile = f"< ../{problemPath}/{testcase}.in"
        cmd = "cd env; "
        cmd += f"isolate {useControlGroup and '--cg' or ''} --meta=isoResult.txt --stdout=output.txt --stderr=error.txt "
        cmd += f"--time={timeLimit / 1000} --mem={memoryLimit} "

        cmd += f"--run -- {langCMD.get(language,'execute')} "
        cmd += f"{inputFile} ; exit"

        cmd = cmd.replace("[ioRedirect]", "")
        cmd = cmd.replace(
            "[sourcePath]", sourcePath.replace(f"{isoPath}/", ""))
        cmd = cmd.replace("[binPath]", "./out")
        cmd = cmd.replace("[uBin]", "/usr/bin/")

        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            proc.communicate(timeout=(timeLimit / 1000) + 2)
        except subprocess.TimeoutExpired:
            if os.path.exists("/proc/" + str(proc.pid)):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            raise Exception("Warning : Isolate use time over limit or not terminated in time")

        if not os.path.exists(f"env/isoResult.txt"):
            raise Exception("Isolate\nisoResult.txt not found")

        try:
            with open(f"env/isoResult.txt", "r") as f:
                isoResult = f.read()
            isoResult = isolateMetaReader(isoResult)
        except:
            raise Exception("Isolate\nisoResult.txt writen wrong format")

        if "status" in isoResult and isoResult["status"] == "XX":
            printFail("GRADER", "internal error of the sandbox")
            printFail("GRADER", "ABORT PROCESS!!!")
            raise Exception("Isolate\ninternal error of the sandbox (status = XX)")

        if "status" in isoResult and isoResult["status"] == "TO":
            exitCode = 124
        elif "exitsig" in isoResult:
            exitCode = int(isoResult["exitsig"])
        elif "exitcode" in isoResult:
            exitCode = int(isoResult["exitcode"])
        else:
            exitCode = 0

        timeUse = float(isoResult["time"])
        if useControlGroup:
            memUse = int(isoResult["cg-mem"])  # TODO : CHECK IS IT RIGHT?
        else:
            memUse = int(isoResult["max-rss"])
            
        os.system("chmod 500 env")
        os.system("chmod 775 env/output.txt")
        os.system("chmod 775 env/error.txt")
        os.system(f"cp {isoPath}/output.txt env/output.txt")
        os.system(f"cp {isoPath}/error.txt env/error.txt")

        return exitCode, timeUse, memUse
    else:

        ioFile = (
            f"< ../{problemPath}/{testcase}.in 1>output.txt 2>error.txt"
        )
        cmd = f"cd env;ulimit -v {str(memoryLimit)}; {langCMD.get(language,'execute')}; exit;"
        cmd = cmd.replace("[ioRedirect]", ioFile)
        cmd = cmd.replace("[sourcePath]", sourcePath.replace("env/", ""))

        cmd = cmd.replace("[binPath]", "./out")
        cmd = cmd.replace("[uBin]", "")

        os.system("chmod 500 env")
        os.system("chmod 775 env/error.txt")
        os.system("chmod 775 env/output.txt")
        starttime = time.time()
        proc = subprocess.Popen([cmd], shell=True, preexec_fn=os.setsid)
        try:
            proc.communicate(timeout=(timeLimit / 1000))
            t = proc.returncode
        except subprocess.TimeoutExpired:
            t = 124
        endtime = time.time()
        timediff = endtime - starttime
        if os.path.exists("/proc/" + str(proc.pid)):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        os.system("chmod -R 750 env")
        return t, timediff, -1


def getJudgeType(problemPath : str) -> JudgeType:
    if Path(f"{problemPath}/interactive_script.py").is_file():
        return JudgeType.ogogi

    if Path(f"{problemPath}/check.cpp").is_file():
        thisCmd = f"g++ {problemPath}/check.cpp -O2 -std=c++17 -fomit-frame-pointer -o {problemPath}/binCheck"
        proc = subprocess.Popen([thisCmd], shell=True, preexec_fn=os.setsid)
        proc.communicate()
        if os.path.exists("/proc/" + str(proc.pid)):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # RIP
        return JudgeType.cppCheck

    if Path(f"{problemPath}/thaco.cpp").is_file() or Path(f"{problemPath}/partial.cpp").is_file():
        judgeFile = "thaco.cpp" if Path(f"{problemPath}/thaco.cpp").is_file() else "partial.cpp"
        thisCmd = f"g++ {problemPath}/{judgeFile} -O2 -std=c++17 -fomit-frame-pointer -o {problemPath}/binCheck"
        proc = subprocess.Popen([thisCmd], shell=True, preexec_fn=os.setsid)
        proc.communicate()
        if os.path.exists("/proc/" + str(proc.pid)):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # RIP
        return JudgeType.thaco

    return JudgeType.standard


def checkAnswer(problemPath: str, userPath: str, solPath: str, testCase: int, srcPath: str, judgeType: JudgeType):
    testCaseDto = TestcaseData(userPath, solPath, testCase, srcPath)

    if judgeType == JudgeType.cppCheck:
        result = cppCheck.getVerdict(testCaseDto, problemPath)
    elif judgeType == JudgeType.ogogi:
        result = ogogi.getVerdict(testCaseDto, problemPath)
    elif judgeType == JudgeType.thaco:
        result = thaco.getVerdict(testCaseDto, problemPath)
    else:  # ? use standard
        result = standard.getVerdict(testCaseDto)

    return result


def excuteAndVerdict(problemPath: str, testcase: int, timeLimit: float, memoryLimit: int, language: str, sourcePath: str, isoPath, judgeType: JudgeType) -> VerdictTestcase:
    exitCode, timeDiff, memUse = excute(
        problemPath, testcase, timeLimit, memoryLimit, language, sourcePath, isoPath)
    errSymbol = error(exitCode)

    if not errSymbol:
        # ? if no error
        userOutputPath = "env/output.txt"
        probOutputPath = f"{problemPath}/{testcase}.sol"

        verdictStatus, percentScore = checkAnswer(
            problemPath, userOutputPath, probOutputPath, testcase, sourcePath, judgeType)

        return VerdictTestcase(verdictStatus, percentScore, timeDiff, memUse)
    elif errSymbol == "TLE":
        return VerdictTestcase(VerdictStatus.timeExceed, 0.0, timeDiff, memUse)
    else:
        return VerdictTestcase(VerdictStatus.runtimeErr, 0.0, timeDiff, memUse)
