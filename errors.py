class RequestError(Exception):
    def __str__(self) -> str:
        '请求异常'

class HtmlParseError(RequestError):
    def __str__(self) -> str:
        return 'html 解析异常'

class LoginError(RequestError):
    def __str__(self) -> str:
        return '登录失败'

class SessionInvalidError(RequestError):
    def __str__(self) -> str:
        return '会话过期'

class NotEvaluatedError(RequestError):
    def __str__(self) -> str:
        return '评教未完成'

class SemesterParseError(RequestError):
    def __str__(self) -> str:
        return '学期解析失败'
