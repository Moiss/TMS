# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _


class TmsSatMaterialPeligroso(models.Model):
    """
    Catálogo c_MaterialPeligroso del SAT.
    Contiene las claves de materiales peligrosos para Carta Porte 3.1.

    Se usa cuando se transportan sustancias peligrosas que requieren
    documentación especial según normativa SCT (Secretaría de Comunicaciones).

    ARQUITECTURA SAAS: Catálogo GLOBAL sin company_id.
    """

    # Nombre técnico del modelo
    _name = 'tms.sat.material.peligroso'

    # Descripción del modelo
    _description = 'Catálogo SAT - Material Peligroso (c_MaterialPeligroso)'

    # Campo usado como nombre en búsquedas
    _rec_name = 'code'

    # Orden por defecto
    _order = 'code asc'

    # ============================================================
    # CAMPOS
    # ============================================================

    # Código del material peligroso (ej: "1203", "1170", etc.)
    # Este código corresponde al número UN (United Nations)
    code = fields.Char(
        string='Clave SAT / UN',
        required=True,
        index=True,
        help='Código de material peligroso según catálogo c_MaterialPeligroso del SAT'
    )

    # Descripción del material peligroso
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción del material peligroso'
    )

    # Clase del material peligroso (División según normativa)
    # Ejemplos: "3" (Líquidos inflamables), "2.1" (Gases inflamables), etc.
    clase = fields.Char(
        string='Clase',
        help='Clase o división del material peligroso según normativa SCT'
    )

    # ============================================================
    # CONSTRAINTS
    # ============================================================

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)',
         'El código de material peligroso SAT ya existe.')
    ]

    # ============================================================
    # MÉTODOS
    # ============================================================

    def name_get(self):
        """
        Muestra: "Código - Descripción (Clase X)"
        Ejemplo: "1203 - Gasolina (Clase 3)"
        """
        result = []
        for record in self:
            # Si tiene clase, la incluimos en el nombre
            if record.clase:
                name = f"{record.code} - {record.name} (Clase {record.clase})"
            else:
                name = f"{record.code} - {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        """
        Permite buscar por código, descripción o clase.
        """
        domain = domain or []

        if name:
            # Buscar en código, descripción o clase
            domain = ['|', '|',
                     ('code', operator, name),
                     ('name', operator, name),
                     ('clase', operator, name)
                     ] + domain

        return super()._name_search(
            name='', domain=domain, operator=operator,
            limit=limit, order=order
        )
