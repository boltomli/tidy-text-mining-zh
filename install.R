#!/usr/bin/env Rscript
# 一次性安装本项目所需的全部 R 包。
# 用法：Rscript install.R
#
# 说明：
# - CRAN 包走 install.packages，已装的跳过。
# - jiebaR / jiebaRD 已从 CRAN 移除，需从 GitHub 源码编译（依赖 Rtools + Rcpp）。
#   Windows 上需先装 Rtools（scoop install rtools，或 https://cran.r-project.org/bin/windows/Rtools/）。
# - mqxsr（明清小说数据）从作者 GitHub 装。
# - mallet / coreNLP / cleanNLP 运行时还需要 Java（rJava）。本脚本不装 Java。

repos <- "https://cloud.r-project.org"

cran_pkgs <- c(
  "dplyr", "tidytext", "stringr", "tidyr", "ggplot2", "gutenbergr",
  "janeaustenr", "showtext", "methods", "scales", "ggraph", "igraph",
  "widyr", "topicmodels", "broom", "quanteda", "mallet", "coreNLP",
  "cleanNLP", "sentimentr", "wordcloud", "wordcloud2", "codetools",
  "purrr", "devtools", "remotes", "Rcpp", "rJava"
)

missing <- cran_pkgs[!vapply(cran_pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  message("Installing from CRAN: ", paste(missing, collapse = ", "))
  install.packages(missing, repos = repos, dependencies = TRUE)
} else {
  message("All CRAN packages already installed.")
}

# jiebaR / jiebaRD 已从 CRAN 移除，从 GitHub 源码编译
if (!requireNamespace("jiebaRD", quietly = TRUE)) {
  message("Installing jiebaRD from GitHub (qinwf/jiebaRD)...")
  remotes::install_github("qinwf/jiebaRD", upgrade = "never")
}
if (!requireNamespace("jiebaR", quietly = TRUE)) {
  message("Installing jiebaR from GitHub (qinwf/jiebaR)...\n",
          "  需要 Rtools（Windows）或编译工具链（macOS/Linux）。")
  remotes::install_github("qinwf/jiebaR", upgrade = "never", dependencies = TRUE)
}

# mqxsr：明清小说数据集
if (!requireNamespace("mqxsr", quietly = TRUE)) {
  message("Installing mqxsr from GitHub (boltomli/mingqingxiaoshuor)...")
  remotes::install_github("boltomli/mingqingxiaoshuor", upgrade = "never")
}

message("\nDone. Verify with:\n",
        "  Rscript -e 'for (p in c(\"jiebaR\",\"mqxsr\",\"quanteda\",\"topicmodels\")) cat(p, \":\", as.character(packageVersion(p)), \"\\n\")'")
