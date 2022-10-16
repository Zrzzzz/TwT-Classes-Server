import time

wait_time = 0.5

def expired(resp):
    return '本次会话已经被过期' in resp.text

def too_fast(resp):
    return '过快' in resp.text

hooks = [expired]

def hooker_test(resp):
    for func in hooks:
        if func(resp):
            return True
    return False

class Requestor():
    def __init__(self, session) -> None:
        self.session = session

    def get(self, url, params={}):
        ret = self.session.get(url, params=params)
        while hooker_test(ret):
            time.sleep(wait_time)
            ret = self.session.get(url, params=params)
        return ret

    def post(self, url, data={}):
        ret = self.session.post(url, params=data)
        while hooker_test(ret):
            time.sleep(wait_time)
            ret = self.session.post(url, params=data)
        return ret
