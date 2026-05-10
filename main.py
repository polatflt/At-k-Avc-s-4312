"""
main.py – Atik Avcisi
Kivy Camera ile kamera ekrani (OpenCV kullanmaz).
"""

import json, os, random, math
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Mesh
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.animation import Animation
from kivy.properties import NumericProperty

try:
    from android.storage import app_storage_path
    from android.permissions import request_permissions, Permission
    IS_ANDROID = True
except ImportError:
    IS_ANDROID = False

from ai_atik_tanima import AtikTanimaMotoru

# ── Renkler ──────────────────────────────────────────────────────────────────
C_BG_KOYU    = get_color_from_hex("#0A1A0A")
C_BG_CARD    = get_color_from_hex("#0F3D1A")
C_YESIL_NEON = get_color_from_hex("#00FF7F")
C_SARI       = get_color_from_hex("#AAFF00")
C_TURUNCU    = get_color_from_hex("#FF8C00")
C_GOKCE      = get_color_from_hex("#00CFCF")
C_KIRMIZI    = get_color_from_hex("#FF4455")
C_BEYAZ      = get_color_from_hex("#E8FFE8")
C_SOLUK      = get_color_from_hex("#5A8A5A")

WASTE_TYPES = {
    "Izmarit": {"puan": 25, "renk": "#FF4444"},
    "Pil":     {"puan": 50, "renk": "#FF8C00"},
    "Plastik": {"puan": 15, "renk": "#00BFFF"},
    "Cam":     {"puan": 20, "renk": "#00FFFF"},
    "Kagit":   {"puan": 10, "renk": "#AAFF00"},
}

BILGI = [
    "Bir izmarit 500 litre suyu kirletir!",
    "Bir pil 400 litre suyu zehirler!",
    "Plastik dogada 450 yilda cozunur.",
    "1 ton kagit geri donusu 17 agaci kurtarir.",
    "Cam yuzde 100 geri donusturulebilir!",
    "Her yil 8 milyon ton plastik okyanuslara karisiyor.",
    "Geri donusum enerjiyi yuzde 70 azaltir.",
]

BASE_XP  = 150
XP_ARTIS = 1.30

# ── Veri ─────────────────────────────────────────────────────────────────────
def _veri_dizini():
    if IS_ANDROID:
        try:
            return app_storage_path()
        except Exception:
            pass
    return os.path.dirname(os.path.abspath(__file__))

def _veri_dosyasi():
    return os.path.join(_veri_dizini(), "atik_avcisi.json")

def veri_yukle():
    yol = _veri_dosyasi()
    if os.path.exists(yol):
        try:
            with open(yol, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"toplam_puan": 0, "mevcut_seviye": 1,
            "hedef_puan": BASE_XP, "kayitlar": []}

def veri_kaydet(data):
    yol = _veri_dosyasi()
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
    except Exception:
        pass
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def seviye_hesapla(s):
    return round(BASE_XP * (XP_ARTIS ** (s - 1)))

# ── Arka Plan ─────────────────────────────────────────────────────────────────
class DogaArkaplan(Widget):
    zaman = NumericProperty(0)
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._ciz, size=self._ciz, zaman=self._ciz)
        Clock.schedule_interval(lambda dt: setattr(self, 'zaman', self.zaman + dt), 1/30)
    def _ciz(self, *a):
        self.canvas.clear()
        w, h = self.width, self.height
        with self.canvas:
            for i in range(20):
                r = i/19
                Color(0.02+r*0.03, 0.05+r*0.15, 0.08+r*0.05, 1)
                Rectangle(pos=(self.x, self.y+h*(1-(i+1)/20)), size=(w, h/20+1))
            Color(0.04, 0.18, 0.06, 1)
            Rectangle(pos=(self.x, self.y), size=(w, h*0.20))
            Color(0.06, 0.28, 0.08, 1)
            Rectangle(pos=(self.x, self.y), size=(w, h*0.12))

# ── UI Yardimcilari ───────────────────────────────────────────────────────────
def etiket(text, font_size=15, color=None, bold=False, halign="center", **kw):
    color = color or C_BEYAZ
    lbl = Label(text=text, font_size=dp(font_size), color=color,
                bold=bold, halign=halign, valign="middle", **kw)
    lbl.bind(size=lbl.setter("text_size"))
    return lbl

