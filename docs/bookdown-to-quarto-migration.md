# Bookdown → Quarto 迁移记录

本文档记录将 `tidy-text-mining-zh` 从 bookdown 迁移到 Quarto 的计划、字段映射、风险点与回滚策略。**迁移的首要动机**不是出书引擎升级，而是 Quarto 原生支持多计算内核（knitr/Jupyter），可在同一本书内并排展示 R/Python/Julia 三种实现，这是 bookdown 做不到的。迁移本身尚未执行，本文件先于代码改动落地。

## 0. 三语言对比的可行性（迁移的核心动机）

### 0.1 bookdown 的限制

- bookdown 只能用 knitr 一个引擎，所有 chunk 必须是 R（`{r}`）。
- 想在书里展示 Python/Julia 等价实现，目前只能：
  - 在 R chunk 里调 `reticulate::py_run_string()`（破坏代码可读性，且无法逐 chunk 缓存）；
  - 或把 Python 代码以纯文本块 `{python eval=FALSE}` 静态展示（不能跑、不能出图）；
  - 或像现在的 `reanalysis-hongloumeng.py` 一样，把 Python 实现剥离成独立脚本，书内外两套。
- 没有原生"同一段落三个折叠标签页分别展示三种语言"的能力。

### 0.2 Quarto 的多引擎能力

Quarto 在同一 `.qmd` 文件内允许混用多个 kernel，通过 chunk label 前缀切换：

````markdown
```{r}```         # knitr 引擎，R
```{python}```    # Jupyter 引擎，Python
```{julia}```     # Jupyter 引擎，Julia
````

三种特性使三语言对比变得**自然且可执行**：

1. **同文件多 kernel 混编**：一个章节内可连续放 R、Python、Julia chunk，每个都能真实运行并出图，无需 reticulate 桥接。
2. **`engine: knitr` 与 `engine: jupyter` 可在 `_quarto.yml` 全局切换，也可在单文件 `---` 头里覆盖**：既能整书保持 R 为主，也能单独把某一章设为 Jupyter 内核跑 Python+Julia。
3. **`::: panel-tabset` 卡片组**：Quarto 原生语法，把 R/Python/Julia 三段代码放进同一组标签页，HTML 端读者点击切换，PDF 端顺序展开。这正是三语言对比最理想的呈现方式。

示例（迁移后可在任一章节直接使用）：

````markdown
::: panel-tabset
## R

```{r}
library(dplyr); library(tidytext)
text <- c("床前明月光", "疑是地上霜")
tibble(line=1:2, text=text) |>
  unnest_tokens(word, text) |>
  count(word, sort=TRUE)
```

## Python

```{python}
import pandas as pd, jieba
text = ["床前明月光", "疑是地上霜"]
rows = [(i, w) for i, t in enumerate(text, 1) for w in jieba.lcut(t)]
pd.DataFrame(rows, columns=["line","word"]).value_counts("word")
```

## Julia

```{julia}
using DataFrames
text = ["床前明月光", "疑是地上霜"]
rows = [(i, w) for i in 1:length(text) for w in split(text[i], "")]
DataFrame(line=first.(rows), word=last.(rows)) |>
  x -> combine(groupby(x, :word), nrow => :n) |> x -> sort(x, :n, rev=true)
```
:::
````

### 0.3 迁移后能做什么（之前做不到的）

| 能力 | bookdown 现状 | Quarto 迁移后 |
|---|---|---|
| 同一章并排可运行的 R/Python/Julia | 否（Python 需 reticulate 或静态块） | 是 |
| 三语言代码用 tabset 切换 | 否 | 是（`::: panel-tabset`） |
| 三语言输出图表同章对比 | 否 | 是 |
| 单独把某一章设为 Jupyter 内核 | 否 | 是（文件头 `engine: jupyter`） |
| Julia chunk 真实执行出图 | 否 | 是（需装 IJulia + Quarto 的 jupyter hook） |
| 三语言 chunk 共享缓存 | 否 | 部分（同一 kernel 内可缓存，跨 kernel 需手动落盘） |

### 0.4 仍需注意的成本

