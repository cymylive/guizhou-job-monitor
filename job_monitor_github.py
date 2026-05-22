#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贵州国企招聘监控 - GitHub Actions 版
每日自动推送符合条件的岗位到钉钉
========================================
需在GitHub仓库设置 Secrets → DINGTALK_TOKEN
"""

import os, json, re
import urllib.request
import ssl
from datetime import datetime

DINGTALK_TOKEN = os.environ.get("DINGTALK_TOKEN", "")
if not DINGTALK_TOKEN:
    print("[错误] 未设置 DINGTALK_TOKEN，请在GitHub Secrets中配置")
    exit(1)

DINGTALK_WEBHOOK = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}"

MATCH_RULES = {
    "排除_keywords": ["2年以上", "3年以上", "5年以上", "8年以上", "10年以上",
                       "中共党员", "高级职称", "中级职称", "中级会计师",
                       "法律职业资格", "一级建造师", "一级注册", "注册土木",
                       "土木工程", "安全工程", "食品科学与工程",
                       "研发", "开发", "工程师", "技术员", "医师", "护理",
                       "总经理", "副总经理", "部长", "总监", "负责人", "经理岗"],
    "专业_keywords": ["经济", "金融", "管理", "财务", "会计", "审计", "不限专业", "专业不限",
                       "运营", "行政", "综合", "办公", "市场", "营销", "人力", "人事"],
    "地点_优先": ["贵阳", "安顺", "平坝", "遵义"],
}

def decode_html(raw):
    for enc in ["utf-8", "gbk", "gb2312"]:
        try: return raw.decode(enc)
        except: continue
    return raw.decode("utf-8", errors="replace")

def fetch(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            return r.read()
    except:
        return b""

def fetch_163():
    jobs = []
    for page in [1, 2, 3, 4]:
        raw = fetch(f"https://163gzw.cn/now.html?page={page}")
        if not raw: break
        html = decode_html(raw)
        for kw in ["报名中", "待报名"]:
            for part in html.split(kw)[1:]:
                m = re.search(r'/article/(\d+).html"[^>]*>(.*?)</a>', part)
                if m:
                    jid = m.group(1)
                    th = m.group(2)
                    tp = (re.search(r'【(.+?)】', th) or [None, ""]).group(1)
                    tl = re.sub(r'【.+?】', '', th).strip()
                    jobs.append({"id": f"163_{jid}", "source": "163贵州网",
                        "type": tp, "title": tl,
                        "url": f"https://163gzw.cn/article/{jid}.html"})
        if f"?page={page+1}" not in html: break
    raw = fetch("https://163gzw.cn/await.html")
    if raw:
        html = decode_html(raw)
        for part in html.split("待报名")[1:]:
            m = re.search(r'/article/(\d+).html"[^>]*>(.*?)</a>', part)
            if m:
                jid, th = m.group(1), m.group(2)
                tp = (re.search(r'【(.+?)】', th) or [None, ""]).group(1)
                tl = re.sub(r'【.+?】', '', th).strip()
                jobs.append({"id": f"163_{jid}", "source": "163贵州网",
                    "type": tp, "title": tl,
                    "url": f"https://163gzw.cn/article/{jid}.html"})
    return jobs

def fetch_renbohui():
    jobs = []
    raw = fetch("https://rc.guizhou.gov.cn/home/frontzp/list.html?natureStr=%E5%9B%BD%E6%9C%89%E4%BC%81%E4%B8%9A&edu=%E6%9C%AC%E7%A7%91")
    if not raw: return jobs
    html = decode_html(raw)
    for m in re.finditer(r'<a[^>]*href="(/home/frontzp/zpinfo\.html\?zpId=(\d+))"[^>]*title="([^"]+)"', html):
        jobs.append({"id": f"rbh_{m.group(2)}", "source": "贵州人才博览会",
            "type": "国企", "title": m.group(3),
            "url": f"https://rc.guizhou.gov.cn{m.group(1)}"})
    return jobs

def match(job):
    t = job.get("title", "") + " " + job.get("type", "")
    for kw in MATCH_RULES["排除_keywords"]:
        if kw in t: return False
    loc = any(x in t for x in MATCH_RULES["地点_优先"])
    maj = any(x in t for x in MATCH_RULES["专业_keywords"])
    sch = "见习" in t or "管培" in t or "应届" in t
    st = job.get("type") in ["国企", "事业编", "合同制"]
    return (st or sch) and (maj or loc)

def send_dingtalk(text):
    payload = json.dumps({"msgtype": "markdown", "markdown": {"title": "贵州国企招聘", "text": text}}, ensure_ascii=False).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(DINGTALK_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.read().decode()
    except Exception as e:
        return str(e)

def main():
    date = datetime.now().strftime("%Y-%m-%d")
    print(f"[监控] 贵州国企招聘 {date}")
    all_jobs = []

    jobs = fetch_163(); all_jobs.extend(jobs); print(f"[163贵州网] {len(jobs)}")
    jobs = fetch_renbohui(); all_jobs.extend(jobs); print(f"[人才博览会] {len(jobs)}")

    print(f"[总计] {len(all_jobs)}")
    matched = [j for j in all_jobs if match(j)]
    print(f"[匹配] {len(matched)} 个")

    if not matched:
        msg = f"### 贵州国企招聘监控 {date}\n\n今日暂无符合条件的岗位\n\n---\n监控: 163贵州网 / 贵州人才博览会"
        send_dingtalk(msg)
        print("[钉钉] 无匹配")
        return

    lines = [f"### 贵州国企招聘监控 {date}\n", f"共 {len(matched)} 个符合条件的岗位:\n"]
    for i, j in enumerate(matched, 1):
        lines.append(f"{i}. 【{j['type']}】{j['title']}")
        lines.append(f"   {j['source']} | {j['url']}\n")
    lines.append("---\n监控: 163贵州网 / 贵州人才博览会")
    lines.append(f"更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    result = send_dingtalk("\n".join(lines))
    print(f"[钉钉] {result[:100]}")
    print("[完成]")

if __name__ == "__main__":
    main()
