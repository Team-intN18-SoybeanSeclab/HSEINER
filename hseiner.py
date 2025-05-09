import requests
import argparse
import sys
import re
from requests.packages import urllib3
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from colorama import init, Fore, Style, Back
import concurrent.futures
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm
import json
from datetime import datetime

init(autoreset=True)
def print_banner():
    banner = f"""
{Fore.CYAN}╔════════════════════════════════════════════════════════════════════════════╗
{Fore.CYAN}║ {Fore.MAGENTA}██╗  ██╗███████╗{Fore.YELLOW}███████╗██╗███╗   ██╗███████╗██████╗ {Fore.CYAN}║
{Fore.CYAN}║ {Fore.MAGENTA}██║  ██║██╔════╝{Fore.YELLOW}██╔════╝██║████╗  ██║██╔════╝██╔══██╗{Fore.CYAN}║
{Fore.CYAN}║ {Fore.MAGENTA}███████║███████╗{Fore.YELLOW}█████╗  ██║██╔██╗ ██║█████╗  ██████╔╝{Fore.CYAN}║
{Fore.CYAN}║ {Fore.MAGENTA}██╔══██║╚════██║{Fore.YELLOW}██╔══╝  ██║██║╚██╗██║██╔══╝  ██╔══██╗{Fore.CYAN}║
{Fore.CYAN}║ {Fore.MAGENTA}██║  ██║███████║{Fore.YELLOW}███████╗██║██║ ╚████║███████╗██║  ██║{Fore.CYAN}║
{Fore.CYAN}║ {Fore.MAGENTA}╚═╝  ╚═╝╚══════╝{Fore.YELLOW}╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝{Fore.CYAN}║
{Fore.CYAN}║ {Fore.GREEN}                    HSEINER - 增强版 v2.0                    {Fore.CYAN}║
{Fore.CYAN}║ {Fore.YELLOW}                    作者: hama                            {Fore.CYAN}║
{Fore.CYAN}╚════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

def print_info(message):
    print(f"{Fore.CYAN}[*] {message}{Style.RESET_ALL}")

def print_success(message):
    print(f"{Fore.GREEN}[+] {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}[-] {message}{Style.RESET_ALL}")

def print_cool(message):
    print(f"{Fore.MAGENTA}[✪] {message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")

def print_debug(message):
    print(f"{Fore.BLUE}[D] {message}{Style.RESET_ALL}")

def print_progress(current, total, prefix='', suffix=''):
    bar_length = 50
    filled_length = int(round(bar_length * current / float(total)))
    percents = round(100.0 * current / float(total), 1)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percents}% {suffix}')
    sys.stdout.flush()

def parse_args():
    parser = argparse.ArgumentParser(
        description='Hseiner - 一个强大的JavaScript文件分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python %(prog)s -u http://www.example.com
  python %(prog)s -u http://www.example.com -d -t 10
  python %(prog)s -f urls.txt -j
        '''
    )
    
    parser.add_argument("-u", "--url", help="目标网站URL", required=True)
    parser.add_argument("-c", "--cookie", help="目标网站的Cookie")
    parser.add_argument("-f", "--file", help="包含URL或JS文件的文件路径")
    
    parser.add_argument("-ou", "--outputurl", help="URL输出文件名")
    parser.add_argument("-os", "--outputsubdomain", help="子域名输出文件名")
    parser.add_argument("-oj", "--outputjson", help="JSON格式输出文件名")
    
    parser.add_argument("-j", "--js", help="在JS文件中查找", action="store_true")
    parser.add_argument("-d", "--deep", help="深度查找", action="store_true")
    parser.add_argument("-t", "--threads", type=int, default=5, help="线程数，默认为5")
    parser.add_argument("-p", "--proxy", help="代理地址，格式：http://proxy.example.com:8080")
    parser.add_argument("-to", "--timeout", type=float, default=3, help="请求超时时间，默认为3秒")
    parser.add_argument("-r", "--retries", type=int, default=3, help="请求重试次数，默认为3次")
    parser.add_argument("-s", "--screenshot", help="截图保存文件夹路径")
    
    parser.add_argument("--no-color", help="禁用彩色输出", action="store_true")
    parser.add_argument("--verbose", help="显示详细信息", action="store_true")
    parser.add_argument("--save-response", help="保存响应内容", action="store_true")
    parser.add_argument("--filter-status", help="过滤HTTP状态码，例如：200,301,302", default="")
    parser.add_argument("--exclude", help="排除的URL模式，支持正则表达式", default="")
    parser.add_argument("--include", help="包含的URL模式，支持正则表达式", default="")
    
    return parser.parse_args()

def request_with_retry(url, headers, timeout, proxy, retries):
    for attempt in range(retries):
        try:
            if proxy:
                proxies = {
                    'http': proxy,
                    'https': proxy
                }
                response = requests.get(url, headers=headers, timeout=timeout, verify=False, proxies=proxies,
                                        allow_redirects=True)
            else:
                response = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
            return response
        except requests.RequestException as e:
            if attempt < retries - 1:
                print_info(f"请求 {url} 失败，正在重试 {attempt + 1}/{retries}... 错误信息: {e}")
            else:
                print_error(f"请求 {url} 失败，已达到最大重试次数。错误信息: {e}")
    return None

def extract_URL(JS):
    pattern_raw = r"""
      (?:"|')                               
      (
        ((?:[a-zA-Z]{1,10}://|//)           
        [^"'/]{1,}\.                        
        [a-zA-Z]{2,}[^"']{0,})              
        |
        ((?:/|\.\./|\./)                    
        [^"'><,;| *()(%%$^/\\\[\]]          
        [^"'><,;|()]{1,})                   
        |
        ([a-zA-Z0-9_\-/]{1,}/               
        [a-zA-Z0-9_\-/]{1,}                 
        \.(?:[a-zA-Z]{1,4}|action)          
        (?:[\?|/][^"|']{0,}|))              
        |
        ([a-zA-Z0-9_\-]{1,}                 
        \.(?:php|asp|aspx|jsp|json|
             action|html|js|txt|xml)             
        (?:\?[^"|']{0,}|))                  
      )
      (?:"|')                               
    """
    pattern = re.compile(pattern_raw, re.VERBOSE)
    result = re.finditer(pattern, str(JS))
    if result is None:
        return None
    js_url = []
    return [match.group().strip('"').strip("'") for match in result if match.group() not in js_url]

def Extract_html(URL):
    global args
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.108 Safari/537.36",
        "Cookie": args.cookie
    }
    response = request_with_retry(URL, header, args.timeout, args.proxy, args.retries)
    if response:
        return response.content.decode("utf-8", "ignore")
    return None

def process_url(URL, re_URL):
    black_url = ["javascript:"]
    URL_raw = urlparse(URL)
    ab_URL = URL_raw.netloc
    host_URL = URL_raw.scheme
    if re_URL[:2] == "//":
        result = host_URL + ":" + re_URL
    elif re_URL[:4] == "http":
        result = re_URL
    elif re_URL[:2] != "//" and re_URL not in black_url:
        if re_URL[0] == "/":
            result = host_URL + "://" + ab_URL + re_URL
        else:
            if re_URL[0] == ".":
                if re_URL[:2] == "..":
                    result = host_URL + "://" + ab_URL + re_URL[2:]
                else:
                    result = host_URL + "://" + ab_URL + re_URL[1:]
            else:
                result = host_URL + "://" + ab_URL + "/" + re_URL
    else:
        result = URL
    return result

def find_last(string, substr):
    positions = []
    last_position = -1
    while True:
        position = string.find(substr, last_position + 1)
        if position == -1:
            break
        last_position = position
        positions.append(position)
    return positions

def find_by_url(url, js=True):
    if not js:
        try:
            print_info(f"正在处理 URL: {url}")
        except Exception as e:
            print_error("请指定一个有效的 URL，例如 https://www.baidu.com")
    html_raw = Extract_html(url)
    if html_raw is None:
        print_error(f"访问 {url} 失败")
        return None
    html = BeautifulSoup(html_raw, "html.parser")
    html_scripts = html.find_all("script")
    script_array = {}
    script_temp = ""
    for html_script in html_scripts:
        script_src = html_script.get("src")
        if script_src is None:
            script_temp += html_script.get_text() + "\n"
        else:
            purl = process_url(url, script_src)
            script_array[purl] = Extract_html(purl)
    script_array[url] = script_temp
    allurls = []
    for script in script_array:
        temp_urls = extract_URL(script_array[script])
        if not temp_urls:
            continue
        for temp_url in temp_urls:
            allurls.append(process_url(script, temp_url))
    result = []
    for singerurl in allurls:
        url_raw = urlparse(url)
        domain = url_raw.netloc
        positions = find_last(domain, ".")
        miandomain = domain
        if len(positions) > 1:
            miandomain = domain[positions[-2] + 1:]
        suburl = urlparse(singerurl)
        subdomain = suburl.netloc
        if miandomain in subdomain or not subdomain.strip():
            if singerurl.strip() not in result:
                result.append(singerurl)
    return result

def find_by_url_deep(url):
    html_raw = Extract_html(url)
    if html_raw is None:
        print_error(f"访问 {url} 失败")
        return None
    html = BeautifulSoup(html_raw, "html.parser")
    html_as = html.find_all("a")
    links = []
    for html_a in html_as:
        src = html_a.get("href")
        if not src and src is not None:
            continue
        link = process_url(url, src)
        if link not in links:
            links.append(link)
    if not links:
        return None
    print_success(f"共找到 {len(links)} 个链接")
    urls = []

    def process_link(link):
        temp_urls = find_by_url(link)
        if temp_urls is not None:
            print_info(f"在 {link} 中找到 {len(temp_urls)} 个 URL")
            return temp_urls
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        results = executor.map(process_link, links)
        for temp_urls in results:
            for temp_url in temp_urls:
                if temp_url not in urls:
                    urls.append(temp_url)

    return urls

def find_by_file(file_path, js=True):
    try:
        with open(file_path, "r") as fobject:
            links = fobject.read().split("\n")
    except FileNotFoundError:
        print_error(f"未找到文件: {file_path}")
        return None
    if not links:
        return None
    print_success(f"共找到 {len(links)} 个链接")
    urls = []

    def process_file_link(link):
        if not js:
            temp_urls = find_by_url(link)
        else:
            temp_urls = find_by_url(link, js=True)
        if temp_urls is not None:
            print_info(f"在 {link} 中找到 {len(temp_urls)} 个 URL")
            return temp_urls
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        results = executor.map(process_file_link, links)
        for temp_urls in results:
            for temp_url in temp_urls:
                if temp_url not in urls:
                    urls.append(temp_url)

    return urls

def find_subdomain(urls, mainurl):
    url_raw = urlparse(mainurl)
    domain = url_raw.netloc
    positions = find_last(domain, ".")
    miandomain = domain
    if len(positions) > 1:
        miandomain = domain[positions[-2] + 1:]
    subdomains = []
    for url in urls:
        suburl = urlparse(url)
        subdomain = suburl.netloc
        if not subdomain.strip():
            continue
        if miandomain in subdomain:
            if subdomain not in subdomains:
                subdomains.append(subdomain)
    return subdomains

SENSITIVE_PATTERNS = {
    "身份证号": re.compile(r'[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}(?:\d|X|x)'),
    "手机号": re.compile(r'1[3-9]\d{9}'),
    "邮箱": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "API密钥": re.compile(r'(?i)(api[_-]?key|access[_-]?key|secret[_-]?key)[_-]?(key)?["\']?\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}'),
    "AWS密钥": re.compile(r'AKIA[0-9A-Z]{16}'),
    "Google API密钥": re.compile(r'AIza[0-9A-Za-z\\-_]{35}'),
    "GitHub Token": re.compile(r'ghp_[0-9a-zA-Z]{36}'),
    "密码": re.compile(r'(?i)(password|passwd|pwd)[_-]?(key)?["\']?\s*[:=]\s*["\']?[^"\'\s]{8,}'),
    "数据库连接": re.compile(r'(?i)(mongodb|mysql|postgresql)://[^"\'\s]+'),
    "JWT Token": re.compile(r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'),
    "私钥": re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'),
    "云存储URL": re.compile(r'(?i)(s3|oss|cos)://[^"\'\s]+'),
    "IP地址": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
}

def detect_sensitive_info(content, url):
    findings = []
    seen_values = set()  
    
    for info_type, pattern in SENSITIVE_PATTERNS.items():
        matches = pattern.finditer(content)
        for match in matches:
            value = match.group()
            
            if value not in seen_values:
                seen_values.add(value)
                findings.append({
                    "type": info_type,
                    "value": value, 
                    "url": url,
                    "position": match.span()
                })
    
    return findings

def print_sensitive_findings(findings):
    if not findings:
        return
    
    print_cool("\n发现敏感信息:")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    findings_by_type = {}
    for finding in findings:
        if finding['type'] not in findings_by_type:
            findings_by_type[finding['type']] = []
        findings_by_type[finding['type']].append(finding)
    
    for info_type, type_findings in findings_by_type.items():
        print(f"{Fore.YELLOW}类型: {info_type}")
        print(f"发现数量: {len(type_findings)}")
        for finding in type_findings:
            print(f"{Fore.GREEN}URL: {finding['url']}")
            print(f"{Fore.RED}Data: {finding['value']}") 
        print(f"{Fore.CYAN}{'-'*80}{Style.RESET_ALL}")

def save_findings_to_file(findings, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for finding in findings:
                f.write(f"类型: {finding['type']}\n")
                f.write(f"URL: {finding['url']}\n")
                f.write(f"Data: {finding['value']}\n") 
                f.write(f"位置: {finding['position']}\n")
                f.write("-" * 80 + "\n")
        print_success(f"敏感信息已保存到: {filename}")
    except Exception as e:
        print_error(f"保存敏感信息时出错: {e}")

def is_api_url(url):
    api_keywords = [
        'api', 'v1', 'v2', 'v3', 'rest', 'graphql', 'service', 'gateway',
        'auth', 'oauth', 'token', 'login', 'register', 'user', 'admin',
        'data', 'query', 'search', 'upload', 'download', 'export', 'import'
    ]

    api_extensions = ['.json', '.xml', '.api', '.rpc', '.soap', '.wsdl']

    non_api_extensions = ['.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot']
    
    url_lower = url.lower()

    if any(url_lower.endswith(ext) for ext in non_api_extensions):
        return False

    if any(keyword in url_lower for keyword in api_keywords):
        return True

    if any(url_lower.endswith(ext) for ext in api_extensions):
        return True

    path_depth = url_lower.count('/')
    if path_depth >= 2:
        return True
    
    return False

def test_endpoints(urls):
    global args
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    if args.screenshot and not os.path.exists(args.screenshot):
        os.makedirs(args.screenshot)

    sensitive_file_dir = 'sensitive_files'
    if not os.path.exists(sensitive_file_dir):
        os.makedirs(sensitive_file_dir)

    sensitive_apis_file = 'sensitive_apis.txt'
    all_apis_file = 'all_apis.txt'

    results = []
    all_findings = []
    seen_values = set() 
    print_cool("开始批量测活接口...")

    api_urls = [url for url in urls if is_api_url(url)]
    print_info(f"发现 {len(api_urls)} 个可能的API端点")
    print_info(f"使用 {args.threads} 个线程进行扫描")

    def process_url(url):
        try:
            header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.108 Safari/537.36",
                "Cookie": args.cookie
            }
            response = request_with_retry(url, header, args.timeout, args.proxy, args.retries)
            
            if response:
                content = response.content.decode("utf-8", "ignore")
                
                findings = detect_sensitive_info(content, url)
                if findings:
                    new_findings = []
                    for finding in findings:
                        if finding['value'] not in seen_values:
                            seen_values.add(finding['value'])
                            new_findings.append(finding)
                            all_findings.append(finding)
                    
                    if new_findings:
                        print_sensitive_findings(new_findings)
                        
                        if args.save_response:
                            file_name = f"sensitive_{url.replace('://', '_').replace('/', '_')}.txt"
                            file_path = os.path.join(sensitive_file_dir, file_name)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                
                with open(all_apis_file, 'a', encoding='utf-8') as f:
                    f.write(f"{url}\n")
                
                if findings:
                    with open(sensitive_apis_file, 'a', encoding='utf-8') as f:
                        f.write(f"{url}\n")
                
                if args.screenshot:
                    driver.get(url)
                    screenshot_path = os.path.join(args.screenshot, f"{url.replace('://', '_').replace('/', '_')}.png")
                    driver.save_screenshot(screenshot_path)
                
                return {
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(content),
                    "findings": findings
                }
            
        except Exception as e:
            print_error(f"处理 {url} 时出错: {e}")
        return None

    with tqdm(total=len(api_urls), desc="扫描进度", unit="url") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
            future_to_url = {executor.submit(process_url, url): url for url in api_urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print_error(f"处理 {url} 时发生异常: {e}")
                pbar.update(1)
    
    driver.quit()
    
    if all_findings:
        save_findings_to_file(all_findings, os.path.join(results_dir, "sensitive_findings.txt"))
    
    return results

def giveresult(urls, domain):
    if urls is None:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"jsfinder_results_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    
    results = {
        "scan_time": timestamp,
        "target_domain": domain,
        "total_urls": len(urls),
        "urls": [],
        "subdomains": [],
        "sensitive_info": [],
        "endpoints": []
    }
    
    print_success(f"\n找到 {len(urls)} 个 URL:")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    content_url = ""
    for url in urls:
        content_url += url + "\n"
        print_info(url)
        results["urls"].append(url)
    
    subdomains = find_subdomain(urls, domain)
    print_success(f"\n找到 {len(subdomains)} 个子域名:")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    content_subdomain = ""
    for subdomain in subdomains:
        content_subdomain += subdomain + "\n"
        print_info(subdomain)
        results["subdomains"].append(subdomain)
    
    if args.outputurl:
        try:
            output_path = os.path.join(results_dir, args.outputurl)
            with open(output_path, "w", encoding='utf-8') as f:
                f.write(content_url)
            print_success(f"\nURL已保存到: {output_path}")
        except Exception as e:
            print_error(f"保存URL文件时出错: {e}")
    
    if args.outputsubdomain:
        try:
            output_path = os.path.join(results_dir, args.outputsubdomain)
            with open(output_path, "w", encoding='utf-8') as f:
                f.write(content_subdomain)
            print_success(f"\n子域名已保存到: {output_path}")
        except Exception as e:
            print_error(f"保存子域名文件时出错: {e}")
    
    print_cool("\n开始测试端点...")
    endpoint_results = test_endpoints(urls)
    results["endpoints"] = endpoint_results
    
    if args.outputjson:
        try:
            output_path = os.path.join(results_dir, args.outputjson)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print_success(f"\n完整结果已保存到: {output_path}")
        except Exception as e:
            print_error(f"保存JSON文件时出错: {e}")
    
    print_cool("\n扫描统计:")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}总URL数: {len(urls)}")
    print(f"子域名数: {len(subdomains)}")
    print(f"端点测试数: {len(endpoint_results)}")
    print(f"发现敏感信息数: {sum(len(r.get('findings', [])) for r in endpoint_results)}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    
    return results

def filter_urls(urls, include_pattern=None, exclude_pattern=None):
    if include_pattern:
        include_regex = re.compile(include_pattern)
        urls = [url for url in urls if include_regex.search(url)]
    
    if exclude_pattern:
        exclude_regex = re.compile(exclude_pattern)
        urls = [url for url in urls if not exclude_regex.search(url)]
    
    return urls

if __name__ == "__main__":
    print_banner()
    
    args = parse_args()
    
    urllib3.disable_warnings()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"jsfinder_results_{timestamp}"
    os.makedirs(results_dir, exist_ok=True)
    
    results = {
        "scan_time": timestamp,
        "target_url": args.url,
        "urls": [],
        "subdomains": [],
        "sensitive_info": [],
        "endpoints": []
    }
    
    try:
        if args.file is None:
            if not args.deep:
                print_info("开始普通扫描模式...")
                urls = find_by_url(args.url)
            else:
                print_info("开始深度扫描模式...")
                urls = find_by_url_deep(args.url)
        else:
            if not args.js:
                print_info("开始从文件读取URL...")
                urls = find_by_file(args.file)
            else:
                print_info("开始从文件读取JS文件...")
                urls = find_by_file(args.file, js=True)
        
        if args.include or args.exclude:
            urls = filter_urls(urls, args.include, args.exclude)
        
        if urls:
            giveresult(urls, args.url)
            
            print_success("扫描完成!")
        else:
            print_error("未找到任何URL")
            
    except KeyboardInterrupt:
        print_warning("\n用户中断扫描")
    except Exception as e:
        print_error(f"扫描过程中出错: {e}")
    finally:
        print_info(f"结果已保存到目录: {results_dir}")