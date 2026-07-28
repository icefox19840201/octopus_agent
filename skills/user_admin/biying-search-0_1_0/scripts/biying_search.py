import requests
from bs4 import BeautifulSoup
import urllib.parse

# 构造搜索查询
query = "屈原与端午节的由来 配图素材 公众号文章"
encoded_query = urllib.parse.quote(query)

# 使用Bing中文搜索
url = f"https://cn.bing.com/search?q={encoded_query}&ensearch=0"

# 设置请求头，模拟浏览器
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
}

try:
    # 发送请求
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # 解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # 提取搜索结果
    results = []
    # 查找所有搜索结果项
    items = soup.find_all('li', class_='b_algo')[:10]

    for item in items:
        title_tag = item.find('h2')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        desc_tag = item.find('p')
        description = desc_tag.get_text(strip=True) if desc_tag else "无描述"

        results.append({
            "title": title,
            "description": description
        })

    # 输出结果
    print(f"=== 2026年6月2日热点新闻前10条 ===")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['description']}")
        print()

except Exception as e:
    print(f"搜索出错: {e}")