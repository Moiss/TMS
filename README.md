# TMS Hombre Camión - NextPack

## 📦 Instalación

### Paso 1: Actualizar Lista de Aplicaciones

Para que el módulo aparezca en Odoo, necesitas actualizar la lista:

1. **Activar Modo Desarrollador:**
   - Ve a Configuración (⚙️)
   - Scroll hasta abajo
   - Haz clic en "Activar el modo de desarrollador"

2. **Actualizar Lista de Aplicaciones:**
   - Ve a Aplicaciones
   - En el menú superior, haz clic en el icono de tres puntos (⋮)
   - Selecciona "Actualizar Lista de Aplicaciones"
   - Haz clic en "Actualizar" en el popup

3. **Buscar e Instalar:**
   - En el buscador, escribe "TMS" o "Hombre Camión"
   - Haz clic en "Instalar"

### Alternativa: Desde Línea de Comandos

Si el servidor está corriendo, puedes actualizar la lista así:

```bash
# Detener el servidor (Ctrl+C en la terminal donde corre)
# Luego ejecutar:
cd /Users/macbookpro/odoo/odoo18ce
python3 odoo-18.0/odoo-bin -c proyectos/tms/odoo.conf -u base -d tms --stop-after-init
```

Luego reinicia el servidor normalmente.

## 🚀 Uso del Módulo

### Menú Principal
Una vez instalado, verás "Hombre Camión" en la barra superior.

### Workflow de Viajes
1. **Crear Viaje** (estado: Borrador)
2. **Confirmar** → estado: Confirmado
3. **Iniciar Ruta** → estado: En Ruta
4. **Entregar** → estado: Entregado

### Gastos
- Agrega gastos desde la pestaña "Gastos" en cada viaje
- La utilidad se calcula automáticamente: `Flete - Total Gastos`

## 📋 Próximos Pasos (TODOs)

### 1. Integración con Fleet
Extender `fleet.vehicle` para agregar campos específicos de transporte.

### 2. Choferes
Extender `res.partner` para agregar:
- Licencia de conducir
- Tipo de licencia
- Fecha de vencimiento
- Certificados

### 3. Carta Porte 3.1
Integrar con el SAT para generar:
- CFDI de Traslado (Tipo T)
- Complemento Carta Porte 3.1
- Autotransporte Federal

## 🔧 Estructura del Proyecto

```
tms/
├── __init__.py              # Inicializador del módulo
├── __manifest__.py          # Configuración del módulo
├── models/                  # Modelos (tablas de BD)
│   ├── tms_waybill.py      # Viajes
│   └── tms_expense.py      # Gastos
├── views/                   # Vistas XML
│   ├── tms_waybill_views.xml
│   ├── tms_expense_views.xml
│   └── tms_menus.xml
├── security/                # Seguridad
│   ├── tms_security.xml    # Grupos y reglas multi-empresa
│   └── ir.model.access.csv # Permisos por modelo
├── data/                    # Datos iniciales
│   └── ir_sequence_data.xml # Secuencias para folios
└── demo/                    # Datos de demostración
    └── tms_demo_data.xml
```

## 📝 Código Comentado

TODO el código está comentado en español línea por línea para facilitar el aprendizaje.

## 🆘 Soporte

Para soporte, contactar a NextPack.

