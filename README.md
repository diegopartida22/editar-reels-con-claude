# Editar Reels con Claude

Una skill para que Claude edite tus Reels, TikToks y Shorts hablados a cámara a partir de los crudos:

- **transcribe** con Whisper, sin internet;
- **escoge las tomas** (descarta repeticiones y arranques en falso);
- **corta** en los silencios y revisa que no salgas parpadeando;
- pone **subtítulos** con la palabra clave resaltada y **gráficos** dentro de la zona que no tapa Instagram;
- hace la **portada**;
- y te entrega el **video terminado** (sin CapCut) o la edición **dentro de tu proyecto de CapCut** de escritorio.

La guía completa, con capturas del proceso real, está en **[diegopartida.dev/edicion](https://diegopartida.dev/edicion)**.

## Instalarla

**La forma fácil:** en [diegopartida.dev/edicion](https://diegopartida.dev/edicion) contesta el cuestionario de estilo y copia el mensaje que te da. Pégalo en Claude y él la ajusta a tu estilo y la instala.

**A mano:**

- **claude.ai o la app de Claude:** baja [`editar-reels.zip`](https://diegopartida.dev/edicion/descargar) y súbelo en la sección **Habilidades** (*Skills*) de la configuración de Claude, con la ejecución de código y creación de archivos encendida. Usa ese ZIP y no el botón *Download ZIP* de GitHub: el de GitHub mete la skill en una carpeta con otro nombre y Claude la rechaza.
- **Claude Code:** copia la carpeta `editar-reels/` a `~/.claude/skills/`.

```bash
git clone https://github.com/diegopartida22/editar-reels-con-claude
cp -R editar-reels-con-claude/editar-reels ~/.claude/skills/
```

## Cómo usarla

Ya instalada, háblale normal, como a un editor. Primero agrega en la app de Claude la carpeta donde están tus videos. Algunos mensajes que funcionan:

| Quieres | Pídele |
|---|---|
| El Reel completo | “Edita mi Reel con la skill. Mis videos están en la carpeta Videos/martes. Antes de editar, enséñame qué partes vas a usar.” |
| Algo rápido | “Edita los videos de Videos/martes solo con cortes y subtítulos.” |
| Un gráfico | “Cuando digo ‘WhatsApp’, pon una notificación con su logo debajo de mi cara.” |
| Animación a pantalla completa | “En la parte donde explico cómo me llegan los pedidos, cambia a una animación a pantalla completa que lo muestre paso a paso.” |
| El estilo de Diego | “Usa gráficos de vidrio estilo iPhone, subtítulos con la palabra clave en amarillo y animaciones sobre fondo crema, como los Reels de Diego Partida.” |
| Varios inicios | “Grabé 3 formas de empezar. Arma el Reel con cada una, con el mismo resto del video, para que yo escoja.” |
| Un cambio | “En el segundo 12 el subtítulo dice mal mi marca: es Café Lunar. Corrígelo.” |
| La portada | “Hazme 3 portadas con el título ‘Así edito en 5 minutos’.” |
| Que se acuerde | “Me gustó el color y las tarjetas de vidrio. Anótalo en mi skill.” |

Más ejemplos y el cuestionario de estilo en [diegopartida.dev/edicion](https://diegopartida.dev/edicion).

## Qué hay aquí

```
editar-reels/
├── SKILL.md            las instrucciones: perfil, pasos, estilos, reglas
└── scripts/render.py   render del video final con ffmpeg + Python, sin CapCut
```

## Qué necesitas

- Un plan de pago de Claude (Pro, Max, Team o Enterprise) y que Claude pueda leer y escribir en tus carpetas: la app de escritorio con tu computadora conectada, o Claude Code.
- `ffmpeg`, Python 3 con Pillow y Node 18+. Si te falta algo, Claude te lo dice en el primer video.
- CapCut de escritorio **solo** si quieres la edición dentro de CapCut.

## Lo que no hace

- **No oye.** Los efectos de sonido los escoges tú; Claude los coloca.
- **No ve todos los frames.** Revisa los que importan: alrededor de cada corte y en los silencios para la portada.
- **No adivina tu estilo.** El primer video lleva varias vueltas; lo que decidas queda escrito en la skill.

---

Hecha por [Diego Partida](https://diegopartida.dev). Si la usas, cuéntame cómo te fue en [Instagram](https://www.instagram.com/diegopartida.dev/).