class Kart(BoxLayout):
    def __init__(self, kenar=None, arka=None, **kw):
        super().__init__(**kw)
        self._kenar = kenar or C_YESIL_NEON
        self._arka  = arka  or C_BG_CARD
        self.bind(pos=self._ciz, size=self._ciz)
    def _ciz(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._arka, 0.85)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
            Color(*self._kenar, 0.9)
            RoundedRectangle(pos=(self.x+dp(1),self.y+dp(1)),
                             size=(self.width-dp(2),self.height-dp(2)), radius=[dp(14)])
            Color(*self._arka, 0.88)
            RoundedRectangle(pos=(self.x+dp(2.5),self.y+dp(2.5)),
                             size=(self.width-dp(5),self.height-dp(5)), radius=[dp(12)])

class YesilButon(Button):
    def __init__(self, renk=None, **kw):
        self._renk = renk or C_YESIL_NEON
        kw.setdefault("background_color", [0,0,0,0])
        kw.setdefault("color", C_BG_KOYU)
        kw.setdefault("bold", True)
        kw.setdefault("font_size", dp(15))
        super().__init__(**kw)
        self.bind(pos=self._ciz, size=self._ciz)
    def _ciz(self, *a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._renk, 1.0)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(self._renk[0], min(1,self._renk[1]+0.2), self._renk[2], 0.9)
            RoundedRectangle(pos=(self.x+dp(3),self.y+dp(3)),
                             size=(self.width-dp(6),self.height-dp(6)), radius=[dp(9)])
    def on_press(self):
        (Animation(opacity=0.5,duration=0.07)+Animation(opacity=1.0,duration=0.07)).start(self)

