"""durum.yml -> index.html (tek sayfalık ilerleme panosu).

Sayfadaki tüm metin durum.yml dosyasından gelir; HTML'e elle metin yazılmaz.
Üretilen sayfa JavaScript, dış kaynak (CDN, yazı tipi, izleme kodu) kullanmaz.
Çıktı deterministiktir: bugünün tarihi kullanılmaz, yalnızca durum.yml'deki değerler yazılır.

Çalıştırma (bu klasörden):
    .venv\\Scripts\\python.exe yayinla.py
Yerel önizleme:
    .venv\\Scripts\\python.exe -m http.server 8000   ->   http://localhost:8000
"""

import html
import re
import struct
import sys
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

sys.stdout.reconfigure(encoding="utf-8")

KLASOR = Path(__file__).resolve().parent
VERI = KLASOR / "durum.yml"
CIKTI = KLASOR / "index.html"
GRAFIK_KLASOR = KLASOR / "grafikler"

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
ROZETLER = {"tamam": "Tamamlandı", "devam": "Devam ediyor", "bekliyor": "Bekliyor"}

# Yayımlanmaması gereken desenler (kişisel bilgi güvenlik ağı): bulunursa betik durur
YASAK_DESENLER = {
    "e-posta adresi": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "Windows dosya yolu": r"[A-Za-z]:\\",
    "kullanıcı klasörü yolu": r"[\\/]Users[\\/]",
}


def dur(mesaj):
    """Hata mesajını yazıp betiği durdurur (yarım çıktı üretilmez)."""
    print(f"HATA: {mesaj}")
    sys.exit(1)


def e(metin):
    """HTML'e girecek her metin kaçırılır (özel karakterler bozulmasın / kod çalışmasın)."""
    return html.escape(str(metin), quote=True)


def sayi_tr(n):
    """Binlik ayırıcı nokta: 2520859 -> '2.520.859'."""
    return f"{n:,}".replace(",", ".")


def tarih_al(deger, alan):
    """YAML'dan gelen tarihi (date ya da 'YYYY-AA-GG' metni) date nesnesine çevirir."""
    if isinstance(deger, date):
        return deger
    try:
        return date.fromisoformat(str(deger))
    except ValueError:
        dur(f"{alan}: geçerli bir tarih değil -> {deger!r} (beklenen YYYY-AA-GG)")


def tarih_uzun(d):
    return f"{d.day} {AYLAR[d.month - 1]} {d.year}"


def tarih_kisa(d):
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def gerekli(sozluk, anahtar, yol, tur=None):
    """Zorunlu anahtarı kontrol edip değerini döndürür."""
    if not isinstance(sozluk, dict) or anahtar not in sozluk or sozluk[anahtar] in (None, ""):
        dur(f"durum.yml: '{yol}{anahtar}' eksik ya da boş")
    deger = sozluk[anahtar]
    if tur is not None and not isinstance(deger, tur):
        dur(f"durum.yml: '{yol}{anahtar}' beklenen türde değil ({tur.__name__})")
    return deger


def png_boyut(yol):
    """PNG başlığından (IHDR) genişlik ve yüksekliği okur; sayfa yerleşimi kaymasın diye."""
    with open(yol, "rb") as f:
        baslik = f.read(24)
    if baslik[:8] != b"\x89PNG\r\n\x1a\n":
        dur(f"{yol.name}: geçerli bir PNG dosyası değil")
    return struct.unpack(">II", baslik[16:24])


# ----------------------------------------------------------------------
# 1) Oku ve doğrula
# ----------------------------------------------------------------------
ham_metin = VERI.read_text(encoding="utf-8")
for ad, desen in YASAK_DESENLER.items():
    for no, satir in enumerate(ham_metin.splitlines(), start=1):
        if re.search(desen, satir):
            dur(f"durum.yml satır {no}: {ad} bulundu; herkese açık sayfaya girmemeli -> {satir.strip()[:60]}")

veri = YAML(typ="safe").load(ham_metin)

proje = gerekli(veri, "proje", "", dict)
for k in ("ad", "baslik", "tur", "odak"):
    gerekli(proje, k, "proje.")

durum = gerekli(veri, "durum", "", dict)
son_guncelleme = tarih_al(gerekli(durum, "son_guncelleme", "durum."), "durum.son_guncelleme")
hafta = gerekli(durum, "hafta", "durum.", int)
toplam_hafta = gerekli(durum, "toplam_hafta", "durum.", int)
gerekli(durum, "ozet", "durum.")
if not 1 <= hafta <= toplam_hafta:
    dur(f"durum.hafta ({hafta}) 1 ile toplam_hafta ({toplam_hafta}) arasında olmalı")

