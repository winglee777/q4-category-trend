#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交叉聚合脚本（Stage 4 自动跑）
=========================================
作用：基于 records.json 里的 attrs 字段，计算 5 张交叉聚合表

前置依赖：records.json 必须已经完成 11 维度属性抽取（attrs 字段）

输出：
  data/flavor_stats.json        品类×口味矩阵（GMV 加权）
  data/scene_stats.json         品类×场景矩阵
  data/ingredient_trends.json   原料热度榜
  data/brand_concentration.json 品类×品牌集中度
  data/selling_point_trends.json 卖点频次榜
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent  # 脚本在 3-脚本/，项目根上一级
DATA_DIR = ROOT / "data"
RECORDS_FILE = DATA_DIR / "records.json"


def load_records():
    return json.loads(RECORDS_FILE.read_text(encoding="utf-8"))


def has_attrs(r):
    """跳过没有 attrs 字段的记录"""
    return isinstance(r.get("attrs"), dict)


def aggregate_flavor_x_cat(records):
    """品类 × 口味 GMV 矩阵"""
    matrix = defaultdict(lambda: defaultdict(float))
    flavor_total = defaultdict(float)
    for r in records:
        if not has_attrs(r):
            continue
        cat = r["cat"]
        flavors = r["attrs"].get("flavor") or []
        for fl in flavors:
            matrix[cat][fl] += r["gmv"]
            flavor_total[fl] += r["gmv"]

    # 排序：每个品类内按 GMV 降序
    out = {
        "by_category": {
            cat: sorted(
                [{"flavor": fl, "gmv": round(v, 2)} for fl, v in flavors.items()],
                key=lambda x: -x["gmv"]
            )
            for cat, flavors in matrix.items()
        },
        "global_top_flavors": sorted(
            [{"flavor": fl, "total_gmv": round(v, 2)} for fl, v in flavor_total.items()],
            key=lambda x: -x["total_gmv"]
        )[:20]
    }
    return out


def aggregate_scene_x_cat(records):
    """品类 × 场景 GMV 矩阵"""
    matrix = defaultdict(lambda: defaultdict(float))
    scene_total = defaultdict(float)
    for r in records:
        if not has_attrs(r):
            continue
        scenes = r["attrs"].get("scene") or []
        for sc in scenes:
            matrix[r["cat"]][sc] += r["gmv"]
            scene_total[sc] += r["gmv"]

    return {
        "by_category": {
            cat: sorted(
                [{"scene": sc, "gmv": round(v, 2)} for sc, v in d.items()],
                key=lambda x: -x["gmv"]
            )
            for cat, d in matrix.items()
        },
        "global_top_scenes": sorted(
            [{"scene": sc, "total_gmv": round(v, 2)} for sc, v in scene_total.items()],
            key=lambda x: -x["total_gmv"]
        )[:15]
    }


def aggregate_ingredients(records):
    """原料热度榜（GMV + SKU 双口径）"""
    gmv_map = defaultdict(float)
    sku_map = defaultdict(int)
    cat_map = defaultdict(set)  # 原料出现在哪些品类

    for r in records:
        if not has_attrs(r):
            continue
        ingreds = r["attrs"].get("ingredient") or []
        for ing in ingreds:
            gmv_map[ing] += r["gmv"]
            sku_map[ing] += 1
            cat_map[ing].add(r["cat"])

    rows = [
        {
            "ingredient": ing,
            "total_gmv": round(gmv, 2),
            "sku_count": sku_map[ing],
            "appears_in_cats": sorted(cat_map[ing]),
            "cross_cat_count": len(cat_map[ing])
        }
        for ing, gmv in gmv_map.items()
    ]
    rows.sort(key=lambda x: -x["total_gmv"])
    return {"top_ingredients": rows[:50]}


