# CLI 接口设计

## 概览

`lit` 是 LiteratureCLI 的命令行入口，基于 `typer` 构建。所有命令默认输出 human-readable 文本，加 `--json` 输出结构化 JSON，供 agent 解析。

---

## 安装与入口

```bash
pip install -e .
lit --help
```

入口点：`lit/main.py` → `typer` app，子命令注册在 `lit/commands/` 下。

---

## JSON 输出规范

### 成功（单篇论文）
```json
{
  "ok": true,
  "paper": {
    "id": 42,
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "year": 2017,
    "venue_full": "Neural Information Processing Systems",
    "venue_acronym": "NeurIPS",
    "paper_type": "conference",
    "abstract": "...",
    "notes": "...",
    "doi": "...",
    "preprint_id": "arXiv 1706.03762",
    "url": "https://arxiv.org/abs/1706.03762",
    "pdf_path": "/home/user/.papercli/pdfs/vaswani2017attention.pdf",
    "collections": ["transformers", "to-read"],
    "added_date": "2024-01-01T00:00:00"
  }
}
```

### 成功（多篇论文）
```json
{
  "ok": true,
  "papers": [ ...paper objects... ],
  "count": 3
}
```

### 错误
```json
{
  "ok": false,
  "error": "Paper not found on arXiv",
  "code": "NOT_FOUND"
}
```

错误码：`NOT_FOUND` | `ALREADY_EXISTS` | `INVALID_INPUT` | `NETWORK_ERROR` | `LLM_ERROR`

---

## 命令参考

### `lit add` — 导入论文

```bash
# arXiv
lit add arxiv 1706.03762 [--json]
lit add arxiv https://arxiv.org/abs/1706.03762 [--json]

# DBLP
lit add dblp https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17 [--json]

# OpenReview
lit add openreview abc123XYZ [--json]
lit add openreview https://openreview.net/forum?id=abc123XYZ [--json]

# DOI
lit add doi 10.5555/3295222.3295349 [--json]

# 本地 PDF（LLM 提取元数据）
lit add pdf ./paper.pdf [--json]

# BibTeX 文件（批量）
lit add bib ./refs.bib [--json]

# RIS 文件（批量）
lit add ris ./refs.ris [--json]

# 手动创建
lit add manual --title "Paper Title" [--json]
```

**返回**：单篇返回 paper 对象；批量（bib/ris）返回 `{ "ok": true, "papers": [...], "errors": [...], "count": N }`

---

### `lit search` — 搜索

```bash
# 全字段搜索
lit search "attention mechanism" [--json]

# 指定字段
lit search "transformer" --fields title,abstract [--json]

# 模糊搜索
lit search "atention" --fuzzy [--threshold 60] [--json]
```

---

### `lit filter` — 过滤

```bash
lit filter --author "Vaswani" [--json]
lit filter --year 2017 [--json]
lit filter --year-range 2020-2023 [--json]
lit filter --venue "NeurIPS" [--json]
lit filter --type conference [--json]   # conference|journal|preprint|workshop
lit filter --collection "to-read" [--json]

# 组合过滤
lit filter --author "LeCun" --year 2020 --type journal [--json]
```

---

### `lit list` — 列出所有论文

```bash
lit list [--json]
lit list --limit 20 [--json]
lit list --sort year|title|added_date [--json]
```

---

### `lit show` — 论文详情

```bash
lit show 42 [--json]
```

**返回**：完整 paper 对象，含 abstract、notes、collections。

---

### `lit edit` — 编辑元数据

```bash
# 编辑单个字段
lit edit 42 --title "New Title"
lit edit 42 --notes "Key insight: ..."
lit edit 42 --year 2023
lit edit 42 --venue-full "International Conference on Machine Learning"
lit edit 42 --venue-acronym "ICML"
lit edit 42 --paper-type conference
lit edit 42 --doi "10.1145/..."
lit edit 42 --url "https://..."

# LLM 重新提取 PDF 元数据
lit edit 42 --extract-pdf [--json]

# LLM 生成摘要写入 notes
lit edit 42 --summarize [--json]
```

---

### `lit delete` — 删除

```bash
lit delete 42
lit delete --ids 1,2,3
```

同时删除关联的本地 PDF 文件。

---

### `lit export` — 导出

```bash
# 格式：bibtex | ieee | markdown | html | json
lit export --format bibtex                        # 全库
lit export --format bibtex --ids 1,3,7            # 指定 ID
lit export --format bibtex --collection "to-read" # 指定 collection
lit export --format json --json                   # JSON 格式 + JSON 输出

# 输出到文件
lit export --format bibtex --output refs.bib
```

---

### `lit collect` — Collection 管理

```bash
lit collect list [--json]
lit collect show "deep-learning" [--json]
lit collect create "deep-learning"
lit collect rename "deep-learning" "dl-papers"
lit collect delete "deep-learning"

# 添加/移除论文
lit collect add "deep-learning" --ids 1,2,3
lit collect remove "deep-learning" --ids 1,2,3

# 清理空 collection
lit collect purge
```

---

### `lit pdf` — PDF 操作

```bash
# 获取 PDF 绝对路径
lit pdf path 42 [--json]

# 用系统默认程序打开
lit pdf open 42

# 重新下载
lit pdf download 42 [--json]
```

---

### `lit db` — 数据库维护

```bash
# 检查孤立记录和文件
lit db check [--json]

# 清理孤立 PDF 文件和数据库记录
lit db clean
```

---

## 实现说明

### 目录结构

```
lit/
├── main.py              # typer app，注册所有子命令
├── output.py            # JSON / human-readable 统一输出
├── logger.py            # CliLogger，实现 _add_log / notify 接口
└── commands/
    ├── add.py
    ├── search.py
    ├── show.py
    ├── edit.py
    ├── delete.py
    ├── export.py
    ├── collect.py
    ├── pdf.py
    └── db.py
```

### CliLogger

所有服务类需要一个 `app` 参数用于日志和通知，CLI 层传入 `CliLogger`：

```python
# lit/logger.py
import logging

class CliLogger:
    def _add_log(self, key: str, message: str):
        logging.debug("[%s] %s", key, message)

    def notify(self, message: str, severity: str = "information"):
        if severity == "error":
            logging.error(message)
        else:
            logging.info(message)
```

### 输出格式化

```python
# lit/output.py
import json, sys

def print_result(data: dict, as_json: bool):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # human-readable 格式化
        ...

def error(message: str, code: str, as_json: bool):
    data = {"ok": False, "error": message, "code": code}
    print_result(data, as_json)
    sys.exit(1)
```