- **Julia kernel**：需在本机装 Julia + `IJulia.jl`，并在 Jupyter 注册 kernel（`jupyter kernelspec install`）。Quarto 调用 Jupyter 时按 `julia` 语言标签匹配 kernel name。
- **中文分词**：R 用 jiebaR，Python 用 jieba，Julia 用 `Jieba.jl`，三者词典不一定同步，对比时需说明版本差异。
- **数据加载**：`data/hongloumeng.rda` 是 R 格式，Python 用 `pyreadr`，Julia 用 `RData.jl`；建议同时导出一份 `parquet`/`csv` 让三语言平等读取。
- **图表风格统一**：R 用 ggplot2，Python 用 matplotlib/seaborn，Julia 用 `CairoMakie.jl`/`Plots.jl`，三套主题需手动对齐才能并排对比时不突兀。
- **执行顺序**：Quarto 同一文件内多 kernel 是顺序执行的，但变量互不可见；三语言版本需各自完整加载数据，不能复用 R chunk 的变量。
- **渲染性能**：三语言混编会让单次 `quarto render` 慢一些（每个 kernel 都要启动），可对 Julia chunk 用 `cache: true` 缓解。

### 0.5 推荐的章节组织方式

迁移稳定后，对每个核心主题（词频、zipf、tf-idf、bigram、情感、LDA），用如下结构组织一节：

1. 算法/概念说明（纯文本 + 公式）。
2. `::: panel-tabset` 三标签页：R / Python / Julia 的等价实现，各自真实运行。
3. 三语言输出图表并排展示（或继续放 tabset 内）。
4. 简短对比说明：代码长度、性能、依赖差异、结果是否一致。
5. （可选）一个跨语言一致性检验的 chunk，把三者结果读回 R 做 `all.equal` 断言。

这样既能保留原书以 R 为主线的叙事，又能让 Python/Julia 版本自然嵌入，而不是像现在 `reanalysis-hongloumeng.py` 那样游离在书外。

## 1. 迁移目标

- 出书引擎由 `bookdown::render_book` + `_output.yml` + `_bookdown.yml` 切换为 `quarto render` + `_quarto.yml`。
- 三种产物保持一致：HTML (gitbook 风格)、PDF (xelatex + 中文)、EPUB。
- 章节内容（`0X-*.Rmd`）尽可能原地保留，只改 YAML 头与少量语法差异点。
- 中文渲染、参考文献、自定义 callout 块（rmdnote/rmdtip/rmdwarning）、Google Analytics 等价保留。
- **新增**：在 `_quarto.yml` 注册多引擎，为后续按 0.5 节插入 R/Python/Julia 对比段做准备。

## 2. 当前 bookdown 配置盘点

### 2.1 文件清单与作用

| 文件 | 作用 | Quarto 对应 |
|---|---|---|
| `index.Rmd` | 书目主文件，含 `---` YAML 头与前言正文 | `_quarto.yml` + `index.qmd`（或保留 `index.Rmd`） |
| `01-tidy-text.Rmd` ~ `06-topic-models.Rmd` | 正文章节 | 文件名不变，扩展名改 `.qmd`（或保留 `.Rmd`，Quarto 兼容） |
| `10-references.Rmd` | 自动生成 `packages.bib` 并输出参考文献章 | Quarto `references` 段 + `knitr` code chunk 仍可保留；或用 `bibliography:` + 自动生成 |
| `_bookdown.yml` | book_filename、clean、language（图/表/章名前缀）、delete_merged_file | `_quarto.yml` 的 `book:` + `language:` 节 |
| `_output.yml` | gitbook/pdf_book/epub_book 三种格式配置 | `_quarto.yml` 的 `format:` 下 `html:` / `pdf:` / `epub:` |
| `css/style.css` | gitbook 与 epub 共用样式 | `html.css` 与 `epub.css` 可分别指定，文件可复用 |
| `latex/preamble.tex` | booktabs/longtable/framed/xeCJK 字体/rmdblock 环境 | `_quarto.yml` 的 `pdf.include-in-header`，内容大部分可直接复用 |
| `latex/template.tex` | 自定义 pandoc LaTeX 模板 | Quarto 用内置模板 + `format.pdf.template` 可覆盖，一般无需自定义 |
| `latex/before_body.tex` | 献词页 + skip 调整 | `pdf.include-before-body`，或改用 Quarto 的 `title-block` / 自定义 `preamble` |
| `latex/after_body.tex` | `\backmatter \printindex` | `pdf.include-after-body`，索引由 Quarto `index` 选项控制 |
| `_includes/analytics.html` | Google Analytics 注入 | `html.include-in-header`，文件可复用 |
| `book.bib` | 手写参考文献 | `bibliography: book.bib`，格式不变 |
| `packages.bib` | 由 `knitr::write_bib` 自动生成 | 保留 `10-references` 中的 chunk，或改用 `quarto addbibliography` |
| `images/` | 封面、note/tip/warning 图标、tidyflow 图 | 路径不变 |
| `Makefile` | `make pdf/epub/html` 调用 Rscript | 改为调用 `quarto render --to pdf/epub/html` |

