import requests
import time
from datetime import datetime

def fetch_from_geonode():
    """从Geonode获取HTTP代理"""
    try:
        url = "https://proxylist.geonode.com/api/proxy-list?limit=100&protocols=http&page=1&sort_by=lastChecked&sort_type=desc"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            proxies = []
            for item in data.get('data', []):
                ip = item.get('ip')
                port = item.get('port')
                protocols = item.get('protocols', [])
                if ip and port and 'http' in protocols:
                    latency = item.get('latency', 999)
                    proxies.append(f"{ip}:{port} {latency:.0f}ms")
            return proxies
    except:
        return []
    return []

def fetch_from_proxyscrape():
    """备用源"""
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lines = r.text.strip().split('\n')
            proxies = []
            for line in lines[:100]:
                if ':' in line:
                    proxies.append(line.strip() + " unknown")
            return proxies
    except:
        return []
    return []

def test_proxy(proxy_str):
    """测试代理是否可用"""
    try:
        ip, port = proxy_str.split()[0].split(':')
        proxies = {'http': f'http://{ip}:{port}', 'https': f'http://{ip}:{port}'}
        start = time.time()
        r = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=3)
        if r.status_code == 200:
            latency = (time.time() - start) * 1000
            return latency
    except:
        pass
    return None

def main():
    print(f"[{datetime.now()}] 开始获取代理...")
    
    # 获取代理
    all_proxies = fetch_from_geonode()
    if len(all_proxies) < 20:
        all_proxies += fetch_from_proxyscrape()
    
    print(f"获取到 {len(all_proxies)} 个代理，开始测试...")
    
    # 测试可用性
    good_proxies = []
    for i, proxy in enumerate(all_proxies[:50]):  # 只测前50个
        if i % 10 == 0:
            print(f"已测试 {i}/50...")
        latency = test_proxy(proxy.split()[0])
        if latency and latency < 5000:
            good_proxies.append(f"{proxy.split()[0]} {latency:.0f}ms")
    
    # 按延迟排序
    good_proxies.sort(key=lambda x: float(x.split()[1].replace('ms', '')))
    
    # 写入文件
    with open('proxies.txt', 'w') as f:
        f.write(f"# 更新时间: {datetime.now()}\n")
        f.write(f"# 可用代理数量: {len(good_proxies)}\n")
        f.write("# 格式: IP:端口 延迟(ms)\n\n")
        for proxy in good_proxies:
            f.write(proxy + '\n')
    
    print(f"完成！找到 {len(good_proxies)} 个可用代理")

if __name__ == "__main__":
    main()