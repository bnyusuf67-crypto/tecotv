#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import shutil
import json
from urllib3 import PoolManager
from urllib3.exceptions import HTTPError, TimeoutError
from urllib3.util import Retry
from datetime import datetime

# -------------------- KANAL LİSTESİ --------------------
kanallar = [
    {"slug": "trthaber", "name": "TRT Haber", "youtube_url": "https://www.youtube.com/@trthaber/live"},
    {"slug": "cnnturk", "name": "CNN Turk", "youtube_url": "https://www.youtube.com/@cnnturk/live"},
    {"slug": "ntv", "name": "NTV", "youtube_url": "https://www.youtube.com/@ntv/live"},
    {"slug": "ahaber", "name": "A Haber", "youtube_url": "https://www.youtube.com/@Ahaber/live"},
    {"slug": "haberturk", "name": "Haber Turk", "youtube_url": "https://www.youtube.com/@haberturktv/live"},
    {"slug": "halktv", "name": "Halk TV", "youtube_url": "https://www.youtube.com/@Halktvkanali/live"},
    {"slug": "sozcutelevizyonu", "name": "Sozcu TV", "youtube_url": "https://www.youtube.com/@sozcutelevizyonu/live"},
    {"slug": "tgrthaber", "name": "TGRT Haber", "youtube_url": "https://www.youtube.com/@tgrthaber/live"},
    {"slug": "flashhaber", "name": "Flash Haber", "youtube_url": "https://www.youtube.com/@flashhabertv/live"},
    {"slug": "haberglobal", "name": "Haber Global", "youtube_url": "https://www.youtube.com/@haberglobal/live"},
    {"slug": "tv100", "name": "TV 100", "youtube_url": "https://www.youtube.com/@tv100/live"},
    {"slug": "bloomberght", "name": "Bloomberg HT", "youtube_url": "https://www.youtube.com/@bloomberght/live"},
    {"slug": "benguturk", "name": "Bengu Turk", "youtube_url": "https://www.youtube.com/@tvbenguturk/live"},
    {"slug": "krttv", "name": "KRT TV", "youtube_url": "https://www.youtube.com/@krtcanli/live"},
    {"slug": "ulusalkanal", "name": "Ulusal Kanal", "youtube_url": "https://www.youtube.com/@ulusalkanaltv/live"},
    {"slug": "ulketv", "name": "Ulke TV", "youtube_url": "https://www.youtube.com/@ulketv/live"},
    {"slug": "ekoturk", "name": "Eko Turk", "youtube_url": "https://www.youtube.com/@ekoturktv/live"},
    {"slug": "tv24", "name": "24 TV", "youtube_url": "https://www.youtube.com/@YirmidortTV/live"},
    {"slug": "aspor", "name": "A Spor", "youtube_url": "https://www.youtube.com/@aspor/live"},
    {"slug": "htspor", "name": "HT Spor", "youtube_url": "https://www.youtube.com/@htspor/live"},
    {"slug": "tvnet", "name": "TV Net", "youtube_url": "https://www.youtube.com/@tvnet/live"},
    {"slug": "beinsportshaber", "name": "Bein Spor Haber", "youtube_url": "https://www.youtube.com/@beINSPORTSTurkiye/live"},
    {"slug": "cnbce", "name": "CNBC-e", "youtube_url": "https://www.youtube.com/@cnbce/live"}
]

# -------------------- AYARLAR --------------------
STREAMS_DIR = "streams"
PLAYLIST_FILE = "playlist.m3u"
USER_AGENT = "VLC/3.0.20"
YT_DLP_TIMEOUT = 30  # saniye

# yt-dlp yolunu bul
YT_DLP = shutil.which("yt-dlp")
if not YT_DLP:
    print("❌ yt-dlp bulunamadı! Lütfen yt-dlp'yi kurun: pip install yt-dlp")
    sys.exit(1)

# urllib3 Havuz Yöneticisi (PoolManager) oluşturma
http = urllib3.PoolManager(headers={"User-Agent": USER_AGENT})

# -------------------- FONKSİYONLAR --------------------
def get_live_manifest_url(youtube_url):
    """YouTube canlı yayınından --dump-single-json ile manifest_url adresini çeker."""
    try:
        result = subprocess.run(
            [YT_DLP, "--cookies", "cookies.txt", "--geo-bypass-country", "--xff", "TR", "--dump-single-json", youtube_url],
            capture_output=True,
            text=True,
            timeout=YT_DLP_TIMEOUT
        )
        if result.returncode != 0:
            return None, f"yt-dlp hatası: {result.stderr.strip()}"
        
        video_data = json.loads(result.stdout.strip())
        manifest_url = video_data.get("manifest_url")
        
        if not manifest_url:
            return None, "manifest_url bulunamadı."
            
        return manifest_url, None
    except subprocess.TimeoutExpired:
        return None, "yt-dlp zaman aşımı"
    except Exception as e:
        return None, str(e)

def download_m3u8_content(manifest_url):
    """manifest_url adresine urllib3 ile istek atıp m3u8 içeriğini indirir."""
    try:
        response = http.request("GET", manifest_url, timeout=15.0)
        if response.status == 200:
            # İçeriği string olarak decode edip döndürüyoruz
            return response.data.decode("utf-8"), None
        else:
            return None, f"HTTP Hata Kodu: {response.status}"
    except Exception as e:
        return None, f"urllib3 hatası: {str(e)}"

def write_channel_file(slug, content):
    """İndirilen ham m3u8 içeriğini doğrudan dosyaya yazar."""
    filepath = os.path.join(STREAMS_DIR, f"{slug}.m3u8")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

# -------------------- ANA PROGRAM --------------------
def main():
    os.makedirs(STREAMS_DIR, exist_ok=True)
    ana_m3u = "#EXTM3U\n"
    print("📡 Kanal linkleri ve m3u8 içerikleri toplanıyor...\n")

    for slug, isim, url in kanallar:
        print(f"➡️  {isim} ... ", end="", flush=True)
        
        # 1. Aşama: yt-dlp ile manifest_url'i bul
        manifest_url, hata = get_live_manifest_url(url)
        if manifest_url is None:
            print(f"❌ {hata}")
            continue

        # 2. Aşama: urllib3 ile m3u8 içeriğini indir
        m3u8_iceriği, hata = download_m3u8_content(manifest_url)
        if m3u8_iceriği is None:
            print(f"❌ İçerik indirilemedi ({hata})")
            continue

        # 3. Aşama: İndirilen içeriği lokal m3u8 dosyası olarak kaydet
        write_channel_file(slug, m3u8_iceriği)

        # 4. Aşama: Ana playlist dosyasına manifest_url linkini ekle
        ana_m3u += f'#EXTINF:-1 tvg-name="{isim}" group-title="Canlı" http-user-agent="{USER_AGENT}",{isim}\n{manifest_url}\n'
        print("✅ İçerik İndirildi & Kaydedildi")

    # Ana playlist'i kaydet
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(ana_m3u)

    print(f"\n📁 Dosyalar '{STREAMS_DIR}/' klasörüne ve '{PLAYLIST_FILE}' dosyasına kaydedildi.")
    git_push()

if __name__ == "__main__":
    main()
