---
name: editar-reels
description: Editar Reels, TikToks y Shorts hablados a cámara a partir de los crudos. Transcribe con Whisper, escoge tomas, corta, pone subtítulos y gráficos, y entrega un mp4 terminado (sin CapCut) o la edición dentro de un proyecto de CapCut de escritorio. También hace la portada. Usar cuando pidan editar un video corto, escoger tomas, poner subtítulos o hacer la portada.
---

# Editar videos cortos con Claude

Sale de editar unos 15 Reels reales. Cada regla con ⚠️ existe porque algo se rompió.

## Lo que esta skill NO puede hacer (decirlo de entrada)

- **No oye.** Puede medir el audio (silencios, volumen), pero no juzgar si un sonido queda bien. Los efectos de sonido los escoge la persona; Claude los coloca al frame.
- **No ve el video en movimiento.** Ve frames sueltos. Revisa los frames alrededor de cada corte, en pasos de 0.1 s; no revisa los 30 de cada segundo.
- **No adivina tu estilo.** El primer video lleva varias vueltas de "esto sí, esto no". Lo que se decida se anota en *Perfil* y en la *Bitácora*. Desde el tercer o cuarto video ya sale casi solo.

## Perfil

Si está vacío, preguntarlo en el primer video (con opciones, no en abierto) y guardarlo aquí. Si la persona llegó con un perfil ya armado, usarlo tal cual.

```
NOMBRE              = 
IDIOMA              = español (México)
SALIDA              = mp4            # mp4 (render directo, sin CapCut) | capcut (edición dentro del proyecto)
SUBTITULOS          = clasico        # clasico | minimal | caja        (ver *Estilos*)
GRAFICOS            = vidrio         # vidrio | plano | stickers        (ver *Estilos*)
ACENTO              = #FFD84A        # el color que resalta palabras clave
RECURSOS            = normal         # pocos | normal | muchos
EXPLICACIONES       = a veces        # cortes a pantalla completa que muestran un proceso: si | no | a veces
CARA_EN_GRAFICOS    = no             # fotos o avatares de la persona dentro de tarjetas
FUENTE_SUBTITULOS   = Rubik Bold     # ver *Fuentes*
FUENTE_GRAFICOS     = Inter
GLOSARIO            = nombres que Whisper oye mal → cómo se escriben
                      p. ej. "Cloud" → Claude, "cap cut" → CapCut, su marca, sus clientes
ENCUADRE            = se mide en el primer video (ver *Zonas seguras*)
```

Para medir el encuadre: sacar un frame donde la persona mire a cámara y anotar en qué píxel (sobre 1080x1920) quedan la coronilla, los ojos, la boca, la barbilla y el pecho. Todo lo que diga "pecho" o "barbilla" en esta skill se refiere a esos números.

**El perfil es el punto de partida, no la última palabra.** En el primer video, componer la primera tarjeta y el primer subtítulo sobre dos frames reales de la persona y confirmar antes de seguir: escoger un estilo en abstracto y verlo sobre tu propia cara son cosas distintas.

## El entregable son dos piezas: el video y la portada

Un Reel no está terminado hasta que tiene portada. Hacerla siempre como último paso, sin que la pidan (ver *Portada*).

## Principio: la edición sirve al contenido

- Leer primero lo que dice el video y decidir qué pide **ese** video. Una enumeración pide lista; una cifra pide que la cifra mande en pantalla; una anécdota a lo mejor no pide más que buenos subtítulos.
- **Cuántos recursos** según `RECURSOS`: `pocos` = subtítulos y como mucho un gráfico; `normal` = 2–3 recursos; `muchos` = hasta 5, con un efecto de sonido por idea. Más que eso satura y se ve a plantilla. Si la persona los va pidiendo uno por uno, decírselo.
- **Proponer 1–2 ideas concretas antes de ejecutar**, como tabla con tiempos. No aplicar nada de sorpresa.
- **No inventar.** Si el guión decía una cifra y en ninguna toma la dijo, decírselo y no meterla por la puerta de atrás en un gráfico.

---

# Paso 1 · Transcribir los crudos

Claude transcribe los crudos directo, sin internet y sin CapCut, con Whisper.

**Sacar el audio en la máquina de la persona** (pesa ~2 MB por minuto, contra cientos de MB del video):

