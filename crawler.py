import logging
import re
import time

import ddddocr
import requests
from loguru import logger as log
from requests_toolbelt.utils import dump

import util
from errors import *
from reqeustor import Requestor

# username = '3019234337'
# passwd = 'lly947559'

# username = '3021005190'
# passwd = 'LHX486666lhx'

username = '2020234407'
passwd = 'Wzy413lib'

ocr = ddddocr.DdddOcr()

def login(s, username, passwd):
    # 特征值
    html = s.get('https://sso.tju.edu.cn/cas/login').text
    if re.findall(r'Log In Successful', html):
        log.info("已经登录")
        return
    try:
        s_exec = re.findall("name=\"execution\" value=\"(.+?)\"",html)[0]
    except:
        raise HtmlParseError()
    # 验证码
    captcha = s.get('https://sso.tju.edu.cn/cas/images/kaptcha.jpg?id=')
    s_captcha = ocr.classification(captcha.content)
    # 进行登录
    data = {
        'username': username,
        'password': passwd,
        'captcha': s_captcha,
        'execution': s_exec,
        '_eventId': 'submit',
    }
    ret = s.post("https://sso.tju.edu.cn/cas/login", data=data).text
    if re.findall(r'Log In Successful', ret):
        # 加载cookie
        ret = s.get('http://classes.tju.edu.cn/eams/homeExt.action')
    else:
        raise LoginError()

def crawlCourses(s, identity):
    hasMinor = identity['hasMinor']

    majorCourses = []
    minorCourses = []

    majorCourses = getDetailTable(s, identity, False)
    if hasMinor:
        minorCourses = getDetailTable(s, identity, True)

    return {
        'major': majorCourses,
        'minor': minorCourses,
    }

def getDetailTable(s, identity, getMinor):
    isMaster = identity['isMaster']
    semesterId = identity['semesterId']
    projectId = 2 if getMinor else 1
    ret = ''
    if not isMaster:
        s.get(f'http://classes.tju.edu.cn/eams/courseTableForStd!index.action?projectId={projectId}')
        time.sleep(0.1)
        ret = s.get(f'http://classes.tju.edu.cn/eams/courseTableForStd!innerIndex.action?projectId={projectId}').text
    else:
        ret = s.get(f'http://classes.tju.edu.cn/eams/courseTableForStd!innerIndex.action?projectId={22}').text
    ids = re.findall("\"ids\",\"([^\"]+)\"", ret)[0]
    time.sleep(0.1)
    ret = s.post('http://classes.tju.edu.cn/eams/courseTableForStd!courseTable.action', data={
        "ignoreHead": "1",
        "setting.kind": "std",
        'startWeek': '',
        "semester.id": semesterId,
        "ids": ids
    }).text
    try:
        return parseCourses(ret)
    except IndexError:
        raise HtmlParseError()

