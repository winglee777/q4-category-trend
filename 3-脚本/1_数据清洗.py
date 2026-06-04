#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
25年Q3品类趋势报告 · 数据加工脚本
===================================
输入：source/ 目录下 6 个友望 xls 文件（按品类分文件）
输出：data/records.json + data/stats.json

特殊设计：
  - 友望数据按品类分文件，文件名含品类信息（食品/酒类/生鲜/保健/宠物/预包装）
  - 文件内无「品类」列，需从文件名推断原始品类
  - 推断后再用 category-rules.json 二次清洗

文件名→品类映射：
  食品 → 休闲食品（友望"食品"多为休闲零食）
  酒类 → 酒类
  生鲜 → 生鲜
  保健 → 保健食品/营养补充
  宠物食品 → 宠物生活
  预包装 → 粮油调味（友望"预包装"多为粮油/调味/速食）
"""

import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("缺少 pandas，请先运行: pip install pandas openpyxl xlrd", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 1. 路径与配置
# ============================================================

ROOT = Path(__file__).parent.parent  # 脚本在 3-脚本/，项目根上一级
SOURCE_DIR = ROOT / "0-原始数据"
DEFAULT_OUT = ROOT / "data"
RULES_FILE = ROOT / "category-rules.json"

# 文件名→品类映射（友望导出文件名含品类关键词）
FILENAME_CAT_MAP = {
    "食品": "休闲食品",
    "酒类": "酒类",
    "生鲜": "生鲜",
    "保健": "保健食品/营养补充",
    "宠物食品": "宠物生活",
    "宠物": "宠物生活",
    "预包装": "粮油调味",
}


def infer_cat_from_filename(fname: str) -> str:
    """从文件名推断品类（长关键词优先匹配）"""
    # 按关键词长度降序排列，确保"宠物食品"优先于"食品"匹配
    sorted_map = sorted(FILENAME_CAT_MAP.items(), key=lambda x: -len(x[0]))
    for key, cat in sorted_map:
        if key in fname:
            return cat
    return "未分类"


# ============================================================
# 2. 品类清洗规则
# ============================================================

def load_rules() -> dict:
    if not RULES_FILE.exists():
        print(f"❌ 规则文件不存在: {RULES_FILE}", file=sys.stderr)
        sys.exit(1)
    with RULES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def reclassify(name: str, original_cat: str, rules: dict) -> tuple:
    """
    返回 (final_cat, reason)
    按 _priority 顺序匹配关键词，命中即覆盖。
    """
    if not name:
        return original_cat, "origin"

    priority = rules.get("_priority", [])
    rule_map = rules.get("rules", {})
    excludes = rules.get("exclude_keywords", {})

    for cat in priority:
        keywords = rule_map.get(cat, [])
        excl = excludes.get(cat, [])
        if any(e in name for e in excl):
            continue
        for kw in keywords:
            if kw in name:
                return cat, f"rule:{kw}"

    return original_cat, "origin"


# ============================================================
# 3. 解析 xls
# ============================================================

def parse_xls_files(source_dir: Path, rules: dict) -> tuple:
    """批量解析 source/ 下所有 xls 文件"""
    xls_files = sorted(source_dir.glob("*.xls")) + sorted(source_dir.glob("*.xlsx"))
    if not xls_files:
        print(f"❌ source/ 目录下没有 xls/xlsx 文件", file=sys.stderr)
        sys.exit(1)

    all_records = []
    reclassified_count = 0
    reclassified_examples = []
    seen_names = set()  # 去重：同一商品名只保留 GMV 最高的
    dup_count = 0

    for fpath in xls_files:
        file_cat = infer_cat_from_filename(fpath.name)
        print(f"  · 加载 {fpath.name} → 初始品类: {file_cat}")

        df = pd.read_excel(fpath)
        print(f"    shape: {df.shape}, columns: {list(df.columns)}")

        for _, row in df.iterrows():
            name = str(row.get("商品名称", "") or "").strip()
            if not name or pd.isna(row.get("排行")):
                continue

            # 去重：同一商品名只保留 GMV 最高的
            gmv = float(row.get("销售额", 0) or 0)
            if name in seen_names:
                dup_count += 1
                # 检查是否需要替换（保留 GMV 更高的）
                existing = next((r for r in all_records if r["name"] == name), None)
                if existing and gmv > existing["gmv"]:
                    all_records.remove(existing)
                else:
                    continue
            seen_names.add(name)

            # 二次清洗
            final_cat, reason = reclassify(name, file_cat, rules)
            if reason != "origin" and final_cat != file_cat:
                reclassified_count += 1
                if len(reclassified_examples) < 8:
                    reclassified_examples.append(
                        f"    [{file_cat} → {final_cat}] {name[:50]} ({reason})"
                    )

            sales = int(row.get("销量", 0) or 0)
            live_sales = int(row.get("直播销量", 0) or 0)
            live_gmv = float(row.get("直播销售额", 0) or 0)
            live_count = int(row.get("关联直播数", 0) or 0)
            video_count = int(row.get("关联视频数", 0) or 0)

            rec = {
                "rank": int(row.get("排行", 0) or 0),
                "cat": final_cat,
                "cat_origin": file_cat,
                "cat_reason": reason,
                "name": name,
                "img": str(row.get("商品主图链接", "") or ""),
                "price": str(row.get("商品价格", "") or ""),
                "shop": str(row.get("商品来源", "") or ""),
                "sales": sales,
                "gmv": round(gmv, 2),
                "live_sales": live_sales,
                "live_gmv": round(live_gmv, 2),
                "live_count": live_count,
                "video_count": video_count,
                "in_dm": str(row.get("是否带货中心", "") or ""),
            }
            all_records.append(rec)

    print(f"\n  · 有效记录（去重后）: {len(all_records)}")
    print(f"  · 重复记录跳过: {dup_count}")
    print(f"  · 品类重分类: {reclassified_count} 条")
    if reclassified_examples:
        print("  · 重分类样例:")
        for line in reclassified_examples:
            print(line)

    # 聚合统计
    stats = {}
    for r in all_records:
        cat = r["cat"]
        if cat not in stats:
            stats[cat] = {"count": 0, "total_sales": 0, "total_gmv": 0.0}
        stats[cat]["count"] += 1
        stats[cat]["total_sales"] += r["sales"]
        stats[cat]["total_gmv"] += r["gmv"]

    stats = dict(sorted(stats.items(), key=lambda x: -x[1]["total_gmv"]))
    for cat, s in stats.items():
        s["total_gmv"] = round(s["total_gmv"], 2)

    return all_records, stats


# ============================================================
# 4. 主流程
# ============================================================

def main():
    print("【25年Q3品类趋势 · 数据加工】")
    print(f"  · 数据源: {SOURCE_DIR}")
    print(f"  · 输出: {DEFAULT_OUT}")
    print()

    if not SOURCE_DIR.exists():
        print(f"❌ 数据源目录不存在: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    DEFAULT_OUT.mkdir(parents=True, exist_ok=True)

    # Step 1: 加载规则
    print("[1/3] 加载品类清洗规则")
    rules = load_rules()
    priority = rules.get("_priority", [])
    print(f"  · 品类优先级: {' > '.join(priority)}")
    total_kw = sum(len(v) for v in rules.get("rules", {}).values())
    print(f"  · 关键词总数: {total_kw}")
    print()

    # Step 2: 解析 xls + 二次清洗
    print("[2/3] 解析 xls 并执行品类二次校正")
    records, stats = parse_xls_files(SOURCE_DIR, rules)
    print()

    # 覆盖率
    total = len(records)
    ruled = sum(1 for r in records if r["cat_reason"] != "origin")
    origin = total - ruled
    coverage = ruled / total * 100 if total else 0
    print(f"  · 品类覆盖率: {ruled}/{total} = {coverage:.2f}%")
    print(f"  · 剩余 origin: {origin} 条")
    print()

    # Step 3: 写出 JSON
    print("[3/3] 写出 JSON")
    records_path = DEFAULT_OUT / "records.json"
    stats_path = DEFAULT_OUT / "stats.json"

    with records_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"  · records.json ({records_path.stat().st_size / 1024:.1f} KB)")
    print(f"  · stats.json ({stats_path.stat().st_size / 1024:.1f} KB)")
    print()

    # 品类汇总
    total_gmv = sum(s["total_gmv"] for s in stats.values())
    print(f"✅ 完成。总 GMV: ¥{total_gmv/10000:,.1f}w，品类汇总：")
    for cat, s in stats.items():
        gmv_w = s["total_gmv"] / 10000
        pct = s["total_gmv"] / total_gmv * 100 if total_gmv else 0
        print(f"  - {cat:<16} {s['count']:>5} SKU · GMV ¥{gmv_w:>10,.1f}w ({pct:.1f}%)")

    # 导出 origin 记录供 Step 2 补丁用
    if origin > 0:
        origin_path = DEFAULT_OUT / "origin_records.txt"
        with origin_path.open("w", encoding="utf-8") as f:
            for r in records:
                if r["cat_reason"] == "origin" and r["gmv"] >= 1000:
                    f.write(f"{r['rank']}|{r['cat_origin']}|{r['gmv']}|{r['name']}\n")
        print(f"\n  · origin 记录（GMV≥1k）已导出: {origin_path}")


if __name__ == "__main__":
    main()
