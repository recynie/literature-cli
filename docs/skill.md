# LiteratureCLI Pi Skill

Skill 定义位于 `skills/literature-cli/SKILL.md`，已完整实现。

---

## 路由规则

| 用户意图 | 命令 |
|---------|------|
| 从 arXiv 导入论文 | `lit add arxiv <id-or-url> --json` |
| 从 DBLP 导入论文 | `lit add dblp <url> --json` |
| 从 OpenReview 导入 | `lit add openreview <id-or-url> --json` |
| 从 DOI 导入 | `lit add doi <doi> --json` |
| 导入本地 PDF | `lit add pdf <path> --json` |
| 手动创建条目 | `lit add manual --title "..." --json` |
| 批量导入 BibTeX | `lit add bib <path> --json` |
| 批量导入 RIS | `lit add ris <path> --json` |
| 搜索论文 | `lit search "<query>" --json` |
| 模糊搜索 | `lit search "<query>" --fuzzy --threshold 60 --json` |
| 按字段过滤 | `lit filter --author/--year/--year-range/--venue/--type/--collection/--query --json` |
| 列出所有论文 | `lit list --json` |
| 查看论文详情 | `lit show <id> --json` |
| 编辑元数据 | `lit edit <id> --title/--venue-full/--venue-acronym/--paper-type/--doi/--url/--notes/--year <value> --json` |
| 重新提取 PDF 元数据 | `lit edit <id> --extract-pdf --json`（需要 OPENAI_API_KEY）|
| 生成摘要写入 notes | `lit edit <id> --summarize --json`（需要 OPENAI_API_KEY）|
| 删除论文 | `lit delete <id> --force --json` 或 `lit delete --ids 1,2,3 --force --json` |
| 导出引用 | `lit export --format bibtex/ieee/markdown/html/json --ids 1,2 --json` |
| 按 collection 导出 | `lit export --format bibtex --collection "name" --json` |
| 导出到文件 | `lit export --format bibtex --output /path/to/file --json` |
| 列出 collections | `lit collect list --json` |
| 查看 collection | `lit collect show "name" --json` |
| 创建 collection | `lit collect create "name" --json` |
| 重命名 collection | `lit collect rename "old" "new" --json` |
| 删除 collection | `lit collect delete "name" --force --json` |
| 清理空 collection | `lit collect purge --json` |
| 添加到 collection | `lit collect add "name" --ids 1,2 --json` |
| 从 collection 移除 | `lit collect remove "name" --ids 1,2 --json` |
| 获取 PDF 路径 | `lit pdf path <id> --json` |
| 打开 PDF | `lit pdf open <id>` |
| 重新下载 PDF | `lit pdf download <id> --json` |
| 数据库健康检查 | `lit db check --json` |
| 清理孤立文件 | `lit db clean --json` |

---

## 典型工作流

### Pattern 1：查找并导入一篇论文

```bash
# 从 arXiv 导入
lit add arxiv 1706.03762 --json
# 返回 paper 对象，含分配的 id 和 pdf_path

# 从 DOI 导入
lit add doi 10.1038/s41586-023-06139-9 --json
```

### Pattern 2：搜索并导出

```bash
# 搜索
lit search "vision transformer" --json
# 从结果中取 id

# 导出指定论文的 BibTeX
lit export --format bibtex --ids 1,3,7

# 导出整个 collection
lit export --format bibtex --collection "my-papers"
```

### Pattern 3：构建阅读列表

```bash
# 创建 collection
lit collect create "to-read" --json

# 搜索相关论文
lit search "diffusion model" --json

# 批量加入 collection
lit collect add "to-read" --ids 2,5,8 --json

# 验证
lit filter --collection "to-read" --json

# 导出为 Markdown
lit export --format markdown --collection "to-read"
```

### Pattern 4：读取论文内容

```bash
# 获取元数据和 notes
lit show 42 --json

# 获取 PDF 路径，供后续处理
lit pdf path 42 --json
# 返回: { "ok": true, "path": "/home/user/.litcli/pdfs/vaswani2017attention.pdf" }
```

### Pattern 5：批量导入文献库

```bash
# 从 BibTeX 文件批量导入
lit add bib ./exported_refs.bib --json
# 返回: { "ok": true, "papers": [...], "errors": [...], "count": 42 }
# errors 记录失败条目（如重复），不影响其他条目导入
```

---

## JSON Schema

### Paper 对象

```json
{
  "id": 42,
  "title": "Attention Is All You Need",
  "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
  "year": 2017,
  "venue_full": "Neural Information Processing Systems",
  "venue_acronym": "NeurIPS",
  "paper_type": "conference",
  "abstract": "The dominant sequence transduction models...",
  "notes": "Key paper for transformer architecture",
  "doi": null,
  "preprint_id": "arXiv 1706.03762",
  "category": "cs.CL",
  "url": "https://arxiv.org/abs/1706.03762",
  "pdf_path": "/home/user/.litcli/pdfs/vaswani2017attention.pdf",
  "collections": ["transformers", "to-read"],
  "added_date": "2024-01-01T00:00:00",
  "modified_date": "2024-01-01T00:00:00"
}
```

`paper_type` 枚举值：`conference` | `journal` | `preprint` | `workshop` | `other`

`pdf_path` 为绝对路径，`null` 表示尚未下载。

### Collection 对象

```json
{
  "id": 3,
  "name": "transformers",
  "paper_count": 12,
  "created_at": "2024-01-01T00:00:00",
  "last_modified": "2024-01-02T00:00:00"
}
```

---

## 注意事项

- **始终使用 `--json`** 处理命令输出，human-readable 格式不保证稳定
- `lit add pdf`、`lit edit --extract-pdf`、`lit edit --summarize` 依赖 LLM，需要 `OPENAI_API_KEY`
- `lit add arxiv` / `lit add openreview` 会自动下载 PDF，网络较慢时需等待
- `lit add bib` / `lit add ris` 批量导入时，`errors` 字段记录失败条目，不影响其他条目
- `lit delete` 同时删除本地 PDF 文件，不可恢复；自动化场景使用 `--force` 跳过确认
- 所有变更命令返回 `"ok": true/false`，继续下一步前应检查此字段
