import json

import html2text
import requests
from bs4 import BeautifulSoup

import Utils
import os


class CrawlerWorker:
    def __init__(self, path, id, header, cookie, progress_callback=None):
        self.path = path
        self.id = id
        self.header = header
        self.cookie = cookie

        self.tags = None
        self.difficulty = None
        self.title = None

        self.exercise_path = None

        self.status = 0
        self.status_text = "等待中..."

        self.progress_callback = progress_callback

    def switch_crawl_progress(self, status):
        if status == 1:
            self.status = 1
            self.status_text = "正在爬取题目!"
        elif status == 2:
            self.status = 2
            self.status_text = "爬取题目完成!"
        elif status == 3:
            self.status = 3
            self.status_text = "正在爬取题解!"
        elif status == 4:
            self.status = 4
            self.status_text = "题解与题目爬取完毕!"

        # 调用回调函数，传递status和status_text
        if callable(self.progress_callback):
            self.progress_callback(self.id, self.status, self.status_text)


    def get_full_website_link(self):
        return "https://www.luogu.com.cn/problem/P" + str(self.id)

    def generate_file_path(self):
        if self.exercise_path is None:
            taglist = ""

            for p in self.tags:
                taglist += "-" + Utils.tag_parser(str(p))
            file_path = (self.path + "/" +
                         Utils.difficulty_parser(str(self.difficulty)) + taglist + "/P" + str(self.id) + "-" + str(
                self.title) + "/")
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            else:
                print("文件夹已存在!")
            self.exercise_path = file_path

        return self.exercise_path

    def generate_exercise_filename(self):
        return self.generate_file_path() + "P" + str(self.id) + "-" + str(self.title) + ".md"

    def generate_solution_filename(self):
        return self.generate_file_path() + "P" + str(self.id) + "-" + str(self.title) + "-" + "题解" + ".md"

    def get_exercise(self):
        page = requests.get(self.get_full_website_link(), headers=self.header, cookies=self.cookie)
        print(page)

        #   判断网页是否成功获取
        if page.status_code == 200:
            soup = BeautifulSoup(page.content, 'lxml')
            self.switch_crawl_progress(1)
            # 获取题目的分类信息
            decoded_json = Utils.uri_component_decoder(soup)
            data = Utils.json_parser(decoded_json)

            print(data)

            try:
                self.tags = data['currentData']['problem']['tags']
                self.difficulty = data['currentData']['problem']['difficulty']
                self.title = Utils.clean_folder_name(soup.article.h1.get_text())
            except KeyError:
                if callable(self.progress_callback):
                    self.progress_callback(self.id, -1, "异常! 你无权查看此题目!")
            html2text_converter = html2text.HTML2Text()
            # 将HTML转换为Markdown
            markdown_content = html2text_converter.handle(str(soup.article))
            # 将Markdown文件保存至文件夹中
            with open(self.generate_exercise_filename(), 'w', encoding='utf-8') as file:
                file.write(markdown_content)
                self.switch_crawl_progress(2)

        else:
            print("Error! Status Code: " + str(page.status_code))

    def get_solution_website_link(self):
        return "https://www.luogu.com.cn/problem/solution/P" + str(self.id)

    def get_solution(self):
        page = requests.get(self.get_solution_website_link(), headers=self.header, cookies=self.cookie)
        #   判断网页是否成功获取
        if page.status_code == 200:
            self.switch_crawl_progress(3)
            soup = BeautifulSoup(page.content, 'lxml')
            decode_res = (Utils.uri_component_decoder(soup))
            data = Utils.json_parser(decode_res)
            # 提取 "result" 数组的第一个对象的 "content" 字段的值

            try:
                first_result_content = data['currentData']['solutions']['result'][0]['content']
            except IndexError:
                if callable(self.progress_callback):
                    self.progress_callback(self.id, -1, "异常! 题解不存在.")
            else:
                with open(self.generate_solution_filename(), 'w', encoding='utf-8') as file:
                    file.write(first_result_content)
                    self.switch_crawl_progress(4)

        else:
            print("Error! Status Code: " + str(page.status_code))
