import os.path
import random
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import pickle
from WebCrawlerWorker import WebCrawlerWorker
from selenium import webdriver
import Utils

complete_message_box_show = False


def select_path():
    path = filedialog.askdirectory()
    path_entry.delete(0, tk.END)
    path_entry.insert(0, path)


def callback(exercise_id, status, status_text):
    # 查找treeview中是否已有信息
    if tree.exists(exercise_id):
        print(tree.item(exercise_id)["values"])
        tree.item(exercise_id, values=(exercise_id, status_text))
    else:
        tree.insert('', "end", exercise_id, values=(exercise_id, status_text))
        tree.yview_moveto(1.0)


def handle_login():
    def get_cookie():
        browser = webdriver.Chrome()
        browser.get("https://www.luogu.com.cn/auth/login")
        while True:
            if browser.current_url == 'https://www.luogu.com.cn/':
                luogu_cookies = browser.get_cookies()
                print(luogu_cookies)
                browser.quit()

                cookies = {}

                # 将获取到的cookie写入准备导出的cookies变量中

                for item in luogu_cookies:
                    cookies[item['name']] = item['value']

                # 获得过期时间
                cookies['expiry'] = min(luogu_cookies[1]['expiry'], luogu_cookies[2]['expiry'])

                print(luogu_cookies)

                # 使用pickle库导出
                output_path = open(r'luogucookie.pickle', 'wb')
                pickle.dump(cookies, output_path)
                output_path.close()

                uid_entry.insert(0,str(cookies['_uid']))
                client_id_entry.insert(0, str(cookies['__client_id']))

                return cookies

    p = threading.Thread(target=get_cookie)
    p.start()


def check_cookie_info_valid():
    if os.path.exists('luogucookie.pickle'):
        cookie_file = open('luogucookie.pickle', 'rb')
        cookie_info = pickle.load(file=cookie_file)
        if cookie_info['expiry'] > int(time.time()):
            return True
    return False


def start_crawling():
    def multithreaded():
        while not work_queue.empty():
            worker = WebCrawlerWorker(exercise_id=work_queue.get(), path=save_path, progress_callback=callback,
                                      cookie=actual_cookie)
            worker.start_work()
            work_queue.task_done()
            # 防止密集请求
            time.sleep(random.uniform(0.3, 1))

    def check_task_complete():
        while True:
            if work_queue.empty():
                messagebox.showinfo("任务完成", "任务完成!")
                break

    # 初始化登录信息
    if check_cookie_info_valid():
        # 初始化队列信息
        work_queue = queue.Queue()

        # 初始化工作信息
        start_id = int(exercise_id_entry.get())
        exercise_num = int(num_of_exercises_entry.get())
        thread_num = int(thread_num_entry.get())
        save_path = path_entry.get()

        # 从pickle文件中读取信息
        cookie_data = Utils.read_pickle_info()

        uid_entry.insert(0, cookie_data['_uid'])
        client_id_entry.insert(0, cookie_data['__client_id'])

        # 生成传给Worker的参数
        actual_cookie = {'_uid': str(cookie_data['_uid']), '__client_id': str(cookie_data['__client_id'])}

        # start_ID - exercise_num 不能是负值
        if start_id - exercise_num < 1:
            raise ValueError("start_ID - exercise_num < 1 !")
        for i in range(start_id - exercise_num + 1, start_id + 1):
            work_queue.put(i)

        # 从queue中拿取一个任务，分配给指定数量的线程
        for x in range(thread_num):
            if not work_queue.empty():
                t = threading.Thread(target=multithreaded)
                t.start()

        # 检测任务是否完成线程
        p = threading.Thread(target=check_task_complete)
        p.start()
    else:
        messagebox.showinfo("Cookie信息", "检测不到你的Cookie信息或已失效, 请重新登录!")
        p = threading.Thread(target=handle_login)
        p.start()


# 创建主窗口
root = tk.Tk()
root.title("Web爬虫GUI")

# 创建标签和输入框
exercise_id_label = tk.Label(root, text="起始题目ID:")
exercise_id_label.pack()
exercise_id_entry = tk.Entry(root)
exercise_id_entry.pack()

num_of_exercises_label = tk.Label(root, text="要爬取的题目数量:")
num_of_exercises_label.pack()
num_of_exercises_entry = tk.Entry(root)
num_of_exercises_entry.pack()

thread_num = tk.Label(root, text="线程数: ")
thread_num.pack()
thread_num_entry = tk.Entry(root)
thread_num_entry.pack()

# 创建选择路径按钮
select_path_button = tk.Button(root, text="选择路径", command=select_path)
select_path_button.pack()

# 创建路径输入框
path_entry = tk.Entry(root)
path_entry.pack()

# __client_id输入框
client_id = tk.Label(root, text="__client_id: ")
client_id.pack()
client_id_entry = tk.Entry(root)
client_id_entry.pack()

# '_uid'输入框
uid = tk.Label(root, text="_uid: ")
uid.pack()
uid_entry = tk.Entry(root)
uid_entry.pack()

# 创建开始按钮
start_button = tk.Button(root, text="开始爬取", command=start_crawling)
start_button.pack()

# 创建登录按钮
login_button = tk.Button(root, text="登录", command=handle_login)
login_button.pack()

# 创建垂直滚动条
vsb = ttk.Scrollbar(root, orient="vertical")

# 创建状态列表框
tree = ttk.Treeview(root, columns=("题目ID", "爬取状态"), show="headings", yscrollcommand=vsb.set)
tree.heading("题目ID", text="题目ID")
tree.heading("爬取状态", text="爬取状态")
tree.pack()

# 配置滚动条
vsb.config(command=tree.yview)

root.mainloop()
