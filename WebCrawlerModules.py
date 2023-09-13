import json
import os
import sqlite3
import threading

import html2text
import requests
from bs4 import BeautifulSoup

import Utils
from Log import LoggerHandler

logger = LoggerHandler(name="CrawlerWorker")
sync_lock = threading.Lock()




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
        self.solution_path = None

        self.exercise_author = None
        self.solution_author = None

        self.status = 0
        self.status_text = "等待中..."

        self.progress_callback = progress_callback

    '''
    def switch_crawl_progress(self, status, status_text=None):
        About status code,
            1: The worker is trying to crawl exercise
            2: The worker has finished the job of crawling exercise
            3: The worker is trying to crawl the solution
            4: The worker has done all the jobs
        
        Err codes,
            -1: Timeout
            -2: You have no auth to check exercise
            -3: Request error
            -4: The exercise has no solution
    '''
    def switch_crawl_progress(self, status, status_text=None):
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
        elif status is not None and status_text is not None:
            self.status = status
            self.status_text = status_text
        # 调用回调函数，传递status和status_text
        if callable(self.progress_callback):
            self.progress_callback(self.id, self.status, self.status_text)

    def get_full_website_link(self):
        return "https://www.luogu.com.cn/problem/P" + str(self.id)

    def generate_file_path(self):
        taglist = ""
        if self.tags is not None:
            for p in self.tags:
                taglist += "-" + Utils.tag_parser(str(p))
        file_path = (self.path + "/" +
                     Utils.difficulty_parser(str(self.difficulty)) + taglist + "/P" + str(self.id) + "-" + str(
                    self.title) + "/")
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        return file_path

    def generate_exercise_filename(self):
        exercise_path = self.generate_file_path() + "P" + str(self.id) + "-" + str(self.title) + ".md"
        self.exercise_path = exercise_path
        return exercise_path

    def generate_solution_filename(self):
        solution_path = self.generate_file_path() + "P" + str(self.id) + "-" + str(self.title) + "-" + "题解" + ".md"
        self.solution_path = solution_path
        return solution_path

    def get_exercise(self):
        try:
            page = requests.get(self.get_full_website_link(), headers=self.header, cookies=self.cookie, timeout=5)
        except requests.exceptions.RequestException:
            self.switch_crawl_progress(-1, "获取练习页面信息异常! 可能超时.")
        else:
            #   判断网页是否成功获取
            if page.status_code == 200:
                # 煲汤喝一下
                soup = BeautifulSoup(page.content, 'lxml')
                self.switch_crawl_progress(1)
                # 获取题目的分类信息
                decoded_json = Utils.uri_component_decoder(soup)
                data = Utils.json_parser(decoded_json)
                logger.info(data)
                try:
                    # 获取练习作者，标签，难度，标题等信息
                    self.exercise_author = data['currentData']['problem']['provider']['name']
                    self.tags = data['currentData']['problem']['tags']
                    # 如果没有标签，则用-1代表该题没有标签
                    if not self.tags:
                        self.tags.append(-1)
                    self.difficulty = data['currentData']['problem']['difficulty']
                    self.title = Utils.clean_folder_name(soup.article.h1.get_text())
                except KeyError:
                    self.switch_crawl_progress(-2, "异常, 你无权查看此题目")
                else:
                    html2text_converter = html2text.HTML2Text()
                    # 将HTML转换为Markdown
                    markdown_content = html2text_converter.handle(str(soup.article))
                    # 将Markdown文件保存至文件夹中
                    with open(self.generate_exercise_filename(), 'w', encoding='utf-8') as file:
                        file.write(markdown_content)
                        self.switch_crawl_progress(2)

            else:
                self.switch_crawl_progress(-3, f"访问题目页面出错, 代码: {page.status_code}")

    def get_solution_website_link(self):
        return "https://www.luogu.com.cn/problem/solution/P" + str(self.id)

    def get_solution(self):
        try:
            page = requests.get(self.get_solution_website_link(), headers=self.header, cookies=self.cookie, timeout=5)
        except requests.exceptions.RequestException:
            self.switch_crawl_progress(-1, "获取题解页面信息异常! 可能超时.")
        else:
            #   判断网页是否成功获取
            if page.status_code == 200:
                self.switch_crawl_progress(3)
                soup = BeautifulSoup(page.content, 'lxml')
                decode_res = (Utils.uri_component_decoder(soup))
                data = Utils.json_parser(decode_res)
                logger.info(data)
                try:
                    first_result_content = data['currentData']['solutions']['result'][0]['content']
                    self.solution_author = data['currentData']['solutions']['result'][0]['author']['name']
                except IndexError:
                    self.switch_crawl_progress(-4, "异常, 题解不存在.")
                except KeyError:
                    self.switch_crawl_progress(-4, "异常, 题解不存在.")
                else:
                    with open(self.generate_solution_filename(), 'w', encoding='utf-8') as file:
                        file.write(first_result_content)
                        self.switch_crawl_progress(4)
            else:
                self.switch_crawl_progress(-3, f"访问题解页面出错, 代码: {page.status_code}")
        self.insert_obj_to_database()

    def insert_obj_to_database(self):
        # 查询自身状态, -1, -2, -3的错误码是不被允许加入数据库的，因为题目信息缺失
        if self.status != -1 and self.status != -2 and self.status != -3:
            # 翻译难度信息和tag信息

            parsed_tags = []
            if self.tags is not None:
                for x in self.tags:
                    parsed_tags.insert(0, Utils.tag_parser(str(x)))

            parsed_difficulty = ""
            if self.difficulty is not None:
                parsed_difficulty = Utils.difficulty_parser(str(self.difficulty))

            exercise_data = {
                'exercise_id': self.id,
                'tags': ','.join(parsed_tags),
                'difficulty': parsed_difficulty,
                'title': self.title,
                'exercise_path': self.exercise_path,
                'solution_path': self.solution_path,
                'solution_author': self.solution_author,
                'exercise_author': self.exercise_author,
            }

            sync_lock.acquire(True)
            # 连接到SQLite数据库
            conn = sqlite3.connect('storage_info.db')

            # 创建一个游标对象，用于执行SQL语句
            cursor = conn.cursor()

            # 检查是否存在exercise表
            cursor.execute('''SELECT name FROM sqlite_master WHERE type='table' AND name='exercise';''')
            table_exists = cursor.fetchone()

            if not table_exists:
                # 如果表不存在，则创建exercise表
                cursor.execute('''
                CREATE TABLE exercise (
                    exercise_id INTEGER PRIMARY KEY,
                    tags TEXT,
                    difficulty TEXT,
                    title TEXT,
                    exercise_path TEXT,
                    solution_path TEXT,
                    solution_author TEXT,
                    exercise_author TEXT
                );
                ''')
                conn.commit()
                print("exercise表已创建")
            else:
                # 查询数据库以检查是否存在具有相同 exercise_id 的记录
                cursor.execute('SELECT exercise_id FROM exercise WHERE exercise_id = :exercise_id',
                               {'exercise_id': self.id})
                existing_id = cursor.fetchone()

                if not existing_id:
                    # 如果不存在具有相同 exercise_id 的记录，才执行插入操作
                    cursor.execute('''
                        INSERT INTO exercise (exercise_id, tags, difficulty, title, exercise_path, solution_path, solution_author, exercise_author)
                        VALUES (:exercise_id, :tags, :difficulty, :title, :exercise_path, :solution_path, :solution_author, :exercise_author)
                    ''', exercise_data)
                    conn.commit()
                    logger.info(f"exercise_id {self.id} 已插入")
                else:
                    logger.info(f"exercise_id {self.id} 已存在，无需插入")
            sync_lock.release()
