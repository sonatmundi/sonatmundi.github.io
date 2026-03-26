# Sonat Mundi — Instagram Otomasyon Sistemi

## Nasil Calisir

Bu sistem, Sonat Mundi Instagram hesabina (@sonat.mundi) otomatik post ve reel paylasimi yapar.

### Yapi

```
growth/
  instagram_publisher.py    ← Ana script
  instagram/
    posts/
      post_01/              ← Her gun icin bir klasor
        caption.txt         ← Post caption metni
        hashtags.txt        ← Hashtagler (ilk yorum olarak atilir)
        reel_caption.txt    ← Reel caption metni
      post_02/
      ...
      post_09/
    README.md               ← Bu dosya
```

### 9 Gunluk Plan

| Gun | Post | Reel |
|-----|------|------|
| 1 | Carousel (5 slide) — Tanitim | short_528hz |
| 2 | World album cover | short_varanasi |
| 3 | Study album cover | short_cafe_study |
| 4 | Carousel (6 slide) — Koleksiyonlar | short_persian |
| 5 | Moods album cover | short_nostalgia |
| 6 | Frequencies album cover | short_432hz |
| 7 | ASJ Vol.1 album cover | short_gobekli_tepe |
| 8 | Civilizations album cover | short_deep_sleep |
| 9 | — (sadece Reel) | short_velvet_silence |

## Gerekli GitHub Secrets

Asagidaki secret'larin repo ayarlarindan tanimlanmasi gerekir:

