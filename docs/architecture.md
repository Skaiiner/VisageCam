# Arquitectura

## Flujo de datos

```
Webcam ──► capture ──► engine ──► processing.pipeline ──► engine ──┬─► output (camara virtual)
                                                                    ├─► output (flujo MJPEG para OBS)
                                                                    └─► ui (vista previa)
```

1. `capture.CameraCapture` lee la webcam en un hilo propio (Media Foundation con respaldo DirectShow) y publica siempre el ultimo fotograma.
2. `processing.Engine` toma cada fotograma nuevo, lo reescala a la resolucion de salida y lo pasa por `FramePipeline`.
3. `FramePipeline` ejecuta tres trabajos en paralelo:
   - hilo principal: reduccion de ruido temporal y mejora de imagen a resolucion completa;
   - seguimiento facial (MediaPipe Face Mesh) sobre una copia de 640 px;
   - segmentacion de fondo (MediaPipe) y fondo desenfocado o imagen.
4. Con los puntos faciales se dibujan, en este orden: belleza, mascara y accesorios.
5. Un hilo de salida separado envia el resultado a la camara virtual y al flujo MJPEG para no bloquear el procesado.

## Paquetes (`src/visagecam`)

| Paquete | Responsabilidad |
| --- | --- |
| `capture` | Enumeracion de camaras y captura con hilo dedicado. |
| `processing` | Seguimiento facial (una o dos personas), deformacion por malla, superposiciones, belleza, deformaciones en vivo, fondo, mejora de imagen y motor. |
| `masks` | Modelo de mascara, almacenamiento JSON/PNG, biblioteca, importacion de imagenes, recorte de fondo y generador. El subpaquete `catalog` agrupa los disenos incluidos: `creatures`, `robots`, `masquerade` y `accessories`. |
| `output` | Camara virtual (`pyvirtualcam`) y servidor MJPEG. |
| `obs` | Cliente OBS WebSocket v5. |
| `ui` | Interfaz PySide6: tema, iconos, componentes, estudio de imagenes y ventana principal. El subpaquete `pages` contiene un modulo por pagina. |
| raiz | `app.py` (arranque), `config.py` (configuracion persistente), `logging_setup.py`, `backgrounds.py`. |

## Como se renderiza una mascara

- **Mascara con anclas** (las incluidas): una transformacion afin calculada con los puntos estables del rostro coloca la imagen. Si el rostro esta calibrado y "Seguir mis gestos" esta activo, la zona de la cara se sustituye por una capa deformada triangulo a triangulo con la malla de 468 puntos, y se mezcla con la capa rigida en los bordes.
- **Imagen con cara**: se detectan sus puntos al importarla y se deforma sobre el rostro, con ajuste de color y de bordes.
- **Imagen sin cara o accesorio**: se ancla segun su zona (cabeza, ojos, boca, orejas o libre) con escala, giro y desplazamiento propios.

## Hilos

| Hilo | Funcion |
| --- | --- |
| `camera-capture` | Lectura de la webcam. |
| `engine` | Procesado de fotogramas. |
| `engine-output` | Envio a camara virtual y MJPEG. |
| `visagecam-N` | Seguimiento facial y fondo en paralelo. |
| hilo de la interfaz | Vista previa y controles; las tareas lentas usan `AsyncRunner`. |

Los ajustes se comparten mediante el objeto `Settings`; la interfaz los modifica y el motor los lee en cada fotograma.
