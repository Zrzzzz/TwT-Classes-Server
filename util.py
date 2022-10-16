from datetime import datetime, timedelta, timezone


def tryInt(s):
    try:
        return int(s)
    except:
        return 0

def tryFloat(s):
    try:
        return float(s)
    except:
        return 0.0

def currentSemester():
    now = datetime.now(tz=timezone(timedelta(hours=8)))
    year = now.year
    month = now.month
    if month > 7:
        return f'{year}-{year+1} 1'
    elif month < 2:
        return f'{year-1}-{year} 1'
    else:
        return f'{year-1}-{year} 2'
