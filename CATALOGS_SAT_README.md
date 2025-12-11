# 📋 Catálogos SAT - Carta Porte 3.1

## ✅ IMPLEMENTACIÓN COMPLETADA

Se han integrado los catálogos oficiales del SAT para Carta Porte 3.1 en el módulo TMS.

---

## 📦 MODELOS CREADOS (Catálogos Globales)

### 1. **tms.sat.clave.prod** - Clave Producto/Servicio
- **Campos:** code, name, material_peligroso, palabras_clave
- **Uso:** Identificar mercancías transportadas según catálogo c_ClaveProdServCP
- **Archivo:** `models/sat_clave_prod.py`
- **Características:**
  - Búsqueda por código, descripción o palabras clave
  - Indica si es material peligroso
  - `_rec_name = 'code'` para búsquedas rápidas

### 2. **tms.sat.clave.unidad** - Clave Unidad
- **Campos:** code, name
- **Uso:** Unidades de medida (KG, LT, PZ, etc.) según c_ClaveUnidad
- **Archivo:** `models/sat_clave_unidad.py`

### 3. **tms.sat.embalaje** - Tipo de Embalaje
- **Campos:** code, name
- **Uso:** Tipos de embalaje (Caja, Pallet, Contenedor, etc.) según c_TipoEmbalaje
- **Archivo:** `models/sat_embalaje.py`

### 4. **tms.sat.material.peligroso** - Material Peligroso
- **Campos:** code, name, clase
- **Uso:** Códigos UN para materiales peligrosos según c_MaterialPeligroso
- **Archivo:** `models/sat_material_peligroso.py`
- **Características:**
  - Incluye clase/división del material
  - Búsqueda por código UN, descripción o clase

### 5. **tms.sat.colonia** - Colonias
- **Campos:** code, zip_code, name
- **Uso:** Colonias por código postal según c_Colonia
- **Archivo:** `models/sat_colonia.py`
- **Optimización:**
  - `zip_code` con índice para búsquedas ultra-rápidas
  - Método auxiliar `get_colonias_by_cp(zip_code)`
  - Batch create optimizado para +140,000 registros

---

## 🔧 WIZARD DE IMPORTACIÓN

### sat.import.wizard
- **Archivo:** `wizard/sat_import_wizard.py`
- **Vista:** `wizard/sat_import_wizard_views.xml`

### Funcionalidades:
1. **Seleccionar catálogo** a importar (radio buttons)
2. **Subir archivo Excel** (.xlsx)
3. **Especificar número de hoja** (0 = primera hoja)
4. **Importación en batch** (optimizada para miles de registros)
5. **Opción de limpiar** catálogo antes de reimportar

### Formato del Excel:

#### Productos (c_ClaveProdServCP):
```
Columna A: Código (ej: "01010101")
Columna B: Descripción
Columna C: Material Peligroso ("0", "1" o "0,1")
Columna D: Palabras clave (opcional)
```

#### Unidades (c_ClaveUnidad):
```
Columna A: Código (ej: "KGM")
Columna B: Descripción (ej: "Kilogramo")
```

#### Colonias (c_Colonia):
```
Columna A: Código de Colonia
Columna B: Código Postal (5 dígitos)
Columna C: Nombre de Colonia
```

---

## 🎯 ARQUITECTURA SAAS

### Catálogos Globales (SIN company_id):
- Los catálogos SAT son estándares federales
- **NO tienen campo `company_id`**
- Son compartidos entre todas las empresas del sistema
- Esto es correcto y esperado para un sistema multi-empresa

### Record Rules:
- NO se aplican record rules a los catálogos
- Todos los usuarios pueden ver todos los catálogos
- Solo los modelos operacionales (tms.waybill, tms.expense) tienen aislamiento por empresa

---

## 🚀 CÓMO USAR

### 1. Acceder al Wizard de Importación:
```
Menú: Hombre Camión → Configuración → Catálogos SAT → Importar Catálogos
```

### 2. Pasos de Importación:
1. Seleccionar tipo de catálogo (radio button)
2. Subir archivo Excel (.xlsx)
3. Especificar número de hoja (default: 0)
4. Hacer clic en "Importar"
5. Esperar notificación de éxito con cantidad de registros

### 3. Ver Catálogos Importados:
```
Menú: Hombre Camión → Configuración → Catálogos SAT → [Seleccionar catálogo]
```

---

## 📊 PERFORMANCE

### Optimizaciones Implementadas:

1. **Batch Create:**
   - En lugar de `create()` en cada fila del Excel
   - Acumula todos los valores y crea de una vez
   - **Resultado:** Importación de 10,000 registros en segundos

2. **Índices en BD:**
   - `code` con `index=True` en todos los catálogos
   - `zip_code` con `index=True` en colonias
   - **Resultado:** Búsquedas instantáneas

3. **Chunking para Colonias:**
   - El catálogo de colonias tiene +140,000 registros
   - Se importa en lotes de 1,000
   - **Resultado:** No satura la memoria

---

## 📝 DESCARGA DE CATÁLOGOS SAT

Los catálogos oficiales se descargan de:
```
https://www.sat.gob.mx/consultas/factura-electronica/catalogo-de-complemento-carta-porte
```

### Archivos necesarios:
- c_ClaveProdServCP.xls
- c_ClaveUnidad.xls
- c_TipoEmbalaje.xls
- c_MaterialPeligroso.xls
- c_Colonia.xls

---

## 🔍 PRÓXIMOS PASOS

Con los catálogos cargados, ya puedes:
1. Asociar productos con claves SAT
2. Definir unidades de medida SAT
3. Configurar embalajes
4. Marcar materiales peligrosos
5. Usar colonias en direcciones de origen/destino

---

## ✅ CHECKLIST DE VERIFICACIÓN

Después de instalar/actualizar el módulo:

- [ ] Menú "Hombre Camión" visible
- [ ] Submenú "Configuración" → "Catálogos SAT"
- [ ] Wizard "Importar Catálogos" accesible
- [ ] Listas de catálogos vacías (hasta que importes datos)
- [ ] Sin errores en el log del servidor

---

## 🆘 TROUBLESHOOTING

### Error al importar Excel:
- Verificar que sea formato .xlsx (no .xls viejo)
- Revisar que el número de hoja sea correcto (empieza en 0)
- Verificar que las columnas estén en el orden esperado

### Importación muy lenta:
- Normal para catálogo de colonias (+140K registros)
- Puede tardar 2-5 minutos en la primera importación
- Usa el índice correcto de hoja

---

## 📞 Soporte
nextpack.mx

