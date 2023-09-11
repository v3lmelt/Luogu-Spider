import json
import os
import queue
import random
import threading
import time
from queue import Queue

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By

import DEPRECATED_WebCrawlerDifficulty


class DifficultyGetter:
    def __init__(self):
        self.header = {'user-agent':
                           'Mozilla/5.0 (iPad; CPU OS 13_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                           'CriOS/87.0.4280.77 Mobile/15E148 Safari/604.1'}
        self.cookie = {
            '__client_id': '1d9dc4c15ef13440c22d357bcde61b47ce930088',
            '_uid': '87731'
        }
        self.path = "F:/json_mapper/difficulty.json"

    def tag_weblink_generator(self, tag_id):
        return "https://www.luogu.com.cn/problem/list?tag=&page=1&difficulty=" + str(tag_id)

    def tag_getter(self, tag_id):
        print(f"当前获取: {tag_id}")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(self.tag_weblink_generator(tag_id))

        try:
            t = driver.find_element(By.CSS_SELECTOR, "#app > div.main-container > main > div > section > div > "
                                                     "section:nth-child(3) > div > div.block-item.tag")
        except selenium.common.exceptions.NoSuchElementException:
            print(f"tag_id: {tag_id} , 该网页获取的不是Tag信息!")

        else:
            print(f"获取结果: {tag_id} 对应的是 {t.text}")
            self.add_tag_to_dictionary(tag_id=tag_id, tag_name=t.text)

    def add_tag_to_dictionary(self, tag_id, tag_name):
        # 如果 JSON 文件已经存在，读取现有数据
        if os.path.exists(self.path):
            with open(self.path, 'r') as file:
                data = json.load(file)
        else:
            # 如果 JSON 文件不存在，创建一个新的数据对象
            data = {"tags": {}}

        # 添加新的词典项
        data["tags"][tag_id] = tag_name

        # 将更新后的数据保存回 JSON 文件
        with open(self.path, 'w') as file:
            json.dump(data, file, indent=4)

    def does_tag_exist(self, tag_id):
        # 检查 JSON 文件是否存在
        if not self.path or not os.path.exists(self.path):
            return False

        # 读取 JSON 文件内容
        with open(self.path, 'r') as file:
            data = json.load(file)

        # 检查 tagID 是否存在于 JSON 数据中的 'tags' 键中
        if 'tags' in data and str(tag_id) in data['tags']:
            return True
        else:
            return False

    # 多线程工作
    def tag_getter_worker(self,threads):
        def multithread():
            while not work_queue.empty():
                tag_id = work_queue.get()
                # 查询是否已经存在在json文件中
                if not self.does_tag_exist(tag_id):
                    self.tag_getter(tag_id)
                    work_queue.task_done()
                    time.sleep(random.uniform(3, 5))
                else:
                    print(f"已获取到tag信息! {tag_id}")
                    work_queue.task_done()

        work_queue = queue.Queue()
        for x in range(0, 10):
            work_queue.put(x)
        for i in range(threads):
            t = threading.Thread(target=multithread)
            time.sleep(random.uniform(0, 3))
            t.start()

if __name__ == '__main__':
    tag_getter = WebCrawlerDifficulty.DifficultyGetter()
    tag_getter.tag_getter_worker(5)