```bash
mkdir -p _aud
for f in *.MP4 *.mp4 *.MOV *.mov; do [ -f "$f" ] || continue
  ffmpeg -loglevel error -i "$f" -vn -ar 16000 -ac 1 "_aud/${f%.*}.wav" -y
done
```

**Transcribir.** Hugging Face suele estar bloqueado en sandboxes, pero npm pasa, y estos paquetes traen el modelo adentro:

```bash
npm i sts-whisper-small        # o sts-whisper-base: 2x más rápido, más errores
npm i --ignore-scripts @huggingface/transformers wavefile
```

```js
// tr.mjs — node tr.mjs audio.wav salida.txt
import { pipeline, env } from '@huggingface/transformers';
import wavefile from 'wavefile';
import fs from 'fs';
env.allowRemoteModels = false;
env.localModelPath = new URL('./node_modules/sts-whisper-small/models/', import.meta.url).pathname;
const [,, wavPath, outPath] = process.argv;
const wav = new wavefile.WaveFile(fs.readFileSync(wavPath));
wav.toBitDepth('32f'); wav.toSampleRate(16000);
let s = wav.getSamples(); if (Array.isArray(s)) s = s[0];
const asr = await pipeline('automatic-speech-recognition', 'Xenova/whisper-small', { dtype: 'q8' });
const r = await asr(s, { language: 'spanish', task: 'transcribe', return_timestamps: true,
                         chunk_length_s: 30, stride_length_s: 5 });
fs.writeFileSync(outPath, r.chunks.map(c =>
  `${c.timestamp[0]?.toFixed(2)}-${c.timestamp[1]?.toFixed(2)} | ${c.text.trim()}`).join('\n') + '\n');
```

- `dtype: 'q8'` es obligatorio: el paquete trae los modelos cuantizados y sin eso busca el archivo completo y falla.
- Velocidad medida en 2 núcleos: `base` ≈ 0.25× la duración del audio, `small` ≈ 0.45×. Diez minutos de crudo con `small` ≈ 5 minutos.
- **Clips sin voz (b-roll) hacen que Whisper invente** ("de", "y que", frases sueltas). Descartar antes los clips donde `silencedetect` (ver *Paso 3*) marque más del 80 % como silencio.
- **Pasar el glosario del perfil** sobre todo el texto. Whisper y CapCut se equivocan en lo mismo: nombres propios, marcas, anglicismos.
- Los tiempos de Whisper son por frase, no por palabra. Para escoger tomas sirven; el borde fino de cada corte sale de los silencios.

Si la persona ya puso subtítulos automáticos en CapCut, también sirven: están en `tracks[1]` del proyecto, con tiempos.

# Paso 2 · Escoger tomas

1. **Agrupar el texto en tomas** cortando donde haya un hueco de más de 0.7 s. Así se ven los arranques en falso y las repeticiones.
2. **Comparar cada grupo contra el guión** y quedarse con la toma completa y fluida (casi siempre la última).
3. **Si las tomas dicen cosas distintas, quedarse con lo que dice en el video, no con el guión.**
4. **Comparar la duración total contra dónde se acaba el guión.** Si sobran 15–20 s, son tomas alternas o de recuperación.
5. Si dos tomas están parejas, ponerlas una tras otra y que la persona escoja.
6. **Presentar el plan antes de cortar**: tabla con clip, segundo de entrada, segundo de salida y qué dice. Excepción: si ya pidió "quédate con las mejores tomas", hacerlo directo.

Si hay varias formas de empezar (varios ganchos), armar el cuerpo una vez y probar cada gancho como versión aparte.

# Paso 3 · Puntos de corte

```bash
ffmpeg -nostats -i CLIP.MP4 -af "silencedetect=noise=-30dB:d=0.20" -f null -
```

- Dejar 0.1–0.2 s de aire antes de la frase y 0.2–0.3 s de cola después.
- Si la persona lee el guión, baja la vista en cuanto termina cada frase: el borde de salida va pegado a la última palabra (+0.05 s), sin cola.
- ⚠️ **Revisar el frame exacto de cada corte.** La gente parpadea seguido, y entrar o salir con los ojos cerrados se nota. Sacar una rejilla de frames cada 0.1 s alrededor de cada borde, recortada a la cara y con el timecode encima:

