import os
import sqlite3
import threading
import unittest

import html2text
import requests
from bs4 import BeautifulSoup

from Log import LoggerHandler
import Utils

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
    ========
    self.status反应了线程爬虫的状态，通过一个进度回调函数将状态反馈给UI图形界面。
        正常码:
        
        当self.status为1时，表示该线程正在爬取题目;
        为2时，表示题目爬取完成;
        为3时，正在爬取题解;
        为4时，题解与题目爬取完毕;
        
        错误码:
        -1: 获取练习信息超时;
        -2: 表示无权获取该练习;
        -3: 访问题目页面出错, 很有可能是用户的线程数设置太高触发了网站的反爬虫机制.
        
        一旦错误码为-1, -2, -3, 爬虫线程将不会试图获取接下来的题解，并且也不会写入数据库中.
    
    switch_crawl_progress(self, status, status_text=None):
        该方法传入status与status_text对自己的状态进行设置，如果status的值是四个正常码之一，则无需传入status_text
        但是如果status的值是负值，那么就需要传入status_text以便对状态文本进行设置.
        
    ========
    '''

    def __switch_crawl_progress(self, status, status_text=None):
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

    '''
    ========
    获取网站地址部分，将self.id传入，返回的是对应的题目的地址。
    ========
    '''

    def __get_full_website_link(self):
        return "https://www.luogu.com.cn/problem/" + str(self.id)

    def __get_solution_website_link(self):
        return "https://www.luogu.com.cn/problem/solution/" + str(self.id)

    '''
    ========
    生成文件地址部分
        def generate_file_path(self):
            该方法尝试获取self.tags, 并通过Utils中的tag翻译器将获取到的题目ID翻译为文本.
            并按照题目给出的要求存放到指定目录。不知道是否可以写的更加优雅一些，目前是字符串拼接。
            
            另，如果file_path不存在，方法会尝试通过os.makedirs生成一个文件夹.
        def generate_exercise_filename(self):
        def generate_solution_filename(self):
            这两个方法调用generate_file_path获取文件夹，并在后面拼接对应markdown文件的地址，存入self.exercise_path与self.solution_pa
            th中.
    ========
    '''

    def __generate_file_path(self):
        taglist = ""
        if self.tags is not None:
            for p in self.tags:
                taglist += "-" + Utils.tag_parser(str(p))
        file_path = (self.path + "/" +
                     Utils.difficulty_parser(str(self.difficulty)) + taglist + "/" + str(self.id) + "-" + str(
                    self.title) + "/")
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        return file_path

    def __generate_exercise_filename(self):
        exercise_path = self.__generate_file_path() + str(self.id) + "-" + str(self.title) + ".md"
        self.exercise_path = exercise_path
        return exercise_path

    def __generate_solution_filename(self):
        solution_path = self.__generate_file_path() + str(self.id) + "-" + str(self.title) + "-" + "题解" + ".md"
        self.solution_path = solution_path
        return solution_path

    '''
    ========
    获取练习内容与题解内容
        def get_exercise(self):
            该方法会通过requests获取洛谷的题目内容, 再用BeautifulSoup煲汤喝一下, 题目内容本程序使用的解决方案是直接获取page.content
            事实上, 注意到BeautifulSoup中获取的内容中的Script有一段uri_component_decoder, 提示了我们应当使用类似uri_component_decoder
            的功能来解码json信息.
            
            获取到的json信息同样包含了题目标题等信息, 但是我偷懒了, 使用了BeautifulSoup获取的page.content通过html2markdown强转,
            在预览的时候排版会有不影响阅读的轻微错误. 
            
            该方法会试图获取tags, 标签, 难度, 标题等信息并存储到self对应的属性中, 在一切工作完毕之后将markdown文件写入.
            
        可能导致的爬虫线程异常:
            状态码变为-1, 获取页面超时;
            变为-2, 无权查看题目;
            变为-3, 访问页面错误;
            
            遇到上述错误时爬虫线程将不会试图获取题解，并在写入数据库时抛弃. 
            
            尝试捕获的exception:
            KeyError
                在无权查看页面的情况下, 会导致获取['problem']键, 从而抛出KeyError
        --------
            
        def get_solution(self):
            该方法同样地通过requests获取洛谷中题目内容, 再用BeautifulSoup煲汤喝一下, 与获取题目不同, 题解要求必须通过decode_uri_componen
            t来获取题解的一些相关信息.
            
            尝试捕获的exception:
            KeyError & IndexError
                在大多数正常情况下，题解的['result']长度应至少为1, 若无法访问['result'][0]则会抛出IndexError
                在某些特定情况下, 会获取不到tags的['problem']下的['tags']键，从而会抛出KeyError
                
    ========
    '''

    def get_exercise(self):
        try:
            page = requests.get(self.__get_full_website_link(), headers=self.header, cookies=self.cookie, timeout=5)
        except requests.exceptions.RequestException:
            self.__switch_crawl_progress(-1, "获取练习页面信息异常! 可能超时.")
            return -1
        else:
            #   判断网页是否成功获取
            if page.status_code == 200:
                # 煲汤喝一下
                soup = BeautifulSoup(page.content, 'lxml')
                self.__switch_crawl_progress(1)
                # 获取题目的分类信息
                decoded_json = Utils.uri_component_decoder(soup)
                data = Utils.json_parser(decoded_json)
                logger.debug(data)
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
                    self.__switch_crawl_progress(-2, "异常, 你无权查看此题目")
                    return -1
                else:
                    html2text_converter = html2text.HTML2Text()
                    content_soup = BeautifulSoup(str(soup.article), 'lxml')
                    # 将HTML转换为Markdown
                    markdown_content = html2text_converter.handle(str(content_soup.prettify()))
                    # 将Markdown文件保存至文件夹中
                    with open(self.__generate_exercise_filename(), 'w', encoding='utf-8') as file:
                        file.write(markdown_content)
                        self.__switch_crawl_progress(2)
                        return 1
            else:
                self.__switch_crawl_progress(-3, f"访问题目页面出错, 代码: {page.status_code}")
                return -1

    def get_solution(self):
        try:
            page = requests.get(self.__get_solution_website_link(), headers=self.header, cookies=self.cookie, timeout=5)
        except requests.exceptions.RequestException:
            self.__switch_crawl_progress(-1, "获取题解页面信息异常! 可能超时.")
        else:
            #   判断网页是否成功获取
            if page.status_code == 200:
                self.__switch_crawl_progress(3)
                soup = BeautifulSoup(page.content, 'lxml')
                decode_res = (Utils.uri_component_decoder(soup))
                data = Utils.json_parser(decode_res)
                logger.debug(data)
                try:
                    first_result_content = data['currentData']['solutions']['result'][0]['content']
                    self.solution_author = data['currentData']['solutions']['result'][0]['author']['name']
                except IndexError:
                    self.__switch_crawl_progress(-4, "异常, 题解不存在, 或未登录 & 登录信息错误.")
                except KeyError:
                    self.__switch_crawl_progress(-4, "异常, 题解不存在, 或未登录 & 登录信息错误.")
                else:
                    with open(self.__generate_solution_filename(), 'w', encoding='utf-8') as file:
                        file.write(first_result_content)
                        self.__switch_crawl_progress(4)
            else:
                self.__switch_crawl_progress(-3, f"访问题解页面出错, 代码: {page.status_code}")
        self.__insert_obj_to_database()

    '''
    ========
    插入数据库部分
        def insert_obj_to_database(self):
            该方法会先检测爬虫线程的状态码, -1, -2, -3的错误码的爬虫线程不会试图执行写入数据库操作, 直接抛弃.
            如果状态码正常, 则会创建search_info.db, 表名为exercise, 数据顺序从左到右分别是exercise_data对象给出的顺序.
            
            由于题目需求, 本程序选用的是SQLite, 较为轻便.
    ========
    '''

    def __insert_obj_to_database(self):
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
                    exercise_id TEXT PRIMARY KEY,
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
                    logger.info(f"ID {self.id} 已成功插入数据库!")
                else:
                    logger.info(f"ID {self.id} 已存在，无需插入")
            sync_lock.release()

class TestWorkers(unittest.TestCase):
    def test_get_exercise(self):
        worker = CrawlerWorker(path=r"./test", id=1000, header={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/70.0.3538.102 Safari/537.36'}, cookie={})
        worker.get_exercise()
        self.assertEqual(worker.status, 2)
        worker.get_solution()
        self.assertEqual(worker.status, 4)
