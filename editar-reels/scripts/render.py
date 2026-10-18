#!/usr/bin/env python3
"""
Render final de un Reel SIN CapCut: crudos + subtítulos + gráficos + sonidos → mp4.

    python3 render.py edicion.json            # todo el video
    python3 render.py edicion.json 4.0 9.5    # solo ese tramo (para revisar rápido)
    python3 render.py edicion.json --frame 6.2 frame.jpg   # un frame compuesto

Requiere ffmpeg, Python 3, Pillow. Todas las rutas del JSON son relativas al JSON.

edicion.json
{
  "salida": "reel.mp4",
  "fps": 30,
  "subtitulos_estilo": "clasico",            # clasico | minimal | caja
  "acento": "#FFD84A",
  "fuente_subtitulos": "fuentes/Rubik-Bold.ttf",
  "tomas": [                                  # en orden; cada una es un tramo de un crudo
    {"clip": "../DJI_0125.MP4", "desde": 8.5, "frames": 189, "zoom": 1.1, "dy": 96}
  ],
  "subtitulos": [                             # tiempos en segundos de la LÍNEA DE TIEMPO final
    {"desde": 0.50, "hasta": 1.78, "texto": "Así se veían mis videos",
     "resaltes": [["mis videos", 12]]}        # [fragmento, tamaño]; tamaño 10 = base
  ],
  "capas": [                                  # secuencias de PNG 1080x1920 con alfa
    {"carpeta": "graficos/pip", "desde_frame": 0}
  ],
  "cortes": [                                 # mp4 opacos a pantalla completa (explicaciones, b-roll)
    {"archivo": "cortes/e1.mp4", "desde_frame": 871, "tinta": true}   # tinta: subtítulos oscuros encima
  ],
  "sonidos": [
    {"archivo": "sfx/pop.mp3", "en": 3.20, "volumen": 0.6}
  ]
}

Una carpeta de capa puede traer `segs.json` ({"segs": [{"f": "f_0000.png", "start": 0, "frames": 3}, ...]})
para sostener un PNG varios frames, o solo PNGs numerados (uno por frame, en orden).
"""
import json, os, subprocess, sys, time
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FS = 1080 * 1920 * 3

# zscale es lo que convierte bien un video HDR; no todas las builds de ffmpeg lo traen.
HAY_ZSCALE = " zscale " in subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                                          capture_output=True, text=True).stdout
PX_POR_TAMANO = 6.0          # tamaño 10 ≈ 60 px, 13 ≈ 78 px
Y_SUB = 365                  # centro de la banda de subtítulos (zona segura: 250–1500)
ANCHO_MAX = 820              # más ancho choca con la columna de botones


def hex_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ subtítulos