### 2.2 关键配置项迁移映射

#### index.Rmd 的 YAML 头（当前）

```yaml
title: "Text Mining with R"
subtitle: "A Tidy Approach (for Chinese Text)"
author: "Julia Silge, David Robinson, Song Li"
date: "`r Sys.Date()`"
documentclass: ctexbook
bibliography: [book.bib, packages.bib]
biblio-style: apalike
link-citations: yes
colorlinks: yes
lot: yes
lof: yes
always_allow_html: yes
geometry: [b5paper, tmargin=2.5cm, bmargin=2.5cm, lmargin=3.5cm, rmargin=2.5cm]
knit: "bookdown::render_book"
site: bookdown::bookdown_site
description: "..."
github-repo: boltomli/tidy-text-mining-zh
cover-image: images/cover.png
```

#### _quarto.yml（迁移后等价）

```yaml
project:
  type: book
  output-dir: _book
  # 等价 delete_merged_file: true 由 Quarto 自动管理

book:
  title: "Text Mining with R"
  subtitle: "A Tidy Approach (for Chinese Text)"
  author: "Julia Silge, David Robinson, Song Li"
  date: today            # 等价 `r Sys.Date()`
  date-format: "YYYY-MM-DD"
  cover-image: images/cover.png
  description: "A guide to text analysis within the tidy data framework, using the tidytext package and other tidy tools, for Chinese text."
  repo-url: https://github.com/boltomli/tidy-text-mining-zh
  repo-subdir: /
  chapters:
    - index.qmd
    - 01-tidy-text.qmd
    - 02-sentiment-analysis.qmd
    - 03-tf-idf.qmd
    - 04-word-combinations.qmd
    - 05-document-term-matrices.qmd
    - 06-topic-models.qmd
    - references.qmd
  # 等价 lot/lof
  appendices: []

bibliography: [book.bib, packages.bib]
biblio-style: apalike
link-citations: true
csl: ~~                   # apalike 由 biblio-style 控制，无需 CSL

format:
  html:
    theme: cosmo           # 取近 gitbook 默认观感
    css: css/style.css
    include-in-header: _includes/analytics.html
    toc: true
    toc-depth: 3
    # 等价 gitbook 的 toc.collapse: section
    toc-title: "目录"
    # 等价 download: [pdf, epub]
    downloads: [pdf, epub]
    # 编辑链接等价
    repo-actions: [edit, source, issue]
    # 多引擎：默认 knitr（R），按章节文件头可覆盖为 jupyter
    engine: knitr
    # 允许 panel-tabset 切换 R/Python/Julia
    tabset: true
  pdf:
    documentclass: ctexbook
    classoption: [b5paper]
    geometry:
      - tmargin=2.5cm
      - bmargin=2.5cm
      - lmargin=3.5cm
      - rmargin=2.5cm
    include-in-header: latex/preamble.tex
    include-before-body: latex/before_body.tex
    include-after-body: latex/after_body.tex
    keep-tex: true
    latex-engine: xelatex
    citation-package: natbib
    toc-depth: 3
    lof: true
    lot: true
    template: latex/template.tex   # 若 Quarto 内置模板够用则删除此项
  epub:
    stylesheet: css/style.css
    cover-image: images/cover.png

language:
  ui:
    edit: "编辑"
  # Quarto 的 language 节更细，下列为大致对应
  figure-prefix: "图 "
  table-prefix: "表 "
  chapter-name: "第 "
  chapter-prefix: " 章"
```

### 2.3 章节文件扩展名

