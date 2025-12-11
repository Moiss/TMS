# -*- coding: utf-8 -*-

# Importamos las clases necesarias de Odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FleetVehicle(models.Model):
    """
    EXTENSIÓN del modelo nativo fleet.vehicle de Odoo.

    VENTAJAS DE HEREDAR EN LUGAR DE CREAR MODELO NUEVO:
    1. Aprovechamos TODO el módulo Fleet nativo:
       - Gestión de mantenimiento (fleet.vehicle.log.services)
       - Costos y contratos (fleet.vehicle.log.contract)
       - Odómetro y combustible
       - Reportes nativos

    2. No duplicamos funcionalidad que Odoo ya tiene

    3. Los usuarios que ya conocen Fleet se sienten cómodos

    ARQUITECTURA:
    - NO usamos _name (porque no creamos tabla nueva)
    - Usamos _inherit para EXTENDER la tabla existente fleet_vehicle
    - Los campos que agregamos aquí se añaden a la tabla fleet_vehicle
    """

    # _inherit: Extendemos el modelo nativo de Fleet
    # Esto AGREGA campos a la tabla existente, NO crea tabla nueva
    _inherit = 'fleet.vehicle'

    # ============================================================
    # ASEGURAMIENTO SAAS: company_id OBLIGATORIO
    # ============================================================
    # El módulo fleet nativo SÍ tiene company_id, pero lo hacemos explícitamente obligatorio
    # para asegurar que TODOS los vehículos pertenezcan a una empresa

    # Sobrescribimos company_id para forzar que sea obligatorio
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,                              # OBLIGATORIO para SaaS
        default=lambda self: self.env.company,      # Compañía del usuario actual
        help='Compañía propietaria del vehículo (CRÍTICO para multi-empresa)'
    )

    # ============================================================
    # ASEGURAMIENTO SAAS: Company ID Obligatorio
    # ============================================================
    # CRÍTICO: Asegura que cada vehículo pertenezca a una empresa
    # Esto permite aislamiento de datos en sistemas multi-empresa

    # Sobrescribimos el campo company_id del módulo Fleet para hacerlo requerido
    # Si el módulo nativo no lo requiere, lo hacemos obligatorio aquí
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,                                      # ← OBLIGATORIO para SaaS
        default=lambda self: self.env.company,             # ← Por defecto, compañía actual
        help='Compañía propietaria del vehículo (aislamiento multi-empresa)'
    )

    # ============================================================
    # CAMPO PRINCIPAL: Diferenciador Tractor vs Remolque
    # ============================================================

    # Boolean: define si este vehículo es un remolque o un tractor
    # CLAVE DE ARQUITECTURA: Con un solo modelo manejamos ambos tipos
    is_trailer = fields.Boolean(
        string='Es Remolque/Semirremolque',
        default=False,
        help='Marcar si este vehículo es un remolque. '
             'Si es False, es un tractocamión o camión unitario.'
    )

    # ============================================================
    # CAMPOS GENERALES (Tractor Y Remolque)
    # ============================================================

    # Char: número económico (identificador interno de la empresa)
    # Ejemplo: "ECO-001", "UNIDAD-42", etc.
    no_economico = fields.Char(
        string='No. Económico',
        help='Número de identificación interna del vehículo en la empresa'
    )

    # Many2one: configuración vehicular según catálogo SAT
    # Ejemplos: C2, C3, T3S2, T3S3, etc.
    sat_config_id = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Configuración SAT',
        help='Configuración vehicular según catálogo c_ConfigAutotransporte del SAT'
    )

    # Many2one: tipo de permiso SCT
    # Solo aplica para tractocamiones (no para remolques)
    sat_permiso_sct_id = fields.Many2one(
        'tms.sat.tipo.permiso',
        string='Tipo de Permiso SCT',
        help='Tipo de permiso SCT según catálogo c_TipoPermiso'
    )

    # Char: número del permiso SCT
    permiso_sct_number = fields.Char(
        string='Número de Permiso SCT',
        help='Número del permiso otorgado por la SCT'
    )

    # ============================================================
    # CAMPOS DE SEGURO (para Carta Porte)
    # ============================================================
    # NOTA: Odoo Fleet ya tiene fleet.vehicle.log.contract para contratos/seguros
    # pero para Carta Porte necesitamos campos rápidos accesibles

    # Char: nombre de la aseguradora
    insurance_company = fields.Char(
        string='Aseguradora',
        help='Nombre de la compañía aseguradora para Carta Porte'
    )

    # Char: número de póliza
    insurance_policy = fields.Char(
        string='Número de Póliza',
        help='Número de póliza del seguro de responsabilidad civil'
    )

    # ============================================================
    # CAMPOS ESPECÍFICOS PARA REMOLQUES
    # ============================================================

    # Many2one: subtipo de remolque según SAT
    # Ejemplos: Caja Seca, Plataforma, Refrigerado, etc.
    sat_subtype_id = fields.Many2one(
        'tms.sat.config.autotransporte',
        string='Subtipo de Remolque (SAT)',
        help='Tipo específico de remolque según catálogo del SAT'
    )

    # ============================================================
    # CAMPOS ESPECÍFICOS PARA TRACTOCAMIONES (no remolques)
    # ============================================================

    # Many2one: remolque 1 asignado a este tractor
    # Domain: solo remolques DE LA MISMA EMPRESA (crítico para SaaS)
    trailer1_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 1',
        domain="[('is_trailer', '=', True), ('company_id', '=', company_id)]",
        help='Primer remolque asignado a este tractocamión (debe ser de la misma empresa)'
    )

    # Many2one: remolque 2 (para doble remolque)
    # Domain: solo remolques DE LA MISMA EMPRESA (crítico para SaaS)
    trailer2_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 2',
        domain="[('is_trailer', '=', True), ('company_id', '=', company_id)]",
        help='Segundo remolque (para configuraciones de doble remolque - misma empresa)'
    )

    # Float: rendimiento de combustible
    # Importante para calcular costo por KM
    performance_km_l = fields.Float(
        string='Rendimiento (Km/L)',
        digits=(10, 2),
        help='Rendimiento promedio en kilómetros por litro'
    )

    # ============================================================
    # CAMPOS COMPUTADOS
    # ============================================================

    # Char: nombre completo del vehículo
    # Sobrescribimos el compute para mostrar formato personalizado
    vehicle_display_name = fields.Char(
        string='Nombre Completo',
        compute='_compute_vehicle_display_name',
        help='Nombre del vehículo con No. Económico y placas'
    )

    @api.depends('no_economico', 'license_plate', 'model_id', 'is_trailer')
    def _compute_vehicle_display_name(self):
        """
        Calcula un nombre descriptivo del vehículo.

        Formato:
        - Tractor: "[ECO-001] Volvo FH16 - ABC123"
        - Remolque: "[REM-001] Remolque Caja Seca - XYZ789"
        """
        for vehicle in self:
            # Lista de partes del nombre
            parts = []

            # Agregar No. Económico si existe
            if vehicle.no_economico:
                parts.append(f"[{vehicle.no_economico}]")

            # Agregar modelo si existe
            if vehicle.model_id:
                parts.append(vehicle.model_id.name)
            elif vehicle.is_trailer:
                parts.append("Remolque")
            else:
                parts.append("Tractocamión")

            # Agregar placas si existen
            if vehicle.license_plate:
                parts.append(f"- {vehicle.license_plate}")

            # Unimos las partes con espacios
            vehicle.vehicle_display_name = ' '.join(parts) if parts else 'Vehículo Sin Nombre'

    # ============================================================
    # VALIDACIONES
    # ============================================================

    @api.constrains('trailer1_id', 'trailer2_id')
    def _check_trailers(self):
        """
        Valida que un tractor no se asigne a sí mismo como remolque.
        Valida que no se asigne el mismo remolque dos veces.
        """
        for vehicle in self:
            # Solo validar si NO es remolque (los tractores tienen remolques)
            if not vehicle.is_trailer:
                # Validación 1: No puede ser su propio remolque
                if vehicle.trailer1_id == vehicle or vehicle.trailer2_id == vehicle:
                    raise ValidationError(
                        _('Un vehículo no puede asignarse a sí mismo como remolque.')
                    )

                # Validación 2: No puede tener el mismo remolque dos veces
                if vehicle.trailer1_id and vehicle.trailer2_id:
                    if vehicle.trailer1_id == vehicle.trailer2_id:
                        raise ValidationError(
                            _('No puede asignar el mismo remolque en ambas posiciones.')
                        )

    # ============================================================
    # MÉTODOS ONCHANGE (Interactividad en el Formulario)
    # ============================================================

    @api.onchange('is_trailer')
    def _onchange_is_trailer(self):
        """
        Cuando se marca/desmarca is_trailer, limpia campos no aplicables.

        LÓGICA:
        - Si es remolque: quita asignaciones de remolques (un remolque no lleva remolques)
        - Si es tractor: permite asignar remolques
        """
        # Si se marca como remolque, limpia los campos de tractor
        if self.is_trailer:
            self.trailer1_id = False
            self.trailer2_id = False
            self.performance_km_l = 0.0

    # ============================================================
    # MÉTODOS DE ACCIÓN (Botones en la Interfaz)
    # ============================================================

    def action_view_services(self):
        """
        Abre los servicios/mantenimientos del vehículo.

        IMPORTANTE: Este método aprovecha el módulo NATIVO de Fleet.
        fleet.vehicle.log.services ya existe en Odoo estándar.
        NO necesitamos crear un modelo nuevo de mantenimiento.

        :return: acción de ventana para mostrar servicios
        """
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': f'Mantenimiento - {self.vehicle_display_name}',
            'res_model': 'fleet.vehicle.log.services',  # Modelo NATIVO de Odoo
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {
                'default_vehicle_id': self.id,
                'default_amount': 0.0,
            },
        }

