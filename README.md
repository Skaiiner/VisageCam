# VisageCam

Camara virtual para Windows 10 y 11 escrita en Python. Captura tu webcam, detecta tu cara con MediaPipe Face Mesh, aplica mascaras, accesorios e imagenes propias como filtro, retoca tu piel, cambia el fondo y publica el resultado como una webcam para Discord, Zoom, Skype, Teams y OBS.

## Caracteristicas

- **Filtros de cara**: seis mascaras incluidas que siguen tus gestos (boca, mejillas, cejas) y cualquier imagen propia: si tiene cara se deforma sobre la tuya con ajuste de color.
- **Accesorios**: sombreros, corona, gafas, bigote, auriculares y los tuyos, combinables y con ajuste individual.
- **Belleza**: piel suave, luminosidad, labios y dientes.
- **Fondo**: desenfoque o imagen propia por segmentacion.
- **Calidad**: captura a 1080p reescalada a 720p, reduccion de ruido temporal y mejora de imagen. 30 fps a 720p.
- **Salida**: camara virtual (OBS Virtual Camera o Unity Capture), flujo MJPEG para OBS sin controladores y cliente OBS WebSocket v5.
- Configuracion persistente en JSON, registro en archivo y reintento automatico si la camara se desconecta.

## Requisitos

- Windows 10 u 11.
- Python 3.10, 3.11 o 3.12.
- [OBS Studio](https://obsproject.com/) 28 o superior (abre su camara virtual una vez para registrar el dispositivo) o el controlador Unity Capture.

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m visagecam
```

Tambien puedes usar `scripts\run.bat`. Para desarrollo: `pip install -e ".[dev]"` y `scripts\run_tests.bat`.

## Uso

1. Elige la camara en **Camara**; la vista previa arranca sola.
2. En **Filtros** elige una mascara o pulsa **Anadir imagen** (o arrastra un archivo a la ventana).
3. Combina **Accesorios**, ajusta **Belleza** y elige el **Fondo**.
4. Pulsa **Iniciar camara virtual** y selecciona la camara en Discord, Zoom, Skype u OBS.

La primera vez, mira de frente con la boca cerrada durante un segundo para calibrar tu rostro; asi las mascaras siguen tus gestos.

## Estructura del proyecto

```
.
├── src/visagecam/
│   ├── capture/        captura de la webcam
│   ├── processing/     seguimiento facial, mallas, superposicion, belleza, fondo, motor
│   ├── masks/          modelo, biblioteca, importacion, recorte y generacion de recursos
│   ├── output/         camara virtual y flujo MJPEG
│   ├── obs/            cliente OBS WebSocket v5
│   ├── ui/             interfaz PySide6
│   ├── app.py          arranque
│   ├── config.py       configuracion persistente
│   └── backgrounds.py  biblioteca de fondos
├── tests/              pruebas automaticas
├── docs/               arquitectura, OBS, recursos y problemas frecuentes
├── scripts/            ejecucion, pruebas y generacion de recursos
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── CHANGELOG.md
```

## Documentacion

- [Arquitectura](docs/architecture.md)
- [OBS y otras aplicaciones](docs/obs.md)
- [Mascaras, accesorios e imagenes propias](docs/assets.md)
- [Problemas frecuentes](docs/troubleshooting.md)

## Pruebas

```bash
pip install -e ".[dev]"
pytest
```

La bateria cubre el nucleo, el renderizado con landmarks sinteticos, el cliente OBS contra un servidor simulado, el flujo MJPEG, el motor con una camara falsa y la interfaz completa.

## Configuracion y registros

- Configuracion: `%APPDATA%\VisageCam\config.json`
- Registro: `%APPDATA%\VisageCam\logs\visagecam.log`

## Vincular con un repositorio remoto de GitHub

Crea un repositorio vacio en GitHub (sin README ni .gitignore) y ejecuta, con tu URL:

```bash
git remote add origin https://github.com/TU_USUARIO/visagecam.git
git branch -M main
git push -u origin main
```
