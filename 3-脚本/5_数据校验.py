#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
属性抽取质量校验脚本（Stage 3.5）
=========================================
跑完 Stage 3 后用这个脚本看抽取质量
"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent  # 脚本在 3-脚本/，项目根上一级
RECORDS = ROOT / "data" / "records.json"

REQUIRED_FIELDS = ["product", "subcat"]
MULTI_FIELDS = ["flavor", "ingredient", "scene", "selling_point"]
SINGLE_FIELDS = ["brand", "spec", "audience", "promo", "timing"]


def main():
    records = json.loads(RECORDS.read_text(encoding="utf-8"))
    total = len(records)
    print(f"【属性抽取质量校验】总计 {total} 条\n")

    # 1. 含 attrs 字段的覆盖率
    has_attrs = [r for r in records if isinstance(r.get("attrs"), dict)]
    print(f"含 attrs 字段: {len(has_attrs)} 条 ({len(has_attrs) / total * 100:.1f}%)")
    if not has_attrs:
        print("❌ 没有 attrs 字段，请先跑 Stage 3 属性抽取")
        return

    # 2. 必填字段非空率
    print("\n[必填字段非空率]")
    for f in REQUIRED_FIELDS:
        valid = sum(1 for r in has_attrs if r["attrs"].get(f))
        rate = valid / len(has_attrs) * 100
        flag = "✅" if rate >= 95 else "⚠️ "
        print(f"  {flag} {f}: {valid}/{len(has_attrs)} ({rate:.1f}%)")

    # 3. 多选字段平均长度
    print("\n[多选字段平均填充率]")
    for f in MULTI_FIELDS:
        lens = [len(r["attrs"].get(f) or []) for r in has_attrs]
        avg = sum(lens) / len(lens) if lens else 0
        non_empty = sum(1 for x in lens if x > 0)
        rate = non_empty / len(has_attrs) * 100
        print(f"  {f}: 平均 {avg:.2f} 个，非空率 {rate:.1f}%")

    # 4. 单值字段填充率
    print("\n[单值字段填充率]")
    for f in SINGLE_FIELDS:
        valid = sum(1 for r in has_attrs if r["attrs"].get(f))
        print(f"  {f}: {valid}/{len(has_attrs)} ({valid / len(has_attrs) * 100:.1f}%)")

    # 5. 每个多选字段的 TOP 10 值（看分布是否合理）
    print("\n[多选字段 TOP 10 高频值]")
    for f in MULTI_FIELDS:
        c = Counter()
        for r in has_attrs:
            for v in (r["attrs"].get(f) or []):
                c[v] += 1
        print(f"\n  ── {f} ──")
        for v, n in c.most_common(10):
            print(f"    {v}: {n} 次")

    # 6. 头部样本检查（GMV TOP 5 的 attrs）
    print("\n[GMV TOP 5 抽样检查]")
    top5 = sorted(has_attrs, key=lambda r: -r["gmv"])[:5]
    for r in top5:
        print(f"\n  · ¥{r['gmv'] / 10000:.1f}w | {r['name'][:40]}")
        attrs = r["attrs"]
        print(f"    brand={attrs.get('brand')} | product={attrs.get('product')}")
        print(f"    flavor={attrs.get('flavor')} | ingredient={attrs.get('ingredient')}")
        print(f"    scene={attrs.get('scene')} | selling_point={attrs.get('selling_point')}")


if __name__ == "__main__":
    main()
