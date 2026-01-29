from __future__ import annotations
import argparse
import sqlite3
from ft_graph.build import compute_edges
from ft_graph.dgs import export_dgs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--graph-name", default="players")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    edges = compute_edges(con)
    export_dgs(con, edges, args.out, graph_name=args.graph_name)
    print(f"Wrote {args.out} with {len(edges)} edges")

if __name__ == "__main__":
    main()
