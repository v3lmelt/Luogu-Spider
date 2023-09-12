import json
import os
import pickle
from urllib.parse import unquote
import re

diff_mapper = r"mappers\difficulty.json"
tag_mapper = r"mappers\mapper.json"


def read_pickle_info():
    if os.path.exists('luogucookie.pickle'):
        f_stream = open('luogucookie.pickle', 'rb+')
        data = pickle.load(file=f_stream)
        f_stream.close()

        return data
    return None


def json_parser(decode_result):
    data = json.loads(decode_result)
    return data


def difficulty_parser(tag_id):
    try:
        # 打开 JSON 文件并读取内容
        # print(os.getcwd())
        with open(diff_mapper, 'r') as file:
            data = json.load(file)

        # 检查指定的 tag_id 是否存在于 JSON 数据中的 'tags' 键中
        if 'tags' in data and tag_id in data['tags']:
            return data['tags'][tag_id]
        else:
            return ""  # 如果 tag_id 不存在，返回 None 或其他适当的值
    except FileNotFoundError:
        return ""  # 如果文件不存在，返回 None 或其他适当的值


def tag_parser(tag_id):
    try:
        # 打开 JSON 文件并读取内容
        with open(tag_mapper, 'r') as file:
            data = json.load(file)

        # 检查指定的 tag_id 是否存在于 JSON 数据中的 'tags' 键中
        if 'tags' in data and tag_id in data['tags']:
            return data['tags'][tag_id]
        else:
            return ""  # 如果 tag_id 不存在，返回 None 或其他适当的值
    except FileNotFoundError:
        return ""  # 如果文件不存在，返回 None 或其他适当的值


def uri_component_decoder(soup):
    # print(soup.script)

    # 使用正则表达式匹配 decodeURIComponent() 函数中的参数值
    match = re.search(r'decodeURIComponent\("([^"]+)"\)', str(soup.script))

    if match:
        parameter_value = match.group(1)
        # 解码URL编码字符串
        decoded_string = unquote(parameter_value)
        return decoded_string

    else:
        print("未找到匹配的参数值!")


def clean_folder_name(folder_name):
    # 匹配Windows不允许的字符
    disallowed_chars = r'[<>:"/\\|?*]'

    # 使用re.sub()函数将不允许的字符替换为空字符串
    clean_string = re.sub(disallowed_chars, '', folder_name)

    return clean_string


def sort_json_data(path):
    def load_json_file(file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_json_file(file_path, data):
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    # 读取现有 JSON 数据
    json_file_path = path
    json_data = load_json_file(json_file_path)

    # 检查是否成功加载 JSON 数据
    if json_data:
        # 按 exercise_id 大小排序 JSON 数据
        sorted_json_data = sorted(json_data, key=lambda x: x['exercise_id'])

        # 将排序后的数据重新写入 JSON 文件
        save_json_file(json_file_path, sorted_json_data)

        print("JSON 数据已按 exercise_id 大小排序并保存到文件。")
    else:
        print("无法加载 JSON 数据或文件为空。")