plan = gerekli(veri, "plan", "", list)
for i, p in enumerate(plan, start=1):
    for k in ("hafta", "tarih", "konu", "durum"):
        gerekli(p, k, f"plan[{i}].")
    if p["durum"] not in ROZETLER:
        dur(f"plan[{i}].durum '{p['durum']}' geçersiz; olabilecekler: {', '.join(ROZETLER)}")

gorusler = gerekli(veri, "danisman_gorusu", "", list)
for i, g in enumerate(gorusler, start=1):
    for k in ("konu", "aciklama", "soru"):
        gerekli(g, k, f"danisman_gorusu[{i}].")

son_liste = gerekli(veri, "son_guncellemeden_bu_yana", "", list)

sayilar = gerekli(veri, "sayilar", "", list)
for i, s in enumerate(sayilar, start=1):
    gerekli(s, "ad", f"sayilar[{i}].")
    gerekli(s, "deger", f"sayilar[{i}].", int)
    if "hedef" in s:
        gerekli(s, "hedef", f"sayilar[{i}].", int)
        if s["hedef"] <= 0 or s["deger"] > s["hedef"]:
            dur(f"sayilar[{i}] ('{s['ad']}'): değer {s['deger']} hedefi {s['hedef']} aşıyor ya da hedef geçersiz")

bulgu = gerekli(veri, "one_cikan_bulgu", "", dict)
for k in ("baslik", "grafik", "aciklama"):
    gerekli(bulgu, k, "one_cikan_bulgu.")
grafik_yolu = (KLASOR / str(bulgu["grafik"])).resolve()
if GRAFIK_KLASOR.resolve() not in grafik_yolu.parents:
    dur(f"one_cikan_bulgu.grafik 'grafikler/' klasörü içinde olmalı -> {bulgu['grafik']}")
if not grafik_yolu.is_file():
    dur(f"one_cikan_bulgu.grafik dosyası yok -> {bulgu['grafik']}")
genislik, yukseklik = png_boyut(grafik_yolu)

kararlar = gerekli(veri, "karar_kaydi", "", list)
for i, k in enumerate(kararlar, start=1):
    tarih_al(gerekli(k, "tarih", f"karar_kaydi[{i}]."), f"karar_kaydi[{i}].tarih")
    gerekli(k, "karar", f"karar_kaydi[{i}].")
    gerekli(k, "gerekce", f"karar_kaydi[{i}].")

# ----------------------------------------------------------------------
# 2) HTML parçaları
# ----------------------------------------------------------------------
yuzde = round(hafta / toplam_hafta * 100)  # takvim çubuğu: hafta / toplam_hafta
takvim = f"Takvim: Hafta {hafta}/{toplam_hafta}"

danisman_html = "\n".join(
    f"""        <li>
          <h3>{e(g['konu'])}</h3>
          <p>{e(g['aciklama'])}</p>
          <p class="soru"><span>Soru</span> {e(g['soru'])}</p>
        </li>"""
    for g in gorusler
)

son_html = "\n".join(f"        <li>{e(m)}</li>" for m in son_liste)

# Sayı kartları: durum.yml'dekiler + karar kaydı sayısı (elle yazılmaz, listeden hesaplanır)
kartlar = list(sayilar) + [{"ad": "Karar kaydı", "deger": len(kararlar)}]
kart_html = []
for s in kartlar:
    if "hedef" in s:
        oran = round(s["deger"] / s["hedef"] * 100)
        deger_metin = f"{sayi_tr(s['deger'])}/{sayi_tr(s['hedef'])}"
        cubuk = (f'<div class="mini" role="progressbar" aria-valuemin="0" aria-valuemax="{s["hedef"]}" '
                 f'aria-valuenow="{s["deger"]}" aria-label="{e(s["ad"])}"><span style="width:{oran}%"></span></div>')
    else:
        deger_metin = sayi_tr(s["deger"])
        cubuk = ""
    kart_html.append(f"""        <div class="kart">
          <div class="deger">{e(deger_metin)}</div>
          <div class="ad">{e(s['ad'])}</div>
          {cubuk}
        </div>""")
kart_html = "\n".join(kart_html)

plan_html = "\n".join(
    f"""        <li{' class="aktif"' if p['hafta'] == hafta else ''}>
          <div class="hafta">Hafta {e(p['hafta'])}<span>{e(p['tarih'])}</span></div>
          <div class="konu">{e(p['konu'])}</div>
          <span class="rozet {e(p['durum'])}">{ROZETLER[p['durum']]}</span>
        </li>"""
    for p in plan
)

karar_html = "\n".join(
    f"""          <tr>
            <td data-label="Tarih">{e(tarih_kisa(tarih_al(k['tarih'], 'karar')))}</td>
            <td data-label="Karar">{e(k['karar'])}</td>
            <td data-label="Gerekçe">{e(k['gerekce'])}</td>
          </tr>"""
    for k in kararlar
)

