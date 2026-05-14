#!/usr/bin/env python3
"""
《红楼梦》中文文本重新分析 — Python 版
使用 tidy 文本挖掘方法（基于 tidy-text-mining-zh 项目的代码逻辑）
"""

import re
import warnings
from collections import Counter, defaultdict
from typing import List, Tuple

import matplotlib

matplotlib.use("Agg")  # 无 GUI 后端，适合保存图片
import jieba
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from wordcloud import WordCloud

warnings.filterwarnings("ignore")

# ============================================================
# 0. 全局设置
# ============================================================
plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "Noto Sans SC",
    "SimHei",
    "DengXian",
    "sans-serif",
]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = "output"
import os

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 停止词列表（来自 data/stop_word_zh.utf8）
STOP_WORDS = set(
    """
了 的 这 這 那 你 我 她 他 它 之 乎 者 也
""".split()
)

# 更多常见虚词（补充）
EXTRA_STOP_WORDS = {
    "是",
    "在",
    "有",
    "不",
    "与",
    "和",
    "就",
    "都",
    "而",
    "且",
    "或",
    "又",
    "还",
    "便",
    "虽",
    "若",
    "已",
    "正",
    "将",
    "把",
    "被",
    "让",
    "给",
    "对",
    "从",
    "到",
    "去",
    "来",
    "说",
    "道",
    "为",
    "以",
    "于",
    "其",
    "所",
    "故",
    "则",
    "乃",
    "因",
    "但",
    "如",
    "如",
    "可",
    "得",
    "未",
    "无",
    "此",
    "何",
    "与",
    "及",
    "之",
    "乎",
    "者",
    "也",
    "矣",
    "焉",
    "哉",
    "欤",
    "耶",
    "耳",
}

ALL_STOP_WORDS = STOP_WORDS | EXTRA_STOP_WORDS

# 标点符号（用于 bigram 过滤）
PUNCTUATION = set("，。、！？：；（）【】《》「」『』〔〕〈〉“”'‘’．　：·…—～·、")

# 过滤非中文字符的正则：只保留含汉字的 token
CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# WordCloud 中文字体路径
CN_FONT_PATH = "C:\\Windows\\Fonts\\simhei.ttf"
import os as _os

if not _os.path.exists(CN_FONT_PATH):
    CN_FONT_PATH = "C:\\Windows\\Fonts\\msyh.ttc"
if not _os.path.exists(CN_FONT_PATH):
    CN_FONT_PATH = None


# ============================================================
# 1. 数据加载
# ============================================================
def load_data() -> pd.DataFrame:
    """加载《红楼梦》原文本数据"""
    import pyreadr

    result = pyreadr.read_r("data/hongloumeng.rda")
    df = result["hongloumeng"]
    print(f"《红楼梦》原始数据行数: {len(df)}")
    print(f"列: {list(df.columns)}")
    return df


# ============================================================
# 2. 中文分词
# ============================================================
def segment_text(
    text: str,
    stop_words: set = None,
    remove_punct: bool = True,
    keep_chinese_only: bool = True,
) -> List[str]:
    """使用 jieba 分词，返回词列表

    keep_chinese_only: 只保留含中文字符的 token，过滤英文、纯数字、符号等
    """
    words = jieba.lcut(text)
    if remove_punct:
        words = [w for w in words if w not in PUNCTUATION]
    if keep_chinese_only:
        words = [w for w in words if CHINESE_PATTERN.search(w)]
    if stop_words:
        words = [w for w in words if w not in stop_words]
    return words


def segment_series(series: pd.Series, stop_words: set = None) -> pd.Series:
    """对文本 Series 逐行分词"""
    return series.apply(lambda x: " ".join(segment_text(x, stop_words)))


# ============================================================
# 3. 章回检测
# ============================================================
CHAPTER_PATTERN = re.compile(r"^第[一二三四五六七八九十百千零]+回(?:[\s\u3000]|$)")


def detect_chapter(text: str) -> bool:
    """检测一行文本是否为章回标题"""
    return bool(CHAPTER_PATTERN.search(text))


