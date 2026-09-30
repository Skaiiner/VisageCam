# Integracion con OBS y otras aplicaciones

## Camara virtual

VisageCam puede publicar la camara de dos formas (pestana **Camara > Salida**):

| Modo | Aparece en OBS como fuente | Aparece en Discord, Zoom, Skype, Teams |
| --- | --- | --- |
| VisageCam (Unity Capture) | Si, como Dispositivo de captura de video | Si |
| OBS Virtual Camera | No (OBS no permite usar su propia camara) | Si |

Para el modo Unity Capture instala el controlador [Unity Capture](https://github.com/schellingb/UnityCapture) ejecutando `Install.bat` como administrador.

Para OBS Virtual Camera instala OBS Studio, pulsa **Iniciar camara virtual** una vez y detenla.

## Fuente de OBS sin controladores

VisageCam publica siempre un flujo MJPEG local. En OBS:

1. Anade una **Fuente multimedia**.
2. Desmarca **Archivo local**.
3. En **Entrada** pega `http://127.0.0.1:8765/stream.mjpg` (la direccion exacta se muestra y se copia desde **Camara**).

Si el puerto esta ocupado, VisageCam prueba los siguientes y muestra la direccion vigente.

## WebSocket

1. En OBS abre **Herramientas > Ajustes del servidor WebSocket** y activa el servidor.
2. En la pestana **OBS** de VisageCam escribe servidor, puerto (4455 por defecto) y contrasena.
3. Desde ahi puedes cambiar de escena, activar o desactivar fuentes y anadir la camara de VisageCam a la escena con un clic.
