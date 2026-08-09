# BarrioPizzaStock IA

Sistema inteligente para planificar el abastecimiento de ingredientes de **Barrio Pizza**, una cadena de pizzerías con sucursales en Panamá. El dashboard revisa automáticamente las órdenes de compra semanales, proyecta el consumo de cada ingrediente y genera alertas claras y accionables, eliminando la necesidad de revisar producto por producto de forma manual.

## Qué resuelve

Cada semana, cada sucursal decide cuánto pedir "al ojo", lo que genera dos problemas recurrentes: pedidos de más (capital inmovilizado y producto que se vence) y pedidos de menos (quiebres de stock en pleno servicio). El dashboard automatiza esa revisión:

- **Proyecta** el consumo de la próxima semana por sucursal e ingrediente, usando el histórico de las últimas 6 semanas y una regresión que capta tendencias de crecimiento o caída (no un simple promedio).
- **Calcula la necesidad real** de cada ingrediente (proyección menos stock actual) y la compara contra lo que la sucursal efectivamente pidió, respetando que solo se compran formatos completos (sacos, cajas, latas).
- **Genera alertas priorizadas y en lenguaje natural**, por ejemplo: *"Alerta: Costa del Este está pidiendo 175 kg de Harina 00 menos que lo proyectado → riesgo de quiebre."*
- **Detecta pedidos atípicos**, comparando estadísticamente cada sucursal contra el resto para detectar comportamientos fuera de lo normal.
- **Agrupa el pedido corregido por proveedor**, listo para reenviar a cada uno.
- Permite **editar cantidades o cargar una nueva orden** desde la misma interfaz y ver las alertas recalcularse al instante.
- Incluye un **chat en español conectado a los datos** (impulsado por IA), para consultar cifras sin tener que leer tablas.

## Pestañas del dashboard

| Pestaña | Qué muestra |
|---|---|
| **Resumen** | Métricas generales del estado de las órdenes y gráficos por sucursal. |
| **Alertas y anomalías** | Alertas accionables priorizadas por urgencia, y pedidos atípicos detectados entre sucursales. |
| **Órdenes de compra** | Edición de cantidades con recálculo instantáneo, y el pedido agrupado por proveedor (descargable). |
| **Proyección y necesidad** | Detalle de consumo, proyección y necesidad por sucursal/ingrediente, con una vista comparativa entre las 4 sucursales. |
| **Chat con los datos** | Consultas en español sobre pedidos, stock e ingredientes, respondidas con IA sobre los datos reales. |

---

## Cómo correrlo

```bash
git clone <repositorio>
cd <repositorio>
pip install -r requirements.txt
streamlit run app.py
```

### Habilitar el chat con los datos (IA)

La pestaña "Chat con los datos" utiliza el modelo de IA **Gemini**, de Google, para responder preguntas en español sobre los pedidos, el stock y los ingredientes, sin que el usuario tenga que leer tablas. Para que funcione, el sistema necesita una **clave de API**: una especie de contraseña única que identifica al proyecto ante Google y le permite hacer esas consultas de forma autorizada y medida (similar a una llave que abre el servicio, pero solo para quien la tiene).

#### Paso 1: Generar la clave de API