CSS = """
    :root {
      color-scheme: light dark;
      --zemin: #f6f6f3; --yuzey: #ffffff; --metin: #1c1c1a; --metin2: #55544f; --soluk: #8a8880;
      --cizgi: #dedcd4; --vurgu: #1f5fbf; --vurgu-zemin: #eaf1fd; --cubuk-zemin: #e4e2da;
      --tamam: #1d6b2f; --tamam-zemin: #e3f3e6; --devam: #1f5fbf; --devam-zemin: #eaf1fd;
      --bekliyor: #55544f; --bekliyor-zemin: #ecebe5;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --zemin: #131312; --yuzey: #1c1c1a; --metin: #f0efec; --metin2: #c3c2b7; --soluk: #8f8d85;
        --cizgi: #34332f; --vurgu: #6da7ec; --vurgu-zemin: #1b2838; --cubuk-zemin: #34332f;
        --tamam: #7fd08f; --tamam-zemin: #1a2c1f; --devam: #6da7ec; --devam-zemin: #1b2838;
        --bekliyor: #c3c2b7; --bekliyor-zemin: #2a2a27;
      }
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--zemin); color: var(--metin);
           font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
    main { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }
    section, header { margin-bottom: 32px; }
    h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 4px; }
    h1 span { font-weight: 400; color: var(--metin2); }
    h2 { font-size: 1.25rem; margin: 0 0 12px; }
    h3 { font-size: 1.05rem; margin: 0 0 6px; }
    p { margin: 0 0 8px; }
    .tur { color: var(--vurgu); font-weight: 600; font-size: .9rem; margin-bottom: 4px; }
    .baslik { font-size: 1.05rem; margin-bottom: 6px; }
    .odak, .ozet, footer { color: var(--metin2); }
    .satir { display: flex; flex-wrap: wrap; gap: 6px 20px; margin: 14px 0 8px; font-weight: 600; }
    .cubuk { height: 12px; background: var(--cubuk-zemin); border-radius: 6px; overflow: hidden; }
    .cubuk span, .mini span { display: block; height: 100%; background: var(--vurgu); border-radius: 6px; }
    .danisman { background: var(--vurgu-zemin); border: 2px solid var(--vurgu); border-radius: 12px; padding: 18px 18px 8px; }
    .danisman > p { color: var(--metin2); }
    .danisman ol { list-style: none; counter-reset: sira; margin: 0; padding: 0; }
    .danisman li { counter-increment: sira; background: var(--yuzey); border: 1px solid var(--cizgi);
                   border-radius: 8px; padding: 14px 14px 6px 52px; margin-bottom: 12px; position: relative; }
    .danisman li::before { content: counter(sira); position: absolute; left: 14px; top: 14px; width: 26px; height: 26px;
                           border-radius: 50%; background: var(--vurgu); color: var(--yuzey);
                           font-weight: 700; text-align: center; line-height: 26px; }
    .soru { font-weight: 600; }
    .soru span { background: var(--vurgu); color: var(--yuzey); border-radius: 4px; padding: 1px 6px;
                 font-size: .8rem; margin-right: 4px; }
    ul.liste { margin: 0; padding-left: 20px; }
    ul.liste li { margin-bottom: 6px; }
    .kartlar { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .kart { background: var(--yuzey); border: 1px solid var(--cizgi); border-radius: 10px; padding: 14px; }
    .kart .deger { font-size: 1.7rem; font-weight: 700; line-height: 1.1; }
    .kart .ad { color: var(--metin2); font-size: .9rem; margin-top: 4px; }
    .mini { height: 6px; background: var(--cubuk-zemin); border-radius: 3px; overflow: hidden; margin-top: 10px; }
    figure { margin: 0 0 10px; }
    figure img { width: 100%; height: auto; border: 1px solid var(--cizgi); border-radius: 8px; background: #fcfcfb; }
    ol.plan { list-style: none; margin: 0; padding: 0; }
    ol.plan li { display: grid; grid-template-columns: 110px 1fr auto; gap: 4px 14px; align-items: center;
                 background: var(--yuzey); border: 1px solid var(--cizgi); border-radius: 8px;
                 padding: 10px 14px; margin-bottom: 8px; }
    ol.plan li.aktif { border: 2px solid var(--vurgu); }
    .hafta { font-weight: 700; }
    .hafta span { display: block; font-weight: 400; font-size: .85rem; color: var(--metin2); }
    .rozet { font-size: .8rem; font-weight: 600; padding: 2px 10px; border-radius: 999px; white-space: nowrap; }
    .rozet.tamam { color: var(--tamam); background: var(--tamam-zemin); }
    .rozet.devam { color: var(--devam); background: var(--devam-zemin); }
    .rozet.bekliyor { color: var(--bekliyor); background: var(--bekliyor-zemin); }
    table { width: 100%; border-collapse: collapse; background: var(--yuzey); border: 1px solid var(--cizgi); }
    th, td { text-align: left; vertical-align: top; padding: 10px 12px; border-bottom: 1px solid var(--cizgi); }
    th { font-size: .85rem; color: var(--metin2); background: var(--zemin); }
    td:first-child { white-space: nowrap; }
    footer { font-size: .85rem; border-top: 1px solid var(--cizgi); padding-top: 14px; }
    @media (max-width: 640px) {
      h1 { font-size: 1.5rem; }
      ol.plan li { grid-template-columns: 1fr; }
      .rozet { justify-self: start; }
      thead { position: absolute; left: -9999px; }
      table, tbody, tr, td { display: block; width: 100%; }
      tr { border-bottom: 2px solid var(--cizgi); padding: 6px 0; }
      td { border: 0; padding: 4px 12px; }
      td::before { content: attr(data-label); display: block; font-size: .8rem; color: var(--metin2); font-weight: 600; }
    }
"""

