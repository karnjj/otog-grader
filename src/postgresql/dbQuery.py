import time
from DTO.result import ResultDTO
from constants.colors import colors
from .dbInit import DB
from datetime import datetime
import traceback
import json

db = DB()


def testDBConnection():
    try:
        db.connect()
    except Exception:
        print(f"{colors.FAIL}[ PostgreSQL ]{colors.RESET} Connection failed.")
        traceback.print_exc()
        exit(1)
    print(
        f"{colors.OKGREEN}[ PostgreSQL ]{colors.RESET} Connect PostgreSQL success fully!.")
    DBDisconnect()


def DBConnect():
    try:
        db.connect()
    except:
        for i in range(5):
            try:
                print(
                    f"{colors.WARNING}[ PostgreSQL ]{colors.RESET} Connection failed, retrying in ({i+1}) secs..."
                )
                time.sleep(i + 1)
                db.connect()
                print(
                    f"{colors.OKGREEN}[ PostgreSQL ]{colors.RESET} Connect PostgreSQL success fully!.")
                return
            except:
                pass
        print(
            f"{colors.FAIL}[ PostgreSQL ]{colors.RESET} Connection Lost.")
        exit(1)


def DBDisconnect():
    db.disconnect()

def getQueueModBalace(nGrader:int, thisGrader:int):
    #thisGrader will count from 1 to nGrader
    db.update()
    cur = db.query(
        f"""SELECT S.*, B."timeLimit", B."memoryLimit", B."case", B."score" as "maxScore" FROM submission as S
            LEFT JOIN problem as B ON S."problemId" = B."id"
            WHERE status = 'waiting' AND mod(S.id,{nGrader}) = {thisGrader - 1} ORDER BY S."creationDate" """
    )
    result = cur.fetchone()
    cur.close()
    return result

def getQueue():
    db.update()
    cur = db.query(
        f"""SELECT S.*, B."timeLimit", B."memoryLimit", B."case", B."score" as "maxScore" FROM submission as S
            LEFT JOIN problem as B ON S."problemId" = B."id"
            WHERE status = 'waiting' ORDER BY S."creationDate" """
    )
    result = cur.fetchone()
    cur.close()
    return result


def updateRunningInCase(resultId, case):
    sql = """UPDATE submission SET "updateDate" = %s, status = 'grading' WHERE id = %s"""
    val = (datetime.now(), str(resultId))
    cur = db.query(sql, val)
    cur.close()
    db.update()


def updateResult(result: ResultDTO):
    # TODO : Imprement memUse in DB
    currentDate = datetime.now()
    sql = ["""UPDATE submission SET status = %s, "updateDate" = %s WHERE id = %s"""]
    val = [result.status.value, currentDate, result.id]
    sql += ["""INSERT INTO "submissionResult" ("submissionId", result, score, "timeUsed", "memUsed", errmsg)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"""]
    val += [result.id, result.result, result.score, result.sumTime, result.memUse, result.errmsg]
    cur = db.query(";".join(sql), tuple(val))
    submissionResultId = cur.fetchone()
    cur.close()
    subtaskIndex = 0
    for subtask in result.fullResult:
        subtaskIndex += 1
        sql = ["""INSERT INTO "subtaskResult" ("submissionResultId", "subtaskIndex", score, "fullScore")
                VALUES (%s, %s, %s, %s) RETURNING id"""]
        val = [submissionResultId, subtaskIndex, subtask.score, subtask.fullScore]
        cur = db.query(";".join(sql), tuple(val))
        subtaskResultId = cur.fetchone()
        cur.close()
        testcaseIndex = 0
        sql = []
        val = []
        for verdict in subtask.verdicts:
            testcaseIndex += 1
            sql += ["""INSERT INTO verdict ("subtaskId", "testcaseIndex", status, percent, "timeUsed", "memUsed")
                    VALUES (%s, %s, %s, %s, %s, %s)"""]
            val += [subtaskResultId, testcaseIndex, verdict.status.value, verdict.percent, verdict.timeUse, verdict.memUse]
        cur = db.query(";".join(sql), tuple(val))
        cur.close()
    db.update()
