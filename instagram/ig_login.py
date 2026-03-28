"""Instagram session oluşturma scripti — IP blacklist çözümlü."""
from instagrapi import Client
import getpass
import time

username = "sonat.mundi"
password = getpass.getpass(f"Instagram sifresi (@{username}): ")

cl = Client()

# Gerçek bir cihaz gibi görünmek için ayarlar
cl.set_locale("tr_TR")
cl.set_country("TR")
cl.set_country_code(90)
cl.set_timezone_offset(3 * 3600)

# Proxy kullanmayı dene (opsiyonel)
# cl.set_proxy("http://user:pass@host:port")

print("\nGiris deneniyor...")
print("Eger 'BadPassword' hatasi alirsan asagidaki secenek 2'yi dene.\n")

try:
    cl.login(username, password)
    cl.dump_settings("D:/Yedekler/UCS/instagram/ig_session.json")
    print("\nSession basariyla kaydedildi!")

except Exception as e:
    error_msg = str(e)

    if "bad_password" in error_msg.lower() or "blacklist" in error_msg.lower():
        print("\n" + "="*60)
        print("IP ENGELI TESPIT EDILDI")
        print("="*60)
        print()
        print("Instagram bu IP adresini engelledi.")
        print("Cozum secenekleri:")
        print()
        print("SECENEK 1: Mobil veri ile dene")
        print("  - WiFi kapat, telefon hotspot ac")
        print("  - Bu scripti hotspot uzerinden tekrar calistir")
        print()
        print("SECENEK 2: Facebook ile giris yap")
        print("  - Instagram'a tarayicidan Facebook ile giris yap")
        print("  - Sonra ig_login_browser.py scriptini calistir")
        print()
        print("SECENEK 3: VPN kullan")
        print("  - Farkli bir ulke IP'si ile baglan")
        print("  - Scripti tekrar calistir")
        print()
        print("SECENEK 4: 24 saat bekle")
        print("  - IP engeli genelde 24 saatte kalkar")
        print()

    elif "two_factor" in error_msg.lower() or "challenge" in error_msg.lower():
        print("\n2FA dogrulama gerekiyor...")
        code = input("2FA kodu: ")
        try:
            cl.login(username, password, verification_code=code)
            cl.dump_settings("D:/Yedekler/UCS/instagram/ig_session.json")
            print("\nSession basariyla kaydedildi!")
        except Exception as e2:
            print(f"\n2FA hatasi: {e2}")

    else:
        print(f"\nBeklenmyen hata: {e}")