def assign_chapter_groups(df: pd.DataFrame, group_size: int = 20) -> pd.DataFrame:
    """
    按章回分组，每 group_size 回为一部分
    返回添加了 chapter_num 和 chapter_group 列的 DataFrame
    """
    df = df.copy()
    # 检测章回
    chapter_nums = []
    current = 0
    # 收集所有含有章回标题的行
    chapter_title_rows = []
    for i, t in enumerate(df["text"]):
        m = CHAPTER_PATTERN.search(t)
        if m:
            chapter_title_rows.append((i, m.group()))

    # 去重：按顺序只保留每个章回第一次出现的位置
    # 并确保章回号递增（剔除乱入的重复引用）
    deduped = []
    seen = set()
    last_chapter = 0
    for i, ch in chapter_title_rows:
        if ch not in seen:
            # 提取数字部分用于验证顺序
            nums = re.findall(r"[一二三四五六七八九十百千零]+", ch)
            if nums:
                num_str = nums[0]
                # 简单对数字字符串排序：按位置顺序自然已有序
                deduped.append((i, ch))
                seen.add(ch)
                last_chapter += 1

    # 分配章回号
    chapter_nums = [0] * len(df)
    for idx, (row_idx, ch_title) in enumerate(deduped):
        chapter_num = idx + 1  # 1-based chapter number
        # 从该行开始到下一个章回标题行之前，都属于该章回
        start = row_idx
        end = deduped[idx + 1][0] if idx + 1 < len(deduped) else len(df)
        for j in range(start, end):
            chapter_nums[j] = chapter_num

    df["chapter_num"] = chapter_nums
    # 只保留有效章回
    df = df[df["chapter_num"] > 0].copy()

    # 每 group_size 回为一部分
    df["chapter_group"] = df["chapter_num"].apply(
        lambda x: f"第{((x - 1) // group_size) + 1}部分"
    )

    print(f"检测到 {len(deduped)} 个章回")
    print(f"部分分布: {sorted(df['chapter_group'].unique())}")
    return df


# ============================================================
# 4. 词频分析
# ============================================================
def analyze_word_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """
    分词并统计词频（按 chapter_group 分组）
    返回 chapter_words DataFrame
    """
    # 分词
    df = df.copy()
    df["segmented"] = segment_series(df["text"])

    # 展开为词级别
    rows = []
    for _, row in df.iterrows():
        words = row["segmented"].split()
        for w in words:
            rows.append(
                {
                    "chapter": row["chapter_group"],
                    "word": w,
                }
            )

    word_df = pd.DataFrame(rows)

    # 简体化部分名称以便排序
    TR_SIMPLE_MAP = {
        "第1部分": "第1部分",
        "第2部分": "第2部分",
        "第3部分": "第3部分",
        "第4部分": "第4部分",
        "第5部分": "第5部分",
        "第6部分": "第6部分",
    }

    # 统计词频
    chapter_words = (
        word_df.groupby(["chapter", "word"])
        .size()
        .reset_index(name="n")
        .sort_values(["chapter", "n"], ascending=[True, False])
    )

    # 计算各部分的词总数
    total_words = chapter_words.groupby("chapter")["n"].sum().reset_index(name="total")

    chapter_words = chapter_words.merge(total_words, on="chapter")
    return chapter_words


def global_word_frequency(chapter_words: pd.DataFrame, top_n: int = 20):
    """全局词频统计"""
    print("\n=== 词频分析 ===")
    global_freq = (
        chapter_words.groupby("word")["n"]
        .sum()
        .reset_index()
        .sort_values("n", ascending=False)
        .head(top_n)
    )
    print(f"全局最常见词 (Top {top_n}):")
    print(global_freq.to_string(index=False))
    return global_freq


