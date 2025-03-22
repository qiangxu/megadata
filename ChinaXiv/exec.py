#!/usr/bin/env python
# CREATED DATE: 2025年03月22日 星期六 17时47分29秒
# CREATED BY: qiangxu, toxuqiang@gmail.com

import requests
from bs4 import BeautifulSoup
import os
import re
import time
import random
from tqdm import tqdm
import logging
import concurrent.futures
from langdetect import detect
import PyPDF2
import io

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("chinaxiv_crawler.log"), logging.StreamHandler()]
)
logger = logging.getLogger("ChinaXiv Crawler")

class ChinaXivCrawler:
    def __init__(self, download_dir="downloads"):
        """初始化爬虫"""
        self.base_url = "https://chinaxiv.org"
        self.download_dir = download_dir
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 创建下载目录
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            
        # 学科类别映射
        self.subject_categories = self._get_subject_categories()
        
        # 统计信息
        self.stats = {
            "total_papers": 0,
            "downloaded": 0,
            "chinese_papers": 0,
            "non_chinese_papers": 0,
            "failed": 0
        }
    
    def _get_subject_categories(self):
        """获取网站上的学科分类"""
        try:
            # 访问网站首页获取学科分类
            resp = self.session.get(self.base_url)
            soup = BeautifulSoup(resp.text, "html.parser")
            categories = {}
            
            # 在首页查找学科分类链接
            subject_links = soup.select(".nav-cont .nav-cont-bor li a")
            
            if not subject_links:
                # 如果上面的选择器无法找到，尝试其他可能的选择器
                subject_links = soup.select(".nav-area a[href*='search.htm?type=filter']")
            
            # 如果仍然找不到，使用硬编码的常见学科分类
            if not subject_links:
                logger.warning("未能从网页找到学科分类，使用预定义的学科列表")
                # 硬编码常见学科分类及其ID
                return {
                    "1": "数学",
                    "2": "物理学",
                    "3": "天文学",
                    "4": "工程与技术",  
                    "5": "化学",
                    "6": "生物学",
                    "7": "信息科学",
                    "8": "地球科学",
                    "9": "材料科学",
                    "10": "医学",
                    "11": "人文社科",
                    "12": "环境科学",
                    "13": "农业科学",
                    "14": "科学基金",
                    "15": "管理学"
                }
            
            # 解析找到的分类链接
            for link in subject_links:
                subject_name = link.text.strip()
                subject_url = link.get('href')
                
                if subject_url and subject_name:
                    # 从URL中提取学科ID
                    match = re.search(r'value=(\d+)', subject_url)
                    if match:
                        subject_id = match.group(1)
                        categories[subject_id] = subject_name
            
            logger.info(f"获取到 {len(categories)} 个学科分类")
            return categories
        except Exception as e:
            logger.error(f"获取学科分类失败: {e}，使用预定义的学科列表")
            # 获取失败时，使用硬编码的常见学科分类
            return {
                "1": "数学",
                "2": "物理学",
                "3": "天文学",
                "4": "工程与技术",  
                "5": "化学",
                "6": "生物学",
                "7": "信息科学",
                "8": "地球科学",
                "9": "材料科学",
                "10": "医学",
                "11": "人文社科",
                "12": "环境科学",
                "13": "农业科学",
                "14": "科学基金",
                "15": "管理学"
            }
            
    def _is_chinese_paper(self, pdf_content=None, title=None):
        """
        检查论文是否为中文
        可以通过PDF内容或标题来判断
        """
        # 优先通过PDF内容判断
        if pdf_content:
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                first_page_text = pdf_reader.pages[0].extract_text()
                
                # 如果PDF第一页有中文字符，认为是中文论文
                if re.search(r'[\u4e00-\u9fa5]', first_page_text):
                    return True
                
                # 尝试检测语言
                try:
                    # 只取前1000个字符做检测
                    lang = detect(first_page_text[:1000])
                    return lang == 'zh-cn' or lang == 'zh-tw' or lang == 'zh'
                except:
                    pass
            except Exception as e:
                logger.warning(f"通过PDF内容判断语言失败: {e}")
        
        # 通过标题判断
        if title:
            # 如果标题包含中文字符，认为是中文论文
            if re.search(r'[\u4e00-\u9fa5]', title):
                return True
            
            # 尝试检测标题语言
            try:
                lang = detect(title)
                return lang == 'zh-cn' or lang == 'zh-tw' or lang == 'zh'
            except:
                pass
                
        # 默认情况下，返回False
        return False
    
    def get_papers_by_subject(self, subject_id, max_pages=10):
        """获取指定学科的论文列表"""
        papers = []
        
        for page in range(1, max_pages + 1):
            try:
                # 使用search.htm接口获取学科论文
                url = f"{self.base_url}/user/search.htm?type=filter&filterField=domain&value={subject_id}&pageSize=20&currentPage={page}"
                logger.info(f"正在获取 {self.subject_categories.get(subject_id, subject_id)} 学科第 {page} 页论文列表")
                
                resp = self.session.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # 查找论文列表项
                paper_items = soup.select(".article-list-item")
                
                if not paper_items:
                    logger.info(f"学科 {subject_id} 已无更多论文，停止翻页")
                    break
                
                for item in paper_items:
                    # 获取标题和链接
                    title_element = item.select_one(".article-list-title a")
                    if not title_element:
                        continue
                        
                    title = title_element.text.strip()
                    paper_url = title_element.get('href')
                    
                    if paper_url and title:
                        # 如果链接是相对路径，添加域名
                        if paper_url.startswith('/'):
                            paper_url = paper_url
                        elif not paper_url.startswith('http'):
                            paper_url = f"/{paper_url}"
                        
                        # 提取论文ID
                        match = re.search(r'/([^/]+)$', paper_url)
                        if match:
                            paper_id = match.group(1)
                        else:
                            # 如果无法提取ID，使用随机ID
                            paper_id = f"paper_{int(time.time())}_{random.randint(1000, 9999)}"
                        
                        papers.append({
                            "id": paper_id,
                            "title": title,
                            "url": paper_url,
                            "subject_id": subject_id,
                            "subject_name": self.subject_categories.get(subject_id, subject_id)
                        })
                
                # 检查是否有下一页
                next_page = soup.select_one(".next") or soup.select_one("a:contains('下一页')")
                if not next_page or "disabled" in next_page.get("class", []):
                    logger.info(f"已到达学科 {subject_id} 的最后一页，停止翻页")
                    break
                
                # 随机延迟，避免请求过于频繁
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"获取学科 {subject_id} 第 {page} 页论文列表失败: {e}")
                break
                
        logger.info(f"共获取到学科 {subject_id} 的 {len(papers)} 篇论文")
        return papers
    
    def download_paper(self, paper):
        """下载论文PDF"""
        try:
            # 处理论文URL（可能是相对路径）
            if paper['url'].startswith('http'):
                paper_url = paper['url']
            else:
                paper_url = f"{self.base_url}{paper['url']}"
            
            # 获取论文详情页
            resp = self.session.get(paper_url)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 查找PDF下载链接（尝试多种可能的选择器）
            download_link = soup.select_one("a.download") or soup.select_one("a[href*='download']") or soup.select_one("a[href*='.pdf']")
            
            if not download_link:
                # 如果找不到直接的下载链接，查找可能的文献详情页面
                detail_link = soup.select_one("a[href*='paper_detail']") or soup.select_one("a[href*='detail']")
                
                if detail_link:
                    detail_url = detail_link.get('href')
                    # 确保URL是完整的
                    if not detail_url.startswith('http'):
                        if detail_url.startswith('/'):
                            detail_url = f"{self.base_url}{detail_url}"
                        else:
                            detail_url = f"{self.base_url}/{detail_url}"
                    
                    # 访问详情页面
                    logger.info(f"未找到直接下载链接，尝试访问详情页: {detail_url}")
                    detail_resp = self.session.get(detail_url)
                    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                    
                    # 在详情页查找下载链接
                    download_link = detail_soup.select_one("a.download") or detail_soup.select_one("a[href*='download']") or detail_soup.select_one("a[href*='.pdf']")
                
                if not download_link:
                    logger.warning(f"未找到论文 {paper['id']} 的下载链接")
                    self.stats["failed"] += 1
                    return False
            
            # 获取下载链接
            pdf_url = download_link.get('href')
            
            # 确保URL是完整的
            if not pdf_url.startswith('http'):
                if pdf_url.startswith('/'):
                    pdf_url = f"{self.base_url}{pdf_url}"
                else:
                    pdf_url = f"{self.base_url}/{pdf_url}"
            
            logger.info(f"找到PDF下载链接: {pdf_url}")
            
            # 下载PDF
            pdf_resp = self.session.get(pdf_url, stream=True)
            
            if pdf_resp.status_code != 200:
                logger.warning(f"下载论文 {paper['id']} 失败, 状态码: {pdf_resp.status_code}")
                self.stats["failed"] += 1
                return False
            
            # 获取PDF内容
            pdf_content = pdf_resp.content
            
            # 检查内容类型是否为PDF
            content_type = pdf_resp.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type.lower():
                logger.warning(f"下载的内容不是PDF (Content-Type: {content_type})")
                # 尝试检查内容的前几个字节是否为PDF文件特征
                if not pdf_content.startswith(b'%PDF'):
                    logger.warning(f"下载的内容不是PDF文件格式")
                    self.stats["failed"] += 1
                    return False
            
            # 检查是否是中文论文
            is_chinese = self._is_chinese_paper(pdf_content, paper['title'])
            
            # 创建学科目录
            subject_dir = os.path.join(self.download_dir, paper['subject_id'])
            if not os.path.exists(subject_dir):
                os.makedirs(subject_dir)
            
            # 为中文和非中文论文分别创建目录
            if is_chinese:
                target_dir = os.path.join(subject_dir, "chinese")
                self.stats["chinese_papers"] += 1
            else:
                target_dir = os.path.join(subject_dir, "non_chinese")
                self.stats["non_chinese_papers"] += 1
                
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            # 构建文件名（使用论文ID和标题的前30个字符）
            pattern = r'[^\w\u4e00-\u9fa5]'  # 先定义模式
            filename = f"{paper['id']}_{re.sub(pattern, '_', paper['title'][:30])}.pdf"
            filepath = os.path.join(target_dir, filename)
            
            # 保存PDF
            with open(filepath, "wb") as f:
                f.write(pdf_content)
            
            logger.info(f"成功下载论文 {paper['id']}: {paper['title'][:30]}... ({'中文' if is_chinese else '非中文'})")
            self.stats["downloaded"] += 1
            
            # 随机延迟，避免请求过于频繁
            time.sleep(random.uniform(0.5, 2))
            
            return True
        except Exception as e:
            logger.error(f"下载论文 {paper['id']} 失败: {e}")
            self.stats["failed"] += 1
            return False
    
    def crawl_by_subject(self, subject_id, max_pages=5, max_papers=None):
        """爬取指定学科的论文"""
        if subject_id not in self.subject_categories:
            logger.warning(f"未找到学科 {subject_id}")
            return
        
        logger.info(f"开始爬取学科: {self.subject_categories[subject_id]} ({subject_id})")
        
        # 获取论文列表
        papers = self.get_papers_by_subject(subject_id, max_pages)
        
        if max_papers:
            papers = papers[:max_papers]
        
        self.stats["total_papers"] += len(papers)
        
        # 显示进度条
        with tqdm(total=len(papers), desc=f"下载 {self.subject_categories[subject_id]} 论文") as pbar:
            # 使用线程池并行下载
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_paper = {executor.submit(self.download_paper, paper): paper for paper in papers}
                
                for future in concurrent.futures.as_completed(future_to_paper):
                    paper = future_to_paper[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"处理论文 {paper['id']} 时发生错误: {e}")
                    finally:
                        pbar.update(1)
    
    def crawl_all_subjects(self, max_pages_per_subject=3, max_papers_per_subject=10):
        """爬取所有学科的论文"""
        if not self.subject_categories:
            logger.error("未获取到学科分类，无法进行爬取")
            return
        
        logger.info(f"开始爬取全部 {len(self.subject_categories)} 个学科的论文")
        
        for subject_id, subject_name in self.subject_categories.items():
            logger.info(f"===== 开始爬取学科: {subject_name} ({subject_id}) =====")
            self.crawl_by_subject(subject_id, max_pages=max_pages_per_subject, max_papers=max_papers_per_subject)
            
            # 显示当前进度
            self._show_progress()
            
            # 学科之间的间隔时间
            time.sleep(random.uniform(2, 5))
    
    def _show_progress(self):
        """显示当前爬取进度和统计信息"""
        logger.info("===== 当前进度 =====")
        logger.info(f"总论文数: {self.stats['total_papers']}")
        logger.info(f"已下载: {self.stats['downloaded']}")
        logger.info(f"中文论文: {self.stats['chinese_papers']}")
        logger.info(f"非中文论文: {self.stats['non_chinese_papers']}")
        logger.info(f"下载失败: {self.stats['failed']}")
        
        if self.stats['total_papers'] > 0:
            success_rate = (self.stats['downloaded'] / self.stats['total_papers']) * 100
            chinese_ratio = (self.stats['chinese_papers'] / self.stats['downloaded']) * 100 if self.stats['downloaded'] > 0 else 0
            logger.info(f"下载成功率: {success_rate:.2f}%")
            logger.info(f"中文论文比例: {chinese_ratio:.2f}%")
        
        logger.info("===================")