```bash
for t in $(seq 82.0 0.1 82.7); do
  ffmpeg -loglevel error -ss $t -i CLIP.MP4 -frames:v 1 -vf "crop=iw*0.6:ih*0.25:iw*0.2:ih*0.22,scale=250:-1,drawtext=text='$t':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:boxcolor=black" "_cut_${t}.jpg" -y
done
ffmpeg -loglevel error -pattern_type glob -i '_cut_*.jpg' -vf tile=8x1 rejilla.jpg -y
```

  Mover el borde dentro del silencio hasta un frame con ojos abiertos. Usar un archivo temporal distinto en cada vuelta del bucle: reusar el mismo nombre provoca "broken data stream".
- **Zoom alterno**: en cortes dentro del mismo plano, alternar el zoom (1.10 / 1.18) para que el salto se lea como intención y no como error.

# Paso 4 · Subtítulos

- Banda arriba de la frente, ~300–420 px (ver *Zonas seguras*). En el pecho van los gráficos.
- Frases de 2–4 palabras. **No más de 820 px de ancho**: más choca con la columna de botones.
- **Resaltar 20–25 % de los subtítulos**, uno cada 2–3 s. **Solo la palabra clave**: sustantivos concretos, cifras y nombres de producto, no la línea entera.
- Tamaños (escala de CapCut; en px ≈ ×6): 10 base · 12 énfasis · 13 listas · 14 los 2–3 golpes fuertes del video.
- **Si un gráfico ya dice lo mismo que el subtítulo, apagar el subtítulo.** Repetir la frase en dos lugares se ve descuidado.
- Corregir de paso las mayúsculas raras y lo que se oyó mal, usando el glosario.

# Paso 5 · Gráficos

## Zonas seguras (mandan sobre todo lo demás)

La interfaz de Instagram, TikTok y Shorts se come la parte de arriba y la de abajo, además de la columna de botones de la derecha. Se usa la guía más apretada:

```
canvas 1080x1920
0    – 250   MUERTA   hora, isla, encabezado        → nada
250  – 1500  SEGURA
1500 – 1920  MUERTA   caption, usuario, audio        → nada
x 960–1080 desde y≈1000   columna de botones         → nada
x 0–60                    margen izquierdo
```

| Qué | Dónde |
|---|---|
| Subtítulos | arriba de la frente, banda ~300–420 px |
| Gráficos y tarjetas | cuello y pecho: caja `x 120–900, y 1080–1480` |
| Nunca | sobre los ojos ni la boca: tapar la cara mata la conexión |

**Nada empieza arriba de la barbilla**, incluidos los frames de rebote de las animaciones. **Revisar el bbox de cada PNG con código, no a ojo:**

```python
for n in sorted(os.listdir(ASSETS)):
    b = Image.open(os.path.join(ASSETS, n)).getbbox()
    assert not b or (b[0]>=60 and b[1]>=250 and b[2]<=960 and b[3]<=1500), (n, b)
```

## ⚠️ Regla de oro: componer y mirar antes de seguir

Antes de dar un gráfico por bueno, pegarlo sobre el frame real y **verlo**, con las zonas muertas en rojo (en `SALIDA = mp4`, `render.py --frame` ya saca el frame compuesto):

```python
d = ImageDraw.Draw(frame)
d.rectangle((0,0,1080,250), outline="red", width=4)
d.rectangle((0,1500,1080,1920), outline="red", width=4)
d.rectangle((960,1000,1080,1920), outline="red", width=4)
```

Componer también **frames intermedios** de cada animación, no solo el estado final: ahí aparecen los textos encimados.

## Dos modos de gráfico (se combinan en el mismo video)

| | Sobre el pecho | Corte a explicación |
|---|---|---|
| Qué es | Tarjeta encima del video mientras la persona habla a cámara | Pantalla completa sin la cara: una escena que muestra cómo funciona algo |
| Cuándo | Nombra algo: una app, un rol, una cifra, un llamado a la acción | Describe un proceso con pasos, un antes y después, datos que se pueden dibujar |
| Duración | Lo que dure la mención | 2.5–5 s. Menos de 2 s parpadea; más de 6 s pierde a la persona |

- La cara se queda en el gancho (siempre el primer segundo), en los arranques de sección, en las frases con emoción u opinión y en el llamado a la acción. Debe ganar: 50–65 % del video con la persona a cuadro.
- El corte entra al inicio de una palabra y regresa al inicio de otra, en un frame con ojos abiertos.
- Con `EXPLICACIONES = no`, o si el video es pura anécdota u opinión: sin cortes a explicación.

## Repertorio (elegir según lo que se dice)

