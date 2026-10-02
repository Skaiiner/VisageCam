# Mascaras, accesorios e imagenes propias

## Deformaciones de cara

Pestana **Deformar**, independiente de las mascaras: deforma tu rostro en directo en vez de superponer una imagen. Incluye ojos grandes, ojos pequenos, frente grande, boca grande, nariz pequena, menton grande, cara delgada, cabeza grande, cara mini y espejo loco (combinacion asimetrica). Tiene un control de intensidad y se puede combinar con una mascara o accesorio, porque actua sobre los pixeles de tu cara antes de dibujarlos encima.

## Efectos de camara y ajustes de imagen

Pestana **Efectos**, independiente de las mascaras y las deformaciones de cara: aplica un efecto a todo el video (tu cara, el fondo, mascaras y accesorios), al final del procesado. Se divide en dos categorias: deformar la imagen (ojo de pez, pellizco, remolino, olas, espejos, caleidoscopio, zoom, cuatro camaras) y color y estilo (blanco y negro, sepia, negativo, cartel, neon, dibujo animado, boceto, pixelado, termico, VHS, vintage, resplandor, frio, calido, vision nocturna, glitch, relieve, alto contraste). Tiene su propio control de intensidad.

Debajo, los ajustes de brillo, contraste, saturacion y temperatura corrigen el color de la camara de forma independiente, se usen o no los efectos.

## Catalogo incluido

**Mascaras de cara completa**: zorro, robot retro, dragon, gato astronauta, alienigena, oso vintage, caballero cromado, fenix, lobo tribal.

**Antifaces de mascarada** (cubren solo frente y ojos, dejan la boca y la barbilla libres, como un antifaz veneciano): veneciana dorada, mariposa, pluma negra, arlequin, ojos de gata. Se generan con las mismas anclas que las mascaras completas; la diferencia es que el PNG solo pinta la zona superior del rostro y deja transparente el resto.

**Accesorios**: sombrero de copa, gorro de fiesta, corona, gorro de lana, corona de flores, gafas de sol, monoculo, bigote, panuelo, auriculares.

## Generar los recursos incluidos

```bash
python scripts/generate_assets.py --out masks_out
```

Crea los PNG con transparencia y sus JSON de anclaje. La aplicacion los genera sola la primera vez en `%APPDATA%\VisageCam`.

## Formato JSON

```json
{
  "name": "Zorro",
  "image": "fox.png",
  "kind": "mask",
  "slot": "free",
  "size": [1024, 1024],
  "anchors": [
    { "name": "eye_left", "landmarks": [33, 133, 159, 145], "point": [397, 430] },
    { "name": "nose_tip", "landmarks": [1], "point": [512, 614] }
  ]
}
```

| Campo | Significado |
| --- | --- |
| `kind` | `mask` (filtro de cara) o `accessory`. |
| `slot` | Solo accesorios: `head`, `eyes`, `mouth`, `ears` o `free`. |
| `anchors` | Cada ancla une un punto de la imagen (en pixeles) con la media de los landmarks del Face Mesh indicados. |
| `pivot`, `width_ratio` | Opcionales en accesorios: punto de la imagen que se coloca sobre la zona y anchura respecto al ancho de la cara. |
| `face_landmarks` | Imagenes con cara: 468 puntos en pixeles, calculados al importar. |

## Imagenes propias

Desde **Anadir imagen** (o arrastrando un archivo a la ventana) el estudio analiza la imagen y propone el uso:

- con cara: filtro que se deforma sobre tu rostro;
- con transparencia: accesorio anclado a la zona elegida;
- sin transparencia ni cara: se recorta el fondo automaticamente.

Los elementos se guardan en `%APPDATA%\VisageCam\masks\custom` y `%APPDATA%\VisageCam\accessories\custom`.

## Crear nuevos disenos por codigo

Registra una funcion que devuelva un arreglo BGRA en `src/visagecam/masks/catalog/` (agrupadas en `creatures.py`, `robots.py` y `masquerade.py`, o en `accessories.py` para accesorios) y registrala en `catalog/__init__.py` y vuelve a generar. El modulo `painter.py` ofrece formas, degradados, biselado, pelo y sombras.
