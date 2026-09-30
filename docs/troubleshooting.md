# Problemas frecuentes

| Sintoma | Solucion |
| --- | --- |
| La camara va a 10 fps | Usa la captura predeterminada (Media Foundation). Con poca luz activa **Mejora de imagen** y ilumina el rostro. |
| No aparece mi webcam | Cierra otras aplicaciones que la usen y pulsa el boton de recargar en **Camara**. |
| No se pudo iniciar la camara virtual | Instala OBS Studio y abre su camara virtual una vez, o instala Unity Capture. |
| OBS no ve VisageCam como dispositivo | Usa la fuente multimedia con la direccion MJPEG (ver `docs/obs.md`). |
| La mascara no sigue mis gestos | Mira de frente con la boca cerrada y pulsa **Recalibrar mi rostro**. |
| El filtro desaparece al girar mucho la cabeza | Con giros extremos el detector pierde la cara; el filtro se mantiene un instante y vuelve al recuperarla. |
| Rendimiento bajo | Baja la resolucion, desactiva fondo o belleza, o reduce los accesorios. |

## Registros y configuracion

- Configuracion: `%APPDATA%\VisageCam\config.json`
- Registro: `%APPDATA%\VisageCam\logs\visagecam.log`
- Rostro calibrado: `%APPDATA%\VisageCam\neutral_face.json`
