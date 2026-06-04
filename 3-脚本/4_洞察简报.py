#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洞察草稿数据简报（Stage 5 前置）
=========================================
作用：把所有聚合数据浓缩成 1-2 KB 的纯文本简报，
      供 Claude 在生成 overall.json + insights.json 草稿时阅读。

用法：python3 insights_brief.py > /tmp/insights_brief.txt
      然后 Claude 用 read_file 工具读这个简报。

为什么要这一步？
  records.json 1.8 MB，直接喂给 Claude 浪费 token。
  这个脚本把所有聚合表浓缩成可读简报，让 Claude 高效产出洞察。
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"  # 脚本在 3-脚本/，data 在项目根


def load(name):
    p = DATA_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def fmt_w(gmv):
    """格式化为 X.X 万"""
    return f"¥{gmv / 10000:.1f}w"


def main():
    print("=" * 60)
    print("【洞察草稿数据简报】")
    print("=" * 60)

    # 1. 总览（来自 stats.json）
    stats = load("stats.json")
    if stats:
        print("\n## 1. 品类总览（按 GMV 排序）")
        items = sorted(stats.items(), key=lambda x: -x[1]["total_gmv"])
        for cat, s in items:
            print(f"  {cat:<14} {s['count']:>5} SKU · 销量 {s['total_sales']:>10,} · GMV {fmt_w(s['total_gmv']):>12}")

    # 2. 全局 TOP 口味（来自 flavor_stats.json）
    flavor = load("flavor_stats.json")
    if flavor:
        print("\n## 2. 跨品类 TOP 10 口味")
        for f in flavor.get("global_top_flavors", [])[:10]:
            print(f"  - {f['flavor']:<10} GMV {fmt_w(f['total_gmv'])}")

        print("\n## 2.1 各品类 TOP 3 口味")
        for cat, flavors in list(flavor.get("by_category", {}).items())[:10]:
            top3 = flavors[:3]
            if not top3:
                continue
            line = " | ".join([f"{f['flavor']}({fmt_w(f['gmv'])})" for f in top3])
            print(f"  [{cat}] {line}")

    # 3. 全局 TOP 场景
    scene = load("scene_stats.json")
    if scene:
        print("\n## 3. 跨品类 TOP 10 场景")
        for s in scene.get("global_top_scenes", [])[:10]:
            print(f"  - {s['scene']:<10} GMV {fmt_w(s['total_gmv'])}")

    # 4. 原料热度榜
    ingred = load("ingredient_trends.json")
    if ingred:
        print("\n## 4. TOP 20 原料热度榜")
        for r in ingred.get("top_ingredients", [])[:20]:
            cats = "/".join(r.get("appears_in_cats", [])[:3])
            print(f"  - {r['ingredient']:<10} GMV {fmt_w(r['total_gmv'])} · {r['sku_count']:>3}SKU · 跨{r['cross_cat_count']}品类({cats})")

    # 5. 品类集中度
    brand = load("brand_concentration.json")
    if brand:
        print("\n## 5. 品类集中度（TOP5 品牌占比）")
        items = sorted(brand.items(), key=lambda x: -x[1]["top5_share"])
        for cat, info in items:
            top1 = info["top5"][0] if info["top5"] else None
            print(f"  [{cat}] TOP5 占 {info['top5_share']:>5.1f}% · 共 {info['brand_count']:>4} 品牌"
                  + (f" · 头部={top1['brand']}" if top1 else ""))

    # 6. 卖点 TOP
    sp = load("selling_point_trends.json")
    if sp:
        print("\n## 6. TOP 15 卖点")
        for s in sp.get("top_selling_points", [])[:15]:
            print(f"  - {s['selling_point']:<14} GMV {fmt_w(s['total_gmv'])} · {s['sku_count']:>3}SKU")

    # 7. 每个品类的 GMV TOP 3 商品（让 LLM 写品类洞察时有具体抓手）
    records = load("records.json")
    if records:
        print("\n## 7. 各品类 GMV TOP 3 商品（含 attrs.product）")
        from collections import defaultdict
        by_cat = defaultdict(list)
        for r in records:
            by_cat[r["cat"]].append(r)

        for cat in sorted(by_cat.keys(), key=lambda c: -sum(r["gmv"] for r in by_cat[c])):
            top3 = sorted(by_cat[cat], key=lambda r: -r["gmv"])[:3]
            print(f"\n  ── {cat} ──")
            for r in top3:
                attrs = r.get("attrs") or {}
                product = attrs.get("product") or "?"
                flavors = ",".join(attrs.get("flavor") or [])
                print(f"    [{fmt_w(r['gmv']):>10}] {product:<10} | {r['name'][:40]}")
                if flavors:
                    print(f"               口味: {flavors}")

    print("\n" + "=" * 60)
    print("END · 用 Claude 把以上简报转换为 overall.json + insights.json 草稿")
    print("=" * 60)


if __name__ == "__main__":
    main()
