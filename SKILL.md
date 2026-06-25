---
name: seedhub
description: "搜索 SeedHub (seedhub.cc) 影视资源，提取夸克网盘、百度网盘、阿里云盘、UC网盘、磁力链接等下载地址。支持查看首页最新影视。触发词：seedhub、影视资源、找片、找电影、找剧、下载链接、夸克网盘、最新电影、新片。"
metadata:
  openclaw:
    emoji: "🎬"
    requires:
      anyBins: ["python3"]
---

# SeedHub Skill

搜索 [SeedHub](https://www.seedhub.cc/) 影视资源，自动提取夸克网盘等下载链接。

## 安装

```bash
# 进入 skill 目录
cd skills/seedhub

# 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/pip install cloudscraper
```

或者直接全局安装：

```bash
pip install cloudscraper
```

## 命令

### 搜索影视

```bash
python3 skills/seedhub/seedhub.py search "关键词"
```

返回：标题、年份、类型、演员、豆瓣评分、电影 ID。

### 获取下载链接

```bash
python3 skills/seedhub/seedhub.py links <电影ID>
```

返回：夸克网盘（自动解析直链）、百度网盘、阿里云盘、UC网盘、磁力链接等。

**电影 ID** 从搜索结果中获取。

### 查看首页最新影视

```bash
python3 skills/seedhub/seedhub.py top
```

返回：首页最新 20 部影视的标题、年份/类型、豆瓣评分、剧情简介、链接类型统计、最新 3 条磁力资源（含名称、大小和真实磁力链接）。

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--limit`, `-n` | search: 最大结果数; links: 解析的夸克链接数; top: 最大数量 | search: 20, links: 10, top: 20 |

## Agent 使用流程

### 搜索场景

1. 用户说「找一下 XXX」→ 执行 `search "XXX"`
2. 从结果中找到匹配的电影 ID
3. 执行 `links <ID>` 获取下载链接
4. 将夸克网盘链接返回给用户

**示例对话：**

> 用户：帮我找一下怪奇物语第五季的夸克链接
>
> Agent：
> 1. `python3 skills/seedhub/seedhub.py search "怪奇物语"` → 找到 ID: 119254
> 2. `python3 skills/seedhub/seedhub.py links 119254` → 提取夸克链接
> 3. 返回前几个夸克链接给用户

### 浏览最新影视场景

1. 用户说「最近有什么新片」「今天更新了什么」→ 执行 `top`
2. 展示首页最新影视列表（含简介和资源信息）
3. 如用户对某部感兴趣，可进一步执行 `links <ID>` 获取完整下载链接

**示例对话：**

> 用户：最近有什么好看的新电影？
>
> Agent：
> 1. `python3 skills/seedhub/seedhub.py top` → 获取首页最新影视
> 2. 展示列表，包含标题、评分、简介、最新资源
> 3. 如用户需要下载链接，用对应 ID 执行 `links`

## 注意事项

- 搜索建议用中文片名，英文可能搜不到
- 首次请求可能需要 5-10 秒（Cloudflare JS Challenge）
- 夸克链接自动解析为 `pan.quark.cn` 直链，其他网盘显示描述
- `--limit` 控制解析的夸克链接数量，数量越多越慢
