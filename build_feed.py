#!/usr/bin/env python3
"""Cash Notess canlı kur feed'i (`documents/models/account/master/exchangeRates.md`
— Canlı Kur).

Kaynakları çeker ve tek bir statik JSON yazar: `rates[c]` = 1 USD kaç `c`.
Uygulama `1 c = rates[ana] / rates[c] ana` hesaplar. Yalnızca standart
kütüphane kullanır; anahtar gerektirmez.

Kaynaklar:
  * ECB günlük referans kurları (EUR tabanlı, ~30 para birimi)
  * TCMB günlük kurları (TRY ve ECB'de olmayanlar; alış/satış ortalaması)
  * Altın ons spot fiyatı (USD) — gram ve ziynet buradan türetilir

Kullanım: python3 build_feed.py out/rates.json
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
GOLD_URL = "https://api.gold-api.com/price/XAU"

TROY_OUNCE_GRAMS = 31.1034768

# Ziynet altınlarının saf altın içeriği (gram). 22 ayar (0,916); işçilik ve
# kuyumcu farkı dahil değildir — uygulama bunları "yaklaşık" etiketler.
ZIYNET_PURE_GRAMS = {
    "CYR": 1.75 * 0.916,   # Çeyrek
    "YRM": 3.50 * 0.916,   # Yarım
    "TAM": 7.00 * 0.916,   # Tam
    "CMH": 7.216 * 0.916,  # Cumhuriyet (Ata)
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "cash-notess-rates/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def ecb_rates() -> dict:
    """1 USD kaç c — ECB'nin EUR tabanlı kurlarından."""
    root = ET.fromstring(fetch(ECB_URL))
    ns = {"e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
    per_eur = {"EUR": 1.0}
    for cube in root.iterfind(".//e:Cube[@currency]", ns):
        per_eur[cube.attrib["currency"]] = float(cube.attrib["rate"])
    usd = per_eur["USD"]
    return {code: rate / usd for code, rate in per_eur.items()}


def tcmb_try_rates() -> dict:
    """1 USD kaç c — TCMB'nin TRY kurlarından (alış/satış ortalaması)."""
    root = ET.fromstring(fetch(TCMB_URL))
    try_per_unit = {}
    for cur in root.iterfind("Currency"):
        code = cur.attrib.get("CurrencyCode")
        unit = float(cur.findtext("Unit") or 1)
        buy = cur.findtext("ForexBuying")
        sell = cur.findtext("ForexSelling")
        if not code or not buy or not sell:
            continue
        try_per_unit[code] = (float(buy) + float(sell)) / 2 / unit
    try_per_usd = try_per_unit["USD"]
    rates = {"TRY": try_per_usd}
    for code, try_per in try_per_unit.items():
        rates[code] = try_per_usd / try_per
    return rates


def gold_rates() -> dict:
    """1 USD kaç ons / gram / ziynet."""
    data = json.loads(fetch(GOLD_URL))
    usd_per_oz = float(data["price"])
    usd_per_gram = usd_per_oz / TROY_OUNCE_GRAMS
    rates = {"XAU": 1 / usd_per_oz, "GAU": 1 / usd_per_gram}
    for code, grams in ZIYNET_PURE_GRAMS.items():
        rates[code] = 1 / (usd_per_gram * grams)
    return rates


def build() -> dict:
    rates = {"USD": 1.0}
    sources = []
    try:
        rates.update(ecb_rates())
        sources.append("ECB")
    except Exception as e:  # noqa: BLE001 — bir kaynak düşse de feed yazılır
        print(f"ECB failed: {e}", file=sys.stderr)
    try:
        tcmb = tcmb_try_rates()
        # TRY daima TCMB'den; ECB'de olmayan kodlar TCMB'den tamamlanır.
        rates["TRY"] = tcmb["TRY"]
        for code, rate in tcmb.items():
            rates.setdefault(code, rate)
        sources.append("TCMB")
    except Exception as e:  # noqa: BLE001
        print(f"TCMB failed: {e}", file=sys.stderr)
    try:
        rates.update(gold_rates())
        sources.append("gold-api.com")
    except Exception as e:  # noqa: BLE001
        print(f"Gold failed: {e}", file=sys.stderr)

    if len(sources) == 0:
        raise SystemExit("All sources failed; previous feed is kept.")

    return {
        "version": 1,
        "updatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "base": "USD",
        "approximate": sorted(["GAU", *ZIYNET_PURE_GRAMS.keys()]),
        "sources": sources,
        "rates": {k: round(v, 10) for k, v in sorted(rates.items())},
    }


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "rates.json"
    feed = build()
    with open(out, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(feed['rates'])} rates from {', '.join(feed['sources'])} to {out}")
