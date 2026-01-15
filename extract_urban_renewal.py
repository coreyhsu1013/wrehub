import camelot
import pandas as pd
from pathlib import Path

PDF_PATH = Path("data/urban_renewal.pdf")
OUT_CSV = Path("data/urban_renewal_raw.csv")

def main():
    print("Reading PDF:", PDF_PATH)

    tables = camelot.read_pdf(
        str(PDF_PATH),
        pages="all",
        flavor="lattice",   # 表格線型 PDF 用 lattice
    )

    print("Tables found:", tables.n)

    dfs = []
    for i, t in enumerate(tables):
        df = t.df
        df["__table_index__"] = i
        dfs.append(df)

    all_df = pd.concat(dfs, ignore_index=True)

    all_df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print("Saved:", OUT_CSV)


if __name__ == "__main__":
    main()



