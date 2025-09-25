import requests
import config
from pyquery import PyQuery as pq
import re
from collections import defaultdict
import json
from typing import Dict
from loguru import logger
import os
import time

class BilibiliDownload:
    # 类初始化，定义相关属性
    def __init__(self,search_key:str="原神"):
        self.search_name=search_key
        self.search_url="https://search.bilibili.com/all"
        self.search_api="https://api.bilibili.com/x/web-interface/wbi/search/all/v2"
        # __refresh__=true
        # _extra=""
        # context=""
        # page=1
        # page_size=50
        # keyword=%E5%8E%9F%E7%A5%9E
        self.header=config.HEADERS
        # 设置代理
        self.proxies = {
            "http": "http://127.0.0.1:7890",  # HTTP 代理
            "https": "http://127.0.0.1:7890",  # HTTPS 代理
        }
        self.bv_dir="BV"
        # 生成存放bv文件的目录
        os.path.exists(self.bv_dir) or os.makedirs(self.bv_dir)
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
    def search_video_use_api(self,page:int=1,pagesize:int=50):
        # 提前定义好video_of_json
        video_of_json=None
        self.page=page
        # api的参数
        params={
            "__refresh__":"true",
            "_extra":"",
            "context":"",
            "page":1,
            "page_size":pagesize,
            "keyword":"原神",
        }
        response = requests.get(url=self.search_api, params=params, headers=self.header, proxies=self.proxies)
        data=response.json()
        # 获取json主要部分
        for part in data.get("data").get("result"):
            if part.get("result_type")=="activity":
                video_of_json=part.get("data")
        return video_of_json
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
if __name__=="__main__":
    bilibili_down=BilibiliDownload()
    data=bilibili_down.search_video_use_api()
    bilibili_down.write_for_json(data)