| Lo que pasa en el video | Recurso |
|---|---|
| Enumera 2–4 cosas | Lista que crece, con un ícono por renglón (no viñetas) |
| Una herramienta avisa algo | Réplica de una notificación del teléfono |
| Nombra una app | Tarjeta con el logo real de la app + nombre + qué hace |
| Dice una cifra o un precio | La cifra en el acento y más grande dentro del subtítulo |
| Hace una cuenta | Tarjeta que crece renglón por renglón conforme lo dice |
| Cita un mensaje de un cliente | Burbuja de chat sola, sin fondo de conversación |
| Contrasta antes y después | Dos colores o dos tamaños en la misma línea |
| Llamado a comentar | La palabra clave grande + barra de comentario que se escribe sola |
| Pausa dramática | Frame limpio, sin subtítulo |

Datos falsos pero creíbles en todas las réplicas. Nunca datos reales de clientes.

## ⚠️ Animación: nada de huecos y todo entra con efecto

- Cada estado es un layout completo. Si después entra un elemento, la tarjeta **crece** y lo que ya estaba se queda en su lugar. Nunca reservar el hueco desde antes.
- Nada "aparece" de golpe. **Entrada con resorte**: sube ~46 px, escala 0.92 → 1, ~0.6 s, ~12 % de sobretiro. Salida: 0.25 s, se desvanece y baja 20 px.

```python
import math
def resorte(t, dur=0.62, zeta=0.55, f=2.2):   # t en s → 0..1
    if t >= dur: return 1.0
    w = 2*math.pi*f; wd = w*math.sqrt(1-zeta**2)
    return 1 - math.exp(-zeta*w*t)*(math.cos(wd*t) + zeta*w/wd*math.sin(wd*t))
```

- **Pre-renderizar cada frame de la animación** como PNG de 1080x1920 con alfa, desde UNA función de dibujo parametrizada. Frecuencia mixta para no generar miles de archivos: 30 fps en las transiciones y un PNG cada 3 frames en los holds, descrito en un `segs.json` (`{"segs": [{"f": "f_0000.png", "start": 0, "frames": 3}, ...]}`).
- ⚠️ **Cada versión de gráficos va en una carpeta nueva** (`v2/`, `v3/`). Nunca sobrescribir un PNG con el mismo nombre.

### Escenas de explicación a pantalla completa

Una página HTML con una función `render(t)` **determinista** (sin transiciones CSS: cada elemento calcula su estado desde `t`), renderizada con Playwright y Chromium a un PNG por frame y codificada a un mp4 por escena:

```bash
ffmpeg -framerate 30 -start_number F0 -i f_%04d.png -frames:v N -c:v libx264 -preset slow -crf 16 \
  -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 -movflags +faststart escena.mp4
```

Revisar primero una hoja de contacto de 10–15 tiempos con las zonas muertas dibujadas. La escena debe arrancar con algo moviéndose. Variar la composición en cada video. Sobre fondo claro, los subtítulos van en tinta oscura y sin sombra.

---

# Estilos

El perfil escoge uno de cada uno. **Un solo estilo de gráficos por video**: mezclarlos se ve a plantilla.

## Subtítulos

| | clasico | minimal | caja |
|---|---|---|---|
| Letra | `FUENTE_SUBTITULOS` en negritas, 60 px | misma fuente, 46 px | mayúsculas, 70 px |
| Color | blanco; la palabra clave en `ACENTO` y más grande | blanco, sin color: el énfasis es solo el tamaño de la frase | blanco con contorno negro; la palabra clave en negro sobre una caja del `ACENTO` |
| Sombra | dura, negra α 0.65, 6 px abajo-derecha | suave, difuminada 6 px | contorno de 5 px |
| Cuándo va bien | casi siempre; el más legible sobre cualquier fondo | videos calmados, marca sobria | videos con mucha energía |

`scripts/render.py` dibuja los tres. En `SALIDA = capcut`, `clasico` y `minimal` se replican con los campos de estilo del texto (ver *Paso 6B*); `caja` depende de que la versión de CapCut tenga fondo por palabra: si no, usar `clasico` y decírselo.

## Gráficos

