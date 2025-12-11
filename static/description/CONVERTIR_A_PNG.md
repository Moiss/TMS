# 🎨 Conversión del Icono SVG a PNG

## ✅ Opción 1: Usar el SVG Directamente (Recomendado)

**Odoo 18 soporta iconos SVG** sin necesidad de convertir a PNG.

El archivo `__manifest__.py` ya está configurado para usar `icon.svg` directamente.

**No necesitas hacer nada más.** El icono funcionará perfectamente.

---

## 🔄 Opción 2: Convertir a PNG (Si lo prefieres)

Si prefieres usar PNG en lugar de SVG, tienes estas opciones:

### A. Usando un Editor Online (Más Fácil):
1. Ir a: https://cloudconvert.com/svg-to-png
2. Subir el archivo `icon.svg`
3. Configurar tamaño: 256x256 píxeles
4. Descargar como `icon.png`
5. Guardar en: `/Users/macbookpro/odoo/odoo18ce/proyectos/tms/static/description/icon.png`

### B. Usando Inkscape (Si está instalado):
```bash
inkscape icon.svg --export-filename=icon.png --export-width=256 --export-height=256
```

### C. Usando ImageMagick (Si está instalado):
```bash
convert -background none -size 256x256 icon.svg icon.png
```

### D. Instalar herramienta y convertir:
```bash
# Opción 1: Instalar rsvg-convert (rápido)
brew install librsvg

# Convertir
rsvg-convert -w 256 -h 256 icon.svg -o icon.png

# Opción 2: Instalar ImageMagick
brew install imagemagick

# Convertir
convert -background none -size 256x256 icon.svg icon.png
```

---

## ✅ Estado Actual

- ✅ `icon.svg` creado en la ruta correcta
- ✅ `__manifest__.py` configurado para usar el SVG
- ⚠️ `icon.png` no es necesario (Odoo 18 acepta SVG)

---

## 🎨 Concepto del Icono Creado

El icono representa:
- **Camión:** Base del negocio (transporte)
- **Conductor con gorra:** El "Hombre Camión" (dueño-operador)
- **Badge SAT:** Cumplimiento fiscal (Carta Porte)
- **Checkmark:** Validación/Catálogos
- **Colores:**
  - Azul: Confianza y profesionalismo
  - Naranja: Acción y logística
  - Verde: Oficial/SAT/Validado

---

## 📝 Nota

El icono SVG es **vectorial** (escala sin perder calidad) y pesa menos que PNG.
Es la opción recomendada para Odoo 18.

