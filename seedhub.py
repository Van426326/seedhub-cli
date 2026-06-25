#!/usr/bin/env python3
"""
SeedHub CLI - 影视资源搜索 & 下载链接提取

搜索 SeedHub (seedhub.cc) 影视资源，自动提取夸克网盘等下载链接。
"""

import sys
import os
import re
import time
import base64
import threading
import argparse
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import cloudscraper
except ImportError:
    print("❌ 缺少依赖: cloudscraper")
    print("   安装: pip install cloudscraper")
    sys.exit(1)

SEEDHUB_BASE = "https://www.seedhub.cc"


_rate_lock = threading.Lock()
_last_req_time = 0.0
_MIN_INTERVAL = 0.5


def _rate_wait():
    """全局速率控制：确保两次请求间隔不小于 _MIN_INTERVAL"""
    global _last_req_time
    with _rate_lock:
        elapsed = time.time() - _last_req_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_req_time = time.time()


def create_scraper():
    return cloudscraper.create_scraper()


def search(keyword: str, limit: int = 20) -> list[dict]:
    """搜索影视资源，返回结果列表"""
    scraper = create_scraper()
    url = f"{SEEDHUB_BASE}/s/{urllib.parse.quote(keyword)}/"

    try:
        r = scraper.get(url, timeout=30)
        if r.status_code != 200:
            print(f"❌ HTTP 错误: {r.status_code}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        return []

    html = r.text

    # Parse movie cards
    movies = re.findall(
        r'title="([^"]+)"[^>]*class="image"[^>]*href="(/movies/\d+)/?"', html
    )
    infos = re.findall(
        r"<li>(\d{4}\s*/\s*(?:电影|剧集|动漫)[^<]*)</li>", html
    )
    ratings = re.findall(
        r'豆瓣评分:\s*<a[^>]*>([^<]+)</a>', html
    )

    results = []
    for i, (title, path) in enumerate(movies[:limit]):
        m = re.search(r"/movies/(\d+)/?", path)
        movie_id = m.group(1) if m else "unknown"
        results.append({
            "title": title,
            "info": infos[i].strip() if i < len(infos) else "",
            "rating": ratings[i] if i < len(ratings) else "?",
            "id": movie_id,
            "url": f"{SEEDHUB_BASE}/movies/{movie_id}/",
        })

    return results


def get_top_movies(limit: int = 20, scraper=None) -> list[dict]:
    """获取首页最新影视列表"""
    if scraper is None:
        scraper = create_scraper()

    try:
        r = scraper.get(SEEDHUB_BASE, timeout=30)
        if r.status_code != 200:
            print(f"❌ HTTP 错误: {r.status_code}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        return []

    html = r.text

    # 复用 search 的正则解析首页电影卡片
    movies = re.findall(
        r'title="([^"]+)"[^>]*class="image"[^>]*href="(/movies/\d+)/?"', html
    )
    infos = re.findall(
        r"<li>(\d{4}\s*/\s*(?:电影|剧集|动漫)[^<]*)</li>", html
    )
    ratings = re.findall(
        r'豆瓣评分:\s*<a[^>]*>([^<]+)</a>', html
    )

    results = []
    for i, (title, path) in enumerate(movies[:limit]):
        m = re.search(r"/movies/(\d+)/?", path)
        movie_id = m.group(1) if m else "unknown"
        # 反转义 HTML 实体
        title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        results.append({
            "title": title,
            "info": infos[i].strip() if i < len(infos) else "",
            "rating": ratings[i] if i < len(ratings) else "?",
            "id": movie_id,
            "url": f"{SEEDHUB_BASE}/movies/{movie_id}/",
        })

    return results


def _resolve_magnet(scraper, link_url: str) -> str:
    """从种子链接页面解析真实磁力链接（base64 编码在 JS 中）"""
    for attempt in range(2):
        try:
            _rate_wait()
            r = scraper.get(link_url, timeout=10)
            if r.status_code != 200:
                continue
            # 匹配 const data = "base64字符串"
            b64_match = re.search(r'const\s+data\s*=\s*"([A-Za-z0-9+/=]+)"', r.text)
            if b64_match:
                decoded = base64.b64decode(b64_match.group(1)).decode("utf-8", errors="ignore")
                if decoded.startswith("magnet:"):
                    return decoded
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
    return ""


def get_movie_detail(movie_id: str, seed_limit: int = 3, scraper=None) -> dict:
    """获取电影详情：简介 + 最新资源"""
    url = f"{SEEDHUB_BASE}/movies/{movie_id}/"
    if scraper is None:
        scraper = create_scraper()

    r = None
    for attempt in range(3):
        try:
            _rate_wait()
            r = scraper.get(url, timeout=30)
            if r.status_code == 200 and len(r.text) > 1000:
                break
            # 状态码异常或内容太短，刷新 scraper 重试
            time.sleep(1)
            scraper = create_scraper()
        except Exception:
            time.sleep(1)
            scraper = create_scraper()
    if r is None or r.status_code != 200:
        return {"summary": "", "seeds": [], "tabs": {}}

    html = r.text

    # 提取简介：id="description" 所在 <h2> 之后的 <p> 标签
    summary = ""
    desc_match = re.search(
        r'id="description"[^>]*>.*?</h2>\s*<p[^>]*>(.*?)</p>',
        html, re.DOTALL,
    )
    if desc_match:
        summary = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()

    # 提取各类型链接数量
    tabs = {}
    for name, count in re.findall(r'(磁力|百度|夸克|迅雷|UC|阿里)\((\d+)\)', html):
        tabs[name] = int(count)

    # 提取种子资源列表（磁力链详情）
    seeds = []
    seed_section = html.find('class="seeds"')
    if seed_section >= 0:
        section = html[seed_section:seed_section + 20000]
        items = re.findall(
            r'<li>\s*<a[^>]*title="([^"]+)"[^>]*href="([^"]+)"[^>]*>.*?</a>.*?'
            r'<code[^>]*>([^<]+)</code>',
            section, re.DOTALL,
        )
        for title, href, size in items[:seed_limit]:
            title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            link = f"{SEEDHUB_BASE}{href}" if href.startswith("/") else href
            # 解析真实磁力链接
            magnet = _resolve_magnet(scraper, link)
            seeds.append({
                "title": title,
                "link": link,
                "size": size.strip(),
                "magnet": magnet,
            })

    return {"summary": summary, "seeds": seeds, "tabs": tabs}


def get_links(movie_id: str, quark_limit: int = 10) -> dict:
    """获取电影的下载链接"""
    movie_id = movie_id.strip("/").split("/")[-1]
    url = f"{SEEDHUB_BASE}/movies/{movie_id}/"

    scraper = create_scraper()

    try:
        r = scraper.get(url, timeout=30)
        if r.status_code != 200:
            print(f"❌ HTTP 错误: {r.status_code}", file=sys.stderr)
            return {}
    except Exception as e:
        print(f"❌ 请求失败: {e}", file=sys.stderr)
        return {}

    html = r.text

    # Extract title
    title_match = re.search(r"<h1[^>]*>.*?#</a>\s*([^<]+)", html)
    title = title_match.group(1).strip() if title_match else "未知标题"

    # Extract all link_start URLs
    all_hrefs = re.findall(
        r'href="(/link_start/\?redirect_to=pan_id_\d+&movie_title=[^"]+)"', html
    )

    # Deduplicate
    seen = set()
    unique_links = []
    for link in all_hrefs:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    # Classify links by type
    classified = {
        "title": title,
        "quark": [],
        "baidu": [],
        "aliyun": [],
        "uc": [],
        "xunlei": [],
        "magnet": re.findall(r'(magnet:\?xt=[^\s<"]+)', html),
        "thunder": re.findall(r'(thunder://[^\s<"]+)', html),
        "ed2k": re.findall(r'(ed2k://[^\s<"]+)', html),
    }

    for link in unique_links:
        esc_link = re.escape(link)
        pattern = rf'(.{{0,300}}href="{esc_link}".{{0,100}})'
        match = re.search(pattern, html)
        if not match:
            continue

        context = match.group(1)
        dl_match = re.search(r'data-link="([^"]+)"', context)
        link_type = dl_match.group(1) if dl_match else "unknown"
        title_match = re.search(r'title="([^"]+)"', context)
        desc = title_match.group(1) if title_match else ""

        if "quark" in link_type.lower():
            classified["quark"].append({"path": link, "desc": desc})
        elif "baidu" in link_type.lower():
            classified["baidu"].append({"path": link, "desc": desc})
        elif "alipan" in link_type.lower() or "aliyun" in link_type.lower():
            classified["aliyun"].append({"path": link, "desc": desc})
        elif "uc" in link_type.lower():
            classified["uc"].append({"path": link, "desc": desc})
        elif "xunlei" in link_type.lower():
            classified["xunlei"].append({"path": link, "desc": desc})

    # Resolve quark links (follow redirects to get actual URLs)
    resolved_quark = []
    for item in classified["quark"][:quark_limit]:
        try:
            redirect_url = f"{SEEDHUB_BASE}{item['path']}"
            r2 = scraper.get(redirect_url, allow_redirects=True, timeout=10)
            actual_links = re.findall(r'(https?://pan\.quark\.cn[^\s<"]+)', r2.text)
            if actual_links:
                item["url"] = actual_links[0]
                resolved_quark.append(item)
        except Exception:
            pass

    classified["quark_resolved"] = resolved_quark
    return classified


def clean_desc(desc: str, max_len: int = 60) -> str:
    """清理资源描述"""
    desc = re.sub(r"今天|昨天|提取码[^\s]*", "", desc).strip()
    desc = desc.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return desc[:max_len] if len(desc) > max_len else desc


def cmd_search(args):
    """搜索命令"""
    keyword = args.keyword
    print(f"🔍 搜索: {keyword}")

    results = search(keyword, limit=args.limit)

    if not results:
        print("❌ 未找到相关结果")
        return

    print(f"\n找到 {len(results)} 个结果:\n")

    for i, item in enumerate(results, 1):
        print(f"{i}. {item['title']}")
        print(f"   📅 {item['info'] or 'N/A'} | ⭐ 豆瓣 {item['rating']}")
        print(f"   📌 ID: {item['id']}")
        print()


def cmd_links(args):
    """获取下载链接"""
    movie_id = args.movie_id
    print(f"🎬 获取下载链接...")

    data = get_links(movie_id, quark_limit=args.limit)

    if not data:
        print("❌ 获取失败")
        return

    print(f"📽️ {data['title']}")
    print("━" * 50)

    found = False

    if data.get("quark_resolved"):
        found = True
        total = len(data["quark"])
        resolved = data["quark_resolved"]
        print(f"\n🔗 夸克网盘 ({total}个, 已解析{len(resolved)}个):")
        for item in resolved:
            print(f"   • {clean_desc(item['desc'])}")
            print(f"     {item['url']}")

    if data.get("baidu"):
        found = True
        print(f"\n📦 百度网盘 ({len(data['baidu'])}个):")
        for item in data["baidu"][:5]:
            print(f"   • {clean_desc(item['desc'], 50)}")

    if data.get("aliyun"):
        found = True
        print(f"\n📦 阿里云盘 ({len(data['aliyun'])}个):")
        for item in data["aliyun"][:5]:
            print(f"   • {clean_desc(item['desc'], 50)}")

    if data.get("uc"):
        found = True
        print(f"\n📦 UC网盘 ({len(data['uc'])}个):")
        for item in data["uc"][:3]:
            print(f"   • {clean_desc(item['desc'], 50)}")

    if data.get("magnet"):
        found = True
        print(f"\n🧲 磁力链接 ({len(data['magnet'])}个):")
        for link in data["magnet"][:5]:
            print(f"   {link[:80]}...")

    if data.get("thunder"):
        found = True
        print(f"\n⚡ 迅雷链接 ({len(data['thunder'])}个):")
        for link in data["thunder"][:5]:
            print(f"   {link[:80]}...")

    if not found:
        print("❌ 未找到下载链接")
    else:
        print(f"\n💡 夸克链接已自动解析为可直接访问的 URL")


def cmd_top(args):
    """首页最新影视"""
    print("🏠 SeedHub 首页最新影视\n")

    movies = get_top_movies(limit=args.limit)

    if not movies:
        print("❌ 获取失败，请稍后重试")
        return

    threads = args.threads

    # 并发获取详情（全局速率控制在 _rate_wait 中）
    details = {}
    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_map = {
            executor.submit(get_movie_detail, movie["id"], 3): idx
            for idx, movie in enumerate(movies)
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                details[idx] = future.result()
            except Exception:
                details[idx] = {"summary": "", "seeds": [], "tabs": {}}

    # 按顺序输出
    for i, movie in enumerate(movies):
        detail = details.get(i, {"summary": "", "seeds": [], "tabs": {}})
        print(f"{i + 1}. {movie['title']}")
        print(f"   📅 {movie['info'] or 'N/A'} | ⭐ 豆瓣 {movie['rating']}")

        if detail["summary"]:
            summary = detail["summary"]
            if len(summary) > 80:
                summary = summary[:80] + "..."
            print(f"   📝 {summary}")

        if detail["tabs"]:
            parts = [f"{name}({cnt})" for name, cnt in detail["tabs"].items() if cnt > 0]
            if parts:
                print(f"   🔗 {' / '.join(parts)}")

        if detail["seeds"]:
            print(f"   🧲 最新资源:")
            for seed in detail["seeds"]:
                title = seed["title"]
                if len(title) > 60:
                    title = title[:60] + "..."
                print(f"      • {title} / {seed['size']}")
                if seed.get("magnet"):
                    print(f"        {seed['magnet']}")

        print(f"   📌 ID: {movie['id']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="SeedHub CLI - 影视资源搜索 & 下载链接提取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s search 怪奇物语
  %(prog)s search "至尊马蒂" --limit 5
  %(prog)s links 119254
  %(prog)s links 129054 --limit 20
  %(prog)s top
  %(prog)s top --limit 10
  %(prog)s top --limit 10 --threads 3
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # search
    sp_search = subparsers.add_parser("search", aliases=["s"], help="搜索影视资源")
    sp_search.add_argument("keyword", help="搜索关键词")
    sp_search.add_argument("--limit", "-n", type=int, default=20, help="最大结果数 (默认: 20)")
    sp_search.set_defaults(func=cmd_search)

    # links
    sp_links = subparsers.add_parser("links", aliases=["l"], help="获取下载链接")
    sp_links.add_argument("movie_id", help="电影 ID (从搜索结果获取)")
    sp_links.add_argument("--limit", "-n", type=int, default=10, help="解析的夸克链接数 (默认: 10)")
    sp_links.set_defaults(func=cmd_links)

    # top
    sp_top = subparsers.add_parser("top", aliases=["t"], help="查看首页最新影视")
    sp_top.add_argument("--limit", "-n", type=int, default=20, help="最大数量 (默认: 20)")
    sp_top.add_argument("--threads", "-j", type=int, default=5, help="并发线程数 (默认: 5)")
    sp_top.set_defaults(func=cmd_top)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