1. Ingresar a [Google AI Studio](https://aistudio.google.com/) con una cuenta de Google (puede ser cualquier cuenta de Gmail; no requiere ser una cuenta corporativa).
2. Buscar el botón **"Get API key"** (o "Crear clave de API"), generalmente visible en la esquina superior o en el menú lateral.
3. Seleccionar **"Create API key"** y, si se solicita, elegir o crear un proyecto de Google Cloud asociado (Google lo guía automáticamente en este paso; no requiere configuración adicional).
4. Copiar la clave generada. Tiene un formato similar a `AIza...` y debe tratarse como una contraseña: no compartirla por chat, correo, ni publicarla en ningún sitio.

> Google ofrece una cuota gratuita mensual para uso con Gemini, suficiente para pruebas y uso moderado como el de este dashboard. Si el consumo crece, se puede vincular una forma de pago desde el mismo panel de Google AI Studio.

#### Paso 2: Configurar la clave en el proyecto

**Para uso local (en la computadora):**

Crear un archivo llamado `secrets.toml` dentro de una carpeta `.streamlit` en la raíz del proyecto (es decir: `.streamlit/secrets.toml`), con el siguiente contenido:

```toml
GEMINI_API_KEY = "clave_generada_aquí"
```

Streamlit detecta este archivo automáticamente al iniciar la app; no requiere ningún paso adicional en el código.

**Para el dashboard publicado (Streamlit Community Cloud):**

1. Entrar a [share.streamlit.io](https://share.streamlit.io) y abrir la app.
2. Ir a los tres puntos (⋮) → **Settings** → **Secrets**.
3. Pegar el mismo contenido:
   ```toml
   GEMINI_API_KEY = "clave_generada_aquí"
   ```
4. Guardar. La app se reinicia automáticamente y toma la clave; si no lo hace sola, se puede forzar con **Reboot app**.

Este método reemplaza la necesidad de crear el archivo manualmente en la nube: la plataforma lo genera internamente a partir de lo que se pega en ese panel.

#### Paso 3: Verificar que funciona

Con la clave configurada, basta con abrir la pestaña "Chat con los datos" y escribir una pregunta de prueba, por ejemplo: *"¿qué sucursal está pidiendo demasiado queso?"*. Si responde con datos concretos, la configuración quedó correcta.

Si en cambio aparece un error, lo más común es que la clave no se haya guardado con el nombre exacto `GEMINI_API_KEY`, o que no se haya reiniciado la app después de configurarla.

#### Consideraciones importantes

- Esta clave es privada y **no debe compartirse ni subirse al repositorio de GitHub**. Por eso, el archivo `.streamlit/secrets.toml` debe agregarse al `.gitignore` del proyecto. Si quedara expuesta públicamente, cualquier persona podría usarla y generar consumo a nombre del proyecto, o Google podría revocarla automáticamente al detectarla en un repositorio público.
- El resto del dashboard (proyección, alertas, órdenes por proveedor) **funciona con total normalidad sin esta clave**; únicamente la pestaña de chat queda inactiva si no está configurada.
- Internamente, el chat solo puede consultar la información ya calculada por el sistema, a través de una función controlada con una lista fija de columnas permitidas. Esto significa que la IA no tiene acceso libre a los datos ni puede modificarlos: siempre responde en base a las cifras reales del análisis, nunca las inventa.

Una vez iniciada la app, se deben cargar los 4 archivos CSV solicitados (`consumo_historico`, `ingredientes`, `inventario_actual`, `orden_compra_semana`) y presionar **"Analizar archivos"**.

---

## Supuestos realizados

- El histórico de consumo cubre exactamente 6 semanas (`S1`–`S6`); la proyección corresponde a la semana `S7`.
- Las claves de cruce entre archivos son `sucursal` e `ingrediente_id`, normalizadas a minúsculas y sin espacios para evitar descalces por formato.
- Un ingrediente sin formato de compra válido no genera pedido sugerido, en lugar de interrumpir el cálculo.
- Una línea ausente en la orden de compra se interpreta como un ingrediente **no incluido** en el pedido, y se prioriza como la alerta de mayor urgencia.
- Cualquier diferencia menor a un formato completo se considera redondeo normal, no un error de sobre o subpedido.
- Los sobrepedidos de ingredientes perecederos se marcan como urgentes, por su mayor riesgo de merma.

---

## Cómo se conectaría a Odoo en producción

Si esta herramienta se llevara a producción sobre un ERP como Odoo, el flujo pasaría de cargar CSV manualmente a una integración en tiempo real:

1. **Reemplazar la carga de archivos** por llamadas a la API de Odoo (XML-RPC/JSON-RPC o el módulo `odoorpc`):
   - `product.product` / `product.template` → catálogo de ingredientes.
   - `stock.quant` → inventario actual por sucursal.
   - `stock.move` (o los movimientos de salida del punto de venta) → consumo histórico.
   - `purchase.order` / `purchase.order.line` → la orden de compra de la semana, y también el destino donde escribir el pedido sugerido corregido.
2. **Automatizar la ejecución** con un cron nativo de Odoo (`ir.cron`) que corra el cálculo de proyección y alertas cada semana, guardando los resultados en un modelo propio o mostrándolos en un dashboard embebido dentro de Odoo.
3. **Cerrar el ciclo**: en lugar de solo alertar, el sistema podría pre-llenar automáticamente las líneas de `purchase.order` con la cantidad sugerida por proveedor, dejando que la gerencia de compras solo apruebe o ajuste — acercándose a la visión final de la herramienta.
4. **Gestionar el acceso** mediante un usuario de servicio con permisos de solo lectura sobre inventario y ventas, y de escritura sobre órdenes de compra, con credenciales gestionadas de forma segura.
5. La lógica de proyección, cálculo de necesidad y alertas no requeriría cambios, ya que está desacoplada de la interfaz: solo cambiaría el origen y destino de los datos.
