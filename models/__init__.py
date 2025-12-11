# -*- coding: utf-8 -*-

# ============================================================
# CATÁLOGOS SAT (Carta Porte 3.1) - GLOBALES (sin company_id)
# ============================================================
# Estos modelos son catálogos oficiales del SAT
# NO tienen company_id porque son estándares federales compartidos entre empresas

# Catálogos de Productos y Mercancías
from . import sat_clave_prod          # c_ClaveProdServCP - Clave Producto/Servicio
from . import sat_clave_unidad        # c_ClaveUnidad - Unidades de medida
from . import sat_embalaje            # c_TipoEmbalaje - Tipos de embalaje
from . import sat_material_peligroso  # c_MaterialPeligroso - Materiales peligrosos

# Catálogos Geográficos
from . import sat_codigo_postal       # c_CodigoPostal - Códigos postales
from . import sat_colonia             # c_Colonia - Colonias por CP
from . import sat_localidad           # c_Localidad - Localidades
from . import sat_municipio           # c_Municipio - Municipios

# Catálogos de Transporte
from . import sat_config_autotransporte  # c_ConfigAutotransporte - Config vehicular
from . import sat_tipo_permiso        # c_TipoPermiso - Permisos SCT
from . import sat_figura_transporte   # c_FiguraTransporte - Figuras en transporte
from . import res_partner_tms         # Extensión de res.partner para Catálogos SAT

# ============================================================
# MODELOS OPERATIVOS - PRIVADOS (CON company_id OBLIGATORIO)
# ============================================================
# Estos modelos SÍ tienen company_id para aislamiento multi-empresa
# Cada empresa solo ve sus propios registros

from . import tms_fleet_vehicle       # Extensión de fleet.vehicle (tractores y remolques)
from . import tms_destination         # Destinos/Rutas comerciales por empresa
from . import tms_waybill             # Viajes / Cartas Porte (MODELO MAESTRO: fusiona Cotización + Viaje)