- Quarto 默认识别 `.qmd`，但同时兼容 `.Rmd`/`.ipynb`。
- 建议：保留 `.Rmd` 以减少 git diff，仅在 `index.Rmd` 中删掉 `knit: "bookdown::render_book"` 与 `site: bookdown::bookdown_site`（这两项会让 RStudio 仍按 bookdown 编织）。
- 若彻底切换，统一改名 `.Rmd` → `.qmd`，并在 `_quarto.yml` 的 `chapters:` 里同步。

### 2.4 自定义 callout 块

当前用法（散落在 `01`~`06`）：

```markdown
```{block, type = "rmdnote"}
... 内容 ...
```
```

Quarto 原生 callout 语法：

```markdown
::: {.callout-note}
... 内容 ...
:::
```

迁移策略：
- 全量替换 `{block, type = "rmdnote"}` → `::: {.callout-note}`，`rmdtip` → `.callout-tip`，`rmdwarning` → `.callout-warning`。
- LaTeX 端 `preamble.tex` 中 `rmdblock/rmdnote/rmdtip/rmdwarning` 环境可保留作 fallback；Quarto 的 callout 在 PDF 端由内置模板渲染，外观略有差异，需目检。
- HTML 端 `css/style.css` 的 `.rmdnote/.rmdtip/.rmdwarning` 样式改为 `.callout-note/.callout-tip/.callout-warning`，或保留旧类名并通过 Quarto 的 `callout` 自定义模板映射。

### 2.5 交叉引用与图表标签

- bookdown 的 `#tidytext`、`#sentiment`、`\@ref(fig:plotcount)` 在 Quarto 下：
  - 章节标签 `{#tidytext}` 兼容，Quarto 也支持。
  - 图表引用 `\@ref(fig:plotcount)` 需改为 Quarto 语法 `@ref(fig-plotcount)`，标签定义由 `fig.cap = "..."` + chunk label `plotcount` 自动生成 `fig-plotcount`。
  - 建议用脚本批量替换：`\@ref(fig:XXX)` → `@ref(fig-XXX)`，`\@ref(tab:XXX)` → `@ref(tab-XXX)`。

### 2.6 参考文献章

`10-references.Rmd` 当前：

````markdown
`r if (knitr:::is_html_output()) '# 参考文献 {#references .unnumbered}'`

```{r include=FALSE}
knitr::write_bib(c(...), 'packages.bib')
```
````

Quarto 等价：
- `packages.bib` 仍由该 chunk 生成，保留 chunk 不动。
- 章标题改为静态 `# 参考文献 {.unnumbered}`，或用 Quarto 的 `references: true` 自动生成章。
- `knitr:::is_html_output()` 的条件渲染可改为 Quarto 的 `::: {.content-visible when-format="html"}`。

### 2.7 Makefile

```make
# 旧
pdf: index.Rmd
	Rscript -e 'bookdown::render_book("index.Rmd", output_format = "bookdown::pdf_book")'

# 新
pdf:
	quarto render --to pdf
html:
	quarto render --to html
epub:
	quarto render --to epub
all: pdf epub html
clean:
	rm -rf _book
```

## 3. 风险与差异点

| 项 | bookdown 行为 | Quarto 行为 | 处理 |
|---|---|---|---|
| 默认 HTML 主题 | gitbook 风格（左侧 toc 折叠） | Bootstrap 5（可调 `theme`） | 选 `theme: cosmo` 或 `pulse` 接近观感；toc 折叠用 `toc-collapse: section` |
| `dev: "cairo_pdf"` | 显式指定 | Quarto PDF 默认 cairo | 一般无需指定；如需保留加 `pdf.dev: cairo_pdf`（实际由 knitr 处理） |
| `quote_footer` | bookdown 特有 | 无直接对应 | 在 `preamble.tex` 重定义 `quote` 环境，或放弃此细节 |
| `template: latex/template.tex` | 自定义 pandoc 模板 | Quarto 用内置模板，覆盖需用 `format.pdf.template` 但与 Quarto 的部分功能冲突 | 优先尝试不指定 template，仅在必要时回退自定义模板 |
| `delete_merged_file` | 合并 Rmd 后清理 | Quarto 不生成合并 Rmd | 无需对应 |
| `always_allow_html` | knitr 选项 | Quarto 自动处理 | 删除 |
| `citation_package: natbib` | bookdown 透传 | `pdf.citation-package: natbib` | 直接对应 |
| 章回编号 `第 X 章` | `_bookdown.yml` 的 `chapter_name` | Quarto `language` 节，但字段名不同 | 见上方 `language` 节示例，需测试 |
| Google Analytics | `_includes/analytics.html` 注入 | 同样可用 `include-in-header`；或用 Quarto 1.4+ 的 `html.google-analytics` 选项 | 二选一 |

