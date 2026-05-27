# LiteratureCLI

面向 code agent 的学术文献管理工具。提供 CLI 接口和 pi skill，支持从多个来源导入论文、检索管理、导出引用。

## 功能

- **多来源导入**：arXiv、DBLP、OpenReview、DOI、本地 PDF、BibTeX、RIS
- **智能元数据提取**：结构化 API 直接解析；PDF 和非标准来源通过 LLM 提取
- **检索与过滤**：全文搜索、模糊搜索、多字段组合过滤
- **Collection 管理**：自定义分组，批量操作
- **多格式导出**：BibTeX、IEEE、Markdown、HTML、JSON
- **PDF 管理**：自动下载、本地存储

## 快速开始

```bash
# 安装
pip install -e .

# 配置 OpenAI API key（PDF 元数据提取需要）
mkdir -p ~/.config/litcli
cp .litcli/auth.example.json ~/.config/litcli/auth.json

# 导入一篇论文
lit add arxiv 1706.03762

# 搜索
lit search "attention mechanism" --json

# 导出 BibTeX
lit export --format bibtex --collection "my-papers"
```

## 文档

- [架构说明](docs/architecture.md) — 目录结构、各层职责、数据流
- [CLI 接口](docs/cli.md) — 完整命令参考和实现说明
- [Pi Skill](docs/skill.md) — agent 使用规范、路由规则、工作流示例

## 项目状态

| 模块 | 状态 |
|------|------|
| `ng/db/` | ✅ 完成（移植自 papercli）|
| `ng/services/` | ✅ 完成（移植并精简）|
| `lit/` CLI 层 | 🔲 待实现 |
| `skills/literature-cli/` | 🔲 待实现 |

## 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | — | 必填，PDF 元数据提取 |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM 模型 |
| `LITCLI_DATA_DIR` | `~/.litcli` | 数据目录 |
| `LITCLI_PDF_PAGES` | `10` | PDF 提取页数 |

参考 `.litcli/auth.example.json` 配置。

配置加载优先级：

1. 已导出的环境变量，例如 `export OPENAI_API_KEY=...`
2. 当前目录或父目录中的项目级 `.litcli/auth.json`
3. 用户级 `~/.config/litcli/auth.json`

`uv tool install` 后从任意目录运行 `lit` 时，推荐使用用户级配置文件。

## 来源

服务层和数据库层移植自 [papercli](https://github.com/SXKDZ/papercli)（MIT License），移除了 TUI、同步、chat 等功能，保留核心文献管理逻辑。原始代码保留在 `references/papercli/` 供参考。