def main():
    """主函数"""
    # 创建爬虫实例
    crawler = ChinaXivCrawler(download_dir="chinaxiv_papers")
    
    # 选择爬取方式
    print("请选择爬取方式:")
    print("1. 爬取所有学科")
    print("2. 爬取指定学科")
    
    choice = input("请输入选择 (1/2): ").strip()
    
    if choice == "1":
        max_pages = int(input("请输入每个学科最大爬取页数 (推荐 3-5): ").strip() or "3")
        max_papers = int(input("请输入每个学科最大爬取论文数 (推荐 10-20): ").strip() or "10")
        
        crawler.crawl_all_subjects(max_pages_per_subject=max_pages, max_papers_per_subject=max_papers)
    elif choice == "2":
        # 显示所有学科
        print("可选学科列表:")
        for subject_id, subject_name in crawler.subject_categories.items():
            print(f"{subject_id}: {subject_name}")
        
        subject_id = input("请输入要爬取的学科ID: ").strip()
        max_pages = int(input("请输入最大爬取页数 (推荐 5-10): ").strip() or "5")
        max_papers = int(input("请输入最大爬取论文数 (0 表示不限): ").strip() or "0")
        
        if max_papers <= 0:
            max_papers = None
            
        crawler.crawl_by_subject(subject_id, max_pages=max_pages, max_papers=max_papers)
    else:
        print("无效的选择")
    
    # 显示最终统计信息
    crawler._show_progress()
    print("爬取完成!")

if __name__ == "__main__":
    main()
