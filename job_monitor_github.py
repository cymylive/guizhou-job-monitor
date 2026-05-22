#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贵州国企招聘监控 - GitHub Actions 版 (含详情页解析)
"""
import os, json, re, urllib.request, ssl
from datetime import datetime

DINGTALK_TOKEN = os.environ.get("DINGTALK_TOKEN", "")
if not DINGTALK_TOKEN:
    print("[错误] 未设置 DINGTALK_TOKEN")
    exit(1)
DINGTALK_WEBHOOK = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}"

# ===== 从 config.json 加载配置 =====
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
def load_config():
    default = {
        "排除条件": {
            "经验要求": ["2年以上", "3年以上", "5年以上", "8年以上", "10年以上"],
            "硬性要求": ["中共党员", "高级职称", "中级职称", "中级会计师",
                         "法律职业资格", "注册会计师", "一级建造师", "一级注册", "注册土木"],
            "特定专业": ["土木工程", "安全工程", "食品科学与工程"],
            "岗位排除": ["研发", "开发", "工程师", "技术员", "医师", "护理",
                         "总经理", "副总经理", "部长", "总监", "负责人", "经理岗"]
        },
        "包含条件": {
            "专业关键词": ["经济", "金融", "管理", "财务", "会计", "审计",
                           "不限专业", "专业不限", "运营", "行政", "综合",
                           "办公", "市场", "营销", "人力", "人事"],
            "特殊岗位": ["见习", "管培", "应届"]
        },
        "求职者信息": {"期望城市": ["贵阳", "安顺", "平坝", "遵义"]}
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default

CONFIG = load_config()
EXCLUDE_KW = (CONFIG["排除条件"]["经验要求"] + CONFIG["排除条件"]["硬性要求"]
              + CONFIG["排除条件"]["特定专业"] + CONFIG["排除条件"]["岗位排除"])
MAJOR_KW = CONFIG["包含条件"]["专业关键词"]
CITIES = CONFIG["求职者信息"]["期望城市"]
SCHOOL_JOBS = CONFIG["包含条件"]["特殊岗位"]

def decode(raw):
    for enc in ["utf-8", "gbk", "gb2312"]:
        try: return raw.decode(enc)
        except: continue
    return raw.decode("utf-8", errors="replace")

def fetch(url, timeout=15):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return r.read()
    except: return b""

def fetch_jobs_163():
    jobs = []
    for page in [1, 2, 3, 4]:
        raw = fetch(f"https://163gzw.cn/now.html?page={page}")
        if not raw: break
        html = decode(raw)
        for kw in ["报名中", "待报名"]:
            for part in html.split(kw)[1:]:
                m = re.search(r'/article/(\d+).html"[^>]*>(.*?)</a>', part)
                if m:
                    jid = m.group(1); th = m.group(2)
                    tp = (re.search(r'【(.+?)】', th) or [None, ""]).group(1)
                    tl = re.sub(r'【.+?】', '', th).strip()
                    jobs.append({"id": f"163_{jid}", "source": "163贵州网", "type": tp,
                        "title": tl, "url": f"https://163gzw.cn/article/{jid}.html"})
        if f"?page={page+1}" not in html: break
    return jobs

def fetch_detail(url):
    """获取详情页，提取学历/经验/专业等关键信息"""
    raw = fetch(url, timeout=10)
    if not raw: return {}
    html = decode(raw)
    info = {}
    
    # 提取信息卡片（招录人数等）
    card = re.search(r'招录人数.*?<span>(.*?)</span>', html)
    if card: info["count"] = card.group(1).strip()
    
    card = re.search(r'考试地区.*?<span>(.*?)</span>', html)
    if card: info["area"] = card.group(1).strip()
    
    # 提取正文内容（包含岗位要求）
    body = re.search(r'class="content_content"[^>]*>(.*?)</div>', html, re.DOTALL)
    if body:
        text = re.sub(r'<[^>]+>', '', body.group(1))
        text = re.sub(r'\s+', ' ', text).strip()
        info["body"] = text[:3000]
    
    # 提取学历要求
    edu_pat = r'学历[要求]*[：:]\s*([^。\n]{2,30})'
    edu = re.search(edu_pat, html)
    if edu: info["edu"] = edu.group(1).strip()
    
    # 提取专业要求
    major_pat = r'专业[要求]*[：:]\s*([^。\n]{2,60})'
    major = re.search(major_pat, html)
    if major: info["major"] = major.group(1).strip()
    
    return info

def rough_match(job):
    """粗筛：基于标题"""
    t = job.get("title", "") + " " + job.get("type", "")
    for kw in EXCLUDE_KW:
        if kw in t: return False
    loc = any(x in t for x in CITIES)
    maj = any(x in t for x in MAJOR_KW)
    sch = any(x in t for x in SCHOOL_JOBS)
    st = job.get("type") in ["国企", "事业编", "合同制"]
    return (st or sch) and (maj or loc)

def match_detail(info, job):
    """精筛：基于详情页"""
    full_text = job.get("title", "") + info.get("body", "")
    for kw in EXCLUDE_KW + ["中级及以上", "中级会计", "注册会计师"]:
        if kw in full_text: return False
    return True

def send_dingtalk(text):
    payload = json.dumps({"msgtype": "markdown", "markdown": {"title": "贵州国企招聘", "text": text}}, ensure_ascii=False).encode()
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(DINGTALK_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            return r.read().decode()
    except Exception as e: return str(e)

def main():
    date = datetime.now().strftime("%Y-%m-%d")
    print(f"[监控] 贵州国企招聘 {date}")
    
    # 1. 获取列表
    all_jobs = fetch_jobs_163()
    print(f"[163贵州网] {len(all_jobs)} 个岗位")
    
    # 2. 粗筛
    candidates = [j for j in all_jobs if rough_match(j)]
    print(f"[粗筛] {len(candidates)} 个候选")
    
    # 3. 获取详情页精筛 (只取前20个以减少时间)
    matched = []
    for i, job in enumerate(candidates):
        if i >= 20:  # 限制详情页请求数
            matched.append(job)
            continue
        print(f"  [详情] {i+1}/{len(candidates)}: {job['title'][:30]}...", end=" ")
        info = fetch_detail(job["url"])
        if not info:
            matched.append(job)
            print("跳过(无详情)")
            continue
        if match_detail(info, job):
            matched.append(job)
            print("匹配")
        else:
            print("排除")
    
    print(f"[精筛] {len(matched)} 个符合条件")
    
    # 4. 推送
    if not matched:
        send_dingtalk(f"### 贵州国企招聘监控 {date}\n\n今日暂无符合条件的岗位")
        print("[钉钉] 无匹配")
        return
    
    lines = [f"### 贵州国企招聘监控 {date}\n", f"共 {len(matched)} 个符合条件的岗位:\n"]
    for i, j in enumerate(matched, 1):
        lines.append(f"{i}. 【{j['type']}】{j['title']}")
        lines.append(f"   {j['source']} | {j['url']}\n")
    lines.append(f"---\n更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    result = send_dingtalk("\n".join(lines))
    print(f"[钉钉] {result[:100]}")
    print("[完成]")

if __name__ == "__main__":
    main()