sayfa = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <meta name="color-scheme" content="light dark">
  <title>{e(proje['ad'])} ilerleme panosu</title>
  <style>{CSS}  </style>
</head>
<body>
  <main>
    <header>
      <p class="tur">{e(proje['tur'])}</p>
      <h1>{e(proje['ad'])} <span>ilerleme panosu</span></h1>
      <p class="baslik">{e(proje['baslik'])}</p>
      <p class="odak"><strong>Odak:</strong> {e(proje['odak'])}</p>
      <div class="satir">
        <span>Son güncelleme: {e(tarih_uzun(son_guncelleme))}</span>
        <span>{e(takvim)}</span>
      </div>
      <div class="cubuk" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{yuzde}" aria-label="{e(takvim)}"><span style="width:{yuzde}%"></span></div>
      <p class="ozet">{e(durum['ozet'])}</p>
    </header>

    <section class="danisman" aria-labelledby="b-danisman">
      <h2 id="b-danisman">Danışman görüşü beklenen konular</h2>
      <p>{len(gorusler)} konuda görüşünüz bekleniyor.</p>
      <ol>
{danisman_html}
      </ol>
    </section>

    <section aria-labelledby="b-son">
      <h2 id="b-son">Son güncellemeden bu yana</h2>
      <ul class="liste">
{son_html}
      </ul>
    </section>

    <section aria-labelledby="b-sayilar">
      <h2 id="b-sayilar">Sayılarla ilerleme</h2>
      <div class="kartlar">
{kart_html}
      </div>
    </section>

    <section aria-labelledby="b-bulgu">
      <h2 id="b-bulgu">Öne çıkan bulgu</h2>
      <h3>{e(bulgu['baslik'])}</h3>
      <figure>
        <a href="{e(bulgu['grafik'])}"><img src="{e(bulgu['grafik'])}" width="{genislik}" height="{yukseklik}" alt="Grafik: {e(bulgu['baslik'])}"></a>
      </figure>
      <p>{e(bulgu['aciklama'])}</p>
    </section>

    <section aria-labelledby="b-plan">
      <h2 id="b-plan">{toplam_hafta} haftalık plan</h2>
      <ol class="plan">
{plan_html}
      </ol>
    </section>

    <section aria-labelledby="b-karar">
      <h2 id="b-karar">Karar kaydı</h2>
      <table>
        <thead><tr><th>Tarih</th><th>Karar</th><th>Gerekçe</th></tr></thead>
        <tbody>
{karar_html}
        </tbody>
      </table>
    </section>

    <footer>Bu sayfa durum.yml dosyasından otomatik üretilir. Son güncelleme: {e(tarih_uzun(son_guncelleme))}.</footer>
  </main>
</body>
</html>
"""

# Son kontrol: sayfa dış kaynağa bağlanmamalı, JavaScript içermemeli
if re.search(r'(src|href)\s*=\s*"(https?:)?//', sayfa) or re.search(r"url\(\s*['\"]?(https?:)?//", sayfa):
    dur("üretilen sayfada dış kaynak bağlantısı bulundu")
if re.search(r"<script", sayfa, re.IGNORECASE):
    dur("üretilen sayfada <script> bulundu")

CIKTI.write_text(sayfa, encoding="utf-8", newline="\n")
print(f"Üretildi: {CIKTI.name} ({len(sayfa.encode('utf-8')):,} bayt)")
print(f"  {takvim} (çubuk %{yuzde}) | danışman konusu: {len(gorusler)} | sayı kartı: {len(kartlar)} "
      f"(karar kaydı: {len(kararlar)}) | plan: {len(plan)} hafta | grafik: {bulgu['grafik']} ({genislik}x{yukseklik})")