## 4. 不可丢失的功能

迁移后必须验证：

1. 六章正文 + 前言 + 参考文献全部能 render。
2. 中文字体在 PDF 中正确（Noto Serif/Sans CJK SC）。
3. 三个 callout 类型在 HTML 与 PDF 中均可见。
4. `fig.cap` / `tab.cap` 交叉引用可点击跳转。
5. `book.bib` + 自动生成的 `packages.bib` 引用在三种格式下都能渲染。
6. `images/cover.png` 在 HTML 首页与 EPUB 封面正确显示。
7. HTML 的编辑链接指向 `github.com/boltomli/tidy-text-mining-zh`。
8. EPUB 的 css/style.css 生效。

## 5. 回滚策略

迁移以**新建文件**为主，旧文件保留：

- `_bookdown.yml`、`_output.yml`、`index.Rmd` 不立即删除，先重命名为 `_bookdown.yml.bak`、`_output.yml.bak`、`index.Rmd.bak`。
- 新增 `_quarto.yml`、`index.qmd`（或在原 `index.Rmd` 上改并备份）。
- 章节文件 `.Rmd` 暂不改名，待 `_quarto.yml` 跑通后再批量改 `.qmd`。
- `Makefile` 保留旧 target 为 `bookdown-pdf` 等别名，新 target 为 `pdf/epub/html`。
- 回滚只需：删 `_quarto.yml`，恢复 `.bak` 文件，恢复 Makefile。

## 6. 执行顺序（建议）

1. 安装 Quarto CLI（`winget install quarto.quarto`）并 `quarto check`。
2. 写 `_quarto.yml`（基于第 2.2 节模板），先只配 `html`，跑 `quarto render --to html`，验证目录、章节、callout、引用。
3. 加 `pdf` 配置，跑 `quarto render --to pdf`，验证中文字体、CTeX、callout LaTeX 渲染。
4. 加 `epub` 配置，验证封面与 css。
5. 批量替换 `{block, type = "rmdnote/rmdtip/rmdwarning"}` → Quarto callout。
6. 批量替换 `\@ref(...)` → `@ref(...)`。
7. 改 Makefile，跑 `make all`。
8. 跑通后清理 `.bak` 文件，提交。
9. （可选）章节文件统一改名 `.qmd`。

## 7. 暂不迁移的部分

- `reanalysis-hongloumeng.py`：独立 Python 脚本，与出书引擎无关，不动。
- `data/`、`images/`、`.venv/`：不动。
- `.Rproj`：RStudio 项目文件，Quarto 不依赖；如需可新建 `.vscode/` 或保留 `.Rproj` 让 RStudio 仍能打开。

## 8. 待确认事项

- [ ] 是否保留 `latex/template.tex` 自定义模板，还是改用 Quarto 内置模板？
- [ ] HTML 主题选 `cosmo` 还是更接近 gitbook 的别的主题？
- [ ] 章节文件是否最终改名 `.qmd`？
- [ ] Google Analytics 是用旧脚本注入还是改用 Quarto 1.4+ 的 `google-analytics` 选项？
- [ ] `packages.bib` 由 `knitr::write_bib` 生成还是手动维护？
- [x] `QUARTO_PYTHON` 持久化方式：用户级 `setx`（全局）还是项目内 `.env`/Makefile 注入（自包含）？→ **已定**：用 Quarto 原生的 `_environment` 文件，写 `QUARTO_PYTHON=.venv/Scripts/python.exe` 相对路径，渲染时自动读入、不覆盖外部已设值、随项目迁移。`.gitignore` 已加 `/_*.local` 规则。已用 `test-env.qmd` 实测：`engine: jupyter` 下 python chunk 输出 `sys.executable` 指向 `.venv\Scripts\python.exe`，机制生效。

### 已验证的多引擎环境（2026-07-04）

