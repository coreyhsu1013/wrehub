from pathlib import Path
import pandas as pd

PDF_PATH = Path("data/urban_renewal.pdf")
OUT_RAW = Path("data/urban_renewal_raw.csv")
OUT_META = Path("data/urban_renewal_extract_meta.txt")

def try_camelot(flavor: str):
    import camelot
    tables = camelot.read_pdf(
        str(PDF_PATH),
        pages="all",
        flavor=flavor,
        strip_text="\n",
    )
    return tables

def main():
    if not PDF_PATH.exists():
        raise SystemExit(f"❌ PDF not found: {PDF_PATH}")

    OUT_RAW.parent.mkdir(parents=True, exist_ok=True)

    meta_lines = []
    meta_lines.append(f"PDF={PDF_PATH}\n")

    # 1) lattice
    print("📄 Reading PDF:", PDF_PATH)
    print("🧪 Try camelot lattice ...")
    try:
        t1 = try_camelot("lattice")
        meta_lines.append(f"lattice tables={t1.n}\n")
    except Exception as e:
        t1 = None
        meta_lines.append(f"lattice error={repr(e)}\n")

    # 2) stream fallback
    t2 = None
    if not t1 or t1.n == 0:
        print("🧪 Try camelot stream ...")
        try:
            t2 = try_camelot("stream")
            meta_lines.append(f"stream tables={t2.n}\n")
        except Exception as e:
            meta_lines.append(f"stream error={repr(e)}\n")

    tables = None
    flavor_used = None
    if t1 and t1.n > 0:
        tables = t1
        flavor_used = "lattice"
    elif t2 and t2.n > 0:
        tables = t2
        flavor_used = "stream"

    if not tables or tables.n == 0:
        OUT_META.write_text("".join(meta_lines), encoding="utf-8")
        raise SystemExit("❌ No tables extracted (lattice+stream). Next: text-extract fallback.")

    print(f"✅ Tables found: {tables.n} (flavor={flavor_used})")

    dfs = []
    for i, t in enumerate(tables):
        df = t.df
        meta_lines.append(f"{flavor_used} table#{i} shape={df.shape}\n")
        df["__table_index__"] = i
        dfs.append(df)

    all_df = pd.concat(dfs, ignore_index=True)
    all_df.to_csv(OUT_RAW, index=False, encoding="utf-8-sig")
    OUT_META.write_text("".join(meta_lines), encoding="utf-8")

    print("✅ CSV written:", OUT_RAW)
    print("📝 meta:", OUT_META)

if __name__ == "__main__":
    main()
