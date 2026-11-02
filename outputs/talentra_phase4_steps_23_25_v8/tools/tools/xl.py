"""Dependency-free reader for the release workbooks (sheet names and rows)."""
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read(path):
    """Return {sheet name: [rows]} with every cell as text or None."""
    out = {}
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
        rels = {
            r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        }
        for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", NS):
            target = rels[sh.get(RID)].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            rows = []
            for row in ET.fromstring(z.read(target)).iter("{%s}row" % NS["m"]):
                cells = []
                for c in row.findall("m:c", NS):
                    idx = _col(c.get("r"))
                    cells.extend([None] * (idx - len(cells) + 1))
                    v = c.find("m:v", NS)
                    if c.get("t") == "s" and v is not None:
                        cells[idx] = shared[int(v.text)]
                    elif c.get("t") == "inlineStr":
                        cells[idx] = "".join(t.text or "" for t in c.iter("{%s}t" % NS["m"]))
                    elif v is not None:
                        cells[idx] = v.text
                rows.append(cells)
            out[sh.get("name")] = rows
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    book = read(sys.argv[1])
    wanted = sys.argv[2:] or None
    for name, rows in book.items():
        if wanted and not any(w.lower() in name.lower() for w in wanted):
            continue
        print(f"--- {name} ({len(rows)} rows)")
        if wanted:
            for r in rows:
                if any(r):
                    print(" | ".join("" if c is None else str(c)[:170] for c in r))
