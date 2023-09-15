import os.path
import pickle
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from QueryModule import QueryLuoguList
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService

import Utils
from Log import LoggerHandler
from WebCrawlerWorker import WebCrawlerWorker

complete_message_box_show = False
is_server_run = False
logger = LoggerHandler(name="UserInterface")

query_result = []
'''
========
UI部分
def select_path():
    该方法弹出一个对话框，让用户选择文件夹路径.
def callback():
    改方法负责更新TkInter Treeview中的爬虫线程信息.
========
'''


def select_path():
    path = filedialog.askdirectory()
    path_entry.delete(0, tk.END)
    path_entry.insert(0, path)


def set_entry_content(entry, content):
    entry.delete(0, 'end')
    entry.insert(0, content)


def clear_library():
    library_var.set('')


def clear_difficulty():
    difficulty_var.set('')


def callback(exercise_id, status, status_text):
    # 查找treeview中是否已有信息
    if tree.exists(exercise_id):
        tree.item(exercise_id, values=(exercise_id, status_text))
    else:
        tree.insert('', "end", exercise_id, values=(exercise_id, status_text))
        tree.yview_moveto(1.0)


'''
登录界面
def handle_login():
    该方法是UI界面中点击"登录"按钮后触发的方法, Selenium会试图获取存放与当前文件夹下的chromedriver.exe,
    并且在获取成功之后打开浏览器页面.
    
    这个方法还使用了pickle库保存用户登录之后的信息，方便之后随时读取.
    为了不阻塞主线程，这个登录是跑在其他线程上的.
'''


def handle_login():
    def get_driver():
        edge_service = EdgeService(executable_path=r"./msedgedriver.exe")
        driver = webdriver.Edge(service=edge_service)
        return driver

    def get_cookie():
        browser = get_driver()
        browser.get("https://www.luogu.com.cn/auth/login")
        while True:
            try:
                if browser.current_url == 'https://www.luogu.com.cn/':
                    luogu_cookies = browser.get_cookies()
                    browser.quit()

                    cookies = {}

                    # 将获取到的cookie写入准备导出的cookies变量中

                    for item in luogu_cookies:
                        cookies[item['name']] = item['value']

                    # 获得过期时间
                    cookies['expiry'] = min(luogu_cookies[1]['expiry'], luogu_cookies[2]['expiry'])

                    # 使用pickle库导出
                    output_path = open(r'luogucookie.pickle', 'wb')
                    pickle.dump(cookies, output_path)
                    output_path.close()

                    set_entry_content(uid_display, str(cookies['_uid']))
                    set_entry_content(client_id_display, str(cookies['__client_id']))

                    uid_display.update()
                    client_id_display.update()

                    return cookies
            except selenium.common.exceptions.NoSuchWindowException:
                messagebox.showinfo("登录失败!", "浏览器窗口已关闭!")
                break

    # 注意! 这是跑在其他线程上的!
    p = threading.Thread(target=get_cookie)
    p.start()


def check_cookie_info_valid():
    if os.path.exists('luogucookie.pickle'):
        cookie_file = open('luogucookie.pickle', 'rb')
        cookie_info = pickle.load(file=cookie_file)
        if cookie_info['expiry'] > int(time.time()):
            return True
    return False


'''
========
开始爬取
    def start_crawling():
        负责爬取工作的初始化工作, 并在之后开辟线程执行multithreaded()和check_task_complete()
        def multithreaded():
            该方法通过创建WebCrawlerWorker对象并从work_queue中取出一个待爬取的ID, 开始爬取工作.
        def check_task_complete():
            该方法运行在其他线程上, 通过死循环检测work_queue是否为空从而检测爬取工作是否成功完成.
========
'''


