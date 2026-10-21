# cash-notess-rates

Cash Notess'in Pro'daki **canlı kur** feed'i. Zamanlanmış bir GitHub Actions işi
ECB, TCMB ve altın spot fiyatını çeker, tek bir statik `rates.json` üretir ve
GitHub Pages'te yayımlar. Sunucu yoktur, anahtar yoktur; uygulama günde en çok bir
kez bu dosyayı indirir.

Kural ve biçim: ana depoda `documents/models/account/master/exchangeRates.md` —
Canlı Kur (Pro).

## Kurulum (bir kez)

1. GitHub'da **public** bir depo aç: `cash-notess-rates`.
2. Bu klasörün içeriğini (bu README, `build_feed.py`, `.github/`) deponun köküne koy ve push et.
3. Depo → Settings → Pages → **Source: GitHub Actions**.
4. Actions → *Publish rates* → **Run workflow** ile ilk yayını elle başlat.
5. `https://yasintuncel.github.io/cash-notess-rates/rates.json` açılıyorsa hazırdır.
   Kullanıcı adı ya da depo adı farklıysa uygulamadaki `LiveRates.feedUrl`'ü güncelle.

Sonrasında iş günlerinde 15:15 UTC'de kendiliğinden yenilenir.

## Biçim

```json
{
  "version": 1,
  "updatedAt": "2026-10-20T15:15:02+00:00",
  "base": "USD",
  "approximate": ["CMH", "CYR", "GAU", "TAM", "YRM"],
  "sources": ["ECB", "TCMB", "gold-api.com"],
  "rates": { "USD": 1.0, "TRY": 41.9, "EUR": 0.86, "XAU": 0.00024, "GAU": 0.0075, "CYR": 0.0047 }
}
```

`rates[c]` = **1 USD kaç `c`**. Uygulama `1 c = rates[ana] / rates[c]` ana para hesaplar.

| Kod | Ne | Not |
| :-- | :-- | :-- |
| `XAU` | Altın, troy ons | spot |
| `GAU` | Gram altın (24 ayar) | ons ÷ 31,1035 |
| `CYR` · `YRM` · `TAM` · `CMH` | Çeyrek · Yarım · Tam · Cumhuriyet altını, **adet** | saf altın içeriğinden; işçilik dahil değil, **yaklaşık** |

Bir kaynak düşerse diğerleriyle yazılır; hepsi düşerse iş başarısız olur ve önceki
yayın yerinde kalır.