# ── Kamera Paneli (Kivy Camera kullanir) ──────────────────────────────────────
class KameraPaneli(FloatLayout):
    """
    Tam ekran kaplayan kamera paneli.
    Kivy'nin Camera widget'i ile goruntu gosterir,
    AtikTanimaMotoru Camera'nin texture'ini analiz eder.
    """
    def __init__(self, on_kabul, on_kapat, **kw):
        super().__init__(**kw)
        self.on_kabul = on_kabul
        self.on_kapat = on_kapat
        self._motor   = None
        self._son_tur   = None
        self._son_guven = 0.0
        self._kamera    = None

        # Koyu arka plan
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._bg_guncelle, size=self._bg_guncelle)

        if IS_ANDROID:
            request_permissions(
                [Permission.CAMERA,
                 Permission.WRITE_EXTERNAL_STORAGE,
                 Permission.READ_EXTERNAL_STORAGE],
                self._izin_sonrasi
            )
        else:
            Clock.schedule_once(lambda dt: self._kurulum(), 0.1)

    def _bg_guncelle(self, *a):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _izin_sonrasi(self, izinler, sonuclar):
        Clock.schedule_once(lambda dt: self._kurulum(), 0.3)

    def _kurulum(self):
        # Kivy Camera widget — tam ekran
        self._kamera = Camera(
            index=0,
            resolution=(640, 480),
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            allow_stretch=True,
            keep_ratio=False,
            play=True,
        )
        # Android'de arka kamera 90 derece donuk gelir, duzelt
        if IS_ANDROID:
            self._kamera.rotation = -90
        else:
            self._kamera.rotation = 0
        self.add_widget(self._kamera)

        # UI katmani: alta sabit yukseklik, kamera tum ekrani kaplar
        ui = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(180),
            pos_hint={"x": 0, "y": 0},
            padding=dp(8), spacing=dp(4),
        )
        with ui.canvas.before:
            Color(0, 0, 0, 0.70)
            self._ui_bg = Rectangle(pos=ui.pos, size=ui.size)
        ui.bind(pos=lambda w,v: setattr(self._ui_bg,'pos',v),
                size=lambda w,v: setattr(self._ui_bg,'size',v))

        # Durum
        self._lbl_durum = etiket("Kamera baslatildi, taranıyor...",
                                 font_size=13, color=C_SARI,
                                 size_hint_y=None, height=dp(28))
        ui.add_widget(self._lbl_durum)

        # Ust sag kapat butonu ayri katmanda (FloatLayout icinde)
        btn_kapat = YesilButon(renk=C_KIRMIZI, text="X  Kapat",
                               size_hint=(None, None),
                               size=(dp(90), dp(40)),
                               pos_hint={"right": 1, "top": 1})
        btn_kapat.bind(on_press=self._kapat)
        self.add_widget(btn_kapat)

        # Guven
        self._pb = ProgressBar(max=100, value=0,
                               size_hint_y=None, height=dp(16))
        ui.add_widget(self._pb)

        # Butonlar
        btn_satir = BoxLayout(orientation="horizontal",
                              size_hint_y=None, height=dp(50), spacing=dp(10))
        self._btn_onayla = YesilButon(renk=C_YESIL_NEON,
                                      text="Onayla & Kaydet", disabled=True)
        self._btn_onayla.bind(on_press=self._onayla)
        btn_yeni = YesilButon(renk=C_TURUNCU, text="Yeniden Tara")
        btn_yeni.bind(on_press=self._yeniden_tara)
        btn_satir.add_widget(self._btn_onayla)
        btn_satir.add_widget(btn_yeni)
        ui.add_widget(btn_satir)

        self.add_widget(ui)

        # Motoru baslat
        self._motor = AtikTanimaMotoru(
            model_yolu="model.tflite",
            etiket_yolu="labels.txt",
        )
        self._motor.set_camera_widget(self._kamera)
        self._motor.on_tespit = self._tespit_alindi
        self._motor.baslat()

    def _tespit_alindi(self, tur, guven, bbox):
        self._son_tur   = tur
        self._son_guven = guven
        pct = int(guven * 100)
        self._lbl_durum.text      = f"Tespit: {tur}  %{pct}"
        self._lbl_durum.color     = C_YESIL_NEON
        self._pb.value            = pct
        self._btn_onayla.disabled = False

    def _onayla(self, *a):
        if self._son_tur and self.on_kabul:
            self.on_kabul(self._son_tur, self._son_guven)
        self._kapat()

    def _yeniden_tara(self, *a):
        self._son_tur             = None
        self._son_guven           = 0.0
        self._lbl_durum.text      = "Tarama baslatildi..."
        self._lbl_durum.color     = C_SARI
        self._pb.value            = 0
        self._btn_onayla.disabled = True

    def _kapat(self, *a):
        if self._motor:
            self._motor.durdur()
        if self._kamera:
            self._kamera.play = False
        if self.on_kapat:
            self.on_kapat()

    def on_parent(self, widget, parent):
        if parent is None:
            if self._motor:
                self._motor.durdur()
            if self._kamera:
                self._kamera.play = False

