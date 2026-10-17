# COUGAR Studio

Aplicación independiente para administrar la pantalla de segmentos del
**COUGAR Poseidon Vistek ARGB**, USB **2C65:1000 / HWCX USB Display**.
No es para el Vistek Pro con pantalla gráfica.

## Instalar en Windows

Descarga el archivo **COUGAR-Studio-Setup-…-x64.exe** de
[la última versión](https://github.com/cgallego17/COUGAR-Studio/releases/latest).
Ejecuta el instalador y abre COUGAR Studio desde el escritorio o Inicio.
Al abrir muestra los datos de CPU; las animaciones se activan desde la interfaz.

El instalador incluye Python, la aplicación, el servicio de sensores y el
controlador oficial firmado PawnIO. No requiere instalar Python, configurar
consolas ni descargar dependencias manualmente. Requiere Windows 10 2004 o
posterior / Windows 11 de 64 bits y permisos de administrador para instalar.
Si Windows solicita un reinicio para activar PawnIO, complétalo antes de usar
las temperaturas. El instalador de COUGAR Studio todavía no tiene firma
comercial; Windows puede mostrar una confirmación de editor desconocido.

## Funciones

- 23 diseños y vista previa de la distribución circular 3/4/3.
- Temperaturas de CPU y GPU, consumo/carga y ventilador CPU cuando hay lectura.
- Ciclo editable: añade diseños, cambia el orden y ajusta sus tiempos.
- Pausa/reanuda, velocidad y control del logo COUGAR en las temperaturas.
- Preferencias en `%LOCALAPPDATA%\COUGAR Studio`.
- Actualizaciones verificadas con SHA-256 desde las versiones de este repositorio.
- Diagnóstico exportable y reinicio del servicio de sensores desde la interfaz.

## Importar un GIF

En la pestaña **GIF**, pulsa **Importar GIF…** o **Cargar demo**. La aplicación
proyecta el brillo de cada cuadro sobre las 70 barras de los diez dígitos,
como una imagen distribuida sobre las luces de un teclado. Conserva el
movimiento aproximado, con pérdida de colores y detalles; no transforma
el panel en una pantalla de píxeles. La geometría se estima a partir de la foto.

Usa **Vista previa** para comprobar la adaptación manteniendo CPU en el
dispositivo. **Mostrar en pantalla** reproduce el GIF durante 2–60 segundos
y vuelve automáticamente a CPU. **Volver a CPU** interrumpe la reproducción;
la pausa y la velocidad general también se aplican al GIF.

Puedes ajustar el umbral de luz, invertir claros y oscuros, proyectar sobre
el área de dígitos o la cara circular, y ajustar la imagen completa o recortarla
para llenar el área. Después de cambiar estos ajustes, pulsa **Aplicar ajustes
al GIF**. Se carga un GIF a la vez para la sesión actual; no forma parte del ciclo
guardado. Las siluetas grandes, claras y sobre negro producen mejores resultados.

Límites: GIF de hasta 20 MB, 60 segundos, 4 megapíxeles, 4096 px por lado y 1200
cuadros originales. El movimiento se muestrea a 10 cuadros/s. La conversión
ocurre en el equipo y no sube el GIF a Internet.

Cuando RM-Hardware está instalado, el servicio de COUGAR Studio lo pausa durante
GIF, diseños y páginas personalizadas para evitar dos escritores USB simultáneos.
Lo restaura al volver a CPU o cerrar la aplicación. El control necesita renovarse
cada segundo y caduca tras cinco segundos sin comunicación. Solo se acepta al
ejecutable instalado en la misma carpeta protegida del servicio; la vista previa
no pausa RM-Hardware. No se cambia su tipo de inicio. Si ya estaba detenido,
se conserva ese estado. Los sensores propios siguen activos durante las escenas.

La pantalla usa segmentos fijos; no admite imágenes a resolución completa, fuentes de píxeles ni
reemplazar la forma física del logo. COUGAR sí puede encenderse y apagarse.
Se envían exclusivamente cuadros HID `03`; la aplicación no actualiza firmware
ni controla bombas o ventiladores. La disponibilidad de cada sensor depende
del hardware; una lectura ausente se muestra con guiones o vacía.

Mantén la aplicación abierta para actualizar la pantalla. Al cerrar se restaura
RM-Hardware si COUGAR Studio lo había pausado. Sin el servicio original, pueden
quedar congelados los últimos valores. No se afirma restaurar un modo autónomo
del firmware: se recupera el servicio de Windows que envía los datos.

## Actualizaciones y publicación

La pestaña **Actualizar** comprueba la última GitHub Release al abrir la app.
Permite descargar el instalador y comprobar su SHA-256 antes de abrirlo.
La instalación se inicia con confirmación del usuario; no se ejecuta código
automáticamente desde Internet.

Cada push a `main` ejecuta `.github/workflows/release.yml`: valida el código,
genera el ejecutable y el instalador, y publica una versión `0.1.N` con sus hashes
y fuentes de terceros. Subir código sin generar una Release no ofrece una
actualización a instalaciones existentes.

## Desarrollo

Para desarrollar se necesita Python 3.14, Git y Windows; el usuario final solo
necesita el instalador. Las herramientas de compilación se preparan de forma
automática y sus descargas se verifican.

```powershell
python -m pip install -r requirements-build.txt
python cougar_studio.py --preview
python -m unittest discover -s tests -v
.\build-release.ps1 -AppVersion 0.1.0
```

La prueba `python cougar_studio.py --smoke-test` abre y recorre la interfaz en
simulación: no accede a USB ni a sensores. Para leer sensores durante desarrollo
puede usarse el servicio instalado; si RM-Hardware ya está presente, se utiliza
como alternativa para las lecturas que falten.

Código de la aplicación: MIT. Consulta [los avisos de terceros](THIRD-PARTY-NOTICES.md).