def plot_word_freq_distribution(chapter_words: pd.DataFrame):
    """各部分的词频分布直方图"""
    chapter_words["term_freq"] = chapter_words["n"] / chapter_words["total"]
    plot_df = chapter_words[chapter_words["term_freq"] < 0.001]

    g = sns.FacetGrid(plot_df, col="chapter", col_wrap=2, sharey=False, height=4)
    g.map_dataframe(sns.histplot, x="term_freq", bins=50)
    g.set_axis_labels("词频 (n/total)", "计数")
    g.set_titles(col_template="{col_name}")
    g.fig.suptitle("《红楼梦》各部分的词频分布", y=1.02, fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/01_word_freq_distribution.png", dpi=100)
    plt.close()
    print("[图] 词频分布 → output/01_word_freq_distribution.png")


# ============================================================
# 5. 齐夫定律
# ============================================================
def zipf_law_analysis(chapter_words: pd.DataFrame):
    """检验齐夫定律"""
    print("\n=== 齐夫定律检验 ===")
    freq_by_rank = chapter_words.copy()
    freq_by_rank["term_frequency"] = freq_by_rank["n"] / freq_by_rank["total"]
    # 在每组内计算排名
    freq_by_rank["rank"] = (
        freq_by_rank.groupby("chapter", group_keys=False)["n"]
        .rank(ascending=False, method="first")
        .astype(int)
    )

    # 拟合中间段（排名 10~500）
    subset = freq_by_rank[(freq_by_rank["rank"] > 10) & (freq_by_rank["rank"] < 500)]
    log_rank = np.log10(subset["rank"])
    log_tf = np.log10(subset["term_frequency"])

    slope, intercept = np.polyfit(log_rank, log_tf, 1)
    print(f"齐夫定律拟合斜率: {slope:.3f} (理论值 -1)")
    print(f"截距: {intercept:.3f}")

    # 可视化
    plt.figure(figsize=(9, 6))
    for chapter, grp in freq_by_rank.groupby("chapter"):
        plt.plot(
            grp["rank"], grp["term_frequency"], label=chapter, linewidth=1.1, alpha=0.8
        )

    # 拟合线
    rank_line = np.logspace(np.log10(10), np.log10(500), 100)
    tf_line = 10 ** (intercept + slope * np.log10(rank_line))
    plt.plot(
        rank_line,
        tf_line,
        "k--",
        alpha=0.5,
        label=f"拟合: y={intercept:.2f}x^{slope:.2f}",
    )

    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("排名 (对数)")
    plt.ylabel("词频 (对数)")
    plt.title("《红楼梦》中的齐夫定律（所有词）", fontsize=14)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/02_zipf_law.png", dpi=100)
    plt.close()
    print("[图] 齐夫定律 → output/02_zipf_law.png")

    return freq_by_rank


# ============================================================
# 5b. 齐夫定律 — 仅实体版（人物 + 地点等专有名词）
# ============================================================
def zipf_law_entities_only(df: pd.DataFrame):
    """仅统计人物等实体的齐夫定律"""
    print("\n=== 齐夫定律（仅实体） ===")

    # 用人物名单直接匹配
    char_set = set(MAIN_CHARACTERS)
    entity_counts = Counter()

    for text in df["text"]:
        words = jieba.lcut(text)
        for w in words:
            # 跳过标点和纯英文/数字
            if not CHINESE_PATTERN.search(w):
                continue
            # 检查是否在已知人物名单或为专有名词（以贾/林/薛/史/王/刘等姓氏开头）
            if w in char_set:
                entity_counts[w] += 1
            # jieba 词性标注常把专名标为 nr (人名), ns (地名)
            # 此处依赖预定义列表，更准确

    if not entity_counts:
        print("警告: 未匹配到任何人物实体")
        return

    # === 合并同人异名 ===
    # 中文里人物常以名代全称：宝玉=贾宝玉、凤姐=王熙凤、黛玉=林黛玉
    alias_to_canonical = {
        "黛玉": "林黛玉",
        "寶釵": "薛寶釵",
        "元春": "賈元春",
        "探春": "賈探春",
        "湘雲": "史湘雲",
        "迎春": "賈迎春",
        "惜春": "賈惜春",
        "鳳姐": "王熙鳳",
        "熙鳳": "王熙鳳",
        "寶玉": "賈寶玉",
    }
    merged = Counter()
    for name, cnt in entity_counts.items():
        canonical = alias_to_canonical.get(name, name)
        merged[canonical] += cnt
    entity_counts = merged

    total_entities = sum(entity_counts.values())
    print(f"实体（已合并同人异名）总出现次数: {total_entities}")
    print(f"唯一实体数: {len(entity_counts)}")
    print("\nTop 15 实体（合并后）:")
    for i, (char, cnt) in enumerate(entity_counts.most_common(15), 1):
        print(f"  {i:3d}. {char}: {cnt}次 ({cnt / total_entities * 100:.1f}%)")

    # 计算排名和频率
    sorted_entities = entity_counts.most_common()
    ranks = np.arange(1, len(sorted_entities) + 1)
    freqs = np.array([c for _, c in sorted_entities])
    total = sum(freqs)
    term_freqs = freqs / total

    # 拟合齐夫定律（排名 3~200 段，跳过前几名抖动）
    mask = (ranks > 2) & (ranks < min(200, len(ranks)))
    log_rank = np.log10(ranks[mask])
    log_tf = np.log10(term_freqs[mask])
    slope, intercept = np.polyfit(log_rank, log_tf, 1)
    print(f"\n实体齐夫定律拟合斜率: {slope:.3f} (理论值 -1)")
    print(f"截距: {intercept:.3f}")

    # 可视化
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 左图：齐夫定律曲线
    ax1 = axes[0]
    ax1.plot(ranks, term_freqs, "o-", color="coral", markersize=3, linewidth=1)
    rank_line = np.logspace(np.log10(3), np.log10(min(200, len(ranks))), 100)
    tf_line = 10 ** (intercept + slope * np.log10(rank_line))
    ax1.plot(
        rank_line,
        tf_line,
        "k--",
        alpha=0.6,
        linewidth=1.5,
        label=f"拟合: y={intercept:.2f}x^{slope:.2f}",
    )
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("排名 (对数)")
    ax1.set_ylabel("词频 (对数)")
    ax1.set_title("齐夫定律 — 仅实体（人物）", fontsize=13)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 右图：Top 15 实体柱状图（合并后）
    ax2 = axes[1]
    top15 = entity_counts.most_common(15)
    names = [c for c, _ in top15[::-1]]
    counts = [c for _, c in top15[::-1]]
    colors = [
        "#e74c3c" if i == len(counts) - 1 else "mediumseagreen"
        for i in range(len(counts))
    ]
    ax2.barh(names, counts, color=colors, height=0.7)
    ax2.set_xlabel("出现次数")
    ax2.set_title("Top 15 人物（同人异名已合并）", fontsize=13)
    for i, v in enumerate(counts):
        ax2.text(v + max(counts) * 0.01, i, str(v), va="center", fontsize=8)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/02b_zipf_entities.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("[图] 齐夫定律（仅实体） → output/02b_zipf_entities.png")

    return entity_counts


# ============================================================
# 6. tf-idf 分析
# ============================================================
def tf_idf_analysis(chapter_words: pd.DataFrame):
    """计算并可视化 tf-idf"""
    print("\n=== tf-idf 分析 ===")

    # 计算 tf-idf
    N = chapter_words["chapter"].nunique()  # 文档（部分）数

    # 计算每个词出现在几个部分中
    word_doc_count = (
        chapter_words.groupby("word")["chapter"].nunique().reset_index(name="doc_count")
    )

    chapter_tf_idf = chapter_words.merge(word_doc_count, on="word")
    chapter_tf_idf["tf"] = chapter_tf_idf["n"] / chapter_tf_idf["total"]
    chapter_tf_idf["idf"] = np.log(N / chapter_tf_idf["doc_count"])
    chapter_tf_idf["tf_idf"] = chapter_tf_idf["tf"] * chapter_tf_idf["idf"]

    # 各部分的 Top 10
    top_per_chapter = (
        chapter_tf_idf.sort_values("tf_idf", ascending=False)
        .groupby("chapter")
        .head(10)
        .reset_index(drop=True)
    )

    print("各部分的代表性词 (tf-idf 最高):")
    for ch in sorted(top_per_chapter["chapter"].unique()):
        subset = top_per_chapter[top_per_chapter["chapter"] == ch]
        print(f"  {ch}: {', '.join(subset['word'].tolist())}")

    # 可视化 - 逐个绘图避免拥挤
    chapters_sorted = sorted(top_per_chapter["chapter"].unique())
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    for idx, ch in enumerate(chapters_sorted):
        ax = axes[idx]
        subset = top_per_chapter[top_per_chapter["chapter"] == ch]
        subset = subset.sort_values("tf_idf", ascending=True)
        ax.barh(subset["word"], subset["tf_idf"], color="steelblue", height=0.7)
        ax.set_title(ch, fontsize=12, fontweight="bold")
        ax.set_xlabel("tf-idf", fontsize=9)
        ax.tick_params(axis="y", labelsize=10)
        ax.tick_params(axis="x", labelsize=8)

    # 隐藏多余的子图
    for idx in range(len(chapters_sorted), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(
        "《红楼梦》各部分 tf-idf 最高的词", y=1.02, fontsize=14, fontweight="bold"
    )
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/03_tfidf.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("[图] tf-idf → output/03_tfidf.png")

    return chapter_tf_idf


# ============================================================
# 7. 词云
# ============================================================
def generate_wordcloud(df: pd.DataFrame):
    """生成全书词云"""
    print("\n=== 词云 ===")
    # 分词（过滤停止词，只保留中文）
    all_words = []
    for text in df["text"]:
        all_words.extend(segment_text(text, ALL_STOP_WORDS, keep_chinese_only=True))

    word_counts = Counter(all_words)
    # 过滤出现 < 50 的词
    wordcloud_data = {w: c for w, c in word_counts.items() if c >= 100}

    print(f"词云包含的词数: {len(wordcloud_data)}")
    print(f"字体路径: {CN_FONT_PATH}")

    wc = WordCloud(
        font_path=CN_FONT_PATH,
        width=900,
        height=600,
        background_color="white",
        max_words=120,
        collocations=False,
    ).generate_from_frequencies(wordcloud_data)

    plt.figure(figsize=(12, 9))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title("《红楼梦》词云（过滤停止词）", fontsize=16)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/04_wordcloud.png", dpi=100)
    plt.close()
    print("[图] 词云 → output/04_wordcloud.png")

    return word_counts


# ============================================================
# 8. N-gram 分析（中文二元组）
# ============================================================
def bigram_analysis(df: pd.DataFrame):
    """中文二元组 (bigram) 分析"""
    print("\n=== N-gram 分析（二元组）===")
    sample_df = df.head(500).copy()

    all_bigrams = []
    for text in sample_df["text"]:
        words = segment_text(text)  # 不分词时不加停止词
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            # 过滤虚词
            if w1 not in ALL_STOP_WORDS and w2 not in ALL_STOP_WORDS:
                all_bigrams.append((w1, w2))

    bigram_counts = Counter(all_bigrams)
    print("最常见的二元组（前20）:")
    for i, ((w1, w2), cnt) in enumerate(bigram_counts.most_common(20), 1):
        print(f"  {i:3d}. {w1} {w2}  ({cnt}次)")

    # 可视化
    top_bigrams = bigram_counts.most_common(20)
    fig, ax = plt.subplots(figsize=(10, 8))
    words = [f"{w1}_{w2}" for (w1, w2), c in top_bigrams[::-1]]
    counts = [c for (w1, w2), c in top_bigrams[::-1]]
    ax.barh(words, counts, color="steelblue")
    ax.set_xlabel("出现次数")
    ax.set_title("《红楼梦》最常见二元组（前500行样本）", fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/05_bigram.png", dpi=100)
    plt.close()
    print("[图] 二元组 → output/05_bigram.png")

    return bigram_counts


# ============================================================
# 9. 人物分析
# ============================================================
# 《红楼梦》中的人物名单
MAIN_CHARACTERS = [
    # 金陵十二钗（繁体）
    "林黛玉",
    "黛玉",
    "薛寶釵",
    "寶釵",
    "賈元春",
    "元春",
    "賈探春",
    "探春",
    "史湘雲",
    "湘雲",
    "妙玉",
    "賈迎春",
    "迎春",
    "賈惜春",
    "惜春",
    "王熙鳳",
    "鳳姐",
    "熙鳳",
    "巧姐",
    "李紈",
    "秦可卿",
    # 贾母/长辈（繁体）
    "賈母",
    "王夫人",
    "邢夫人",
    "薛姨媽",
    "劉姥姥",
    # 男主（繁体）
    "賈寶玉",
    "寶玉",
    # 贾府男性（繁体）
    "賈政",
    "賈赦",
    "賈珍",
    "賈璉",
    "賈蓉",
    "賈薔",
    "賈芸",
    "賈環",
    "賈蘭",
    "賈瑞",
    # 丫鬟（繁体）
    "襲人",
    "晴雯",
    "麝月",
    "紫鵑",
    "平兒",
    "鴛鴦",
    "司棋",
    "鶯兒",
    "香菱",
    "金釧",
    "玉釧",
    "小紅",
    "柳五兒",
    "翠縷",
    "雪雁",
    "秋紋",
    "碧痕",
    # 其他（繁体）
    "薛蟠",
    "尤氏",
    "尤二姐",
    "尤三姐",
    "賈雨村",
    "甄士隱",
    "冷子興",
    "張道士",
    "馬道婆",
    "北靜王",
    "蔣玉菡",
    "柳湘蓮",
]

# 去重
MAIN_CHARACTERS = list(dict.fromkeys(MAIN_CHARACTERS))


def character_analysis(df: pd.DataFrame):
    """人物出现频次及共现分析"""
    print("\n=== 人物分析 ===")

    # 为每个人物建立别名映射
    alias_map = {
        "黛玉": "林黛玉",
        "寶釵": "薛寶釵",
        "元春": "賈元春",
        "探春": "賈探春",
        "湘雲": "史湘雲",
        "迎春": "賈迎春",
        "惜春": "賈惜春",
        "鳳姐": "王熙鳳",
        "熙鳳": "王熙鳳",
        "寶玉": "賈寶玉",
    }
    char_set = set(MAIN_CHARACTERS)

    # 按章节统计人物
    df = df.copy()
    # 复用 assign_chapter_groups 的逻辑，但只需 chapter_num
    chapter_nums = [0] * len(df)
    # 找章回标题
    chapter_title_rows = []
    for i, t in enumerate(df["text"]):
        m = CHAPTER_PATTERN.search(t)
        if m:
            chapter_title_rows.append((i, m.group()))
    # 去重
    deduped = []
    seen = set()
    for i, ch in chapter_title_rows:
        if ch not in seen:
            deduped.append((i, ch))
            seen.add(ch)
    # 分配章回号
    for idx, (row_idx, ch_title) in enumerate(deduped):
        chapter_num = idx + 1
        start = row_idx
        end = deduped[idx + 1][0] if idx + 1 < len(deduped) else len(df)
        for j in range(start, end):
            chapter_nums[j] = chapter_num

    df["chapter_num"] = chapter_nums
    df = df[df["chapter_num"] > 0].copy()

    # 逐行分词并统计人物
    char_counter = Counter()
    chapter_char_counts = defaultdict(Counter)

    for _, row in df.iterrows():
        ch = row["chapter_num"]
        words = segment_text(row["text"], ALL_STOP_WORDS)
        words_in_line = set(words) & char_set
        for w in words_in_line:
            canonical = alias_map.get(w, w)
            char_counter[canonical] += 1
            chapter_char_counts[ch][canonical] += 1

    # 全局人物频次
    print("\n主要人物词频统计（Top 30）:")
    for i, (char, cnt) in enumerate(char_counter.most_common(30), 1):
        print(f"  {i:3d}. {char}: {cnt}次")

    # 人物频次图
    top_chars = char_counter.most_common(30)
    fig, ax = plt.subplots(figsize=(10, 10))
    names = [c for c, _ in top_chars[::-1]]
    counts = [c for _, c in top_chars[::-1]]
    ax.barh(names, counts, color="steelblue")
    ax.set_xlabel("出现次数")
    ax.set_title("《红楼梦》主要人物出现频次（Top 30）", fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/06_characters_frequency.png", dpi=100)
    plt.close()
    print("[图] 人物频次 → output/06_characters_frequency.png")

    # 人物在各章的分布（Top 10 人物）
    top_10_chars = [c for c, _ in char_counter.most_common(10)]
    chapter_list = sorted(chapter_char_counts.keys())

    char_chapter_data = []
    for ch in chapter_list:
        for char in top_10_chars:
            char_chapter_data.append(
                {
                    "chapter": ch,
                    "character": char,
                    "count": chapter_char_counts[ch].get(char, 0),
                }
            )

    char_chapter_df = pd.DataFrame(char_chapter_data)

    # 绘制热力图
    pivot = char_chapter_df.pivot_table(
        index="character", columns="chapter", values="count", fill_value=0
    )

    fig, ax = plt.subplots(figsize=(16, 6))
    sns.heatmap(pivot, ax=ax, cmap="YlOrRd", cbar_kws={"label": "出现次数"})
    ax.set_xlabel("章回")
    ax.set_ylabel("人物")
    ax.set_title("《红楼梦》Top 10 人物在各章的分布", fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/07_characters_heatmap.png", dpi=100)
    plt.close()
    print("[图] 人物热力图 → output/07_characters_heatmap.png")

    # 人物共现（同回中出现的人物对）
    print("\n=== 人物共现分析 ===")
    chapter_char_sets = {}
    for ch, cc in chapter_char_counts.items():
        chapter_char_sets[ch] = set(cc.keys())

    cooccur_counts = Counter()
    for ch, chars in chapter_char_sets.items():
        chars_list = sorted(chars)
        for i in range(len(chars_list)):
            for j in range(i + 1, len(chars_list)):
                pair = (chars_list[i], chars_list[j])
                cooccur_counts[pair] += 1

    print("最常见的人物共现对（Top 20）:")
    for i, ((c1, c2), cnt) in enumerate(cooccur_counts.most_common(20), 1):
        print(f"  {i:3d}. {c1} × {c2}: {cnt}回同现")

    return char_counter, chapter_char_counts, cooccur_counts


# ============================================================
# 10. 各章回字数分析
# ============================================================
def chapter_length_analysis(df: pd.DataFrame):
    """分析各章回的字数分布"""
    print("\n=== 各章回字数分析 ===")
    df = df.copy()

    chapter_nums = []
    current = 0
    for t in df["text"]:
        if CHAPTER_PATTERN.search(t):
            current += 1
        chapter_nums.append(current)

    df["chapter_num"] = chapter_nums
    df = df[df["chapter_num"] > 0].copy()

    chapter_lengths = (
        df.groupby("chapter_num")
        .agg(
            raw_chars=("text", lambda x: sum(len(t) for t in x)),
            lines=("text", "count"),
        )
        .reset_index()
    )

    print(f"总章回数: {len(chapter_lengths)}")
    print(
        f"最短章回: 第{chapter_lengths.loc[chapter_lengths['raw_chars'].idxmin(), 'chapter_num']}回 "
        f"({chapter_lengths['raw_chars'].min()}字符)"
    )
    print(
        f"最长章回: 第{chapter_lengths.loc[chapter_lengths['raw_chars'].idxmax(), 'chapter_num']}回 "
        f"({chapter_lengths['raw_chars'].max()}字符)"
    )
    print(
        f"平均每回: {chapter_lengths['raw_chars'].mean():.0f}±{chapter_lengths['raw_chars'].std():.0f}字符"
    )

    # 可视化
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(
        chapter_lengths["chapter_num"],
        chapter_lengths["raw_chars"],
        color="coral",
        marker="o",
        markersize=3,
        linewidth=1,
    )
    ax.axhline(
        chapter_lengths["raw_chars"].mean(),
        color="gray",
        linestyle="--",
        alpha=0.7,
        label="均值",
    )
    ax.fill_between(
        chapter_lengths["chapter_num"],
        chapter_lengths["raw_chars"].mean() - chapter_lengths["raw_chars"].std(),
        chapter_lengths["raw_chars"].mean() + chapter_lengths["raw_chars"].std(),
        alpha=0.15,
        color="gray",
        label="±1σ",
    )
    ax.set_xlabel("章回")
    ax.set_ylabel("字符数")
    ax.set_title("《红楼梦》各章回字数分布", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/08_chapter_length.png", dpi=100)
    plt.close()
    print("[图] 章回字数 → output/08_chapter_length.png")

    return chapter_lengths


# ============================================================
# 11. 关键词在各部分的分布趋势
# ============================================================
def keyword_trend(chapter_words: pd.DataFrame):
    """关键词在各部分的词频变化"""
    print("\n=== 高频词在各部分的分布 ===")
    top_words = ["賈寶玉", "林黛玉", "薛寶釵", "王熙鳳", "賈母", "笑道", "說道"]

    # 使用别名判断
    word_variants = {
        "賈寶玉": ["寶玉", "賈寶玉"],
        "林黛玉": ["黛玉", "林黛玉"],
        "薛寶釵": ["寶釵", "薛寶釵"],
        "王熙鳳": ["鳳姐", "王熙鳳", "熙鳳"],
        "賈母": ["賈母"],
        "笑道": ["笑道"],
        "說道": ["說道"],
    }

    trend_data = []
    for canonical, variants in word_variants.items():
        subset = chapter_words[chapter_words["word"].isin(variants)]
        if subset.empty:
            continue
        grouped = subset.groupby("chapter")["n"].sum().reset_index(name="count")
        # 需要 total
        chapter_totals = chapter_words.groupby("chapter")["total"].first().reset_index()
        grouped = grouped.merge(chapter_totals, on="chapter")
        grouped["term_frequency"] = grouped["count"] / grouped["total"]
        grouped["word"] = canonical
        trend_data.append(grouped)

    trend_df = pd.concat(trend_data, ignore_index=True)

    # 可视化
    fig, ax = plt.subplots(figsize=(10, 6))
    for word, grp in trend_df.groupby("word"):
        ax.plot(
            grp["chapter"], grp["term_frequency"], marker="o", label=word, linewidth=1.5
        )

    ax.set_xlabel("部分")
    ax.set_ylabel("词频")
    ax.set_title("《红楼梦》关键词在各部分的词频变化", fontsize=14)
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/09_keyword_trend.png", dpi=100)
    plt.close()
    print("[图] 关键词趋势 → output/09_keyword_trend.png")


# ============================================================
# 12. 词汇丰富度分析
# ============================================================
def lexical_richness(chapter_words: pd.DataFrame):
    """分析各部分的词汇丰富度（type-token ratio）"""
    print("\n=== 词汇丰富度分析 ===")
    chapter_stats = (
        chapter_words.groupby("chapter")
        .agg(
            tokens=("n", "sum"),
            types=("word", "nunique"),
        )
        .reset_index()
    )
    chapter_stats["ttr"] = chapter_stats["types"] / chapter_stats["tokens"]
    chapter_stats["hapax"] = (
        chapter_words[chapter_words["n"] == 1].groupby("chapter").size().values
    )

    print(chapter_stats.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(chapter_stats["chapter"], chapter_stats["ttr"], color="mediumseagreen")
    ax.set_xlabel("部分")
    ax.set_ylabel("Type-Token Ratio")
    ax.set_title("《红楼梦》各部分词汇丰富度 (TTR)", fontsize=14)
    for i, row in chapter_stats.iterrows():
        ax.text(i, row["ttr"] + 0.0005, f"{row['ttr']:.4f}", ha="center", fontsize=9)
    ax.set_ylim(0, chapter_stats["ttr"].max() * 1.2)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/10_lexical_richness.png", dpi=100)
    plt.close()
    print("[图] 词汇丰富度 → output/10_lexical_richness.png")


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 50)
    print("《红楼梦》文本重新分析 — Python 版")
    print("=" * 50)

    # 1. 加载数据
    df = load_data()

    # 2. 检测章回并分组（每20回一部分，共6部分）
    df_grouped = assign_chapter_groups(df, group_size=20)
    print(f"\n有效章回行数: {len(df_grouped)}")
    print(f"部分分布: {sorted(df_grouped['chapter_group'].unique())}")

    # 3. 词频分析
    chapter_words = analyze_word_frequency(df_grouped)
    print(f"分词后总词条数: {chapter_words['n'].sum()}")

    # 4. 全局词频
    global_word_frequency(chapter_words)

    # 5. 词频分布图
    plot_word_freq_distribution(chapter_words)

    # 6. 齐夫定律
    zipf_law_analysis(chapter_words)

    # 6b. 齐夫定律（仅人物实体）
    zipf_law_entities_only(df)

    # 7. tf-idf
    tf_idf_analysis(chapter_words)

    # 8. 词云
    generate_wordcloud(df)

    # 9. 二元组
    bigram_analysis(df)

    # 10. 人物分析
    character_analysis(df)

    # 11. 章回字数
    chapter_length_analysis(df)

    # 12. 关键词趋势
    keyword_trend(chapter_words)

    # 13. 词汇丰富度
    lexical_richness(chapter_words)

    print("\n" + "=" * 50)
    print("分析完成！")
    print(f"图片保存至: {OUTPUT_DIR}/")
    print("=" * 50)


if __name__ == "__main__":
    main()
