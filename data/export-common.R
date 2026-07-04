#!/usr/bin/env Rscript
# 将 data/*.rda 导出为通用格式（parquet + csv），供 Python/Julia 章节读取。
# 一次性运行：Rscript data/export-common.R

library(arrow)

data_dir <- "data"
common_dir <- "data/common"
dir.create(common_dir, showWarnings = FALSE, recursive = TRUE)

rda_files <- list.files(data_dir, pattern = "\\.rda$", full.names = TRUE)

for (f in rda_files) {
  e <- new.env()
  load(f, envir = e)
  obj_name <- ls(e)[1]
  df <- as.data.frame(get(obj_name, envir = e))
  base <- sub("\\.rda$", "", basename(f))
  parquet_path <- file.path(common_dir, paste0(base, ".parquet"))
  csv_path <- file.path(common_dir, paste0(base, ".csv"))
  tryCatch({
    write_parquet(df, parquet_path)
    write.csv(df, csv_path, row.names = FALSE, fileEncoding = "UTF-8")
    cat(sprintf("exported: %-20s -> %s, %s (%d rows)\n",
                basename(f), basename(parquet_path), basename(csv_path), nrow(df)))
  }, error = function(err) {
    # 非扁平表（如 stock_articles 含 WebCorpus 列），跳过 parquet，仅尝试 csv 或跳过
    cat(sprintf("SKIP:    %-20s -> %s\n", basename(f), conditionMessage(err)))
  })
}

cat("\nDone. All datasets exported to", common_dir, "\n")
