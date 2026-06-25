# SeedHub CLI 🎬

搜索 [SeedHub](https://www.seedhub.cc/) 影视资源，自动提取夸克网盘等下载链接。

> SeedHub 是一个中文影视资源聚合站，收录来自各大网盘和磁力链接的电影、电视剧、动漫资源。

## 功能

- 🔍 按关键词搜索电影、电视剧、动漫
- 🏠 浏览首页最新影视（含简介、磁力链接、资源详情）
- 🔗 自动提取详情页下载链接
- 🚀 夸克网盘链接自动解析为可直接访问的 URL
- 🧲 磁力链接自动解析（base64 解码，直接可用）
- 📦 同时支持：百度网盘、阿里云盘、UC网盘、迅雷、磁力链接、ED2K
- ⚡ 多线程并发抓取，内置速率控制
- 🛡️ 自动绕过 Cloudflare 防护
- 🔄 请求失败自动重试

## 安装

```bash
git clone https://github.com/CaliCastle/seedhub-cli.git
cd seedhub-cli
pip install -r requirements.txt
```

### 依赖

- Python 3.8+
- [cloudscraper](https://github.com/VeNoMouS/cloudscraper)（处理 Cloudflare JS Challenge）

## 使用方法

### 搜索影视

```bash
python seedhub.py search "怪奇物语"
```

输出：

```
🔍 搜索: 怪奇物语

找到 5 个结果:

1. 怪奇物语 第五季 Stranger Things Season 5
   📅 2025 / 剧集 / 美国 / 英语 / 薇诺娜·瑞德 大卫·哈伯 | ⭐ 豆瓣 9.6
   📌 ID: 119254

2. 怪奇物语 第一季 Stranger Things Season 1
   📅 2016 / 剧集 / 美国 / 英语 / 薇诺娜·瑞德 大卫·哈伯 | ⭐ 豆瓣 8.9
   📌 ID: 1754
...
```

### 查看首页最新影视

```bash
python seedhub.py top
```

输出：

```
🏠 SeedHub 首页最新影视

1. 镖人：风起大漠
   📅 2026 / 电影 / 中国大陆 / 汉语普通话 / 吴京 谢霆锋 | ⭐ 豆瓣 7.5
   📝 大漠之上，镖人、官府、西域五大家族等多方势力盘根错节、暗潮涌动...
   🔗 磁力(36)
   🧲 最新资源:
      • 镖人：风起大漠[国粤语配音/中文字幕].2026.1080p.WEB-DL.H264.AAC-QuickIO / 1.38GB
        magnet:?xt=urn:btih:d09fe45f08307eb35aac6640d2c9265bdafb5a4e
      • 镖人：风起大漠[国粤语配音/中文字幕].2026.2160p.WEB-DL.H265.DTS-QuickIO / 3.92GB
        magnet:?xt=urn:btih:dc556f451078f5d2c4cab48d510b42f123b84e2d
   📌 ID: 128634
...
```

### 获取下载链接

使用搜索结果中的 **ID**：

```bash
python seedhub.py links 119254
```

输出：

```
📽️ 怪奇物语 第五季 Stranger Things Season 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 夸克网盘 (135个, 已解析10个):
   • 【怪奇物语 全收集】【4K 1080P】
     https://pan.quark.cn/s/f830c8bb0787
   • 【全季4K优化版】已更新完结【内嵌简中】【附1-4季】
     https://pan.quark.cn/s/433dc491200f
   ...

📦 百度网盘 (90个):
   • ...

📦 UC网盘 (9个):
   • ...

💡 夸克链接已自动解析为可直接访问的 URL
```

### 参数

```bash
# 限制搜索结果数量
python seedhub.py search "至尊马蒂" --limit 5

# 解析更多夸克链接（默认 10 个，数量越多越慢）
python seedhub.py links 129054 --limit 20

# 查看最新 10 部影视
python seedhub.py top --limit 10

# 使用 3 个并发线程（默认 5）
python seedhub.py top --threads 3

# 组合使用
python seedhub.py top --limit 10 --threads 3
```

| 参数 | 命令 | 说明 | 默认值 |
|------|------|------|--------|
| `--limit`, `-n` | search / links / top | 最大结果数 / 解析夸克链接数 / 最大数量 | 20 / 10 / 20 |
| `--threads`, `-j` | top | 并发线程数 | 5 |

## 支持的链接类型

| 类型 | 自动解析 | 说明 |
|------|:---:|------|
| 夸克网盘 | ✅ | 直接输出 `pan.quark.cn` 链接 |
| 百度网盘 | ❌ | 显示资源描述 |
| 阿里云盘 | ❌ | 显示资源描述 |
| UC网盘 | ❌ | 显示资源描述 |
| 磁力链接 | ✅ | 从种子页面自动解析 base64 编码的真实磁力链接 |
| 迅雷链接 | — | 直接输出 thunder:// URI |
| ED2K | — | 直接输出 ed2k:// URI |

> 夸克链接会自动跟进 SeedHub 的跳转页，解析出实际的 `pan.quark.cn` 地址。磁力链接从 `/link_start/` 页面的 JS 中提取 base64 数据并解码。其他网盘类型显示资源描述，可访问 SeedHub 页面手动获取。

## 作为 Python 库使用

```python
from seedhub import search, get_links, get_top_movies, get_movie_detail

# 搜索
results = search("怪奇物语")
for r in results:
    print(f"{r['title']} (ID: {r['id']}) ⭐ {r['rating']}")

# 获取链接
links = get_links("119254")
for item in links.get("quark_resolved", []):
    print(f"🔗 {item['url']}")

# 获取首页最新影视
movies = get_top_movies(limit=10)
for m in movies:
    print(f"{m['title']} ⭐ {m['rating']}")

# 获取电影详情（简介 + 磁力资源）
detail = get_movie_detail("128634", seed_limit=3)
print(detail["summary"])       # 剧情简介
print(detail["tabs"])          # {'磁力': 36, '百度': 0, ...}
for seed in detail["seeds"]:
    print(f"🧲 {seed['title']} / {seed['size']}")
    if seed.get("magnet"):
        print(f"   {seed['magnet']}")  # 真实磁力链接
```

## 工作原理

1. 使用 [cloudscraper](https://github.com/VeNoMouS/cloudscraper) 绕过 Cloudflare JS Challenge
2. **搜索**：解析 `seedhub.cc/s/{关键词}/` 页面的影片卡片
3. **首页浏览**：解析 `seedhub.cc` 首页影片卡片，通过 `ThreadPoolExecutor` 并发获取详情
4. **磁力解析**：访问 `/link_start/?seed_id=XXX` 页面，从 JS 的 `const data = "..."` 中提取 base64 编码的真实磁力链接并解码
5. **链接提取**：访问 `seedhub.cc/movies/{id}/`，通过 `data-link` 属性分类提取各网盘链接
6. **夸克解析**：跟进 `/link_start/?redirect_to=pan_id_XXX` 跳转，从目标页提取实际夸克链接
7. **速率控制**：全局 `threading.Lock` 保证任意两次 HTTP 请求间隔 ≥ 0.5s，避免触发服务器限流
8. **自动重试**：请求失败时自动创建新的 scraper 实例重试（最多 3 次）

## 注意事项

- **搜索建议**：使用中文片名效果最好，纯英文可能搜不到
- **Cloudflare**：首次请求可能需要 5-10 秒完成 JS Challenge
- **并发控制**：`top` 命令默认 5 线程并发，内置速率控制避免触发限流
- **请求频率**：请合理使用，不要频繁大量请求
- **夸克解析**：每个夸克链接需要一次额外的 HTTP 请求，`--limit` 控制解析数量

## 免责声明

本工具仅供个人学习和研究使用。不托管、不分发、不提供任何版权内容，仅聚合 SeedHub 上公开可访问的链接。请遵守所在地区的法律法规。

## 给 AI Agent 使用

如果你想让 AI Agent（如 OpenClaw、Claude Code 等）使用这个工具，请参考 [SKILL.md](./SKILL.md)，里面包含了 Agent 所需的安装方式、命令格式和使用流程。

## 开源协议

MIT
