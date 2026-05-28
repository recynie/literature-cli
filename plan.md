# 重构方案：统一入口 + 后端 fallback

## 目标

1. `lit add <identifier>` — 统一导入入口，自动识别来源并获取元数据
2. `lit edit <id> --fetch` — 根据已有信息自动补全空字段
3. PDF 获取支持 fallback 链
4. 新增 OpenAlex、Semantic Scholar、Unpaywall 三个免费 API

现有子命令（`lit add arxiv`、`lit add doi` 等）保留，向后兼容。

---

## 后端服务选择

### 元数据获取

| 功能 | 后端顺序（按稳定性/信息丰富度） |
|------|-------------------------------|
| arXiv ID → 元数据 | 1. arXiv API |
| DOI → 元数据 | 1. Crossref  2. OpenAlex  3. Semantic Scholar |
| DBLP URL → 元数据 | 1. DBLP BibTeX |
| OpenReview ID → 元数据 | 1. OpenReview API |
| 标题 → 元数据 | 1. OpenAlex `search=`  2. Semantic Scholar `/paper/search` |

### PDF 获取

| 后端顺序 | 适用条件 |
|---------|---------|
| 1. arXiv 直链 | 有 arXiv ID |
| 2. OpenReview 直链 | 有 OpenReview ID |
| 3. Unpaywall | 有 DOI |
| 4. OpenAlex `best_oa_location.pdf_url` | 有 DOI 或 OpenAlex ID |
| 5. Semantic Scholar `openAccessPdf.url` | 以上均失败 |

### 补全空字段（`--fetch`）

根据论文已有 identifier 选择后端：

| 已有 identifier | 后端顺序 |
|---------------|---------|
| arXiv ID | 1. arXiv API  2. Semantic Scholar（补机构） |
| DOI | 1. Crossref  2. OpenAlex  3. Semantic Scholar |
| 仅有标题 | 1. OpenAlex  2. Semantic Scholar |
| 无任何信息 | 报错，提示用户至少提供 title 或 DOI |

补全策略：**只填空字段，不覆盖已有值**。加 `--overwrite` 时用远端数据覆盖。

---

## 服务配置

### config.toml 新增

```toml
[litcli]
data_dir = "~/.litcli"
pdf_pages = 10

[services]
# Unpaywall 需要一个 email（免费，无需 key）
unpaywall_email = "your-email@example.com"

# OpenAlex polite pool（可选，提供 email 可获得更高速率）
openalex_email = "your-email@example.com"

# Semantic Scholar（免费 tier 无需 key，有 key 可提高速率）
# semantic_scholar_api_key = ""
```

### 环境变量映射

```python
CONFIG_ENV_MAP = {
    # ... 现有 ...
    "services.unpaywall_email": "UNPAYWALL_EMAIL",
    "services.openalex_email": "OPENALEX_EMAIL",
    "services.semantic_scholar_api_key": "SEMANTIC_SCHOLAR_API_KEY",
}
```

三个服务均为免费 API，无需 key 即可使用。email 参数用于进入 polite pool（更高速率限制），非必填。

---

## Identifier 识别规则

`lit add <identifier>` 的 dispatch 逻辑：

```
1. 本地文件路径（.pdf/.bib/.ris 后缀且文件存在）→ PDF / BibTeX / RIS
2. arXiv URL（含 arxiv.org）→ 提取 arXiv ID
3. arXiv ID 格式（\d{4}\.\d{4,5}(v\d+)?）→ arXiv
4. DOI URL（含 doi.org）→ 提取 DOI
5. DOI 格式（10\.\d+/...）→ DOI
6. OpenReview URL（含 openreview.net）→ 提取 OpenReview ID
7. DBLP URL（含 dblp.org）→ DBLP
8. 其他 → 当作标题，走 OpenAlex/S2 搜索
```

---

## 文件改动清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `ng/services/openalex.py` | OpenAlex API 封装：`search_by_doi()`、`search_by_title()`、`get_pdf_url()` |
| `ng/services/semantic_scholar.py` | Semantic Scholar API 封装：`search_by_doi()`、`search_by_title()`、`get_pdf_url()` |
| `ng/services/unpaywall.py` | Unpaywall API 封装：`get_oa_pdf_url(doi)` |
| `ng/services/identifier.py` | Identifier 识别：`detect(raw_input) → (type, cleaned_value)` |
| `ng/services/fetch.py` | 补全逻辑：`fetch_metadata_for_paper(paper, overwrite=False)` |

### 修改文件

| 文件 | 改动 |
|------|------|
| `lit/config.py` | `CONFIG_ENV_MAP` 新增三个 services 条目 |
| `lit/commands/add.py` | 新增顶层 `lit add <identifier>` 命令，调用 identifier dispatch |
| `lit/commands/edit.py` | 新增 `--fetch` 和 `--overwrite` flag |
| `ng/services/add_paper.py` | 新增 `add_by_identifier(raw_input)` 方法，内部 dispatch |
| `ng/services/pdf.py` | PDF 获取增加 Unpaywall/OpenAlex/S2 fallback 链 |
| `ng/services/__init__.py` | 导出新模块 |
| `.litcli/config.example.toml` | 新增 `[services]` 段 |

### 不动的文件

- `ng/db/models.py` — 数据模型不变
- `ng/services/metadata.py` — 现有 `extract_from_*` 方法保持原样，新 API 放独立文件
- 现有子命令（`lit add arxiv` 等）— 保留，不改

---

## 实施顺序

```
Phase 1: 基础设施
  1. ng/services/identifier.py — identifier 识别
  2. config.py 新增 services 配置
  3. .litcli/config.example.toml 更新

Phase 2: 新 API 封装
  4. ng/services/openalex.py
  5. ng/services/semantic_scholar.py
  6. ng/services/unpaywall.py

Phase 3: 统一入口
  7. ng/services/add_paper.py — add_by_identifier()
  8. lit/commands/add.py — lit add <identifier>

Phase 4: 补全与 PDF fallback
  9. ng/services/fetch.py — fetch_metadata_for_paper()
  10. lit/commands/edit.py — --fetch / --overwrite
  11. ng/services/pdf.py — PDF 获取 fallback 链
```

每个 phase 独立可测试，可以分 PR 提交。

---

## API 速率限制

| API | 免费限制 | 应对 |
|-----|---------|------|
| arXiv | 3 秒间隔（已实现） | 保持现有 `_ARXIV_MIN_INTERVAL` |
| Crossref | 50 req/s（polite pool） | 无需特殊处理 |
| OpenAlex | 10 req/s（无 email）/ 100 req/s（有 email） | 配置 email 即可 |
| Semantic Scholar | 1 req/s（无 key）/ 10 req/s（有 key） | 加 1s sleep |
| Unpaywall | 100k req/day | 无需特殊处理 |
| OpenReview | 无公开限制 | 保持现状 |
| DBLP | 无公开限制 | 保持现状 |