| Secret | Aciklama |
|--------|----------|
| `INSTAGRAM_USERNAME` | Instagram kullanici adi (ornek: `sonat.mundi`) |
| `INSTAGRAM_PASSWORD` | Instagram sifresi |
| `GMAIL_ADDRESS` | Bildirim icin Gmail adresi (diger workflow'larla ortak) |
| `GMAIL_APP_PASSWORD` | Gmail App Password (diger workflow'larla ortak) |

**Secret ekleme yolu:** GitHub repo → Settings → Secrets and variables → Actions → New repository secret

## Nasil Tetiklenir

### Manuel Tetikleme (Onerilen)

1. GitHub'da repo sayfasina gidin
2. **Actions** sekmesine tiklayin
3. Sol taraftan **Instagram Publisher** secin
4. **Run workflow** butonuna tiklayin
5. Parametreleri doldurun:
   - **day**: Hangi gun? (`1`-`9` veya `all`)
   - **mode**: `both` (post + reel), `posts-only`, veya `reels-only`
   - **dry_run**: `true` ise gercek yukleme yapilmaz (test icin)
6. **Run workflow** ile baslatin

### Lokal Calistirma

```bash
# Ortam degiskenlerini ayarla
export INSTAGRAM_USERNAME=sonat.mundi
export INSTAGRAM_PASSWORD=sifreniz

# Plani goster
python -m growth.instagram_publisher --show-plan

# Dry-run (test)
python -m growth.instagram_publisher --day 1 --dry-run

# Gercek paylasim
python -m growth.instagram_publisher --day 1

# Sadece postlar
python -m growth.instagram_publisher --day 1 --posts-only

# Tum gunler
python -m growth.instagram_publisher --day all
```

### Otomatik Cron (Devre Disi)

Workflow dosyasinda cron schedule varsayilan olarak devre disidir.
Etkinlestirmek icin `.github/workflows/instagram-publish.yml` dosyasindaki
`schedule` bolumundeki yorum isaretlerini kaldirin.

**UYARI:** Cron kullanimi onerilmez (asagidaki guvenlik notlarina bakin).

## Yeni Post Ekleme

1. `growth/instagram/posts/` altinda yeni klasor olusturun (ornek: `post_10/`)
2. Asagidaki dosyalari ekleyin:
   - `caption.txt` — Post metni
   - `hashtags.txt` — Hashtagler (ilk yorum olarak atilir)
   - `reel_caption.txt` — Reel caption metni (opsiyonel)
3. `growth/instagram_publisher.py` dosyasindaki `PLAN` listesine yeni gunu ekleyin
4. Medya dosyalarini (gorsel/video) uygun klasore yerlestirin

### Caption Format

**Post caption (`caption.txt`):**
```
Baslik veya tanitim metni.

Aciklama satirlari...

Bio'daki linkten dinleyin!
```

**Reel caption (`reel_caption.txt`):**
```
REEL FILE: video_adi.mp4
SOURCE: kaynak bilgisi
---
Gercek caption metni buraya yazilir.

#hashtag1 #hashtag2 #hashtag3
```

`---` isareti oncesi meta bilgi (otomatik olarak kaldirilir), sonrasi caption olarak kullanilir.

## Medya Dosyalari

Buyuk medya dosyalari (gorsel, video) Git reposunda TUTULMAZ.

- **Carousel gorselleri**: Lokal calistirmada `INSTAGRAM_MEDIA_DIR` ortam degiskeni ile belirtilen klasorde olmali
- **Album kapak gorselleri**: `INSTAGRAM_COVERS_DIR` klasorunde veya YouTube thumbnail'den otomatik indirilir (fallback)
- **Reel videolari**: `INSTAGRAM_SHORTS_DIR` klasorunde olmali — otomatik indirilemez, yoksa atlanir

### Ortam Degiskenleri ile Yol Ayarlari

| Degisken | Varsayilan | Aciklama |
|----------|-----------|----------|
| `INSTAGRAM_POSTS_DIR` | `growth/instagram/posts` | Caption dosyalari |
| `INSTAGRAM_MEDIA_DIR` | `media/` | Genel medya klasoru |
| `INSTAGRAM_COVERS_DIR` | `media/covers/` | Album kapak gorselleri |
| `INSTAGRAM_SHORTS_DIR` | `media/shorts/` | Reel videolari |
| `INSTAGRAM_SESSION_FILE` | `ig_session.json` | Session dosyasi |

## Guvenlik Uyarilari

### IP Degisikligi Riski
GitHub Actions runner'lari her calistirmada farkli IP adresi kullanir.
Instagram bu durumu suphe verici bulabilir ve hesabi gecici olarak kilitleyebilir.

**Oneri:** Manuel tetikleme (`workflow_dispatch`) kullanin, otomatik cron'dan kacinin.

### 2FA (Iki Faktorlu Dogrulama)
Instagram hesabinizda 2FA aktifse, GitHub Actions uzerinden giris **calismaz**.
Cozum:
- 2FA'yi gecici olarak kapatin VEYA
- Lokal bilgisayarinizda giris yapin, `ig_session.json` dosyasini olusturun,
  sonra bu dosyayi GitHub Actions cache'ine yukleyin

### Rate Limiting
Script otomatik olarak paylasimlara arasi beklemeler ekler:
- Post arasi: 3-5 dakika
- Post → Reel arasi: 3-5 dakika
- Gun arasi: 10-15 dakika
- Gunluk limit: 5 icerik

Bu sureler ortam degiskenleri ile ayarlanabilir:
- `INSTAGRAM_MIN_DELAY` (varsayilan: 180 saniye)
- `INSTAGRAM_MAX_DELAY` (varsayilan: 300 saniye)
- `INSTAGRAM_DAILY_LIMIT` (varsayilan: 5)

### Session Yonetimi
- Session dosyasi (`ig_session.json`) GitHub Actions cache'inde saklanir
- Her basarili giristen sonra guncellenir
- Session suresi dolmadan yeniden kullanilir (her seferinde yeni giris yapilmaz)
- Session dosyasini ASLA repo'ya commit etmeyin (gitignore'a eklidir)

### Ilk Calistirma Onerileri
1. Once `dry_run: true` ile test edin
2. Tek bir gun ile baslatin (`day: 1`)
3. Basarili olursa diger gunlere devam edin
4. `all` secenegini sadece ihtiyac duydugunuzda kullanin
