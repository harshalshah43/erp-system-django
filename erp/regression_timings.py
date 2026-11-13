"""Time each stock page against a running server (regression testing).

    python regression_timings.py http://127.0.0.1:8001 PRODUCT_ID DOCUMENT_ID

PRODUCT_ID: any regression product (the save test also uses the next two ids).
DOCUMENT_ID: any stock document. Each page is requested 3 times; the median and
the slowest time are printed. The save test posts real documents, so only run
this against the regression database.
"""
import http.cookiejar
import json
import re
import statistics
import sys
import time
import urllib.request

base, pid, doc = sys.argv[1], sys.argv[2], sys.argv[3]
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def hit(path, data=None, headers=None):
    req = urllib.request.Request(base + path, data=data, headers=headers or {})
    t = time.perf_counter()
    try:
        with opener.open(req, timeout=600) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(), e.code
    return time.perf_counter() - t, status, body


PAGES = [
    ("Home (all products)", "/core/home/"),
    ("Search: empty, page 1", "/core/product-search/?q=&page=1"),
    ("Search: 'Drill', page 1", "/core/product-search/?q=Drill&page=1"),
    ("Search: 'Drill', page 40", "/core/product-search/?q=Drill&page=40"),
    ("Search: by ID", f"/core/product-search/?q={pid}"),
    ("Item history, page 1", f"/core/products/{pid}/history/"),
    ("Item history, page 20 (last)", f"/core/products/{pid}/history/?page=20"),
    ("Documents: All, page 1", "/core/documents/"),
    ("Documents: Incoming", "/core/documents/?direction=in"),
    ("Documents: Outgoing", "/core/documents/?direction=out"),
    ("Documents: Outgoing + type", "/core/documents/?direction=out&kind=TXN"),
    ("Documents: page 20,000", "/core/documents/?page=20000"),
    ("Document detail", f"/core/documents/{doc}/"),
    ("Stock Transaction page", "/core/stock-transaction/"),
    ("Stock Take page", "/core/stock-take/"),
]

print(f"{'Page':32} {'status':>6} {'median':>9} {'max':>9} {'size':>10}")
for name, path in PAGES:
    runs = [hit(path) for _ in range(3)]
    times = [t for t, _, _ in runs]
    t0, status, body = runs[-1]
    print(f"{name:32} {status:>6} {statistics.median(times):>8.3f}s {max(times):>8.3f}s {len(body)/1024:>8.0f} KB")

# Saving a transaction: CSRF token from the page, then 3 POSTs of a 3-line document.
_, _, page = hit("/core/stock-transaction/")
token = re.search(rb"'X-CSRFToken': '([^']+)'", page).group(1).decode()
times = []
for _ in range(3):
    payload = json.dumps({"note": "timing", "lines": [
        {"product": int(pid), "type": "IN", "quantity": 1},
        {"product": int(pid) + 1, "type": "IN", "quantity": 1},
        {"product": int(pid) + 2, "type": "IN", "quantity": 1},
    ]}).encode()
    t, status, body = hit("/core/stock-transaction/", payload,
                          {"Content-Type": "application/json", "X-CSRFToken": token,
                           "Referer": base + "/core/stock-transaction/"})
    times.append(t)
print(f"{'Save 3-line transaction':32} {status:>6} {statistics.median(times):>8.3f}s {max(times):>8.3f}s")
