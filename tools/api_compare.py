"""Put api_test.py reports side by side, e.g. the same device over USB and over Wi-Fi.

Usage: python tools/api_compare.py snapshots/api-test-A/report.json snapshots/api-test-B/report.json [...] [--md]
Each column is one report, headed by its --via label and TiinyOS version; --md prints a Markdown table.
"""
import json
import sys


def main():
    args = [a for a in sys.argv[1:] if a != "--md"]
    md = "--md" in sys.argv
    if not args:
        sys.exit(__doc__)
    reports = [json.loads(open(p, encoding="utf-8").read()) for p in args]
    heads = [f"{r.get('via', '?')} ({r.get('tiiny_os') or '?'})" for r in reports]
    checks = list(dict.fromkeys(x["check"] for r in reports for x in r["results"]))
    rows = []
    for c in checks:
        cells = []
        for r in reports:
            x = next((x for x in r["results"] if x["check"] == c), None)
            cells.append("-" if not x else x["status"] + ("" if x["status"] == "PASS" else f": {x['detail'][:60]}"))
        differs = len({cell.split(":")[0] for cell in cells if cell != "-"}) > 1
        rows.append((c, cells, differs))
    if md:
        print("| check | " + " | ".join(heads) + " |")
        print("|---|" + "---|" * len(heads))
        for c, cells, differs in rows:
            print(f"| {'**' + c + '**' if differs else c} | " + " | ".join(x.replace("|", r"\|") for x in cells) + " |")
    else:
        w = max(len(c) for c in checks) + 2
        print("check".ljust(w) + "  ".join(h.ljust(30) for h in heads))
        for c, cells, differs in rows:
            print(("* " if differs else "  ") + c.ljust(w - 2) + "  ".join(x[:30].ljust(30) for x in cells))
        print("\n* = differs between the runs")


if __name__ == "__main__":
    main()