def parseCourses(html):
    arrangePairArray = []
    courses = []
    arrangeHtmls = re.findall('in TaskActivity([\s\S]+?)fillTable', html)[0].split('var teachers')
    for arrangeItem in arrangeHtmls[1:]:
        rawTeachers = re.findall('var actTeachers = ([^;]+);', arrangeItem)[0]
        teacherArray = re.findall("\"([^\"]+)\"", rawTeachers)
        # 这节课的信息
        lineList = arrangeItem.split(';')
        # 课程相关
        courseLine = lineList[14].split(',')
        # classID
        classID = re.findall("\\((\\w+)\\)", courseLine[4])[0]
        threePair = re.findall("\"([^\"]+)\",\"[^\"]*\",\"([^\"]*)\",\"([01]+)\"", arrangeItem)[0]
        location = threePair[1].strip()
        rawWeeks = threePair[2].strip()
        weekArray = []
        for i, b in enumerate(rawWeeks):
            if b == "1": weekArray.append(i)
        twoPair = re.findall("([0-9]+)\\*unitCount\\+([0-9]+)", arrangeItem)
        weekday = util.tryInt(twoPair[0][1]) + 1
        unitArray = list(map(lambda x : util.tryInt(x[1]) + 1, twoPair))
        arrangePairArray.append(
            (
                classID,
                {
                    'teacherList': teacherArray,
                    'weekList': weekArray,
                    'unitList': unitArray,
                    'weekday': weekday,
                    'location': location,
                }
            )
        )
    trs = re.findall('<tr([\s\S]+?)</tr>', re.findall('<tbody([\s\S]+?)</tbody>', html)[0])
    for tr in trs:
        tds = re.findall('<td>([\s\S]+?)</td>', tr)
        if len(tds) <= 9: continue
        serial = re.findall('>(\d*)</a>', tds[1])[0]
        no = tds[2]
        name = tds[3]
        if 'style' in tds[3]:
            name = re.findall('(.+?)<sup', tds[3])[0].strip()+' '+re.findall('\">(.+?)</s', tds[3])[0].strip()
        credit = util.tryFloat(tds[4])
        teachers = tds[5].split(',')
        weeks = tds[6].strip()
        campus = ''
        if re.findall('(.+?校区)',tds[9]):
            campus = re.findall('(.+?校区)',tds[9])[0].strip()
        courseData = {
            "classId": serial,
            "courseId": no,
            "name": name,
            "credit": str(credit),
            "teacherList": teachers,
            "weeks": weeks,
            "campus": campus,
        }
        courseData["arrangeList"] = list(
            map(lambda x: x[1], filter(lambda x: x[0] == serial, arrangePairArray))
        )
        courses.append(courseData)
    return courses

def crawlGPA(s):
    ret = s.post('http://classes.tju.edu.cn/eams/dataQuery.action', data={'entityId': ''}).text
    isMaster = "研究" in ret
    s.get('http://classes.tju.edu.cn/eams/courseTableForStd!index.action', params={'projectId': '22' if isMaster else '1'})
    ret = s.get('http://classes.tju.edu.cn/eams/teach/grade/course/person!historyCourseGrade.action?projectType=MAJOR')
    try:
        return parseGPA(ret.text, isMaster)
    except IndexError:
        raise HtmlParseError()


def parseGPA(html, isMaster):
    total = re.findall(('汇总' if isMaster else '总计') + '</th>([\s\S]+?)</tr', html)
    if total:
        s_total = re.findall('<th>(.+?)</th>', total[0])
    total_data = {}

    if len(s_total) == 4:
        total_data['count'] = s_total[0]
        total_data['credits'] = util.tryFloat(s_total[1])
        total_data['gpa'] = util.tryFloat(s_total[2])
        total_data['weighted'] = util.tryFloat(s_total[3])
    elif len(s_total) == 2:
        total_data['count'] = s_total[0]
        total_data['credits'] = util.tryFloat(s_total[1])
        total_data['gpa'] = 0.0
        total_data['weighted'] = 0.0

    tables = re.findall('class=\"gridtable\">([\s\S]+?)</table>', html)
    grid_head = re.findall('gridhead([\s\S]+?)</thead>', tables[1])
    grid_head_list = re.findall('>(.+?)</th', grid_head[0])
    attr_dict = {}
    key_dict = {
        "学年学期":"semester",
        "课程代码":"code",
        "课程序号":"no",
        "课程类别":"type",
        "课程性质":"classProperty",
        "课程名称":"name",
        "学分":"credit",
        "考试情况":"condition",
        "最终": "score",
        "成绩":"score",
        "绩点":"gpa",
    }
    for i, name in enumerate(grid_head_list):
        for k, v in key_dict.items():
            if k == name:
                attr_dict[v] = i
    def getAttr(arr, key):
        try:
            return arr[attr_dict[key]]
        except:
            return ''

    s_courses = re.findall('<tr .+?\">([\s\S]+?)</tr>', tables[1])
    courses_data = []
    for c in s_courses:
        vals = re.findall('<td[^>]*>\\s*([^<\\t\\n]*)', c)
        data = {
            'semester': getAttr(vals, 'semester'),
            'code': getAttr(vals, 'code'),
            'no': getAttr(vals, 'no'),
            'type': getAttr(vals, 'type'),
            'classType': getAttr(vals, 'classProperty'),
            'name': getAttr(vals, 'name'),
            'credit': util.tryFloat(getAttr(vals, 'credit')),
            'score': util.tryFloat(getAttr(vals, 'score')),
            'rawScore': getAttr(vals, 'score'),
            'gpa': util.tryFloat(getAttr(vals, 'gpa')),
        }
        courses_data.append(data)

    return {
        'total': total_data,
        'courses': courses_data,
    }


