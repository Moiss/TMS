# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TmsSatConfigAutotransporte(models.Model):
    """
    Catálogo c_ConfigAutotransporte del SAT.
    Define las configuraciones vehiculares permitidas para autotransporte.

    EJEMPLOS:
    - C2: Camión Unitario de 2 ejes
    - T3S2: Tractocamión con Semirremolque (3 ejes + 2 ejes)
    - C3R2: Camión con Remolque

    USO: Se usa en Carta Porte para especificar el tipo exacto de vehículo.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.config.autotransporte'

    # Descripción del modelo
    _description = 'Catálogo SAT - Configuración Autotransporte (c_ConfigAutotransporte)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código de configuración (ej: "C2", "T3S2", "C3R2")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de configuración vehicular según c_ConfigAutotransporte'
    )

    # Descripción de la configuración
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción de la configuración del autotransporte'
    )

    # Número de remolques que soporta esta configuración
    # 0 = Camión unitario (sin remolque)
    # 1 = Un remolque
    # 2 = Doble remolque
    numero_ejes_remolque = fields.Integer(
        string='Número de Ejes de Remolque',
        default=0,
        help='Cantidad de ejes del remolque o semirremolque (0 si no lleva)'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)',
         'El código de configuración ya existe.')
    ]

    # ============================================================
    # MÉTODOS
    # ============================================================

    def name_get(self):
        """
        Muestra: "Código - Descripción"
        Ejemplo: "T3S2 - Tractocamión-Semirremolque"
        """
        result = []
        for record in self:
            name = f"{record.code} - {record.name}"
            result.append((record.id, name))
        return result