class Subtitulos:
    """Dibuja un subtítulo en una capa RGBA 1080x1920. Tres estilos."""

    def __init__(self, fuente, estilo="clasico", acento="#FFD84A"):
        self.fuente, self.estilo, self.acento = fuente, estilo, hex_rgb(acento)
        self._tinta = False
        self._f, self._cache = {}, {}

    def f(self, px):
        px = int(round(px))
        if px not in self._f: self._f[px] = ImageFont.truetype(self.fuente, px)
        return self._f[px]

    def corridas(self, texto, resaltes):
        marcas = []
        for frag, tam in resaltes:
            i = texto.find(frag)
            if i >= 0: marcas.append((i, i + len(frag), tam))
        marcas.sort(); out = []; pos = 0
        for a, b, tam in marcas:
            if a > pos: out.append((texto[pos:a], 10, False))
            out.append((texto[a:b], tam, True)); pos = b
        if pos < len(texto): out.append((texto[pos:], 10, False))
        return out

    def capa(self, texto, resaltes=(), tinta=False):
        """tinta=True: sobre un corte claro (papel crema). Texto oscuro, acento naranja y sin
        sombra: el blanco con sombra no se lee sobre fondo claro."""
        clave = (texto, tuple(map(tuple, resaltes)), tinta)
        if clave not in self._cache:
            self._tinta = tinta
            self._cache[clave] = getattr(self, "_" + self.estilo)(texto, [tuple(r) for r in resaltes])
        return self._cache[clave]

    # Blanco con sombra dura; la palabra clave en el acento y más grande.
    def _clasico(self, texto, resaltes):
        runs = [(s, self.f(t * PX_POR_TAMANO), r) for s, t, r in self.corridas(texto, resaltes)]
        return self._linea(runs, sombra="dura", color_resalte=self.acento)

    # Más chico, sin color: el énfasis es solo el peso. Sombra suave.
    def _minimal(self, texto, resaltes):
        runs = [(s, self.f(46), False) for s, _, _ in self.corridas(texto, resaltes)]
        return self._linea(runs, sombra="suave", color_resalte=None)

    # Mayúsculas grandes; la palabra clave va sobre una caja del color de acento.
    def _caja(self, texto, resaltes):
        runs = [(s.upper(), self.f(70), r) for s, _, r in self.corridas(texto, resaltes)]
        return self._linea(runs, sombra="contorno", color_resalte=None, caja=True)

    def _linea(self, runs, sombra, color_resalte, caja=False):
        anchos = [f.getlength(s) for s, f, _ in runs]
        ancho = sum(anchos)
        if ancho > ANCHO_MAX:
            print(f"  ⚠ subtítulo de {ancho:.0f} px (máx {ANCHO_MAX}): {''.join(s for s, _, _ in runs)!r}")
        asc = max(f.getmetrics()[0] for _, f, _ in runs)
        base = Y_SUB + asc // 2
        capa = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        blanco, acento = (255, 255, 255), (color_resalte or self.acento)
        if self._tinta:
            blanco, acento, sombra = (23, 22, 19), (224, 107, 69), None
            color_resalte = color_resalte and acento

        if sombra == "suave":
            s = Image.new("RGBA", capa.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(s); x = 540 - ancho / 2
            for (t, f, _), w in zip(runs, anchos):
                ds.text((x, base - f.getmetrics()[0] + 3), t, font=f, fill=(0, 0, 0, 150)); x += w
            capa.alpha_composite(s.filter(ImageFilter.GaussianBlur(6)))

        d = ImageDraw.Draw(capa); x = 540 - ancho / 2
        for (t, f, r), w in zip(runs, anchos):
            y = base - f.getmetrics()[0]
            if caja and r and t.strip():
                b = d.textbbox((x, y), t.strip(), font=f)
                lead = f.getlength(t) - f.getlength(t.lstrip())
                d.rounded_rectangle((b[0] + lead - 14, b[1] - 10, b[2] + lead + 14, b[3] + 12), 14, fill=self.acento + (255,))
            if sombra == "dura":
                d.text((x + 6, y + 6), t, font=f, fill=(0, 0, 0, 166))
            color = (acento if (r and color_resalte) else blanco)
            if caja and r: color = (17, 17, 17)
            kw = dict(stroke_width=5, stroke_fill=(0, 0, 0, 255)) if (sombra == "contorno" and not r) else {}
            d.text((x, y), t, font=f, fill=color + (255,), **kw)
            x += w
        return capa


# ------------------------------------------------------------------ edición

class Edicion:
    def __init__(self, ruta):
        self.dir = os.path.dirname(os.path.abspath(ruta))
        self.e = json.load(open(ruta))
        self.fps = self.e.get("fps", 30)
        self.sub = Subtitulos(self.p(self.e["fuente_subtitulos"]), self.e.get("subtitulos_estilo", "clasico"),
                              self.e.get("acento", "#FFD84A"))
        self.capas = [self._secuencia(c) for c in self.e.get("capas", [])]
        self.cortes = [dict(c, archivo=self.p(c["archivo"])) for c in self.e.get("cortes", [])]
        self.total = sum(t["frames"] for t in self.e["tomas"])
        self._png = {}
        self._info = {}
        self._avisos = set()

    def p(self, r): return r if os.path.isabs(r) else os.path.normpath(os.path.join(self.dir, r))

    def _secuencia(self, c):
        d = self.p(c["carpeta"]); f0 = c.get("desde_frame", 0); m = {}
        sj = os.path.join(d, "segs.json")
        if os.path.exists(sj):
            for s in json.load(open(sj))["segs"]:
                for k in range(s["frames"]): m[f0 + s["start"] + k] = os.path.join(d, s["f"])
        else:
            for k, n in enumerate(sorted(x for x in os.listdir(d) if x.lower().endswith(".png"))):
                m[f0 + k] = os.path.join(d, n)
        return m

    def png(self, ruta):
        if ruta not in self._png:
            if len(self._png) > 64: self._png.clear()
            self._png[ruta] = Image.open(ruta).convert("RGBA")
        return self._png[ruta]

    def subtitulo(self, t, tinta=False):
        for s in self.e.get("subtitulos", []):
            if s["desde"] <= t < s["hasta"] and s["texto"].strip():
                return self.sub.capa(s["texto"], s.get("resaltes", []), tinta)

    def info(self, clip):
        """Lo que hace falta saber de un archivo: si tiene audio y si es HDR."""
        ruta = self.p(clip)
        if ruta not in self._info:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,color_transfer", "-of", "json", ruta], capture_output=True, text=True).stdout
            streams = json.loads(out or "{}").get("streams", [])
            video = next((x for x in streams if x.get("codec_type") == "video"), {})
            self._info[ruta] = {
                "audio": any(x.get("codec_type") == "audio" for x in streams),
                # PQ (smpte2084) y HLG (arib-std-b67): lo que graban los iPhone y muchos Android en HDR.
                "hdr": video.get("color_transfer") in ("smpte2084", "arib-std-b67"),
            }
        return self._info[ruta]

    def decodificar(self, clip, desde, n, zoom=1.0, dy=0):
        # Escala para CUBRIR 1080x1920 sin deformar y recorta lo que sobra: un video
        # horizontal o cuadrado queda centrado en vez de aplastado. `dy` mueve el
        # recorte hacia abajo (positivo) o arriba, sin salirse del cuadro.
        Wd = int(round(1080 * zoom / 2)) * 2; Hd = int(round(1920 * zoom / 2)) * 2
        vf = f"fps={self.fps},scale={Wd}:{Hd}:force_original_aspect_ratio=increase,crop=1080:1920:(iw-1080)/2:max(0\\,min(ih-1920\\,(ih-1920)/2+{dy}))"
        if self.info(clip)["hdr"]:
            if HAY_ZSCALE:
                # HDR → SDR: sin esto los videos HDR salen lavados y grises.
                vf = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
                      "zscale=t=bt709:m=bt709:r=tv,format=yuv420p," + vf)
            elif clip not in self._avisos:
                self._avisos.add(clip)
                print(f"  ⚠ {clip} es HDR y este ffmpeg no trae zscale: los colores pueden salir lavados.")
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{desde:.4f}", "-i", self.p(clip),
            "-frames:v", str(n), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def componer(self, f, base):
        """Frame f de la línea de tiempo sobre la imagen base (RGB del crudo)."""
        tinta = False
        for c in self.cortes:
            if c.get("_n") is None:
                c["_n"] = round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "csv=p=0", c["archivo"]], capture_output=True, text=True).stdout) * self.fps)
            if c["desde_frame"] <= f < c["desde_frame"] + c["_n"]:
                base = self._corte(c, f - c["desde_frame"]); tinta = c.get("tinta", False)
        im = base.convert("RGBA")
        for capa in self.capas:
            r = capa.get(f)
            if r: im.alpha_composite(self.png(r))
        s = self.subtitulo(f / self.fps, tinta)
        if s: im.alpha_composite(s)
        return im.convert("RGB")

    def _corte(self, c, i):
        """Frame i del corte. Se lee en secuencia con un solo ffmpeg abierto; si se pide fuera
        de orden (p. ej. --frame), se vuelve a abrir en ese punto."""
        if c.get("_sig") != i:
            if c.get("_proc"): c["_proc"].kill()
            c["_proc"] = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{i / self.fps:.4f}", "-i", c["archivo"],
                "-vf", f"fps={self.fps},scale=1080:1920", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            c["_ultimo"] = None
        raw = c["_proc"].stdout.read(FS)
        if len(raw) == FS: c["_ultimo"] = raw
        c["_sig"] = i + 1
        return Image.frombytes("RGB", (1080, 1920), c["_ultimo"]) if c["_ultimo"] else self._frame_de(c["archivo"], i / self.fps)

    def _frame_de(self, archivo, t):
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", archivo, "-frames:v", "1",
            "-vf", "scale=1080:1920", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        return Image.frombytes("RGB", (1080, 1920), raw)

    def cerrar(self):
        for c in self.cortes:
            if c.get("_proc"): c["_proc"].stdout.close(); c["_proc"].kill(); c["_proc"].wait()

    def frame(self, t, salida):
        f = round(t * self.fps); acc = 0
        for tm in self.e["tomas"]:
            if f < acc + tm["frames"]:
                d = self.decodificar(tm["clip"], tm["desde"] + (f - acc) / self.fps, 1, tm.get("zoom", 1), tm.get("dy", 0))
                raw = d.stdout.read(FS); d.wait()
                self.componer(f, Image.frombytes("RGB", (1080, 1920), raw)).save(salida, quality=92)
                return
            acc += tm["frames"]

    def video(self, f_ini, f_fin, silencioso):
        enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", "1080x1920", "-r", str(self.fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            silencioso], stdin=subprocess.PIPE)
        acc = 0
        for tm in self.e["tomas"]:
            a, b = max(f_ini, acc), min(f_fin, acc + tm["frames"])
            if a < b:
                dec = self.decodificar(tm["clip"], tm["desde"] + (a - acc) / self.fps, b - a, tm.get("zoom", 1), tm.get("dy", 0))
                ultimo = None
                for f in range(a, b):
                    raw = dec.stdout.read(FS)
                    if len(raw) == FS: ultimo = raw
                    enc.stdin.write(self.componer(f, Image.frombytes("RGB", (1080, 1920), ultimo)).tobytes())
                dec.stdout.close(); dec.wait()
            acc += tm["frames"]
        enc.stdin.close(); enc.wait()

    def audio(self, f_ini, f_fin, salida):
        ent, fil, n = [], [], 0; acc = 0
        for tm in self.e["tomas"]:
            a, b = max(f_ini, acc), min(f_fin, acc + tm["frames"])
            if a < b:
                d = (b - a) / self.fps
                if self.info(tm["clip"])["audio"]:
                    ent += ["-ss", f"{tm['desde'] + (a - acc) / self.fps:.4f}", "-t", f"{d:.4f}", "-i", self.p(tm["clip"])]
                else:
                    # Un clip sin pista de audio (b-roll de algunas cámaras) entra como silencio.
                    ent += ["-f", "lavfi", "-t", f"{d:.4f}", "-i", "anullsrc=r=48000:cl=stereo"]
                # Todo a 48 kHz estéreo: mezclar un clip mono con uno estéreo rompe el concat.
                fil.append(f"[{n}:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,"
                           f"afade=t=in:d=0.01,afade=t=out:st={max(0, d - 0.012):.4f}:d=0.012[v{n}]"); n += 1
            acc += tm["frames"]
        voz = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[voz]"
        mezcla, k = ["[voz]"], n
        for s in self.e.get("sonidos", []):
            t = s["en"] - f_ini / self.fps
            if t < 0 or t > (f_fin - f_ini) / self.fps: continue
            ent += ["-i", self.p(s["archivo"])]
            fil.append(f"[{k}:a]aresample=48000,aformat=sample_rates=48000:channel_layouts=stereo,"
                       f"volume={s.get('volumen', 0.6)},adelay={int(t * 1000)}:all=1[s{k}]")
            mezcla.append(f"[s{k}]"); k += 1
        fil.append(voz)
        fil.append("".join(mezcla) + f"amix=inputs={len(mezcla)}:normalize=0:duration=first[a]" if len(mezcla) > 1 else "[voz]anull[a]")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ent, "-filter_complex", ";".join(fil),
            "-map", "[a]", "-c:a", "aac", "-b:a", "192k", salida], check=True)


