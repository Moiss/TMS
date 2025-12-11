# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TmsDestination(models.Model):
    """
    Modelo para gestionar Rutas Comerciales (Punto A -> Punto B).

    CONCEPTO: Representa rutas frecuentes que la empresa maneja.
    Ejemplo: "GDL-CDMX", "Monterrey-Tijuana"

    USO: Pre-llenar datos en cotizaciones (origen, destino, distancia, tiempo, casetas).

    =========================================================
    ARQUITECTURA SAAS (CRÍTICO):
    =========================================================
    Este modelo es PRIVADO por empresa.

    ¿POR QUÉ?
    - La Empresa A tiene sus propias rutas comerciales
    - La Empresa B NO debe ver las rutas de la Empresa A
    - Cada empresa maneja diferentes orígenes/destinos

    SOLUCIÓN:
    - company_id es OBLIGATORIO (required=True)
    - Record Rule filtra por company_id (ver security/tms_security.xml)
    - Domain en búsquedas incluye company_id
    """

    # Nombre técnico del modelo (tabla: tms_destination)
    _name = 'tms.destination'

    # Descripción del modelo
    _description = 'Ruta Comercial (Punto A -> Punto B)'

    # Orden por defecto
    _order = 'name asc'

    # ============================================================
    # CAMPO CRÍTICO SAAS: company_id
    # ============================================================

    # Many2one: compañía propietaria de la ruta
    # OBLIGATORIO: Cada ruta debe pertenecer a una empresa
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,                              # ← OBLIGATORIO para SaaS
        default=lambda self: self.env.company,      # ← Compañía actual por defecto
        index=True,                                  # ← Índice para Record Rules rápidas
        help='Compañía a la que pertenece esta ruta (CRÍTICO para multi-empresa)'
    )

    # ============================================================
    # CAMPOS ESENCIALES DE RUTA (Punto A -> Punto B)
    # ============================================================

    # Identificación básica
    name = fields.Char(string='Nombre de la Ruta', required=True)
    active = fields.Boolean(default=True, string="Activa")

    # REEMPLAZO: Usamos State (Estado) en lugar de Municipio
    state_origin_id = fields.Many2one(
        'res.country.state',
        string='Estado Origen',
        domain="[('country_id.code', '=', 'MX')]",
        help='Estado de origen de la ruta (México)'
    )

    state_dest_id = fields.Many2one(
        'res.country.state',
        string='Estado Destino',
        domain="[('country_id.code', '=', 'MX')]",
        help='Estado de destino de la ruta (México)'
    )

    distance_km = fields.Float(string='Distancia (km)', digits=(10, 2))
    duration_hours = fields.Float(string='Duración (hrs)', digits=(10, 2))
    notes = fields.Text(string='Notas')

    # Float: costo promedio de casetas para esta ruta
    toll_cost = fields.Float(
        string='Costo de Casetas',
        digits=(10, 2),
        help='Costo promedio de casetas en pesos para esta ruta'
    )

    # ============================================================
    # VALIDACIONES
    # ============================================================

    @api.constrains('distance_km')
    def _check_distance(self):
        """
        Valida que la distancia sea mayor a cero.
        """
        for record in self:
            if record.distance_km and record.distance_km <= 0:
                raise ValidationError(
                    _('La distancia debe ser mayor a cero.')
                )

    @api.constrains('state_origin_id', 'state_dest_id')
    def _check_locations(self):
        for record in self:
            if record.state_origin_id and record.state_dest_id:
                if record.state_origin_id == record.state_dest_id:
                    # Opcional: Permitir rutas intra-estatales.
                    # El prompt no prohíbe explícitamente rutas dentro del mismo estado,
                    # pero la validación anterior impedía mismo municipio.
                    # Si el estado es el mismo, es posible que sea válido (ej. GDL a Pto Vallarta son mismo estado).
                    # Eliminaremos la restricción estricta de "mismo estado" a menos que sea requerida,
                    # ya que rutas internas son comunes.
                    pass


    def action_apply_matched_route(self):
        """
        PROXY METHOD:
        Necesario porque el botón está en la vista lista de 'tms.destination'.
        Delega la ejecución al modelo 'tms.waybill' vía context, como solicitado.
        """
        # Obtenemos el ID del Waybill activo desde el contexto
        # Dependiendo de dónde se abra, suele ser 'active_id' o 'parent_id'
        # En una vista embebida (inline list), el active_id es el padre.
        waybill_id = self.env.context.get('parent.id') or self.env.context.get('active_id')

        # Fallback: intentar recuperar desde el contexto si se pasó explícitamente
        if not waybill_id and self.env.context.get('waybill_id'):
            waybill_id = self.env.context.get('waybill_id')

        if waybill_id:
            # Llamamos al método en tms.waybill pasando el ID de esta ruta
            # Esto cumple con "ejecutar exclusivamente en tms.waybill"
            return self.env['tms.waybill'].browse(waybill_id).with_context(route_id=self.id).action_apply_matched_route()

        return False
