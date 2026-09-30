# VisageCam

Camara virtual para Windows 10 y 11 escrita en Python. Captura tu webcam, detecta la cara con MediaPipe Face Mesh, aplica una mascara o una imagen cualquiera como filtro, cambia el fondo y publica el resultado como una webcam que Discord, Zoom, Skype u OBS pueden usar.

## Caracteristicas

- Captura con OpenCV (DirectShow, MJPG) optimizada para 1280x720 a 30 fps.
- Seguimiento facial con 468 puntos y suavizado temporal para evitar temblores.
- **Cualquier imagen como filtro**, con acabado realista (ver mas abajo).
- Sustitucion de fondo por segmentacion de MediaPipe: desenfoque o imagen propia.
- Salida como camara virtual con `pyvirtualcam` y el backend de OBS.
- Cliente OBS WebSocket v5: cambio de escena y activacion de fuentes desde la aplicacion.
- Configuracion persistente en JSON y registro en archivo.

## Requisitos

- Windows 10 u 11.
- Python 3.10, 3.11 o 3.12 (MediaPipe aun no ofrece ruedas para versiones mas recientes).
- [OBS Studio](https://obsproject.com/) 28 o superior. Hace falta para registrar el dispositivo de camara virtual: abre OBS, pulsa **Iniciar camara virtual** una vez y detenla. Despues puedes cerrar OBS.

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m visagecam
```

Tambien puedes ejecutar `run.bat`.

## Uso

1. Elige la camara y la resolucion en el panel derecho. La vista previa arranca sola.
2. En **Mascaras** elige una de la galeria o pulsa **Cargar imagen...** para usar una propia.
3. Ajusta escala, rotacion, desplazamiento, opacidad y los controles de realismo.
4. En **Fondo** elige desenfoque o una imagen propia.
5. Pulsa **Iniciar camara virtual** y selecciona **OBS Virtual Camera** como webcam en Discord, Zoom, Skype u OBS.

### Cualquier imagen como filtro

Al cargar una imagen, VisageCam la analiza y decide como usarla:

| Tipo de imagen | Que hace |
| --- | --- |
| Foto o dibujo con una cara | Detecta sus 468 puntos y deforma la imagen triangulo a triangulo sobre tu cara, siguiendo tus gestos. Tus ojos y tu boca se conservan (opcional) para que la expresion siga viva. |
| PNG con transparencia (gafas, sombrero, mascara) | Se superpone centrada en tu cara y orientada segun la inclinacion de tu cabeza. |
| Imagen sin transparencia ni cara | Se elimina el fondo automaticamente y se trata como una pegatina. |

Para que el resultado parezca real:

- **Ajuste de color**: iguala el tono y el contraste de la imagen con la piel que ve la camara, en espacio LAB y suavizado en el tiempo.
- **Ajuste de luz**: adapta el brillo de las superposiciones a la iluminacion de tu habitacion.
- **Bordes suaves**: difumina y encoge el contorno para eliminar el efecto de recorte.
- **Conservar ojos y boca**: deja pasar tus ojos y tu boca reales a traves de la imagen.
- Los puntos faciales se filtran con un filtro adaptativo que elimina el temblor sin anadir retraso al moverte.

Consejos: usa fotos frontales, bien iluminadas y sin gafas ni pelo tapando la frente; cuanto mas parecida sea la pose de la foto a la tuya, mas creible sera el resultado. Si una imagen con cara prefieres usarla como pegatina, desactiva **Deformar la imagen sobre mi rostro**.

Las imagenes cargadas se guardan en `%APPDATA%\VisageCam\masks\custom` junto con un JSON. Puedes eliminarlas desde la galeria.

## Accesorios y belleza

- **Accesorios**: sombrero de copa, gorro de fiesta, corona, gafas de sol, bigote y auriculares. Se pueden combinar varios a la vez, con o sin mascara, y cada uno tiene su propia escala, rotacion y desplazamiento. Con **Anadir imagen...** conviertes cualquier PNG en accesorio y eliges donde se ancla: cabeza, ojos, boca, orejas o libre. Si la imagen no tiene transparencia se recorta el fondo.
- **Belleza**: piel suave, luminosidad, color de labios y blanqueado de dientes, aplicados solo sobre el rostro.
- Hay seis mascaras incluidas: zorro, robot retro, dragon, gato astronauta, alienigena de un ojo y oso vintage.

## Que la camara aparezca en OBS y en otras aplicaciones

Hay dos formas de publicar la camara, seleccionables en **Salida**:

- **VisageCam (Unity Capture)**: crea un dispositivo propio que OBS lista como *Dispositivo de captura de video*, ademas de Discord, Zoom, Skype, Teams y navegadores. Instala el controlador [Unity Capture](https://github.com/schellingb/UnityCapture) (ejecuta `Install.bat` como administrador y, si quieres, cambia el nombre del dispositivo a "VisageCam"). Despues, en la pestana **OBS** pulsa **Anadir camara VisageCam a la escena** y la fuente se crea sola.
- **OBS Virtual Camera**: sirve para Discord, Zoom, etc., pero OBS no permite usar su propia camara virtual como fuente.

Sin controlador, tambien puedes capturar la ventana de VisageCam en OBS con *Captura de ventana*.

## Mascara incluida y archivos de anclaje

La mascara del zorro se genera por codigo la primera vez que se ejecuta la aplicacion. Para exportarla manualmente:

```bash
python -m visagecam.masks.generator --out masks_out
```

Se crean `fox.png` (con transparencia) y `fox.json`, que lista los puntos del Face Mesh donde se fija cada zona:

```json
{
  "name": "Zorro",
  "image": "fox.png",
  "anchors": [
    { "name": "eye_left", "landmarks": [33, 133, 159, 145], "point": [397, 430] },
    { "name": "nose_tip", "landmarks": [1], "point": [512, 614] }
  ]
}
```

Cada ancla asocia un punto de la imagen (en pixeles) con la media de los landmarks indicados. Puedes crear tu propia mascara colocando un PNG y un JSON con este formato en `%APPDATA%\VisageCam\masks\custom`. Nuevos disenos se anaden registrando una funcion en `visagecam/masks/designs.py`.

## OBS WebSocket

1. En OBS abre **Herramientas > Ajustes del servidor WebSocket** y activa el servidor.
2. En la pestana **OBS** de VisageCam escribe servidor, puerto (4455 por defecto) y contrasena, y pulsa **Conectar**.
3. Elige una escena y pulsa **Cambiar a esta escena**, o marca y desmarca fuentes para activarlas o desactivarlas.

## Estructura

```
visagecam/
  capture/      captura de la webcam
  processing/   seguimiento facial, deformacion, superposicion, fondo, motor
  masks/        generacion de mascaras, biblioteca e importacion de imagenes
  output/       camara virtual
  obs/          cliente OBS WebSocket v5
  ui/           interfaz PySide6
  config.py     configuracion persistente
```

## Configuracion y registros

- Configuracion: `%APPDATA%\VisageCam\config.json`
- Registro: `%APPDATA%\VisageCam\logs\visagecam.log`

## Rendimiento

- 1280x720 a 30 fps es el objetivo. Si tu equipo no llega, baja a 960x540.
- Muchas webcams reducen los fotogramas por segundo con poca luz (compensacion automatica). Ilumina bien la habitacion o desactiva esa opcion en el software del fabricante.
- El desenfoque y la sustitucion de fondo consumen mas CPU que las mascaras.

## Problemas frecuentes

- **No se pudo iniciar la camara virtual**: instala OBS Studio y abre su camara virtual una vez.
- **No aparece mi webcam**: cierra otras aplicaciones que la esten usando y pulsa **Actualizar**.
- **La camara virtual muestra otra imagen**: en la aplicacion de videollamada elige **OBS Virtual Camera**.

## Vincular con un repositorio remoto de GitHub

1. Crea un repositorio vacio en GitHub (sin README ni .gitignore).
2. Ejecuta, sustituyendo la URL por la tuya:

```bash
git remote add origin https://github.com/TU_USUARIO/visagecam.git
git branch -M main
git push -u origin main
```
