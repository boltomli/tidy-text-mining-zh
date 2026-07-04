if (.Platform$OS.type == 'windows') Sys.setlocale('LC_CTYPE', 'Chinese_China.65001')
options(repos = c(CRAN = "https://cran.rstudio.com"))

# execute:false 验证期间（TIDY_TEXT_NOEXEC=1），让 knitr 内联 R 求值出错时
# 静默返回空字符串，避免因 chunk 未执行、对象不存在而中断整本书渲染。
# 开执行后删除 _environment 里的 TIDY_TEXT_NOEXEC=1 即自动停用本守卫。
if (nzchar(Sys.getenv("TIDY_TEXT_NOEXEC")) &&
    requireNamespace("knitr", quietly = TRUE)) {
  orig_inline_exec <- knitr:::inline_exec
  utils::assignInNamespace(
    "inline_exec",
    function(...) tryCatch(orig_inline_exec(...), error = function(e) ""),
    asNamespace("knitr")
  )
}
