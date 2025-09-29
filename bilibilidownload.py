import argparse
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
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from tqdm import tqdm

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
        # 设置代理，如果没有代理可以设制为None
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
    def search_video_use_api(self,page:int=1,order:str="default"):
        # 提前定义好video_of_json
        videos_of_json=None
        self.page=page
        # api的参数
        params={
            "keyword":"原神",
            "search_type":"video",# 必填参数
            "page":page, # 非必填参数
            "order":order # 排列方式
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
            if requests.status_codes==-501:
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
    def __init__(self,bv_number:str,max_retries:int=3):
        # 定义属相
        self.bv_number=bv_number
        self.aid_cid_api="https://api.bilibili.com/x/web-interface/view"
        self.download_url="https://api.bilibili.com/x/player/playurl"
        self.headers=config.HEADERS
        # 设置代理，如果代理设置为None
        self.proxies = {
            "http": "http://127.0.0.1:7890",  # HTTP 代理
            "https": "http://127.0.0.1:7890",  # HTTPS 代理
        }
        # self.proxies=None
        # 创建存放从bv那获取的信息的目录
        self.video_information_dir="information"
        os.path.exists(self.video_information_dir) or os.makedirs(self.video_information_dir)
        # 创建视频存放的目录
        self.video_dir = "downloads"
        os.path.exists(self.video_dir) or os.makedirs(self.video_dir)
        # 重试次数
        self.max_retries=max_retries
        # 设置重试机制
        self.retries=Retry(
            total=max_retries, # 设置重试次数
            backoff_factor=1, # 重试间隔
            status_forcelist=[500, 502, 503, 504], # 遇见这些状态码的时候重试
            allowed_methods=["GET"] # 允许重试的请求方式
        )
    # 将协议和适配器绑定
    def bind_session(self):
        session=requests.Session()
        session.mount(prefix="http://",adapter=HTTPAdapter(max_retries=self.retries))
        session.mount(prefix="https://",adapter=HTTPAdapter(max_retries=self.retries))
        return session
    # 通过BV号获取aid、cid
    def get_aid_cid(self):
        # 定义存放数据的字典
        data=defaultdict(None)
        # 使用session保留请求信息
        self.session=requests.Session()
        params={
            "bvid":self.bv_number,
        }
        # 向api发送请求，获取aid，cid
        try:
            logger.info(f"正在获取aid,cid💪!")
            response=self.session.get(url=self.aid_cid_api,params=params,headers=self.headers,proxies=self.proxies)
            logger.info(f"获取到与aid，cid相关的json")
        except Exception as error:
            logger.error(f"请求api失败😭！")
            raise requests.RequestException("向api发送请求失败😭！")
        # 若请求成功，处理相关的json，从而获取aid，cid
        aid_cid_json=response.json()
        state_code=aid_cid_json.get("code")
        # 判断返回的内容是否有问题
        if state_code!=0:
            logger.error(f"请求的内容是无效的❌！")
            raise ValueError(f"返回的json内容是无效的！")
        else:
            # 获取aid
            data.update({"aid":aid_cid_json.get("data").get("aid")})
            # 获取cid
            data.update({"cid":aid_cid_json.get("data").get("cid")})
            # 获取title
            data.update({"title":aid_cid_json.get("data").get("title")})
            # 获取视频详情
            data.update({"desc":aid_cid_json.get("data").get("desc")})
        file_name=os.path.join(self.video_information_dir,f"{data.get('title')}.json")
        # 将数据写入文件
        try:
            with open(file_name,"w",encoding="utf-8") as file:
                file.write(json.dumps(data,indent=2,ensure_ascii=False))
            logger.info(f"视频的相关信息已经成功写入json文件👍！")
            self.title=data.get("title")
        except OSError as error:
            # 文件名格式错误的报错
            logger.warning(f"{data.get('title')}.json,文件名格式错误❌！")
            # 使用时间戳来定义文件名
            timestamp=time.strftime("%Y%m%d%H%M%S", time.localtime())
            file_name=os.path.join(self.video_information_dir,f"{timestamp}.json")
            with open(file_name,"w",encoding="utf-8") as file:
                file.write(json.dumps(data,indent=2,ensure_ascii=False))
            logger.info(f"视频的相关信息已经成功写入json文件👍！")
            self.title=timestamp
        except Exception as error:
            logger.error(f"文件写入出现错误💔！")
            raise Exception("文件写入错误！")
        return data
    # 获取真实的下载链接
    def get_download_url(self,aid: int, cid: int, quality: int = 0):
        # 定义参数
        params={
            "avid":aid,
            "cid":cid,
            "qn":quality,
        }
        self.headers.update({"Referer": "https://www.bilibili.com"})
        logger.info(f"正在向bilibili请求视频💪！")
        response=requests.get(url=self.download_url,params=params,proxies=self.proxies,headers=self.headers)
        state_code=response.json().get("code")
        if state_code==-400:
            logger.error(f"请求失败💔！")
            raise requests.RequestException(f"请求失败😭！")
        elif state_code==-404:
            logger.error(f"没有这个视频🤔！")
            raise requests.RequestException(f"没有这个视频🤔！")
        durl=response.json().get("data").get("durl")[0].get("url")
        return durl
    # 下载视频
    def download_video(self,url: str=None, file_name: str=None, save_dir: str = "./downloads"):
        r"""
        :param url: 视频的真实URL
        :param file_name: 视频下载存放的文件名！！（文件名是要开后缀！！！！👀）
        :param save_dir: 视频存放的目录！
        :return: None
        """
        os.makedirs(save_dir, exist_ok=True)
        # 判断file_name是否为None，如果不是None直接创建文件路径
        if file_name is not None:
            file_path = os.path.join(save_dir, file_name)
        # 如果None，则
        else:
            file_name = self.title
            file_path=os.path.join(save_dir,f"{file_name}.mp4")
        # 定义计数器
        attempt=0
        # 获取session
        session=self.bind_session()
        while attempt<self.max_retries:
            try:
                with session.get(url=url,stream=True,headers=self.headers,proxies=self.proxies) as response:
                    # 验证状态码，如果状态不符合要求就会自动报错！
                    response.raise_for_status()
                    # 获取视频的大小
                    video_size=int(response.headers.get("Content-Length"))
                    with open(file_path,"wb") as file,tqdm(
                        total=video_size, # 设置总长度
                        unit="B",
                        unit_divisor=1024,
                        unit_scale=True
                    ) as bar: # 下载进度条
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                file.write(chunk)
                                bar.update(1024)
                logger.info(f"download successful👌!Please check {file_path}")
                exit(0) # 正常退出
            except requests.exceptions.RequestException as error:
                attempt+=1
                logger.warning(f"下载错误，尝试第{attempt}/{self.max_retries}次下载♻️！")
        raise Exception(f"多次下载失败，结束下载😡！")
# 设置指令
def main():
    parser=argparse.ArgumentParser(description=f"Fetch Bilibili video😍!")
    # 是否获取BV号
    parser.add_argument("--fetchBV","-fb",dest="fetch_bv",action="store_ture",help="determine whether to obtain the BV number")
    # 关键字填写
    parser.add_argument("--key","-k",dest="key",default="原神",help="search keyword",type=str)
    # 获取BV号的方式
    parser.add_argument("--method","-m",dest="method",choices=["search","api"],help="ways to obtain a BV number",type=str)
    # 页码
    parser.add_argument("--page","-p",dest="page",default=1,type=int,help="page number")
    # 修改排列方式
    parser.add_argument("--order","-o",type=str,default="default",help="sorting method",dest="order")
    # 是否需要保存
    parser.add_argument("--save","-s",dest="save",choices=[True,False],default=False,type=bool,help="Do you need to save the obtained JSON?")
    # 存放json文件的文件名
    parser.add_argument("--filename","-fn",default=None,type=str,dest="filename",help="The filename for saving the JSON file")
    # 输入BV号
    parser.add_argument("--BV","-bv",dest="bv",type=str,help="BV number")
    # 最大尝试次数
    parser.add_argument("--maxretries","-mt",type=int,default=3,dest="max_retries",help="Maximum number of attempts")
    # aid号
    parser.add_argument("--aid","-a",type=int,dest="aid",help="aid number")
    # cid号
    parser.add_argument("--cid","-c",type=int,dest="cid",help="cid number")
    # 清晰度
    parser.add_argument("--quality","-q",type=int,default=0,dest="quality",help="quality")
    # 存放视频的目录
    parser.add_argument("--savedir","-sd",type=str,default="./downloads",dest="savedir",help="Directory for storing videos")
    # 存放视频的文件名称
    parser.add_argument("--videoname","-vn",dest="videoname",type="str",default=None,help="The file name for storing videos")
if __name__=="__main__":
    bilibili_download=BilibiliDownload(bv_number="BV1jhJCzSEa7")
    data=bilibili_download.get_aid_cid()
    url=bilibili_download.get_download_url(aid=data.get("aid"),cid=data.get("cid"))
    bilibili_download.download_video(url=url,file_name="1.mp4")