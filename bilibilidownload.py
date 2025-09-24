import requests
import config
from pyquery import PyQuery as pq
import re
from collections import defaultdict
import json

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
    # 搜索，根据关键字搜索相关的内容
    def search_video_for_key(self,page:int=1,pagesize:int=30):
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
        # 设置代理
        proxies = {
            "http": "http://127.0.0.1:7890",  # HTTP 代理
            "https": "http://127.0.0.1:7890",  # HTTPS 代理
        }
        # 发送请求
        response=requests.get(url=self.search_url,params=params,headers=self.header,proxies=proxies)
        # 解析请求的结果
        document=pq(response.text.encode("utf-8"))
        # 获取视频列表
        video_list=document("div.video.i_wrapper.search-all-list div.video-list.row div.bili-video-card")
        for video_card in video_list.items():
            result=self.construct_regular_expression(video_card.html()) # 一定需要将pyquery对象转化为str
            if result is not None:
                # 将标题和bv号一一对应
                bv_dict.update({result[1][0]:result[0]})
        return bv_dict
    # 将字典保存在json文件里面

if __name__=="__main__":
    bilibili_down=BilibiliDownload()
    print(bilibili_down.search_video_for_key())