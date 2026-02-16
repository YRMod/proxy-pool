import requests
import time
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# ==================== 代理源配置 ====================
PROXY_SOURCES = [
    {
        'name': '站大爷API',
        'url': 'http://open.zdaye.com/FreeProxy/Get/?count=50&protocol_type=1&return_type=3',
        'type': 'json',
        'parser': lambda data: [(item['ip'], item['port']) for item in data.get('data', {}).get('proxy_list', [])]
    },
    {
        'name': 'ProxyScrape HTTP',
        'url': 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all',
        'type': 'text',
        'parser': lambda text: [line.strip().split(':') for line in text.strip().split('\n') if ':' in line]
    },
    {
        'name': 'ProxyScrape SOCKS',
        'url': 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all',
        'type': 'text',
        'parser': lambda text: [line.strip().split(':') for line in text.strip().split('\n') if ':' in line]
    },
    {
        'name': 'Geonode',
        'url': 'https://proxylist.geonode.com/api/proxy-list?limit=100&protocols=http%2Chttps&page=1&sort_by=lastChecked&sort_type=desc',
        'type': 'json',
        'parser': lambda data: [(item['ip'], item['port']) for item in data.get('data', []) if 'http' in item.get('protocols', [])]
    },
    {
        'name': 'FreeProxyList',
        'url': 'https://free-proxy-list.net/',
        'type': 'html',
        'parser': lambda html: re.findall(r'<tr><td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>', html)
    },
    {
        'name': 'SSL Proxies',
        'url': 'https://www.sslproxies.org/',
        'type': 'html',
        'parser': lambda html: re.findall(r'<tr><td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td>', html)
    },
    {
        'name': 'GitHub SpeedX',
        'url': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
        'type': 'text',
        'parser': lambda text: [line.strip().split(':') for line in text.strip().split('\n') if ':' in line]
    },
    {
        'name': 'ProxyList Download',
        'url': 'https://www.proxy-list.download/api/v1/get?type=http',
        'type': 'text',
        'parser': lambda text: [line.strip().split(':') for line in text.strip().split('\n') if ':' in line]
    }
]

# 测试目标（多选一，随机）
TEST_URLS = [
    'http://httpbin.org/ip',
    'http://ip-api.com/json',
    'http://api.ipify.org?format=json'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36'
]

def fetch_from_source(source):
    """从单个源抓取代理"""
    try:
        print(f"[*] 正在从 {source['name']} 抓取...")
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        r = requests.get(source['url'], headers=headers, timeout=10)
        
        if r.status_code != 200:
            print(f"  └─ 失败: HTTP {r.status_code}")
            return []
        
        if source['type'] == 'json':
            data = r.json()
            proxies = source['parser'](data)
        elif source['type'] == 'html':
            proxies = source['parser'](r.text)
        else:  # text
            proxies = source['parser'](r.text)
        
        # 转换为统一格式 [(ip, port)]
        result = []
        for p in proxies:
            if len(p) == 2:
                ip, port = p
                if ip and port and port.isdigit():
                    result.append((ip.strip(), int(port)))
        
        print(f"  └─ 成功: 获取 {len(result)} 个")
        return result
    except Exception as e:
        print(f"  └─ 异常: {str(e)[:50]}")
        return []

def test_proxy(proxy):
    """测试单个代理是否可用"""
    ip, port = proxy
    test_url = random.choice(TEST_URLS)
    
    try:
        start = time.time()
        proxies = {
            'http': f'http://{ip}:{port}',
            'https': f'http://{ip}:{port}'
        }
        r = requests.get(test_url, proxies=proxies, timeout=5, headers={'User-Agent': random.choice(USER_AGENTS)})
        latency = (time.time() - start) * 1000
        
        if r.status_code == 200:
            return (ip, port, int(latency))
    except:
        pass
    return None

def main():
    print("="*60)
    print(f"代理抓取开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. 从所有源抓取
    all_proxies = set()
    for source in PROXY_SOURCES:
        proxies = fetch_from_source(source)
        for p in proxies:
            all_proxies.add(p)
    
    print(f"\n[*] 去重后共 {len(all_proxies)} 个待测试代理")
    
    if not all_proxies:
        print("[!] 没有获取到任何代理")
        return
    
    # 2. 并发测试可用性
    print("\n[*] 开始测试代理可用性...")
    valid_proxies = []
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(test_proxy, proxy): proxy for proxy in all_proxies}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                valid_proxies.append(result)
            if (i + 1) % 50 == 0:
                print(f"  已测试 {i+1}/{len(all_proxies)}，发现 {len(valid_proxies)} 个可用")
    
    # 3. 按延迟排序
    valid_proxies.sort(key=lambda x: x[2])
    
    print(f"\n[✓] 测试完成：可用 {len(valid_proxies)}/{len(all_proxies)} 个")
    
    # 4. 写入文件
    with open('proxies.txt', 'w') as f:
        f.write(f"# 更新时间: {datetime.now()}\n")
        f.write(f"# 来源: 站大爷, ProxyScrape, Geonode, FreeProxyList, SSL Proxies, GitHub SpeedX\n")
        f.write(f"# 总数: {len(valid_proxies)} 个\n")
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
