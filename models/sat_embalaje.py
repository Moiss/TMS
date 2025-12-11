# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatEmbalaje(models.Model):
    """
    Catálogo c_TipoEmbalaje del SAT.
    Contiene los tipos de embalaje para mercancías en Carta Porte 3.1.

    Ejemplos: Caja, Pallet, Contenedor, Granel, etc.

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.embalaje'

    # Descripción del modelo
    _description = 'Catálogo SAT - Tipo de Embalaje (c_TipoEmbalaje)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código del tipo de embalaje (ej: "4A", "4B", "4C")
    code = fields.Char(
        string='Clave SAT',
        required=True,
        index=True,
        help='Código de tipo de embalaje según catálogo c_TipoEmbalaje del SAT'
    )

    # Descripción del embalaje
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción del tipo de embalaje'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)',
         'El código de embalaje SAT ya existe.')
    ]

    # ============================================================
    # MÉTODOS
    # ============================================================

    def name_get(self):
        """
        Muestra: "Código - Descripción"
        Ejemplo: "4A - Caja de madera"
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
            domain = ['|',
                     ('code', operator, name),
                     ('name', operator, name)
                     ] + domain

        return super()._name_search(
            name='', domain=domain, operator=operator,
            limit=limit, order=order
        )