# ── Ana Ekran ─────────────────────────────────────────────────────────────────
class AtikAvcisiUI(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.data = veri_yukle()
        self._bilgi_i = random.randint(0, len(BILGI)-1)
        self._kamera_paneli = None

        self._arka = DogaArkaplan(size_hint=(1,1))
        self.add_widget(self._arka)

        self._ana_kutu = BoxLayout(
            orientation="vertical", spacing=dp(7), padding=dp(10), size_hint=(1,1))
        self.add_widget(self._ana_kutu)
        self._ui_olustur()

        self.bind(pos=self._boyutla, size=self._boyutla)
        Clock.schedule_interval(self._bilgi_dontur, 7)

    def _boyutla(self, *a):
        self._arka.pos  = self.pos
        self._arka.size = self.size

    def _ui_olustur(self):
        # Baslik
        h = Kart(kenar=C_YESIL_NEON, arka=C_BG_KOYU,
                 size_hint_y=None, height=dp(58),
                 orientation="horizontal", padding=[dp(12),dp(6)])
        h.add_widget(etiket("Atik Avcisi", font_size=23,
                            color=C_YESIL_NEON, bold=True, halign="left"))
        h.add_widget(etiket("Dogayi Koru!", font_size=13,
                            color=C_SARI, halign="right"))
        self._ana_kutu.add_widget(h)

        # Bilgi
        kart = Kart(kenar=C_GOKCE, arka=C_BG_KOYU,
                    size_hint_y=None, height=dp(48), padding=[dp(10),dp(4)])
        self._bilgi_lbl = etiket(BILGI[self._bilgi_i], font_size=12, color=C_GOKCE)
        kart.add_widget(self._bilgi_lbl)
        self._ana_kutu.add_widget(kart)

        # Stat satiri
        satir = BoxLayout(orientation="horizontal",
                          size_hint_y=None, height=dp(78), spacing=dp(7))
        for baslik, attr, renk in [
            ("SEVIYE","_lbl_seviye",C_SARI),
            ("TOPLAM XP","_lbl_puan",C_YESIL_NEON),
            ("HEDEF XP","_lbl_hedef",C_TURUNCU),
        ]:
            k = Kart(kenar=renk, arka=C_BG_KOYU, orientation="vertical", padding=dp(5))
            k.add_widget(etiket(baslik, font_size=9, color=C_SOLUK))
            deger = {"_lbl_seviye": str(self.data["mevcut_seviye"]),
                     "_lbl_puan":   str(self.data["toplam_puan"]),
                     "_lbl_hedef":  str(self.data["hedef_puan"])}[attr]
            lbl = etiket(deger, font_size=25, color=renk, bold=True)
            setattr(self, attr, lbl)
            k.add_widget(lbl)
            satir.add_widget(k)
        self._ana_kutu.add_widget(satir)

        # Ilerleme
        kart2 = Kart(kenar=C_YESIL_NEON, arka=C_BG_KOYU,
                     size_hint_y=None, height=dp(48),
                     orientation="vertical", padding=[dp(10),dp(4)])
        seviye = self.data["mevcut_seviye"]
        onceki = seviye_hesapla(seviye-1) if seviye > 1 else 0
        pct = min(100, max(0,
            (self.data["toplam_puan"]-onceki) /
            max(1, self.data["hedef_puan"]-onceki)*100))
        ust = BoxLayout(orientation="horizontal")
        ust.add_widget(etiket("Seviye Ilerleme:", font_size=11, color=C_SOLUK, halign="left"))
        self._lbl_pct = etiket(f"{pct:.0f}%", font_size=11, color=C_YESIL_NEON, halign="right")
        ust.add_widget(self._lbl_pct)
        kart2.add_widget(ust)
        self._pb_seviye = ProgressBar(max=100, value=pct, size_hint_y=None, height=dp(18))
        kart2.add_widget(self._pb_seviye)
        self._ana_kutu.add_widget(kart2)

        # Kamera butonu
        panel = Kart(kenar=C_GOKCE, arka=C_BG_KOYU,
                     orientation="vertical", size_hint_y=None, height=dp(100),
                     padding=dp(12), spacing=dp(8))
        panel.add_widget(etiket("Atik Tanimla", font_size=14,
                                color=C_GOKCE, bold=True, halign="left"))
        btn_ai = YesilButon(renk=C_GOKCE, text="AI Kamera ile Tara",
                            size_hint_y=None, height=dp(46))
        btn_ai.bind(on_press=self._kamera_ac)
        panel.add_widget(btn_ai)
        self._ana_kutu.add_widget(panel)

        # Gecmis
        self._ana_kutu.add_widget(etiket("Son Kayitlar", font_size=12,
                                         color=C_SOLUK, size_hint_y=None, height=dp(22)))
        scroll = ScrollView()
        self._glist = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self._glist.bind(minimum_height=self._glist.setter("height"))
        scroll.add_widget(self._glist)
        self._ana_kutu.add_widget(scroll)
        self._guncelle_gecmis()

    def _kamera_ac(self, *a):
        if self._kamera_paneli:
            return
        self._kamera_paneli = KameraPaneli(
            on_kabul=self._ai_kabul,
            on_kapat=self._kamera_kapat,
            size_hint=(1,1),
            pos=self.pos,
        )
        self.add_widget(self._kamera_paneli)

    def _ai_kabul(self, tur, guven):
        if tur in WASTE_TYPES:
            self._kaydet(tur, miktar=1)

    def _kamera_kapat(self):
        if self._kamera_paneli:
            self.remove_widget(self._kamera_paneli)
            self._kamera_paneli = None

    def _bilgi_dontur(self, dt):
        self._bilgi_i = (self._bilgi_i+1) % len(BILGI)
        self._bilgi_lbl.text = BILGI[self._bilgi_i]

    def _kaydet(self, tur, miktar=1):
        xp  = WASTE_TYPES[tur]["puan"] * miktar
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.data["kayitlar"].insert(0, {"tarih":now,"tur":tur,"miktar":miktar,"xp":xp})
        self.data["toplam_puan"] += xp
        level_up = False
        while self.data["toplam_puan"] >= self.data["hedef_puan"]:
            self.data["mevcut_seviye"] += 1
            self.data["hedef_puan"] = seviye_hesapla(self.data["mevcut_seviye"])
            level_up = True
        veri_kaydet(self.data)
        self._stats_guncelle()
        self._guncelle_gecmis()
        if level_up:
            self._popup("SEVIYE ATLADIN!",
                        f"Tebrikler! Seviye {self.data['mevcut_seviye']} oldun!\n"
                        f"Yeni hedef: {self.data['hedef_puan']} XP")
        else:
            self._popup("Kaydedildi!", f"+{xp} XP kazandin!\n({tur} x {miktar})")

    def _stats_guncelle(self):
        self._lbl_seviye.text = str(self.data["mevcut_seviye"])
        self._lbl_puan.text   = str(self.data["toplam_puan"])
        self._lbl_hedef.text  = str(self.data["hedef_puan"])
        seviye = self.data["mevcut_seviye"]
        onceki = seviye_hesapla(seviye-1) if seviye > 1 else 0
        pct = min(100, max(0,
            (self.data["toplam_puan"]-onceki)/max(1,self.data["hedef_puan"]-onceki)*100))
        self._pb_seviye.value = pct
        self._lbl_pct.text    = f"{pct:.0f}%"

    def _guncelle_gecmis(self):
        self._glist.clear_widgets()
        kayitlar = self.data["kayitlar"][:15]
        if not kayitlar:
            self._glist.add_widget(etiket("Henuz kayit yok.",
                font_size=12, color=C_SOLUK, size_hint_y=None, height=dp(38)))
            return
        for k in kayitlar:
            renk = get_color_from_hex(WASTE_TYPES.get(k["tur"],{}).get("renk","#00FF7F"))
            satir = Kart(kenar=renk, arka=C_BG_KOYU, orientation="horizontal",
                         size_hint_y=None, height=dp(42), padding=[dp(8),dp(3)], spacing=dp(6))
            satir.add_widget(etiket(f"{k['tur']} x{k['miktar']}",
                                   font_size=12, color=C_BEYAZ, halign="left"))
            satir.add_widget(etiket(f"+{k['xp']} XP", font_size=13,
                                   color=renk, halign="center", bold=True))
            satir.add_widget(etiket(k["tarih"], font_size=10,
                                   color=C_SOLUK, halign="right"))
            self._glist.add_widget(satir)

    def _popup(self, baslik, mesaj):
        icerik = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        with icerik.canvas.before:
            Color(*C_BG_KOYU, 0.97)
            _bg = Rectangle()
        def _upd(w,*a): _bg.pos=w.pos; _bg.size=w.size
        icerik.bind(pos=_upd, size=_upd)
        icerik.add_widget(etiket(mesaj, font_size=14, color=C_BEYAZ))
        btn = YesilButon(text="Tamam", renk=C_YESIL_NEON,
                         size_hint_y=None, height=dp(42))
        icerik.add_widget(btn)
        popup = Popup(title=baslik, title_color=C_YESIL_NEON, title_size=dp(16),
                      content=icerik, size_hint=(0.85,0.35),
                      background_color=C_BG_KOYU, separator_color=C_YESIL_NEON)
        btn.bind(on_press=popup.dismiss)
        popup.open()

# ── App ───────────────────────────────────────────────────────────────────────
class AtikAvcisiApp(App):
    def build(self):
        Window.clearcolor = C_BG_KOYU
        if not IS_ANDROID:
            Window.size = (400, 750)
        self.title = "Atik Avcisi"
        return AtikAvcisiUI()

if __name__ == "__main__":
    AtikAvcisiApp().run()