def start_query():
    def query_func():
        if check_cookie_info_valid() or (client_id_display.get() != "" and uid_display.get() != ""):
            # 先获取难度信息, 并转换成对应的ID
            try:
                difficulty_id = Utils.difficulty_to_id_parser(difficulty_var.get())
                # 获取tag信息, 并转换成对应的ID
                tag_str = tag_entry.get()
                tag_id_for_query = ""
                tag_id = []
                if tag_str != '':
                    tag_arr = tag_str.split(',')
                    for item in tag_arr:
                            tag_id.append(Utils.tag_to_id_parser(item))
                            tag_id_for_query = "|".join(tag_id)
            except ValueError:
                messagebox.showinfo("Tag错误!, 你输入了一个不正确的Tag")
            else:
                # 获取题库信息, 并转换成对应的ID
                library_var_id = Utils.library_type_parser(library_var.get())
                keyword_for_query = keyword_entry.get()

                query_obj = QueryLuoguList(keyword_for_query, difficulty_id, tag_id_for_query, library_var_id)
                query_obj.search_with_params()

                global query_result
                query_result = query_obj.get_result_id()
                query_tree.delete(*query_tree.get_children())
                for x, y in zip(query_obj.get_result_id(), query_obj.get_result_name()):
                    query_tree.insert('', "end", x, values=(x, y))
                    query_tree.yview_moveto(1.0)
    p = threading.Thread(target=query_func)
    p.start()

def start_crawling():
    def multithreaded():
        while not work_queue.empty():
            worker = WebCrawlerWorker(exercise_id=work_queue.get(), path=save_path, progress_callback=callback,
                                      cookie=actual_cookie)
            worker.start_work()
            work_queue.task_done()
            # 防止密集请求
            time.sleep(random.uniform(0.5, 1))

    def check_task_complete():
        global is_server_run
        while True:
            if work_queue.empty():
                time.sleep(2)
                messagebox.showinfo("任务完成", "任务完成!")
                if not is_server_run:
                    is_server_run = True
                    Utils.run_jar(root)
                break

    # 初始化登录信息，要么有保存在本地的cookie内容，要么用户输入了cookie内容
    if check_cookie_info_valid() or (uid_display.get() != "" and client_id_display.get() != ""):
        # 检查用户输入信息是否合法
        if (thread_num_entry.get().
                isdecimal() and path_entry.get() != ""):
            # 初始化队列信息
            work_queue = queue.Queue()
            thread_num = int(thread_num_entry.get())
            save_path = path_entry.get()

            actual_cookie = {}
            if check_cookie_info_valid():
                # 从pickle文件中读取信息
                cookie_data = Utils.read_pickle_info()

                set_entry_content(uid_display, str(cookie_data['_uid']))
                set_entry_content(client_id_display, str(cookie_data['__client_id']))
                # 生成传给Worker的参数
                actual_cookie = {'_uid': str(cookie_data['_uid']), '__client_id': str(cookie_data['__client_id'])}
            else:
                # 用户自定义输入
                actual_cookie = {'_uid': str(uid_display.get()), '__client_id': str(client_id_display.get())}
            # 将任务放入队列
            global query_result
            if query_result:
                for i in query_result:
                    work_queue.put(i)
                # 从queue中拿取一个任务，分配给指定数量的线程
                for x in range(thread_num):
                    if not work_queue.empty():
                        t = threading.Thread(target=multithreaded)
                        t.start()

                        time.sleep(random.uniform(0.5, 1))

                # 检测任务是否完成线程
                p = threading.Thread(target=check_task_complete)
                p.start()
            else:
                messagebox.showinfo("你还没有搜索!", "你还没有搜索, 没有办法爬取!")
        else:
            messagebox.showinfo("输入错误", "你输入的信息有误!")
    else:
        messagebox.showinfo("Cookie信息", "检测不到你的Cookie信息或已失效, 请重新登录!")
        p = threading.Thread(target=handle_login)
        p.start()


'''
========
 UI部分
========
'''

# 创建主窗口
root = tk.Tk()
root.title("Web爬虫GUI")

# 创建所属题库标签和下拉菜单
library_label = tk.Label(root, text="所属题库")
library_label.grid(row=7, column=0, padx=(10, 5), pady=5)

library_var = tk.StringVar()
library_optionmenu = tk.OptionMenu(root, library_var, "主题库", "入门与面试", "CodeForces", "SPOJ", "AtCoder",
                                   "UVA")
library_optionmenu.grid(row=7, column=1, padx=(5, 10), pady=5)

clear_library = tk.Button(root, text="清空题库", command=clear_library)
clear_library.grid(row=7, column=2, padx=(10, 5), pady=5)