| 组件 | 版本 | 路径 |
|---|---|---|
| Quarto | 1.9.38 | `C:\Users\songl\scoop\apps\quarto\current` |
| Python | 3.14.5 | `D:\exp\tidy-text-mining-zh\.venv\Scripts\python.exe`（uv 管理） |
| Jupyter core | 5.9.1 | 同上 venv |
| ipykernel | 7.3.0 | 同上 venv |
| Julia | 1.12.6 | `C:\Users\songl\.julia\juliaup\julia-1.12.6+...\bin\julia.exe` |
| IJulia kernel | julia-1.12 | `C:\Users\songl\AppData\Roaming\jupyter\kernels\julia-1.12` |
| Python kernel | python3 | `D:\exp\tidy-text-mining-zh\.venv\share\jupyter\kernels\python3` |

`quarto check jupyter` 通过，Kernels: `python3, julia-1.12`。

环境配置要点：
- Python venv 由 `uv sync` 重建（原 venv 的 Python 3.14 已丢失，`uv python install 3.14` 后重建）。
- jupyter 全家桶通过 `uv add --dev jupyter ipykernel` 装入项目 venv，记入 `pyproject.toml` 的 `[dev-dependencies]`。
- Python kernel 通过 `python -m ipykernel install --user --name python3 --display-name "Python 3 (project venv)"` 注册到用户级 jupyter kernels 目录。
- Julia kernel 由 IJulia 自动注册。
- Quarto 找不到 PATH 上的 `python`，必须设 `QUARTO_PYTHON`，否则 `quarto check jupyter` 报 "Unable to locate an installed version of Python 3"。**已固化**：项目根新增 `_environment` 文件，内容 `QUARTO_PYTHON=.venv/Scripts/python.exe`（相对路径）。Quarto 渲染项目时自动读入，不覆盖外部已设值，随项目迁移无需改路径。`.gitignore` 已加 `/_*.local` 允许本地覆盖且不入版本控制。实测：未设外部 `QUARTO_PYTHON` 时，`engine: jupyter` 的 python chunk 输出 `sys.executable = D:\exp\tidy-text-mining-zh\.venv\Scripts\python.exe`。注意 `quarto check jupyter` 不读 `_environment`（非项目命令），仍会报找不到 python，但实际项目渲染不受影响。

待解决：`engine: jupyter` 下 `{julia}` chunk 未走 IJulia kernel，被 Quarto 自带的 `julia-engine` 扩展当成静态代码透传（render 日志只执行 1 个 cell）。需调研是否要装第三方 Quarto Julia extension、或在 chunk 头显式指定 kernel、或改用 `engine: knitr` + JuliaCall。这影响 §0 三语言对比的 Julia 那一栏。

已知无害警告（Python 3.14 deprecation）：
- `asyncio.WindowsSelectorEventLoopPolicy is deprecated (slated for removal in Python 3.16)` —— 来自 Quarto 自带 `jupyter.py`，无需处理。
- `Kernel is running over TCP without encryption` —— 本地渲染无影响。
- jieba 0.42.1 抛 `SyntaxWarning: invalid escape sequence "\."` —— 旧正则字面量在 3.12+ deprecation，3.14 转为警告；功能不受影响，可 `warnings.filterwarnings("ignore", category=SyntaxWarning)` 静音或升级 jieba。

### 与三语言对比相关的决策

- [ ] 整书默认引擎：`knitr`（R 为主）还是 `jupyter`（Python 为主）？建议 `knitr`，保持原书叙事，对比段用 tabset 局部混编。
- [ ] 是否在本机装 Julia + `IJulia.jl` 并注册 Jupyter kernel？若不装，Julia chunk 只能 `eval: false` 静态展示，对比能力打折扣。
- [ ] 三语言共用数据格式：是否把 `data/hongloumeng.rda` 同时导出 `parquet`/`csv`，避免 Python/Julia 各装一个 R 格式读取库？
- [ ] 图表风格是否强行统一（统一调色板、字体、尺寸），还是允许三语言原生风格并存以体现差异？
- [ ] 对比段组织方式：每个主题都做三语言，还是只在词频/tf-idf/LDA 等关键节点做？
- [ ] 是否新增一章附录专门做三语言实现差异总结（代码行数、运行时间、依赖数量、结果一致性）？
- [ ] `reanalysis-hongloumeng.py` 是否拆解进书的 Python tabset，还是保留为独立脚本并在书中引用？
