# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatClaveUnidad(models.Model):
    """
    Catálogo c_ClaveUnidad del SAT.
    Contiene las claves de unidades de medida para Carta Porte 3.1.

    Ejemplos: KG (Kilogramo), LT (Litro), PZ (Pieza), etc.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.clave.unidad'

    # Descripción del modelo
    _description = 'Catálogo SAT - Clave Unidad (c_ClaveUnidad)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código de la unidad (ej: "KGM", "LTR", "H87")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de unidad de medida según catálogo c_ClaveUnidad del SAT'
    )

    # Descripción de la unidad (ej: "Kilogramo", "Litro", "Pieza")
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción de la unidad de medida'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)',
         'El código de unidad SAT ya existe.')
    ]

    # ============================================================
    # MÉTODOS
    # ============================================================

    def name_get(self):
        """
        Muestra: "Código - Descripción"
        Ejemplo: "KGM - Kilogramo"
        """
        result = []
        for record in self:
            name = f"{record.code} - {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        """
        Permite buscar por código o descripción.
        """
        domain = domain or []

        if name:
            # Buscar en código o descripción
            domain = ['|',
                     ('code', operator, name),
                     ('name', operator, name)
                     ] + domain

        return super()._name_search(
            name='', domain=domain, operator=operator,
            limit=limit, order=order
        )
