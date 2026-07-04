# Julia FMM 分词器（正向最大匹配）
# 词典来自 jieba 的 dict.txt（data/jieba_dict.txt），纯数据，非跨语言调用。
# 精度低于 R jiebaR / Python jieba（无 HMM、无新词发现），仅用于教学对比。

function load_dict(path::String)
    words = Dict{String,Int}()
    for line in eachline(path)
        parts = split(line, ' ')
        if length(parts) >= 2
            w = parts[1]
            f = tryparse(Int, parts[2])
            if !isnothing(f) && !isempty(w)
                words[w] = f
            end
        end
    end
    return words
end

is_cjk(ch::Char) = let c = codepoint(ch)
    0x4E00 <= c <= 0x9FFF  # CJK Unified Ideographs
end

function fmm_segment(text::String, dict::Dict{String,Int}, max_len::Int=5)
    chars = collect(text)
    n = length(chars)
    result = String[]
    i = 1
    while i <= n
        if isspace(chars[i])
            i += 1
            continue
        end
        # 非 CJK（拉丁字母、数字、标点）：连续切为一个 token
        if !is_cjk(chars[i])
            j = i
            while j <= n && !is_cjk(chars[j]) && !isspace(chars[j])
                j += 1
            end
            push!(result, String(chars[i:j-1]))
            i = j
            continue
        end
        # CJK：正向最大匹配
        matched = false
        for l in min(max_len, n-i+1):-1:2
            word = String(chars[i:i+l-1])
            if haskey(dict, word)
                push!(result, word)
                i += l
                matched = true
                break
            end
        end
        if !matched
            push!(result, String(chars[i:i]))
            i += 1
        end
    end
    return result
end

function load_stopwords(path::String)
    Set(strip(line) for line in eachline(path) if !isempty(strip(line)))
end