**vidrio** — réplicas de componentes de iPhone (notificaciones, widgets, mosaicos) sobre vidrio esmerilado. Un PNG no puede desenfocar lo que tiene detrás, así que el vidrio se renderiza frame por frame desde el crudo: recortar la caja de la tarjeta más 80 px de margen → `GaussianBlur(26)` → saturación ×1.8 → tinte blanco α 0.22 → 0.08 de arriba a abajo → máscara de rectángulo redondeado (radio 56) supersampleada ×4 → borde claro de 2 px → sombra de caída negra α 0.55, 30 px abajo, blur 30 → contenido encima. Si la ropa es clara o hay luz fuerte detrás del pecho, tinte oscuro `#2C2C30` α ~0.62: el vidrio claro se lava.

**plano** — tarjeta opaca, sin desenfoque ni sombra grande: blanco `#FFFFFF` con texto `#111111` (o negro `#141414` con texto blanco si el fondo es claro), radio 28, borde de 1 px α 0.08, sombra mínima (α 0.18, 8 px). El `ACENTO` solo en un detalle: el ícono, una barra, la cifra. Letra `FUENTE_GRAFICOS` SemiBold. Movimiento corto: entra en 0.35 s sin rebote.

**stickers** — recortes con borde blanco de 9 px, radio 28, rotados ±3–8°, colores saturados (el `ACENTO` como relleno), sombra suave. Notas a mano con una fuente manuscrita (Caveat) y flechas dibujadas que se trazan. Entran con `pop` (escala 0.6 → 1.06 → 1) o caen girando. Va bien con mucha energía; con `RECURSOS = pocos` se ve fuera de lugar.

Para los tres:
- **Íconos de verdad**, no dibujados con primitivas: Lucide (`npm pack lucide-static`, SVG → PNG con `cairosvg`). Logos de apps: `npm pack @iconify-json/logos`, o del sitio oficial.
- `FUENTE_GRAFICOS` distinta de la de subtítulos (Inter: `npm pack @fontsource/inter`). Google Fonts y muchos CDN están bloqueados en sandboxes; npm pasa.
- Nada de cromo de ventana (los tres puntitos rojo/amarillo/verde): es lo que más delata una plantilla.

---

# Paso 6A · Render directo (`SALIDA = mp4`)

El video final sale de los crudos con ffmpeg y Python. Sin CapCut, sin archivo de proyecto, funciona en Mac, Windows y Linux.

**Requisitos:** `ffmpeg`, Python 3 con `Pillow`, y la fuente de subtítulos como `.ttf` (Rubik Bold: `npm pack @fontsource/rubik`, y convertir el `.woff2` con `fontTools` + `brotli`).

**Cómo:** escribir un `edicion.json` con las tomas, los subtítulos, las capas de gráficos, los cortes, los sonidos y el estilo, y correr `scripts/render.py` (viene con esta skill; el formato completo está al inicio del script):

```bash
python3 render.py edicion.json --frame 6.2 revisar.jpg   # un frame compuesto, para revisar
python3 render.py edicion.json 4.0 9.5                   # solo un tramo
python3 render.py edicion.json                           # el video completo
```

- Medido en una Mac: ~2 s de render por segundo de video. Un Reel de 45 s sale en menos de 2 minutos.
- **Tiempos de los subtítulos en segundos de la línea de tiempo final**, no del crudo.
- Las capas son carpetas de PNG 1080x1920 con alfa (con o sin `segs.json`). Los cortes a explicación son mp4 opacos; marcar `"tinta": true` si son claros.
- **Revisar por tramos**: renderizar el tramo que cambió y mandárselo a la persona, no el video entero cada vez.
- **Sonidos**: sin CapCut no hay librería. Pedirle a la persona sus archivos, o que los baje de un banco de efectos con licencia libre, escoja con el oído, y Claude los coloca. Antes de colocar uno, medir dónde está su golpe:

```bash
ffmpeg -nostats -i X.mp3 -af "astats=metadata=1:reset=3,ametadata=print:key=lavfi.astats.Overall.RMS_level" -f null -
```

  `en` del sonido = momento del video − offset del golpe. Un sonido por idea, no por corte. Volúmenes: golpes 0.6–0.7, clicks 0.55, acentos 0.35.
- **Cambios**: la persona no tiene línea de tiempo para retocar. Cada corrección es editar `edicion.json` y volver a renderizar el tramo. Dejar el `edicion.json` limpio y comentado en la carpeta del video: es "el proyecto".
- Exportar también un `.srt` de los subtítulos por si la persona quiere subirlos aparte.

# Paso 6B · Dentro de CapCut (`SALIDA = capcut`)