def crawlExam(s, identity):
    ret = s.post('http://classes.tju.edu.cn/eams/stdExamTable.action', data={
        'project.id': '1',
        # 'semester.id': identity['semesterId']
        'semester.id': 75
    })
    ret = s.get('http://classes.tju.edu.cn/eams/stdExamTable!examTable.action').text
    try:
        return parseExam(ret)
    except IndexError:
        raise HtmlParseError()


def parseExam(html):
    exams = []

    tbody = re.findall('<tbody([\s\S]+?)</tbody>', html)[0]
    courses = re.findall('<tr>([\s\S]+?)</tr>', tbody)
    for course in courses:
        arr = re.findall('<td>(.+?)</td>', course)
        if not arr: continue
        arr = list(map(lambda x: re.findall('>(.+?)</font')[0] if 'color' in x else x,
                        arr))
        ext = "" if arr[8] == '正常' else arr[9]
        exams.append({
            'id': arr[0],
            'name': arr[1],
            'type': arr[2],
            'date': arr[3],
            'arrange': arr[5],
            'location': arr[6],
            'seat': arr[7],
            'state': arr[8],
            'ext': ext,
        })
    exams.sort(key=lambda x: x['date']+x['arrange'])
    return exams

def getIdentity(s):
    ret = s.post('http://classes.tju.edu.cn/eams/dataQuery.action', data={'entityId': ''}).text
    isMaster = "研究" in ret
    hasMinor = "辅修" in ret

    ret = s.post('http://classes.tju.edu.cn/eams/dataQuery.action',data= {"dataType": "semesterCalendar"}).text
    semesters = re.findall("id:([0-9]+),schoolYear:\"([0-9]+)-([0-9]+)\",name:\"(1|2)\"" ,ret)
    # 获取semesterId
    semesterId = None
    cur_semester = util.currentSemester()
    for arr in semesters:
        if f'{arr[1]}-{arr[2]} {arr[3]}' == cur_semester:
            semesterId = arr[0]
            break

    if semesterId is None:
        raise SemesterParseError()

    return {
        'isMaster': isMaster,
        'hasMinor': hasMinor,
        'semesterId': semesterId,
    }

def crawl(username, passwd):
    rsession = requests.session()
    rsession.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en-us",
            "Connection": "keep-alive",
            "Keep-Alive": "timeout=1, max=1000",
            "Accept-Charset": "GB2312,utf-8;q=0.7,*;q=0.7",
        })

    session = Requestor(rsession)
    login(session, username, passwd)
    identity = getIdentity(session)
    gpa = crawlGPA(session)
    courses = crawlCourses(session, identity)
    exam = crawlExam(session, identity)

    all = {
        'gpa': gpa,
        'courses': courses,
        'exams': exam,
    }
    return all

# if __name__ == '__main__':
#     try:
#         rsession = requests.session()
#         rsession.headers.update({
#                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
#                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
#                 "Accept-Language": "en-us",
#                 "Connection": "keep-alive",
#                 "Keep-Alive": "timeout=1, max=1000",
#                 "Accept-Charset": "GB2312,utf-8;q=0.7,*;q=0.7",
#             })

#         session = Requestor(rsession)
#         login(session, username, passwd)
#         identity = getIdentity(session)
#         gpa = crawlGPA(session)
#         courses = crawlCourses(session, identity)
#         exam = crawlExam(session, identity)

#         all = {
#             'gpa': gpa,
#             'courses': courses,
#             'exam': exam,
#         }

#     except Exception as e:
#         log.error(e, backtrace=True)

