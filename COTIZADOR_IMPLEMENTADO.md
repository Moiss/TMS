# ✅ COTIZADOR DE FLETES IMPLEMENTADO

## 🎉 Paso 3 Completado

Se ha implementado el Cotizador de Fletes con lógica inteligente de autocompletado y cálculo de 3 propuestas automáticas.

---

## 📦 MODELOS CREADOS:

### 1. **tms.quotation** - Cotización de Flete
**Archivo:** `models/tms_quotation.py` (270+ líneas comentadas)

**Campos por Paso:**

#### Paso 1: Origen y Destino
- `origin_municipio_id` - Municipio origen (catálogo SAT)
- `dest_municipio_id` - Municipio destino (catálogo SAT)
- `origin_address` / `dest_address` - Direcciones completas
- `distance_km` - Distancia (autocompletada o manual)
- `duration_hours` - Duración (autocompletada o manual)

#### Paso 2: Mercancías
- `line_ids` - One2many a líneas de cotización
- `total_weight_kg` - Peso total (calculado)
- `total_items` - Cantidad de artículos (calculado)

#### Paso 3: Operaciones y Costos
- `vehicle_id` - Vehículo asignado
- `driver_id` - Chofer
- `trailer1_id` / `trailer2_id` - Remolques
- **Costos Base:**
  - `fuel_price_liter` - Precio diesel
  - `fuel_performance` - Rendimiento Km/L
  - `cost_tolls` - Casetas
  - `cost_maneuver` - Maniobras
  - `cost_driver` - Pago chofer
  - `cost_other` - Otros

#### Paso 4: Propuestas y Resumen
- **Propuesta 1: Por KM**
  - `price_per_km` - Precio por kilómetro
  - `prop_km_total` - Total calculado

- **Propuesta 2: Por Viaje**
  - `diesel_total_cost` - Costo diesel calculado
  - `profit_percentage` - % de utilidad deseada
  - `total_costs` - Costos totales calculados
  - `prop_trip_total` - Total calculado

- **Propuesta 3: Directa**
  - `prop_direct_amount` - Monto fijo manual

- `selected_proposal` - Cuál propuesta se usará
- `amount_final` - Monto final (según propuesta seleccionada)

### 2. **tms.quotation.line** - Mercancías
**Archivo:** `models/tms_quotation_line.py` (150+ líneas comentadas)

**Campos:**
- `product_sat_id` - Clave SAT del producto
- `description` - Descripción de la mercancía
- `quantity` - Cantidad
- `uom_sat_id` - Unidad SAT
- `weight_kg` - Peso en kilogramos
- `dimensions` - Dimensiones
- `is_dangerous` - Material peligroso (auto-detectado)

---

## 🧠 LÓGICA INTELIGENTE IMPLEMENTADA:

### 1. **Autocompletado de Ruta** (`_onchange_route_autocomplete`)
```
Usuario selecciona: Monterrey → CDMX

Sistema busca en tms.destination:
  ¿Existe ruta Monterrey-CDMX?

  SI existe:
    ✅ Pre-llena distancia: 920 km
    ✅ Pre-llena duración: 12 hrs
    ✅ Pre-llena casetas: $1,200
    ✅ Muestra mensaje: "Ruta encontrada"

  NO existe:
    ℹ️ Deja campos en 0
    ℹ️ Usuario captura manualmente
```

### 2. **Detección de Material Peligroso** (`_compute_is_dangerous`)
```
Usuario selecciona producto SAT: "1203 - Gasolina"

Sistema revisa catálogo SAT:
  material_peligroso = '1'

  ✅ Marca automáticamente is_dangerous = True
  ⚠️ El usuario sabe que necesita documentación adicional
```

### 3. **Rendimiento del Vehículo** (`_onchange_vehicle_performance`)
```
Usuario selecciona vehículo: "Volvo FH16"

Sistema trae del vehículo:
  performance_km_l = 3.5 Km/L

  ✅ Pre-llena fuel_performance = 3.5
  ✅ Se usa automáticamente en cálculo de diesel
```

### 4. **Cálculo de 3 Propuestas** (`_compute_proposals`)

#### Propuesta 1: Por Kilómetro
```python
# Fórmula:
Total = (Distancia * Precio/KM) + Gastos Extra

# Ejemplo:
Distancia = 920 km
Precio/KM = $15
Gastos Extra = Casetas($1,200) + Maniobras($500) = $1,700

Total = (920 * 15) + 1,700 = $13,800 + $1,700 = $15,500
```

#### Propuesta 2: Por Viaje (Basada en Costos Reales)
```python
# Paso 1: Calcular diesel
Litros = Distancia / Rendimiento = 920 / 3.5 = 263 litros
Costo Diesel = 263 * $24 = $6,312

# Paso 2: Sumar costos
Costos = Diesel + Casetas + Chofer + Maniobras + Otros
Costos = $6,312 + $1,200 + $3,000 + $500 + $200 = $11,212

# Paso 3: Aplicar utilidad
Utilidad = 20%
Total = $11,212 * 1.20 = $13,454
```

#### Propuesta 3: Directa
```
Usuario captura: $14,000
Total = $14,000 (sin cálculos)
```

### 5. **Monto Final** (`_compute_amount_final`)
```
Usuario selecciona: "Propuesta Por Viaje"
amount_final = prop_trip_total = $13,454

Este monto se usa para facturación
```

---

## 🎯 NAVEGACIÓN DEL WIZARD:

### Botones de Navegación:
- `action_next_step()` - Avanza al siguiente paso
- `action_prev_step()` - Regresa al paso anterior

### Control de Visibilidad:
```xml
<group invisible="current_step != '1_origin'">
  <!-- Campos del Paso 1 -->
</group>

<group invisible="current_step != '2_materials'">
  <!-- Campos del Paso 2 -->
</group>
```

---

## 📋 ARCHIVOS PENDIENTES:

Para completar el cotizador falta crear:
- ❌ `views/tms_quotation_views.xml` - Vistas del wizard
- ❌ Actualizar `views/tms_menus.xml` - Agregar menú de cotizaciones

---

## 🚀 ESTADO ACTUAL:

- ✅ Modelos creados y validados
- ✅ Lógica de negocio implementada
- ✅ Autocompletado inteligente
- ✅ 3 propuestas con cálculos automáticos
- ✅ Seguridad multi-empresa
- ✅ Secuencias configuradas

**El backend está completo. Solo faltan las vistas para la interfaz.**

¿Quieres que continúe creando las vistas del cotizador?

