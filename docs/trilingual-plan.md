# 三语言对照实现规划（R / Python / Julia）

## 1. 目标与非目标

**目标**：在书中逐章对照 R、Python、Julia 三种实现，每个语言用各自**原生库**完成同样的分析，输出可执行、可对比。

**非目标**：
- 不追求三种语言结果完全一致（分词词典、随机种子、数值精度会有差异，反而作为对比点呈现）。
- 不替换现有 R 章节，R 章节保持主线。

## 2. 数据：统一格式导出

当前数据是 R 的 `.rda` 格式，Python/Julia 各装一个读取库（pyreadr / RData.jl）才能读。为消除这部分非原生依赖，先一次性把数据导出为通用格式：

- **格式选 parquet**（保留类型、列名、比 csv 小）；csv 作为 fallback。
- **导出脚本** `data/export-common.R`：读取所有 `.rda`，写出 `data/common/<name>.parquet`（及 `.csv`）。
- 三语言都从 `data/common/` 读：
  - R：`arrow::read_parquet()`（或保留原 .rda）
  - Python：`pandas.read_parquet()`（pyarrow，已在 venv）
  - Julia：`Parquet2.jl` 或 `Arrow.jl`

涉及数据集：`hongloumeng`、`hongloumeng_en`、`books`（明清小说）、`sanyan`、`zibuyu`、`kjv`、`afinn`、`nrc`、`loughran`、`stem`、`stock_articles`。

## 3. 每语言原生库映射（按任务）

| 任务 | R（已有） | Python（已有 venv） | Julia（待装） |
|---|---|---|---|
| 数据框/tidy | dplyr, tidyr | pandas | DataFrames.jl ✓ |
| 英文分词 | tokenizers/unnest_tokens | str.split / nltk | Base.split / TextAnalysis.jl |
| 中文分词 | jiebaR | jieba | **见 §4** |
| 词频/count | dplyr::count | value_counts | StatsBase / combine(groupby) |
| 停止词 | tidytext::stop_words | 自载 | 自载（同文件） |
| tf-idf | tidytext::bind_tf_idf | sklearn TfidfVectorizer | 手动（DataFrames + 广播） |
| 情感词典 | tidytext::get_sentiments | 自载 dict | 自载（CSV/DataFrames） |
| n-gram | tidytext ngrams | nltk/sklearn ngrams | 手动 bigrams |
| 网络/共现 | ggraph + igraph + widyr | networkx | Graphs.jl + GraphMakie.jl |
| DTM | tidytext::cast_dtm, quanteda | sklearn CountVectorizer + scipy.sparse | SparseArrays + TextAnalysis.jl |
| LDA | topicmodels::LDA, mallet | sklearn LatentDirichletAllocation | TopicModels.jl / TextAnalysis.jl |
| 绘图 | ggplot2 | matplotlib/seaborn | CairoMakie.jl ✓ |
| 词云 | wordcloud2 | wordcloud | WordCloud.jl（待查） |

原则：**方法用原生库，不用 PythonCall/reticulate/JuliaCall 跨语言调用**。数据读取用各语言的 parquet/arrow 库（算 I/O 不算方法）。

## 4. Julia 中文分词（关键难点）

Julia 没有官方维护的 jieba 等价物。选项：

**调研结论（2026-07-04）**：Julia 生态无可用现代中文分词包。
- `cuiweiqiang/Jieba.jl`：2015 年 Julia 0.3 时代，`REQUIRE` + C++(CppJieba) 绑定 + `Pkg.clone`，无 `Project.toml`，Julia 1.12 不兼容，弃用。
- General 注册表无 `Jieba`，`WordTokenizers.jl` / `TextAnalysis.jl` 无中文 tokenizer。

**采纳方案：纯 Julia FMM（正向最大匹配）+ jieba 词典文件**。
- 词典用 jieba 自带 `dict.txt`（~35 万词，5MB），复制到 `data/jieba_dict.txt`。词典是纯数据，非跨语言调用。
- FMM 算法 ~30 行 Julia，精度低于 jieba 的 HMM/混合模型（无新词发现、无 HMM），但可复现、纯原生。
- 章节里注明"Julia 用纯 FMM 分词，精度低于 R jiebaR / Python jieba，差异主要在未登录词；生产应接 cppjieba 或训练模型"。

## 5. 书结构与执行引擎（核心决策）

三种语言要在同一节里对照展示，有两条路：

### 方案甲：单文件 panel-tabset，knitr 引擎 + 跨语言桥
- 文件 `engine: knitr`。`{r}` 原生 R；`{python}` 走 reticulate（Python 原生库）；`{julia}` 走 JuliaCall（Julia 原生库）。
- 用 `::: panel-tabset` 三标签页并排，HTML 切换、PDF 顺序展开。
- **优点**：R 章节几乎不动；一本书、一份目录；对照最直观。
- **缺点**：Python/Julia 经 R 桥执行（reticulate/JuliaCall），启动慢、偶有兼容坑；"原生库"满足了，但执行宿主是 R。
- **成本**：装 reticulate、JuliaCall；每章插入 Python/Julia tabset。

### 方案乙：单文件 panel-tabset，jupyter 引擎 + IRkernel
- 文件 `engine: jupyter`。`{python}` 原生 ipykernel；`{julia}` 原生 IJulia；`{r}` 走 IRkernel（R 原生库）。
- **优点**：三语言都原生内核，无 R 桥。
- **缺点**：**所有 R chunk 要重写**（knitr 的 `dependson`/`cache`/`opts_chunk$set` 在 jupyter 下不工作）；IRkernel 要装；R 章节大改。
- **成本**：高（重写 6 章 R chunk）。

### 方案丙：独立分语言章节
- R 章节不动（knitr）；为每章新增 `XX-...-python.qmd`（engine: jupyter）和 `XX-...-julia.qmd`（engine: jupyter）。
- **优点**：每个文件单引擎、最干净；R 零改动；Python/Julia 原生执行。
- **缺点**：对照不在同一视图（要翻章）；书变厚 3 倍。
- **成本**：中等（写 6×2 个新章节）。

## 6. 推荐与实施顺序

推荐 **方案甲（knitr + panel-tabset + reticulate/JuliaCall）**：
- 满足"原生库"（Python 用 jieba/pandas，Julia 用 DataFrames/CairoMakie，只是经 R 桥执行）。
- R 章节几乎不动，对照在同一节，最贴合"对照 R Python Julia"的初衷。
- 若你坚持执行宿主也必须原生（不走 R 桥），则走方案丙（独立 jupyter 章节）。

实施顺序（无论甲丙）：
1. 数据导出 `data/export-common.R` → parquet/csv。
2. 装/确认三语言依赖（reticulate、JuliaCall、Julia 原生分析包、Python 已有）。
3. 解决 Julia 中文分词（§4）。
4. 第 1 章原型：建 panel-tabset（或独立 Julia/Python 章），跑通三语言词频分析，对齐输出。
5. 逐章推进 2→6，每章对照表 + 结果差异说明。
6. 附录：三语言实现差异总结（代码行数、运行时间、依赖数、结果一致性）。

## 7. 已决策

1. **书结构/引擎**：方案丙 — R 章节不动（knitr），为关键章新增独立 Python/Julia `.qmd`（engine: jupyter，原生内核）。
2. **Julia 中文分词**：纯 Julia FMM + jieba `dict.txt`（见 §4 调研结论）。
3. **数据格式**：parquet（主）+ csv（备）。
4. **Python/Julia 范围**：先只做关键章节（Ch1 词频、Ch3 tf-idf、Ch6 LDA），按 R 叙事改写。