def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    ed = Edicion(args[0])
    if len(args) >= 4 and args[1] == "--frame":
        ed.frame(float(args[2]), args[3]); ed.cerrar(); print(args[3]); return
    f_ini = round(float(args[1]) * ed.fps) if len(args) > 2 else 0
    f_fin = round(float(args[2]) * ed.fps) if len(args) > 2 else ed.total
    salida = ed.p(ed.e.get("salida", "reel.mp4"))
    if len(args) > 2: salida = salida.replace(".mp4", f"_{args[1]}-{args[2]}.mp4")
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"render_{os.getpid()}")
    t0 = time.time()
    ed.video(f_ini, f_fin, tmp + "_v.mp4"); ed.cerrar()
    ed.audio(f_ini, f_fin, tmp + "_a.m4a")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp + "_v.mp4", "-i", tmp + "_a.m4a", "-c", "copy",
        "-shortest", "-movflags", "+faststart", salida], check=True)
    for x in ("_v.mp4", "_a.m4a"):
        try: os.remove(tmp + x)
        except OSError: pass
    seg = (f_fin - f_ini) / ed.fps; dt = time.time() - t0
    print(f"{salida} · {seg:.1f} s de video en {dt:.0f} s ({dt / seg:.1f} s por segundo)")


if __name__ == "__main__":
    main()