def aggregate_brand_concentration(records):
    """品类×品牌集中度（每个品类 TOP 5 品牌）"""
    cat_brand = defaultdict(lambda: defaultdict(float))
    for r in records:
        if not has_attrs(r):
            continue
        brand = r["attrs"].get("brand")
        if not brand:
            continue
        cat_brand[r["cat"]][brand] += r["gmv"]

    out = {}
    for cat, brands in cat_brand.items():
        total = sum(brands.values())
        sorted_brands = sorted(brands.items(), key=lambda x: -x[1])[:5]
        out[cat] = {
            "top5": [
                {
                    "brand": b,
                    "gmv": round(g, 2),
                    "share": round(g / total * 100, 1) if total else 0
                }
                for b, g in sorted_brands
            ],
            "top5_share": round(sum(g for _, g in sorted_brands) / total * 100, 1) if total else 0,
            "brand_count": len(brands)
        }
    return out


def aggregate_selling_points(records):
    """卖点频次榜"""
    sp_gmv = defaultdict(float)
    sp_sku = defaultdict(int)
    for r in records:
        if not has_attrs(r):
            continue
        sps = r["attrs"].get("selling_point") or []
        for sp in sps:
            sp_gmv[sp] += r["gmv"]
            sp_sku[sp] += 1

    rows = sorted(
        [
            {"selling_point": sp, "total_gmv": round(g, 2), "sku_count": sp_sku[sp]}
            for sp, g in sp_gmv.items()
        ],
        key=lambda x: -x["total_gmv"]
    )
    return {"top_selling_points": rows[:30]}


def main():
    print("【交叉聚合】Stage 4 ──────────────")
    records = load_records()
    print(f"  · 加载 records: {len(records)} 条")

    has_attr_count = sum(1 for r in records if has_attrs(r))
    print(f"  · 含 attrs 字段: {has_attr_count} 条 ({has_attr_count / len(records) * 100:.1f}%)")

    if has_attr_count == 0:
        print("\n❌ 没有任何记录包含 attrs 字段。")
        print("   请先完成 Stage 3（11 维度属性抽取），再跑本脚本。")
        return

    print("\n[1/5] 品类 × 口味")
    flavor_stats = aggregate_flavor_x_cat(records)
    (DATA_DIR / "flavor_stats.json").write_text(
        json.dumps(flavor_stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    top_fl = flavor_stats["global_top_flavors"][:5]
    print("  · 全局 TOP 5 口味:")
    for f in top_fl:
        print(f"    - {f['flavor']}: ¥{f['total_gmv'] / 10000:.1f}w")

    print("\n[2/5] 品类 × 场景")
    scene_stats = aggregate_scene_x_cat(records)
    (DATA_DIR / "scene_stats.json").write_text(
        json.dumps(scene_stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    top_sc = scene_stats["global_top_scenes"][:5]
    print("  · 全局 TOP 5 场景:")
    for s in top_sc:
        print(f"    - {s['scene']}: ¥{s['total_gmv'] / 10000:.1f}w")

    print("\n[3/5] 原料热度榜")
    ingred = aggregate_ingredients(records)
    (DATA_DIR / "ingredient_trends.json").write_text(
        json.dumps(ingred, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  · TOP 5 原料:")
    for i in ingred["top_ingredients"][:5]:
        print(f"    - {i['ingredient']}: ¥{i['total_gmv'] / 10000:.1f}w · {i['sku_count']} SKU · 跨 {i['cross_cat_count']} 品类")

    print("\n[4/5] 品类 × 品牌集中度")
    brand = aggregate_brand_concentration(records)
    (DATA_DIR / "brand_concentration.json").write_text(
        json.dumps(brand, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  · 各品类 TOP 5 品牌集中度:")
    for cat, info in sorted(brand.items(), key=lambda x: -x[1]["top5_share"])[:5]:
        print(f"    - {cat}: TOP5 占 {info['top5_share']}% (共 {info['brand_count']} 个品牌)")

    print("\n[5/5] 卖点频次榜")
    sp = aggregate_selling_points(records)
    (DATA_DIR / "selling_point_trends.json").write_text(
        json.dumps(sp, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  · TOP 5 卖点:")
    for s in sp["top_selling_points"][:5]:
        print(f"    - {s['selling_point']}: ¥{s['total_gmv'] / 10000:.1f}w · {s['sku_count']} SKU")

    print("\n✅ 所有交叉聚合表已写入 data/")


if __name__ == "__main__":
    main()
