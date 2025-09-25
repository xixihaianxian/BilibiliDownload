import requests
import config
from pyquery import PyQuery as pq
import re
from collections import defaultdict
import json
from typing import Dict,Any,List
from loguru import logger
import os
import time

# 获取BV号的类
class FetchBV:
    # 类初始化，定义相关属性
    def __init__(self,search_key:str="原神"):
        self.search_name=search_key
        self.search_url="https://search.bilibili.com/all"
        self.search_api="https://api.bilibili.com/x/web-interface/search/type"
        # keyword=原神
        # search_type=video
        # page
        # order
        self.header=config.HEADERS
        # 设置代理
        self.proxies = {
            "http": "http://127.0.0.1:7890",  # HTTP 代理
            "https": "http://127.0.0.1:7890",  # HTTPS 代理
        }
        # 存储通过目录的名称
        self.bv_dir="BV"
        # 存储
        self.api_dir="API"
        # 生成存放bv文件的目录
        os.path.exists(self.bv_dir) or os.makedirs(self.bv_dir)
        # 生成存放api返回json文件的目录
        os.path.exists(self.api_dir) or os.makedirs(self.api_dir)
    # 列表判断是否为空
    def is_empty(self,target:list):
        if len(target)==0:
            return True
        else:
            return False
    # 构造正则表达式
    def construct_regular_expression(self,content:str):
        # bv号的正则表达式
        pattern_bv = re.compile(r'/(BV\w+)/')
        # title的正则表达式
        pattern_title=re.compile(r'title="(.*?)"')
        # bv号匹配
        bv_code=re.findall(pattern=pattern_bv,string=content)
        # title号匹配
        title=re.findall(pattern=pattern_title,string=content)
        # 如果为空则设置为None
        if self.is_empty(bv_code):
            return None
        else:
            bv_code=bv_code[0]
        return bv_code,title
    # 获取vt
    def update_url_with_vt(self,url:str) -> str:
        # 获取当前时间戳后 8 位
        now = str(int(time.time() * 1000))[-8:]
        # 找 ? 的位置
        qs_idx = url.find("?")
        if qs_idx == -1:  # 没有参数
            url = f"{url}?vt={now}"
        elif re.search(r"vt=\d{8}", url):  # 已有 vt 参数，替换
            url = re.sub(r"vt=\d{8}", f"vt={now}", url)
        else:  # 没有 vt 参数，加上
            suffix = url[qs_idx + 1:]
            url = url[:qs_idx + 1] + f"vt={now}"
            if suffix:
                url = url + "&" + suffix
        return url
    # 使用api来搜索
    def search_video_use_api(self,page:int=1):
        # 提前定义好video_of_json
        videos_of_json=None
        self.page=page
        # api的参数
        params={
            "keyword":"原神",
            "search_type":"video",# 必填参数
            "page":page, # 非必填参数
            "order":"default" # 排列方式
        }
        try:
            # 尝试向api发送请求
            logger.info(f"尝试向哔哩哔哩api发送请求😘！")
            response = requests.get(url=self.search_api, params=params, headers=self.header, proxies=self.proxies)
            # 发送请求成功
            logger.info(f"请求api成功😘！")
        except Exception as error:
            # 发送请求失败
            logger.error(f"请求api失败😓！")
            # 501代表系统失败
            if requests.status_codes==501:
                raise requests.RequestException(f"系统错误😫！")
            # 其它错误
            else:
                raise requests.RequestException(f"请求失败😫！")
        data=response.json()
        # 获取json目标部分
        videos_of_json=data.get("data").get("result")
        return videos_of_json
    # 搜索，根据关键字搜索相关的内容
    def search_video_for_key(self,page:int=1,pagesize:int=30):
        self.page=page
        # 定义存放bv号的字典
        bv_dict=defaultdict(None)
        # 查询参数
        params={
            "keyword":self.search_name,
            "page":page,
            # 防止o等于负数
            "o":(page-1)*pagesize if (page-1)*pagesize>=0 else 0,
            "single_column":0,
        }
        logger.info(f"正在获取第{page}页的数据😄！")
        # url加入vt
        url=self.update_url_with_vt(url=self.search_url)
        # 发送请求
        try:
            response=requests.get(url=url,params=params,headers=self.header,proxies=self.proxies)
            logger.info(f"第{page}页的数据获取成功😄！")
        except Exception as error:
            logger.error(f"第{page}页的数据获取失败💔！")
            raise requests.RequestException(f"请求失败😭！")
        # 解析请求的结果
        document=pq(response.text.encode("utf-8"))
        # 获取视频列表
        video_list=document("div.video.i_wrapper.search-all-list div.video-list.row div.bili-video-card")
        for video_card in video_list.items():
            result=self.construct_regular_expression(video_card.html()) # 一定需要将pyquery对象转化为str
            if result is not None:
                # 将标题和bv号一一对应
                bv_dict.update({result[1][0]:result[0]})
        logger.info(f"获取BV号成功📺！")
        return bv_dict
    # 将字典保存在json文件里面
    def write_for_json(self,data:Dict[str,str],json_path:str=None):
        if json_path is None:
            json_path=os.path.join(self.bv_dir,f"{self.page}.json")
        with open(json_path,"w",encoding="utf-8") as file:
            file.write(json.dumps(data,indent=2,ensure_ascii=False))
    # api获取的json，处理和写入方式
    def write_for_json_api(self,data:List[Dict[str,Any]],json_path:str=None):
        # 定义存放数据的列表
        video_datas=list()
        # 判断json_path是否为空
        if json_path is None:
            json_path=os.path.join(self.api_dir,f"{self.page}.json")
        # 处理api获取的json数据
        logger.info(f"正在处理获取的json数据🥳！")
        for video_json in data:
            video_datas.append({
                "type":video_json.get("type"), # 文件类型
                "author":video_json.get("author"), # 作者
                "typename":video_json.get("typename"), # 类型
                "url":video_json.get("arcurl"), # url
                "bvid":video_json.get("bvid"), # 视频BV号
                "title":video_json.get("title"), # 视频标题
                "description":video_json.get("description"), # 视频简介，详细内容
                "tag":video_json.get("tag"), # 作品标签
                "duration":video_json.get("duration"), # 视频持续时间
            })
        # 将修改之后的json写入
        try:
            logger.info(f"正在向文件写入数据😘！")
            with open(json_path,"w",encoding="utf-8") as file:
                file.write(json.dumps(video_datas,ensure_ascii=False,indent=2))
            logger.info(f"写入成功💕！")
        except Exception as error:
            logger.error(f"写入失败😅！")
            raise Exception("写入文件失败！")
# 下载哔哩哔哩视频
class BilibiliDownload:
    def __init__(self,bv_number:str):
        # 定义属相
        self.bv_number=bv_number
    # 通过BV号获取aid、cid
    def get_aid_cid(self,bvid):
        pass
if __name__=="__main__":
    bilibili_down=FetchBV()
    data=bilibili_down.search_video_use_api()
    bilibili_down.write_for_json_api(data)