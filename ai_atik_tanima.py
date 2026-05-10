"""
ai_atik_tanima.py — Kivy Camera + TFLite tabanli atik tanima.
Android'de OpenCV yerine Kivy'nin Camera widget'i kullanilir.
"""

import threading
import time
import os
import numpy as np
from kivy.clock import Clock
from kivy.uix.camera import Camera
from kivy.graphics.texture import Texture

try:
    import tflite_runtime.interpreter as tflite
    TFLITE_OK = True
except Exception:
    try:
        import tensorflow.lite as tflite
        TFLITE_OK = True
    except Exception:
        TFLITE_OK = False

LABEL_HARITASI = {
    "cigarette": "Izmarit", "butt": "Izmarit",
    "plastic_bag": "Plastik", "plastic bottle": "Plastik", "water bottle": "Plastik",
    "wine bottle": "Cam", "beer bottle": "Cam", "glass": "Cam",
    "battery": "Pil",
    "paper": "Kagit", "newspaper": "Kagit", "cardboard": "Kagit",
    "Izmarit": "Izmarit", "Plastik": "Plastik",
    "Cam": "Cam", "Pil": "Pil", "Kagit": "Kagit",
}

GUVEN_ESIGI    = 0.80
ANALIZ_ARALIGI = 2.0   # saniye
MODEL_BOYUT    = (224, 224)


class AtikTanimaMotoru:
    """
    Kivy Camera uzerinden kare alir, TFLite ile siniflandirir.
    TFLite yoksa veya model dosyasi yoksa simule modda calisir.
    """

    def __init__(self, model_yolu="model.tflite",
                 etiket_yolu="labels.txt", kamera_id=0):
        self.model_yolu   = model_yolu
        self.etiket_yolu  = etiket_yolu
        self.kamera_id    = kamera_id
        self.on_tespit    = None   # (tur, guven, bbox) -> None
        self.on_kare      = None   # kullanilmiyor (Camera widget direk gosterilir)

        self._aktif       = False
        self._interpreter = None
        self._etiketler   = []
        self._son_analiz  = 0.0
        self._camera_widget = None  # dis koddan set edilir

        model_var     = os.path.exists(model_yolu)
        self._simule  = not (TFLITE_OK and model_var)
        if not model_var:
            print(f"[AI] {model_yolu} bulunamadi – simule mod.")

    # ── Dis kod buraya Kivy Camera widget'ini atar ──────────────────────────
    def set_camera_widget(self, cam):
        self._camera_widget = cam

    # ── Baslat / Durdur ─────────────────────────────────────────────────────
    def baslat(self):
        if self._aktif:
            return
        self._aktif = True
        self._model_yukle()
        # Periyodik analiz: Clock ile ana thread'de calisir (texture erisimi icin)
        Clock.schedule_interval(self._analiz_et, ANALIZ_ARALIGI)
        print("[AI] Motor baslatildi.")

    def durdur(self):
        self._aktif = False
        Clock.unschedule(self._analiz_et)
        print("[AI] Motor durduruldu.")

    # ── Model ───────────────────────────────────────────────────────────────
    def _model_yukle(self):
        if self._simule:
            return
        try:
            self._interpreter = tflite.Interpreter(model_path=self.model_yolu)
            self._interpreter.allocate_tensors()
            self._giris = self._interpreter.get_input_details()
            self._cikis = self._interpreter.get_output_details()
            print(f"[AI] Model yuklendi: {self.model_yolu}")
        except Exception as e:
            print(f"[AI] Model hatasi: {e} – simule moda gecildi.")
            self._simule = True
        try:
            with open(self.etiket_yolu, "r", encoding="utf-8") as f:
                self._etiketler = [l.strip() for l in f]
        except Exception:
            self._etiketler = list(LABEL_HARITASI.keys())

    # ── Periyodik analiz (Clock, ana thread) ────────────────────────────────
    def _analiz_et(self, dt):
        if not self._aktif:
            return

        if self._simule:
            self._simule_tespit()
            return

        # Kivy Camera texture'indan piksel al
        if self._camera_widget is None:
            return
        tex = self._camera_widget.texture
        if tex is None:
            return

        try:
            # Texture -> numpy array
            w, h   = tex.size
            buf    = tex.pixels          # RGBA, 4 byte/piksel
            arr    = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
            rgb    = arr[:, :, :3]       # Alpha'yi at
            rgb    = rgb[::-1]           # Y ekseni duzelt

            # Modele uygun boyuta getir
            try:
                from PIL import Image as PILImage
                img = PILImage.fromarray(rgb).resize(MODEL_BOYUT)
                kucuk = np.array(img)
            except Exception:
                # PIL yoksa basit numpy slice
                kucuk = rgb[
                    ::max(1, h//MODEL_BOYUT[1]),
                    ::max(1, w//MODEL_BOYUT[0])
                ][:MODEL_BOYUT[1], :MODEL_BOYUT[0]]
                if kucuk.shape[:2] != MODEL_BOYUT[::-1]:
                    self._simule_tespit()
                    return

            giris = np.expand_dims(kucuk.astype(np.float32) / 255.0, axis=0)
            self._interpreter.set_tensor(self._giris[0]['index'], giris)
            self._interpreter.invoke()
            cikis     = self._interpreter.get_tensor(self._cikis[0]['index'])[0]
            idx       = int(np.argmax(cikis))
            guven     = float(cikis[idx])
            ham_etiket = (self._etiketler[idx]
                          if idx < len(self._etiketler) else "bilinmiyor")
            tur = self._etiket_eslestir(ham_etiket)

            if tur and guven >= GUVEN_ESIGI and self.on_tespit:
                self.on_tespit(tur, guven, None)

        except Exception as e:
            print(f"[AI] Analiz hatasi: {e}")

    def _etiket_eslestir(self, ham):
        h = ham.lower()
        for k, v in LABEL_HARITASI.items():
            if k.lower() in h:
                return v
        return None

    def _simule_tespit(self):
        import random
        tur   = random.choice(list(LABEL_HARITASI.values()))
        guven = random.uniform(0.82, 0.98)
        print(f"[SIM] {tur}  %{guven*100:.1f}")
        if self.on_tespit:
            self.on_tespit(tur, guven, None)
