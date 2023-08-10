from locust import HttpUser, TaskSet, task
import time

# 定义用户行为
class UserBehavior(TaskSet):
    
    @task
    def req(self):
        header = 'Mozilla/5.0 (Linux; Android 10; Redmi K30 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'

        h = {'username': '3019244343', 'passwd': 'Zzxzdi89'}
        resp = self.client.post("/get_classes", data=h, headers={'User-Agent': header})
        print(resp.text)


class WebsiteUser(HttpUser):
    tasks = [UserBehavior] # 指向一个定义的用户行为类
    min_wait = 3000 # 执行事务之间用户等待时间的下界（单位：毫秒）
    max_wait = 6000 # 执行事务之间用户等待时间的上界（单位：毫秒）