# 创建难度标签和下拉菜单
difficulty_label = tk.Label(root, text="难度")
difficulty_label.grid(row=10, column=0, padx=(10, 5), pady=5)

difficulty_var = tk.StringVar()
difficulty_optionmenu = tk.OptionMenu(root, difficulty_var, "暂无评定 ", "入门 ", "普及- ", "普及 提高- ",
                                      "普及+ 提高 ", "提高+ 省选- ", "省选 NOI- ", "NOI NOI+ CTSC ")
difficulty_optionmenu.grid(row=10, column=1, padx=(5, 10), pady=5)

clear_difficulty = tk.Button(root, text="清空难度", command=clear_difficulty)
clear_difficulty.grid(row=10, column=2, padx=(10, 5), pady=5)

# 创建标签标签和输入框
tag_label = tk.Label(root, text="标签")
tag_label.grid(row=11, column=0, padx=(10, 5), pady=5)

tag_entry = tk.Entry(root)
tag_entry.grid(row=11, column=1, padx=(5, 10), pady=5)

# 创建关键词标签和输入框
keyword_label = tk.Label(root, text="关键词")
keyword_label.grid(row=12, column=0, padx=(10, 5), pady=5)

keyword_entry = tk.Entry(root)
keyword_entry.grid(row=12, column=1, padx=(5, 10), pady=5)

# 创建线程数标签和输入框
thread_num_label = tk.Label(root, text="线程数")
thread_num_label.grid(row=2, column=0, padx=(10, 5), pady=5)

thread_num_entry = tk.Entry(root)
thread_num_entry.grid(row=2, column=1, padx=(5, 10), pady=5)

# 创建选择路径按钮和路径输入框
select_path_button = tk.Button(root, text="选择路径", command=select_path)
select_path_button.grid(row=3, column=0, padx=(10, 5), pady=5)

path_entry = tk.Entry(root)
path_entry.grid(row=3, column=1, padx=(5, 10), pady=5)

# 创建__client_id标签和输入框
client_id_label = tk.Label(root, text="__client_id")
client_id_label.grid(row=4, column=0, padx=(10, 5), pady=5)

client_id_display = tk.Entry(root)
client_id_display.grid(row=4, column=1, padx=(5, 10), pady=5)

# 创建_uid标签和输入框
uid_label = tk.Label(root, text="_uid")
uid_label.grid(row=5, column=0, padx=(10, 5), pady=5)

uid_display = tk.Entry(root)
uid_display.grid(row=5, column=1, padx=(5, 10), pady=5)
# 创建开始按钮
start_button = tk.Button(root, text="开始爬取", command=start_crawling)
start_button.grid(row=6, column=0, columnspan=2, padx=10, pady=5)

# 创建登录按钮
login_button = tk.Button(root, text="登录", command=handle_login)
login_button.grid(row=6, column=1, columnspan=2, padx=10, pady=5)

# 创建查询按钮
login_button = tk.Button(root, text="查询", command=start_query)
login_button.grid(row=6, column=2, columnspan=2, padx=10, pady=5)
# 创建垂直滚动条
vsb = ttk.Scrollbar(root, orient="vertical")

# 创建状态列表框
tree = ttk.Treeview(root, columns=("题目ID", "爬取状态"), show="headings", yscrollcommand=vsb.set)
tree.heading("题目ID", text="题目ID")
tree.heading("爬取状态", text="爬取状态")
tree.grid(row=8, column=0, columnspan=5, padx=10, pady=5)

# 创建查询列表框
query_tree = ttk.Treeview(root, columns=("题目ID", "题目名称"), show="headings")
query_tree.heading("题目ID", text="题目ID")
query_tree.heading("题目名称", text="题目名称")
query_tree.grid(row=8, column=5, columnspan=10, padx=10, pady=5)

# 配置滚动条
vsb.config(command=tree.yview)

if __name__ == '__main__':
    if os.path.exists('luogucookie.pickle'):
        # 从pickle文件中读取信息
        cookie_data = Utils.read_pickle_info()

        set_entry_content(uid_display, str(cookie_data['_uid']))
        set_entry_content(client_id_display, str(cookie_data['__client_id']))

        uid_display.update()
        client_id_display.update()
    # root.protocol("WM_DELETE_WINDOW", on_exit)
    root.mainloop()
