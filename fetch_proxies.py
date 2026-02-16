import requests
import time
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

# ==================== 代理源 ====================
SOURCES = [
    {
        'name': 'ProxyScrape HTTP',
        'url': 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all',
        'type': 'text'
    },
    {
        'name': 'ProxyScrape SOCKS',
        'url': 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all',
        'type': 'text'
    },
    {
        'name': 'Geonode',
        'url': 'https://proxylist.geonode.com/api/proxy-list?limit=100&protocols=http&page=1&sort_by=lastChecked&sort_type=desc',
        'type': 'json'
    },
    {
        'name': 'FreeProxyList',
        'url': 'https://free-proxy-list.net/',
        'type': 'html'
    },
    {
        'name': 'SSL Proxies',
        'url': 'https://www.sslproxies.org/',
        'type': 'html'
    },
    {
        'name': 'GitHub SpeedX',
        'url': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
        'type': 'text'
    }
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36'
]

def fetch_from_source(source):
    """从单个源抓取代理"""
    try:
        print(f"[*] 抓取 {source['name']}...")
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        r = requests.get(source['url'], headers=headers, timeout=10)
        
        if r.status_code != 200:
            return []
        
        proxies = []
        
        if source['type'] == 'json':
            data = r.json()
            for item in data.get('data', []):
                ip = item.get('ip')
                port = item.get('port')
                if ip and port:
                    proxies.append((ip, int(port)))
        
        elif source['type'] == 'html':
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if ip and port.isdigit():
                            proxies.append((ip, int(port)))
        
        else:  # text
            for line in r.text.strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2 and parts[1].isdigit():
                        proxies.append((parts[0], int(parts[1])))
        
        print(f"  └─ 获取 {len(proxies)} 个")
        return proxies
    
    except Exception as e:
        print(f"  └─ 失败: {str(e)[:50]}")
        return []

def test_proxy(proxy):
    """测试单个代理"""
    ip, port = proxy
    test_urls = [
        'http://httpbin.org/ip',
        'http://api.ipify.org?format=json'
    ]
    
    for url in test_urls:
        try:
            start = time.time()
            proxies = {
                'http': f'http://{ip}:{port}',
                'https': f'http://{ip}:{port}'
            }
            r = requests.get(url, proxies=proxies, timeout=3, 
                           headers={'User-Agent': random.choice(USER_AGENTS)})
            
            if r.status_code == 200:
                latency = (time.time() - start) * 1000
                return (ip, port, int(latency))
        except:
            continue
    return None

def main():
    print("="*60)
    print(f"代理抓取开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. 抓取所有源
    all_proxies = set()
    for source in SOURCES:
        proxies = fetch_from_source(source)
        for p in proxies:
            all_proxies.add(p)
    
    print(f"\n[*] 去重后共 {len(all_proxies)} 个待测试代理")
    
    if not all_proxies:
        print("[!] 没有获取到任何代理")
        return
    
    # 2. 并发测试
    print("\n[*] 开始测试代理可用性...")
    valid_proxies = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(test_proxy, proxy): proxy for proxy in all_proxies}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                valid_proxies.append(result)
            if (i + 1) % 50 == 0:
                print(f"  已测试 {i+1}/{len(all_proxies)}，发现 {len(valid_proxies)} 个")
    
    # 3. 按延迟排序
    valid_proxies.sort(key=lambda x: x[2])
    
    print(f"\n[✓] 测试完成：可用 {len(valid_proxies)}/{len(all_proxies)} 个")
    
    # 4. 写入文件
    with open('proxies.txt', 'w') as f:
        f.write(f"# 更新时间: {datetime.now()}\n")
        f.write(f"# 可用代理: {len(valid_proxies)} 个\n")
        f.write("# 格式: IP:端口 延迟(ms)\n\n")
        
        for ip, port, latency in valid_proxies:
            f.write(f"{ip}:{port} {latency}ms\n")
    
    # 5. 显示最快的前10个
    print("\n🚀 最快的10个代理:")
    for i, (ip, port, lat) in enumerate(valid_proxies[:10]):
        print(f"  {i+1:2d}. {ip}:{port} - {lat}ms")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
