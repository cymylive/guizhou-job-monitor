# 贵州国企招聘监控

自动监控贵州国企/事业单位招聘信息，每小时推送匹配岗位到钉钉。

## 功能

- 自动抓取 **163贵州网** 正在报名和待报名的招聘信息
- 自动抓取 **贵州人才博览会** 国企本科岗位
- 粗筛：基于标题快速匹配（地点/专业/类型）
- 精筛：获取详情页提取学历、经验、职称要求
- 每小时通过 **钉钉机器人** 推送最新匹配岗位

## 快速开始

### 1. 配置钉钉机器人

在钉钉群添加机器人，获取 Webhook 地址。

### 2. 设置 GitHub Secrets

仓库 → Settings → Secrets and variables → Actions → New repository secret

| 名称 | 说明 |
|------|------|
| `DINGTALK_TOKEN` | 钉钉机器人 access_token |

### 3. 手动触发

在 GitHub Actions 页面点击 **Run workflow** 即可手动运行。

## 运行时间

- 自动运行：**每小时一次**（UTC整点）
- 手动触发：随时在 Actions 页面点击 Run workflow

## 匹配规则

### 包含条件
- 学历：本科及以上
- 专业：经济/金融/管理/财务/会计/审计/不限专业等
- 经验：1年以内可报（含见习/管培/应届）
- 地点：贵阳优先，安顺/平坝/遵义亦可
- 类型：国企/事业编/合同制

### 排除条件
- 要求2年以上经验
- 中共党员要求
- 中级/高级职称要求
- 法律/土木/安全工程等特定专业
- 总经理/总监/部长等管理岗
- 医师/护理等技术岗

## 项目结构

```
guizhou-job-monitor/
├── job_monitor_github.py    # 监控脚本（GitHub Actions版）
├── .github/workflows/
│   └── job_monitor.yml      # GitHub Actions 配置
└── README.md
```

## 数据来源

- [163贵州网](https://163gzw.cn)
- [贵州人才博览会](https://rc.guizhou.gov.cn)