Para quien quiere retocar a mano en una línea de tiempo. Claude no mueve la interfaz: lee y escribe el archivo del proyecto (`draft_info.json`), que es JSON. CapCut descarta los cambios en silencio si no se hacen exactamente así.

**Requisitos:** CapCut **de escritorio** (probado en Mac; la de celular no deja leer el proyecto). ⚠️ **Si el archivo del proyecto no es JSON legible, parar**: esa versión de CapCut lo cifra y este modo no sirve. Decírselo y cambiar a `SALIDA = mp4`. No intentar romper el cifrado.

## Acceso

| | Ruta del proyecto |
|---|---|
| Mac (descarga directa) | `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/<NOMBRE>/` |
| Mac (App Store) | `~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Projects/com.lveditor.draft/<NOMBRE>/` |
| Windows | `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\<NOMBRE>\` (no probado) |

- Los crudos viven donde la persona los tenga; sus rutas están en `materials.videos[].path`.
- Si Claude trabaja a través de una carpeta montada, la ruta montada no es la real. **Las rutas dentro del JSON siempre son las reales** de la máquina de la persona.
- Escribir los JSON con archivo temporal + `os.replace`: si la conexión se corta a media escritura, no queda un JSON truncado.

## ⚠️ Las dos copias

```
<proyecto>/draft_info.json                              (raíz)
<proyecto>/Timelines/<TIMELINE_ID>/draft_info.json      ← el que CapCut lee
```

**Escribir siempre los 6 archivos con el mismo contenido**: `draft_info.json`, `draft_info.json.bak` y `template-2.tmp`, en la raíz Y en `Timelines/<id>/` (`main_timeline_id` de `Timelines/project.json`). Si la versión no tiene carpeta `Timelines`, solo existe la raíz.

## Procedimiento

1. **Verificar que no exista `.locked`** en la carpeta del proyecto. Si existe, CapCut está abierto: pedir que lo cierren y NO escribir. Lo que se escriba con CapCut abierto lo pisa al salir.
2. **Reconstruir desde el archivo recién liberado**: al salir, CapCut reescribe, reajusta tiempos y aplica los cortes hechos a mano.
3. Respaldar en `<proyecto>/_backup_claude/<HHMMSS>/`.
4. Asserts: ids únicos, sin traslapes, todo dentro de `duration`, archivos referenciados existen.
5. Escribir los 6 archivos y actualizar `tm_duration` en `draft_meta_info.json`.
6. Releer del disco y volver a verificar.
7. Que la persona reabra y cierre, y **volver a contar los segmentos por pista**. Si bajó el número, algo se perdió.

## ⚠️ Cada segmento necesita un `id` nuevo

Al clonar con `copy.deepcopy`, el clon hereda el `id`. CapCut se queda con uno y **borra los demás en silencio**. En un video sobrevivieron 22 de 71 segmentos de gráficos.

```python
s = copy.deepcopy(proto)
s["id"] = U()          # SIEMPRE, sin condicionales
```

Lo mismo para materiales clonados, cada objeto de `extra_material_refs` y los ids de `common_keyframes`. CapCut a veces deja él mismo materiales repetidos: los asserts ignoran los duplicados que ya existían.

## Prototipos

El JSON no se escribe desde cero: se clonan segmentos que CapCut ya creó. **Antes de empezar, pedir que en el proyecto pongan a mano un texto y una imagen PNG cualquiera**, guarden y cierren. (Si hay subtítulos automáticos, sirven de prototipo de texto.)

## Cortes sin romper el proyecto

Que los haga la persona en la interfaz cuando se pueda. Si hay que hacerlo por archivo: **no borrar elementos de los arrays** (CapCut revierte el archivo completo). Reutilizar los segmentos que sobran con `material_id`, rangos e `id` nuevos; lo que sobre se "estaciona" (texto `" "`, `volume: 0.0`, alfa 0). Actualizar `duration` y `tm_duration`.

## Estructura del JSON

- `tracks[0]` video · `tracks[1]` subtítulos · `materials.texts[]` un objeto por subtítulo
- Tiempos en **microsegundos**; a 30 fps, redondear a `round(t*30)/30`
- `render_index` mayor = más al frente (gráficos 100, segunda capa 101)
- `clip.transform.y`: positivo = arriba, en medio canvas (`px = 960 − y·960`). Subtítulos en `+0.62`.

El `content` de un texto es un **string JSON** (copiarlo también a `base_content`); varios `styles` con distintos `range` = resaltado por palabra:

```json
{"styles":[{
  "fill":{"alpha":1.0,"content":{"render_type":"solid","solid":{"alpha":1.0,"color":[r,g,b]}}},
  "range":[inicio, fin],
  "shadows":[{"content":{"solid":{"color":[0,0,0]},"render_type":"solid"},
              "distance":8,"alpha":0.65,"diffuse":0,"angle":-45}],
  "useLetterColor":true,"size":10,"bold":true,
  "font":{"path":"<ruta de la fuente>","id":"<resource id de la fuente>"}
}],"text":"..."}
```

`color` en RGB de 0 a 1; `range` en caracteres `[inicio, fin)`. Al cambiar el texto, vaciar `words` y `current_words`. Para `minimal`: `size` 8, sin color de acento, `diffuse` alto en la sombra.

**Segmentos de imagen (`photo`)**: viven en `materials.videos` con `type: "photo"`; `extra_material_refs` necesita sus 8 objetos (`speeds`, `placeholder_infos`, `canvases`, `material_animations`, `sound_channel_mappings`, `material_colors`, `loudnesses`, `vocal_separations`) clonados con id nuevo. PNG de 1080x1920 completo, con el gráfico donde va: `transform` (0,0) y `scale` 1.0. Las secuencias de animación se montan como segmentos contiguos de 1/30 s.

**Sonidos en CapCut**: la persona abre Audio → Efectos de sonido, **arrastra a la línea de tiempo** los que le gusten (solo se descargan al tocarla), guarda y cierra. Quedan en `materials.audios[]` con su `path`.

## Lo que NO funciona en CapCut

- `clip.alpha = 0` no oculta un subtítulo: cambiar su texto a `" "`.
- Borrar segmentos del array: revierte el archivo completo.
- Repetir un `id`: borra todos menos uno.
- `.mov` con alfa (ProRes 4444): se ve negro. Usar secuencias de PNG; los mp4 opacos sí funcionan.
- Sobrescribir un PNG ya cargado con el mismo nombre: parpadean frames viejos.
- Escribir con CapCut abierto: lo pisa al salir.

---

# Paso 7 · Portada

Al final, con el corte cerrado: el frame limpio sale del corte final y el titular sale del gancho.

- Sacar candidatos de los **silencios largos (> 2 s)**, sobre todo en la cola del último clip. Montar 10–12 en una hoja de contacto y descartar: mirada hacia abajo (leyendo el guión), manos o teléfono a cuadro, boca abierta.
- Si siempre está leyendo, barrer cada 0.4 s los silencios de 2–4 s justo después de una frase dicha a cámara.
- 1080x1920. Titular de 2–3 renglones (~84 px, una palabra en el `ACENTO`) con la frase más concreta del video, de preferencia la que trae un número. Degradado oscuro de la mitad hacia abajo. Todo dentro de la franja **285–1635**, que es lo que se ve en la cuadrícula del perfil.
- **Entregar dos o tres versiones** en JPG calidad 95, menos de 8 MB. La portada se sube desde el teléfono y se puede cambiar después de publicar.

# Paso 8 · Verificación (nunca dar por hecho que se aplicó)

1. bbox de cada PNG contra las zonas seguras.
2. Frames compuestos con las líneas rojas encima (`render.py --frame` o, en CapCut, leyendo el draft).
3. Frames intermedios de cada animación.
4. Rejilla de cada corte: ojos abiertos al entrar y al salir.
5. En CapCut: asserts del JSON y conteo de segmentos después de reabrir.
6. Portada con la franja 285–1635 dibujada.
7. Lista de timecodes para la persona: qué debería ver u oír en cada uno.

---

## Fuentes

Verificar que una fuente trae un glifo antes de prometerlo:

```python
from fontTools.ttLib import TTFont
print(ord('ñ') in TTFont(FUENTE).getBestCmap())
```

Las fuentes de emoji a color no suelen estar disponibles: traer emojis de Twemoji (`npm pack @twemoji/svg`, convertir con `cairosvg`). En CapCut, las fuentes que la persona ya usó están en `.../CapCut/User Data/Cache/effect/<id>/<hash>/`.

## Bitácora (agregar una fila por video)

Lo que la persona pidió, rechazó o corrigió. Si contradice una regla de arriba, **cambiar la regla** (o el perfil), no solo ese video.

| Video | Recursos usados | Qué pidió cambiar | Regla nueva |
|---|---|---|---|
| | | | |
