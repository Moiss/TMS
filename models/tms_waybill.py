# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class TmsWaybill(models.Model):
    """
    Modelo Maestro: Viaje / Carta Porte (SINGLE DOCUMENT FLOW).

    CONCEPTO: Fusiona Cotización + Operación + Carta Porte en un solo documento.

    WORKFLOW (7 Etapas):
    1. Solicitud (request)       → Cotización inicial
    2. Por Asignar (confirmed)    → Confirmada, asignar vehículo/chofer
    3. Carta Porte (carta_porte)  → CP lista para timbrar
    4. En Trayecto (transit)      → Chofer en camino
    5. En Destino (destination)   → Entregado
    6. Facturado (invoiced)       → Cerrado
    7. Cancelado (cancel)         → Anulado

    ARQUITECTURA HÍBRIDA:
    - Plan A: App Móvil reporta GPS (action_driver_report API)
    - Plan B: Operación Manual desde Odoo (botones action_*_manual)

    ARQUITECTURA SAAS: company_id obligatorio.
    """

    _name = 'tms.waybill'
    _description = 'Viaje / Carta Porte (Maestro)'
    # Herencia de mixins: mail.thread (chatter), mail.activity.mixin (actividades), portal.mixin (portal web)
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date_created desc, id desc'

    # ============================================================
    # CAMPO CRÍTICO SAAS
    # ============================================================

    # Many2one: compañía propietaria del viaje
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        help='Compañía propietaria del viaje (CRÍTICO para multi-empresa)'
    )

    # Many2one: moneda (relacionada a la compañía)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
        store=True,
    )

    # ============================================================
    # CONTROL DE WORKFLOW
    # ============================================================

    # Char: folio del viaje (secuencia automática)
    name = fields.Char(
        string='Folio',
        required=True,
        readonly=True,
        copy=False,
        default='Nuevo',
        tracking=True,
        help='Número de folio del viaje (VJ/0001, VJ/0002, etc.)'
    )

    # Selection: estado del viaje (8 etapas, agregado 'rejected' para portal)
    # group_expand: asegura que todas las columnas aparezcan en Kanban
    state = fields.Selection(
        string='Estado',
        selection=[
            ('draft', 'Solicitud'),
            ('en_pedido', 'En Pedido'),
            ('assigned', 'Por Asignar'),
            ('waybill', 'Carta Porte Lista'),
            ('in_transit', 'En Trayecto'),
            ('arrived', 'En Destino'),
            ('closed', 'Facturado / Cerrado'),
            ('cancel', 'Cancelado'),
            ('rejected', 'Rechazado'),  # Agregado para rechazo desde portal
        ],
        default='draft',
        required=True,
        tracking=True,
        group_expand='_expand_states',
        help='Estado actual del viaje en el workflow'
    )

    # Date: fecha de creación
    date_created = fields.Date(
        string='Fecha de Solicitud',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )

    # ============================================================
    # CONFIGURACIÓN FISCAL (Carta Porte)
    # ============================================================

    # Selection: tipo de carta porte
    # Determina si es Ingreso (cobro) o Traslado (sin cobro)
    # Requerimiento: Si el campo cp_type no existe → crearlo
    cp_type = fields.Selection([
        ('ingreso','Ingreso (Flete Cobrado)'),
        ('traslado','Traslado (Sin Cobro)'),
    ], string="Tipo de Carta Porte", default='ingreso', tracking=True)

    # Mantener waybill_type por compatibilidad o usar cp_type como principal
    waybill_type = fields.Selection(
        string='Tipo de Carta Porte (Legacy)',
        selection=[
            ('income', 'Ingreso (Flete Cobrado)'),
            ('transfer', 'Traslado (Sin Cobro)'),
        ],
        required=True,
        default='income',
        tracking=True,
        help='Tipo de operación: Ingreso (cobra flete) o Traslado (sin cobro)'
    )

    # ============================================================
    # ACTORES: CLIENTE DE FACTURACIÓN (Quién Paga)
    # ============================================================

    # Many2one: cliente que paga el flete
    partner_invoice_id = fields.Many2one(
        'res.partner',
        string='Cliente Facturación',
        domain="[('company_id', '=', company_id)]",  # Solo partners de la misma empresa
        check_company=True,
        tracking=True,
        help='Cliente al que se le facturará el servicio'
    )

    # Char: RFC del cliente (relacionado, readonly)
    invoice_rfc = fields.Char(
        string='RFC Cliente',
        related='partner_invoice_id.vat',
        readonly=True,
        store=False,
    )

    # Char: domicilio fiscal del cliente (computado)
    invoice_address = fields.Char(
        string='Domicilio Fiscal',
        compute='_compute_partner_addresses',
        store=False,
    )

    # ============================================================
    # ACTORES: ORIGEN / REMITENTE (Quien Entrega)
    # ============================================================

    # Many2one: contacto en el origen
    partner_origin_id = fields.Many2one(
        'res.partner',
        string='Remitente (Origen)',
        domain="[('company_id', '=', company_id)]",  # Solo partners de la misma empresa
        check_company=True,
        help='Contacto que entrega la mercancía'
    )

    # Char: RFC del remitente (relacionado, readonly)
    origin_rfc = fields.Char(
        string='RFC Remitente',
        related='partner_origin_id.vat',
        readonly=True,
        store=False,
    )

    # Many2one: municipio origen (catálogo SAT)
    origin_city_id = fields.Many2one(
        'tms.sat.municipio',
        string='Municipio Origen',
        help='Municipio de origen según catálogo SAT'
    )

    # Char: código postal origen
    origin_zip = fields.Char(
        string='CP Origen',
        size=5,
    )

    # Char: dirección origen (calle y número)
    origin_address = fields.Char(
        string='Dirección Origen',
        help='Calle y número de la dirección de origen'
    )

    # ============================================================
    # ACTORES: DESTINO / DESTINATARIO (Quien Recibe)
    # ============================================================

    # Many2one: contacto en el destino
    partner_dest_id = fields.Many2one(
        'res.partner',
        string='Destinatario',
        domain="[('company_id', '=', company_id)]",  # Solo partners de la misma empresa
        check_company=True,
        help='Contacto que recibe la mercancía'
    )

    # Char: RFC del destinatario (relacionado, readonly)
    dest_rfc = fields.Char(
        string='RFC Destinatario',
        related='partner_dest_id.vat',
        readonly=True,
        store=False,
    )

    # Many2one: municipio destino (catálogo SAT)
    dest_city_id = fields.Many2one(
        'tms.sat.municipio',
        string='Municipio Destino',
        help='Municipio de destino según catálogo SAT'
    )

    # Char: código postal destino
    dest_zip = fields.Char(
        string='CP Destino',
        size=5,
    )

    # Char: dirección destino (calle y número)
    dest_address = fields.Char(
        string='Dirección Destino',
        help='Calle y número de la dirección de destino'
    )

    # ============================================================
    # RUTA: DATOS DE DISTANCIA Y DURACIÓN
    # ============================================================

    # Float: distancia en kilómetros (base de la ruta)
    distance_km = fields.Float(
        string='Distancia (Km)',
        digits=(10, 2),
        help='Distancia base en kilómetros de la ruta'
    )

    # Float: kilómetros extras por desvíos o periferia
    # Se suma a distance_km para el cálculo de la propuesta por KM
    extra_distance_km = fields.Float(
        string='Km Extras / Desvío',
        digits=(10, 2),
        default=0.0,
        help='Kilómetros adicionales al centro de la ciudad o por desvíos operativos. Se suman a la distancia base para el cobro.'
    )

    # Float: duración estimada en horas
    duration_hours = fields.Float(
        string='Duración Estimada (Hrs)',
        digits=(10, 2),
        help='Duración estimada del viaje en horas'
    )

    # Char: ruta completa (computado)
    # Formato: "Monterrey → CDMX"
    route_name = fields.Char(
        string='Ruta',
        compute='_compute_route_name',
        store=True,
        help='Ruta en formato: Origen → Destino'
    )

    # Many2one: ruta frecuente seleccionada
    # Al seleccionar una ruta, se auto-llenan origen, destino, distancia y duración
    route_id = fields.Many2one(
        'tms.destination',
        string='Seleccionar Ruta Frecuente',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        check_company=True,
        tracking=True,
        help='Selecciona una ruta frecuente para auto-completar origen, destino, distancia y duración'
    )

    # ============================================================
    # SELECTOR INTELIGENTE DE RUTAS
    # ============================================================

    # ============================================================
    # SELECTOR INTELIGENTE DE RUTAS -> ESTADOS
    # ============================================================

    state_origin_search_id = fields.Many2one(
        'res.country.state',
        string='Estado Origen (Buscador)',
        domain="[('country_id.code', '=', 'MX')]",
        help='Selecciona el estado de origen para buscar rutas'
    )

    state_dest_search_id = fields.Many2one(
        'res.country.state',
        string='Estado Destino (Buscador)',
        domain="[('country_id.code', '=', 'MX')]",
        help='Selecciona el estado de destino para buscar rutas'
    )

    # Requerimiento: Si origin_state_id o dest_state_id no existen → crearlos:
    origin_state_id = fields.Many2one('res.country.state', string="Estado Origen")
    dest_state_id = fields.Many2one('res.country.state', string="Estado Destino")

    # Monetary: costo de casetas (Nuevo campo solicitado)
    toll_cost = fields.Monetary(
        string='Costo Casetas',
        currency_field='currency_id',
        help='Costo de casetas copiado desde la ruta seleccionada'
    )

    @api.onchange('route_id')
    def _onchange_route_id(self):
        """
        Auto-llena los datos del viaje cuando se selecciona una ruta manualmente.
        """
        if self.route_id:
            self.route_name = self.route_id.name
            self.distance_km = self.route_id.distance_km
            self.duration_hours = self.route_id.duration_hours
            self.toll_cost = self.route_id.toll_cost
            # Requerimiento: Sincronizar datos al seleccionar una ruta
            self.origin_state_id = self.route_id.origin_state_id.id
            self.dest_state_id = self.route_id.dest_state_id.id
        else:
            self.distance_km = 0.0
            self.duration_hours = 0.0
            self.toll_cost = 0.0

    @api.depends('origin_state_id', 'dest_state_id')
    def _compute_route_name(self):
        """
        Calcula el nombre de la ruta para mostrar en tarjetas Kanban.
        Formato: "Origen → Destino"
        """
        for record in self:
            if record.origin_state_id and record.dest_state_id:
                record.route_name = f"{record.origin_state_id.name} → {record.dest_state_id.name}"
            elif record.origin_state_id:
                record.route_name = f"{record.origin_state_id.name} → ?"
            elif record.dest_state_id:
                record.route_name = f"? → {record.dest_state_id.name}"
            else:
                record.route_name = "Sin ruta definida"

    # ============================================================
    # CONFIGURACIÓN OPERATIVA: VEHÍCULOS Y CHOFER
    # ============================================================

    # Many2one: vehículo asignado (tractor)
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo (Tractor)',
        domain="[('is_trailer', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        tracking=True,
        help='Tractocamión asignado al viaje'
    )

    # Many2one: chofer asignado
    driver_id = fields.Many2one(
        'res.partner',
        string='Chofer',
        domain="[('company_id', '=', company_id)]",  # Solo partners de la misma empresa
        check_company=True,
        tracking=True,
        help='Conductor asignado al viaje'
    )

    # Many2one: remolque 1
    trailer1_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 1',
        domain="[('is_trailer', '=', True), ('company_id', '=', company_id)]",
        check_company=True,
        help='Primer remolque asignado'
    )

    # Many2one: remolque 2 (opcional)
    trailer2_id = fields.Many2one(
        'fleet.vehicle',
        string='Remolque 2',
        domain="[('is_trailer', '=', True), ('company_id', '=', company_id)]",
        check_company=True,
        help='Segundo remolque asignado (opcional)'
    )

    # ============================================================
    # BITÁCORA DE TIEMPOS Y GPS (HÍBRIDO: App + Manual)
    # ============================================================
    # IMPORTANTE: Estos campos se llenan automáticamente por la App (Plan A)
    # o manualmente por botones de Odoo (Plan B)

    # ===== PUNTO 1: LLEGADA A ORIGEN =====

    # Datetime: fecha/hora de llegada al punto de origen
    date_arrived_origin = fields.Datetime(
        string='Llegada a Origen',
        help='Fecha y hora en que llegó al punto de carga'
    )

    # Float: latitud GPS de llegada a origen
    lat_arrived_origin = fields.Float(
        string='Latitud Origen',
        digits=(12, 8),
        help='Latitud GPS al llegar a origen (App) o 0.0 (Manual)'
    )

    # Float: longitud GPS de llegada a origen
    long_arrived_origin = fields.Float(
        string='Longitud Origen',
        digits=(12, 8),
        help='Longitud GPS al llegar a origen (App) o 0.0 (Manual)'
    )

    # ===== PUNTO 2: INICIO DE RUTA =====

    # Datetime: fecha/hora de inicio de ruta
    date_started_route = fields.Datetime(
        string='Inicio de Ruta',
        help='Fecha y hora en que inició el trayecto'
    )

    # Float: latitud GPS de inicio de ruta
    lat_started_route = fields.Float(
        string='Latitud Inicio',
        digits=(12, 8),
        help='Latitud GPS al iniciar ruta (App) o 0.0 (Manual)'
    )

    # Float: longitud GPS de inicio de ruta
    long_started_route = fields.Float(
        string='Longitud Inicio',
        digits=(12, 8),
        help='Longitud GPS al iniciar ruta (App) o 0.0 (Manual)'
    )

    # ===== PUNTO 3: LLEGADA A DESTINO =====

    # Datetime: fecha/hora de llegada a destino
    date_arrived_dest = fields.Datetime(
        string='Llegada a Destino',
        help='Fecha y hora en que llegó al punto de entrega'
    )

    # Float: latitud GPS de llegada a destino
    lat_arrived_dest = fields.Float(
        string='Latitud Destino',
        digits=(12, 8),
        help='Latitud GPS al llegar a destino (App) o 0.0 (Manual)'
    )

    # Float: longitud GPS de llegada a destino
    long_arrived_dest = fields.Float(
        string='Longitud Destino',
        digits=(12, 8),
        help='Longitud GPS al llegar a destino (App) o 0.0 (Manual)'
    )

    # ===== TRACKING EN TIEMPO REAL (Solo App) =====

    # Float: última latitud reportada por la app
    last_app_lat = fields.Float(
        string='Última Latitud (App)',
        digits=(12, 8),
        help='Última posición GPS reportada por la app móvil'
    )

    # Float: última longitud reportada por la app
    last_app_long = fields.Float(
        string='Última Longitud (App)',
        digits=(12, 8),
        help='Última posición GPS reportada por la app móvil'
    )

    # Datetime: última actualización de posición
    last_report_date = fields.Datetime(
        string='Última Actualización GPS',
        help='Última vez que la app reportó posición'
    )

    # ============================================================
    # MONTOS Y COSTOS
    # ============================================================

    # Monetary: valor del viaje (monto a cobrar)
    amount_total = fields.Monetary(
        string='Valor del Viaje',
        currency_field='currency_id',
        tracking=True,
        help='Monto total a cobrar por el servicio'
    )

    # ============================================================
    # FIRMA DIGITAL (PORTAL WEB)
    # ============================================================

    # Binary: imagen de la firma del cliente (base64)
    # Se guarda cuando el cliente firma la cotización en el portal
    signature = fields.Image(
        string='Firma Digital',
        copy=False,
        attachment=True,
        help='Firma digital del cliente capturada en el portal web'
    )

    # Char: nombre de la persona que firmó
    # Se captura junto con la firma para identificación
    signed_by = fields.Char(
        string='Firmado Por',
        help='Nombre de la persona que firmó la cotización digitalmente'
    )

    # Datetime: fecha y hora en que se firmó
    # Se establece automáticamente cuando se ejecuta _action_sign()
    signed_on = fields.Datetime(
        string='Fecha de Firma',
        copy=False,
        help='Fecha y hora en que el cliente firmó la cotización'
    )

    # Text: motivo de rechazo desde el portal
    # Se captura cuando el cliente rechaza la cotización desde el portal
    rejection_reason = fields.Text(
        string='Motivo de Rechazo',
        copy=False,
        help='Motivo del rechazo capturado desde el portal web'
    )

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Cotizacion-%s' % (self.name)

    def action_preview_waybill(self):
        """Abre la cotización en el portal en una NUEVA pestaña"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',  # <--- 'new' fuerza la nueva pestaña
            'url': self.get_portal_url(),
        }

    # ============================================================
    # MOTOR DE COTIZACIÓN (Costos y Propuestas)
    # ============================================================

    # --- INPUTS DE COSTOS ---
    fuel_price_liter = fields.Float(string='Precio Diesel (L)', default=24.00, digits=(10,2))
    fuel_performance = fields.Float(string='Rendimiento (Km/L)', default=2.5, digits=(10,2), help="Kms por Litro")
    cost_tolls = fields.Float(string='Costo Casetas', digits=(10,2))
    cost_driver = fields.Float(string='Sueldo Chofer', digits=(10,2))
    cost_maneuver = fields.Float(string='Maniobras', digits=(10,2))
    cost_other = fields.Float(string='Otros Gastos', digits=(10,2))

    # Costo Diesel Estimado (Calculado y Almacenado)
    # IMPORTANTE: Este campo tiene store=True, por lo que necesita su propio método compute
    # para evitar warnings de Odoo sobre inconsistencia entre campos almacenados y no almacenados
    cost_diesel_total = fields.Float(
        string='Costo Diesel Est.',
        compute='_compute_cost_diesel_total',
        store=True
    )

    # --- PROPUESTA 1: POR KILÓMETRO ---
    price_per_km = fields.Float(string='Precio por Km', digits=(10,2))
    # IMPORTANTE: Este campo NO tiene store=True, usa método separado
    proposal_km_total = fields.Monetary(
        string='Total (Por KM)',
        compute='_compute_proposal_values',
        currency_field='currency_id',
        store=False
    )

    # --- PROPUESTA 2: POR VIAJE (Costos + Utilidad) ---
    profit_margin_percent = fields.Float(string='Margen Utilidad (%)', default=30.0)
    # IMPORTANTE: Este campo NO tiene store=True, usa método separado
    proposal_trip_total = fields.Monetary(
        string='Total (Por Viaje)',
        compute='_compute_proposal_values',
        currency_field='currency_id',
        store=False
    )

    # --- PROPUESTA 3: VENTA DIRECTA ---
    proposal_direct_amount = fields.Monetary(string='Precio Directo', currency_field='currency_id')

    # --- SELECCIÓN ---
    selected_proposal = fields.Selection(
        [('km', 'Por Kilómetro'), ('trip', 'Por Viaje (Costos)'), ('direct', 'Directo')],
        string='Propuesta Seleccionada',
        default='direct',
        tracking=True
    )

    # ============================================================
    # MERCANCÍAS (One2many)
    # ============================================================

    # One2many: líneas de mercancía
    line_ids = fields.One2many(
        'tms.waybill.line',
        'waybill_id',
        string='Mercancías',
        help='Mercancías transportadas en el viaje'
    )

    # ============================================================
    # MÉTODOS COMPUTADOS
    # ============================================================

    @api.depends('distance_km', 'extra_distance_km', 'fuel_price_liter', 'fuel_performance')
    def _compute_cost_diesel_total(self):
        """
        Calcula el costo total de diesel estimado.

        FÓRMULA:
        - Distancia Total = Distancia Base + Km Extras
        - Litros necesarios = Distancia Total (km) / Rendimiento (km/L)
        - Costo Total = Litros necesarios * Precio por Litro

        IMPORTANTE:
        - Este método es SEPARADO porque cost_diesel_total tiene store=True
        - Odoo recomienda separar métodos para campos almacenados y no almacenados
        - Esto evita warnings de inconsistencia en compute_sudo y store
        - Los Km Extras se incluyen en el cálculo de combustible
        """
        for record in self:
            total_distance = record.distance_km + record.extra_distance_km
            if record.fuel_performance > 0:
                liters_needed = total_distance / record.fuel_performance
                record.cost_diesel_total = liters_needed * record.fuel_price_liter
            else:
                record.cost_diesel_total = 0.0

    @api.depends('distance_km', 'extra_distance_km', 'price_per_km', 'cost_diesel_total',
                 'cost_tolls', 'cost_driver', 'cost_maneuver', 'cost_other',
                 'profit_margin_percent', 'proposal_direct_amount', 'selected_proposal')
    def _compute_proposal_values(self):
        """
        Calcula las 3 propuestas de cotización automáticamente.

        PROPUESTA 1 (Por KM): (Distancia Base + Km Extras) * Precio/KM
        PROPUESTA 2 (Por Viaje): (Costos Totales) / (1 - Margen%)
        PROPUESTA 3 (Directa): Monto fijo capturado manualmente

        El campo amount_total se actualiza según la propuesta seleccionada.

        IMPORTANTE:
        - Este método es para campos NO almacenados (store=False)
        - Depende de cost_diesel_total que SÍ está almacenado
        - Esto evita warnings de inconsistencia en compute_sudo y store
        - Los Km Extras se suman a la distancia base para el cobro por KM
        """
        for record in self:
            # 1. Calcular Propuesta KM
            # Distancia Total = Distancia Base + Km Extras
            # Total = Distancia Total * Precio por KM
            total_distance = record.distance_km + record.extra_distance_km
            record.proposal_km_total = total_distance * record.price_per_km

            # 2. Calcular Propuesta Viaje
            # Costo Total = Diesel + Casetas + Chofer + Maniobras + Otros
            total_costs = record.cost_diesel_total + record.cost_tolls + record.cost_driver + record.cost_maneuver + record.cost_other
            # Precio Venta = Costo Total / (1 - Margen%)
            margin_factor = 1 - (record.profit_margin_percent / 100)
            if margin_factor > 0:
                record.proposal_trip_total = total_costs / margin_factor
            else:
                record.proposal_trip_total = total_costs

            # 3. Actualizar Monto Final (Amount Total) basado en selección
            if record.selected_proposal == 'km':
                record.amount_total = record.proposal_km_total
            elif record.selected_proposal == 'trip':
                record.amount_total = record.proposal_trip_total
            else:
                record.amount_total = record.proposal_direct_amount

    def _compute_access_url(self):
        """
        Sobrescribe el método de portal.mixin para generar la URL del portal.

        ¿QUÉ HACE?
        - Llama primero a super() para mantener la lógica base de portal.mixin
        - Luego asigna una URL personalizada para cada waybill: /my/waybills/<id>

        ¿POR QUÉ SOBRESCRIBIR?
        - portal.mixin genera URLs genéricas por defecto
        - Necesitamos URLs específicas para el controlador /my/waybills/<waybill>

        EJEMPLO:
        - Waybill ID 5 → access_url = '/my/waybills/5'
        - El cliente puede acceder desde el portal usando esta URL
        """
        # Llamar al método padre para mantener la lógica base
        super()._compute_access_url()
        # Asignar URL personalizada para cada waybill
        for waybill in self:
            waybill.access_url = '/my/waybills/%s' % (waybill.id)

    @api.depends('partner_invoice_id', 'partner_invoice_id.street', 'partner_invoice_id.city',
                 'partner_invoice_id.zip', 'partner_invoice_id.state_id')
    def _compute_partner_addresses(self):
        """
        Calcula la dirección completa del cliente de facturación.
        Formato: "Calle, Ciudad, Estado, CP"
        """
        for record in self:
            if record.partner_invoice_id:
                # Construir dirección desde las partes
                parts = []
                if record.partner_invoice_id.street:
                    parts.append(record.partner_invoice_id.street)
                if record.partner_invoice_id.city:
                    parts.append(record.partner_invoice_id.city)
                if record.partner_invoice_id.state_id:
                    parts.append(record.partner_invoice_id.state_id.name)
                if record.partner_invoice_id.zip:
                    parts.append(record.partner_invoice_id.zip)

                record.invoice_address = ', '.join(parts) if parts else ''
            else:
                record.invoice_address = ''

    # ============================================================
    # MÉTODOS ONCHANGE (Autocompletado Inteligente)
    # ============================================================

    @api.onchange('partner_origin_id')
    def _onchange_partner_origin(self):
        """
        AUTOCOMPLETADO DE DATOS DEL REMITENTE.
        Copia dirección, CP y busca municipio SAT.
        """
        if self.partner_origin_id:
            self.origin_address = self.partner_origin_id.street or ''
            self.origin_zip = self.partner_origin_id.zip or ''

            # Buscar municipio SAT por nombre de ciudad
            if self.partner_origin_id.city:
                municipio = self.env['tms.sat.municipio'].search([
                    ('name', 'ilike', self.partner_origin_id.city),
                ], limit=1)
                if municipio:
                    self.origin_city_id = municipio

    @api.onchange('partner_dest_id')
    def _onchange_partner_dest(self):
        """
        AUTOCOMPLETADO DE DATOS DEL DESTINATARIO.
        Copia dirección, CP y busca municipio SAT.
        """
        if self.partner_dest_id:
            self.dest_address = self.partner_dest_id.street or ''
            self.dest_zip = self.partner_dest_id.zip or ''

            # Buscar municipio SAT por nombre de ciudad
            if self.partner_dest_id.city:
                municipio = self.env['tms.sat.municipio'].search([
                    ('name', 'ilike', self.partner_dest_id.city),
                ], limit=1)
                if municipio:
                    self.dest_city_id = municipio

    @api.onchange('route_id')
    def _onchange_route_id(self):
        """
        AUTOCOMPLETADO DE RUTA AL SELECCIONAR UNA RUTA FRECUENTE.

        Cuando el usuario selecciona una ruta desde el campo route_id:
        - Auto-llena origin_city_id con el municipio de origen de la ruta
        - Auto-llena dest_city_id con el municipio de destino de la ruta
        - Auto-llena distance_km con la distancia de la ruta
        - Auto-llena duration_hours con la duración de la ruta
        - Auto-llena cost_tolls con el costo de casetas de la ruta
        """
        if self.route_id:
            # Auto-llenar estados de origen y destino (Sincronización requerida)
            self.origin_state_id = self.route_id.state_origin_id
            self.dest_state_id = self.route_id.state_dest_id

            # Auto-llenar distancia y duración
            self.distance_km = self.route_id.distance_km or 0.0
            self.duration_hours = self.route_id.duration_hours or 0.0

            # Auto-llenar costo de casetas
            self.cost_tolls = self.route_id.toll_cost or 0.0
            self.toll_cost = self.route_id.toll_cost or 0.0

    @api.onchange('origin_state_id', 'dest_state_id')
    def _onchange_route_autocomplete(self):
        """
        AUTOCOMPLETADO INTELIGENTE DE RUTA (Búsqueda inversa).

        Busca en tms.destination si existe la ruta basándose en Estados
        y pre-llena datos. También actualiza route_id si encuentra una coincidencia.
        """
        if self.origin_state_id and self.dest_state_id:
            route = self.env['tms.destination'].search([
                ('state_origin_id', '=', self.origin_state_id.id),
                ('state_dest_id', '=', self.dest_state_id.id),
                ('company_id', '=', self.company_id.id),
                ('active', '=', True),
            ], limit=1)

            if route:
                # Actualizar route_id si se encuentra una ruta
                self.route_id = route
                self.distance_km = route.distance_km or 0.0
                self.duration_hours = route.duration_hours or 0.0
                self.cost_tolls = route.toll_cost or 0.0
                self.toll_cost = route.toll_cost or 0.0

                return {
                    'warning': {
                        'title': _('✅ Ruta Encontrada'),
                        'message': _('Distancia: %s km | Duración: %s hrs') % (
                            route.distance_km,
                            route.duration_hours
                        )
                    }
                }
            else:
                # Si no se encuentra ruta, limpiar route_id
                self.route_id = False

    # ============================================================
    # MÉTODO: Group Expand (CRÍTICO para Kanban)
    # ============================================================

    def _expand_states(self, states, domain, order=None):
        """
        Asegura que TODAS las columnas del Kanban aparezcan siempre.
        Retorna la lista completa de estados.
        """
        return [
            'draft',
            'en_pedido',
            'assigned',
            'waybill',
            'in_transit',
            'rejected',  # Agregado para rechazo desde portal
            'arrived',
            'closed',
            'cancel',
        ]

    # ============================================================
    # MÉTODOS DE ACCIÓN MANUAL (Plan B: Botones en Odoo)
    # ============================================================
    # IMPORTANTE: Estos métodos son el RESPALDO cuando la App falla
    # o no está disponible. Permiten operar el sistema 100% manualmente.

    # Solución al duplicado: action_confirm ahora establece el estado 'en_pedido'
    # incorporando la lógica de validación existente.

    def action_set_en_pedido(self):
        """
        Cambia el estado a en_pedido.
        Incluye validaciones de action_confirm.
        """
        self.action_confirm()

    def action_confirm(self):
        """
        MANUAL: Confirmar Solicitud → En Pedido.
        Se ejecuta al aprobar la cotización.
        """
        self.ensure_one()

        # Validar que tenga cliente y ruta definidos
        if not self.partner_invoice_id:
            raise UserError(_('Debe seleccionar un cliente antes de confirmar.'))
        if not self.origin_city_id or not self.dest_city_id:
            raise UserError(_('Debe definir origen y destino antes de confirmar.'))

        self.write({'state': 'en_pedido'})

    def action_approve_cp(self):
        """
        MANUAL: Aprobar Carta Porte → Carta Porte Lista.
        Se ejecuta cuando el vehículo y chofer están asignados.
        """
        self.ensure_one()

        # Validar que tenga vehículo y chofer
        if not self.vehicle_id:
            raise UserError(_('Debe asignar un vehículo antes de aprobar la CP.'))
        if not self.driver_id:
            raise UserError(_('Debe asignar un chofer antes de aprobar la CP.'))

        self.write({'state': 'carta_porte'})

    def action_start_route_manual(self):
        """
        MANUAL: Iniciar Ruta → En Trayecto.

        PLAN B (Respaldo Manual):
        - Registra la fecha/hora actual
        - NO registra GPS (lat/long quedan en 0.0)
        - Cambia estado a 'transit'

        VENTAJA: El sistema sigue funcionando aunque la App falle.
        """
        self.ensure_one()

        # Registrar fecha/hora actual
        now = fields.Datetime.now()

        # Escribir valores
        # GPS en 0.0 indica operación MANUAL (sin app)
        self.write({
            'date_started_route': now,
            'lat_started_route': 0.0,  # 0.0 = Manual
            'long_started_route': 0.0,  # 0.0 = Manual
            'state': 'transit',
        })

    def action_arrived_dest_manual(self):
        """
        MANUAL: Llegada a Destino → En Destino.

        PLAN B (Respaldo Manual):
        - Registra la fecha/hora actual
        - NO registra GPS (lat/long quedan en 0.0)
        - Cambia estado a 'destination'
        """
        self.ensure_one()

        # Registrar fecha/hora actual
        now = fields.Datetime.now()

        # Escribir valores
        self.write({
            'date_arrived_dest': now,
            'lat_arrived_dest': 0.0,  # 0.0 = Manual
            'long_arrived_dest': 0.0,  # 0.0 = Manual
            'state': 'destination',
        })

    def action_create_invoice(self):
        """
        MANUAL: Crear Factura → Facturado.
        Marca el viaje como cerrado.
        """
        self.ensure_one()

        # Validar que tenga monto
        if not self.amount_total:
            raise UserError(_('Debe definir el valor del viaje antes de facturar.'))

        # TODO: Aquí se puede integrar la creación real de factura
        # account_invoice = self.env['account.move'].create({...})

        self.write({'state': 'invoiced'})

    def _action_sign(self, signature, signed_by):
        """
        Acción de Firma Digital desde el Portal Web.

        ¿QUÉ HACE?
        1. Guarda la firma (imagen base64) en el campo signature
        2. Guarda el nombre de quien firma en signed_by
        3. Establece signed_on con la fecha/hora actual
        4. Cambia el estado a 'confirmed' (cotización aceptada)
        5. Registra en el chatter un mensaje de confirmación

        PARÁMETROS:
        - signature: String base64 con la imagen de la firma
        - signed_by: String con el nombre de la persona que firma

        VALIDACIONES:
        - Solo se puede firmar si el estado es 'request' (Solicitud)
        - La firma debe ser válida (no vacía)

        USO:
        - Llamado desde el controlador portal.py cuando el cliente firma
        - Se ejecuta con sudo() para permitir acceso desde portal
        """
        self.ensure_one()

        # Validar que esté en estado de solicitud
        if self.state != 'draft':
            raise UserError(_('Solo se pueden firmar cotizaciones en estado "Solicitud".'))

        # Validar que la firma no esté vacía
        if not signature:
            raise ValidationError(_('La firma no puede estar vacía.'))

        # Obtener fecha/hora actual
        now = fields.Datetime.now()

        # Guardar firma y datos
        self.write({
            'signature': signature,
            'signed_by': signed_by,
            'signed_on': now,
            'state': 'en_pedido',  # Cambiar a "En Pedido" (cotización confirmada)
        })

        # Registrar en el chatter
        self.message_post(
            body=_('✅ Cotización firmada digitalmente por <strong>%s</strong> el %s') % (
                signed_by,
                now.strftime('%d/%m/%Y %H:%M:%S')
            ),
            subject=_('Firma Digital Recibida'),
        )

    def action_cancel(self):
        """Cancela el viaje."""
        self.ensure_one()
        self.write({'state': 'cancel'})

    # ============================================================
    # API PARA APP MÓVIL (Plan A: Automático)
    # ============================================================

    @api.model
    def action_driver_report(self, waybill_id, status, lat, long):
        """
        API para recibir reportes de la App Móvil.

        PLAN A (Automático):
        - La app del chofer reporta su posición GPS
        - Actualiza fecha/hora, latitud y longitud automáticamente
        - Cambia el estado del viaje según el status

        :param waybill_id: ID del viaje (int)
        :param status: Estado reportado ('started_route', 'arrived_dest', 'tracking')
        :param lat: Latitud GPS (float)
        :param long: Longitud GPS (float)
        :return: dict con resultado

        EJEMPLO DE USO (desde la App):
        POST /web/dataset/call_kw/tms.waybill/action_driver_report
        {
            "params": {
                "args": [123, "started_route", 25.6866, -100.3161]
            }
        }
        """
        # Buscar el viaje
        waybill = self.browse(waybill_id)

        if not waybill.exists():
            return {
                'success': False,
                'message': _('Viaje no encontrado')
            }

        # Registrar fecha/hora actual
        now = fields.Datetime.now()

        # Actualizar según el status reportado
        if status == 'started_route':
            # Chofer inició el viaje
            waybill.write({
                'date_started_route': now,
                'lat_started_route': lat,
                'long_started_route': long,
                'last_app_lat': lat,
                'last_app_long': long,
                'last_report_date': now,
                'state': 'transit',
            })
            message = _('Ruta iniciada correctamente')

        elif status == 'arrived_dest':
            # Chofer llegó a destino
            waybill.write({
                'date_arrived_dest': now,
                'lat_arrived_dest': lat,
                'long_arrived_dest': long,
                'last_app_lat': lat,
                'last_app_long': long,
                'last_report_date': now,
                'state': 'destination',
            })
            message = _('Llegada a destino registrada')

        elif status == 'tracking':
            # Actualización de posición (sin cambio de estado)
            waybill.write({
                'last_app_lat': lat,
                'last_app_long': long,
                'last_report_date': now,
            })
            message = _('Posición actualizada')

        else:
            return {
                'success': False,
                'message': _('Status no válido: %s') % status
            }

        return {
            'success': True,
            'message': message,
            'waybill_id': waybill_id,
            'current_state': waybill.state,
        }

    # ============================================================
    # MÉTODO CREATE (Generar folio automático)
    # ============================================================

    @api.model_create_multi
    def create(self, vals_list):
        """
        Genera folio automático para cada viaje.
        Formato: VJ/0001, VJ/0002, etc.
        """
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('tms.waybill') or 'Nuevo'
        return super(TmsWaybill, self).create(vals_list)


    def action_send_email(self):
        """ Abre el wizard de correo con la plantilla pre-cargada """
        self.ensure_one()
        # Referencia a la plantilla creada en data/mail_template_data.xml
        template = self.env.ref('tms.email_template_tms_waybill')

        ctx = {
            'default_model': 'tms.waybill',
            'default_res_ids': self.ids,
            'default_use_template': bool(template),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'force_email': True,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


# ============================================================
# MODELO DE LÍNEAS: Mercancías del Viaje
# ============================================================


class TmsWaybillLine(models.Model):
    """
    Líneas de Mercancía de un Viaje.

    CONCEPTO: Detalla qué mercancías se transportan en el viaje.
    Ejemplo: 100 cajas de refrescos, 50 sacos de cemento, etc.
    """

    _name = 'tms.waybill.line'
    _description = 'Línea de Mercancía (Viaje)'
    _order = 'sequence, id'

    # Many2one: viaje al que pertenece
    waybill_id = fields.Many2one(
        'tms.waybill',
        string='Viaje',
        required=True,
        ondelete='cascade',  # Si se elimina el viaje, se eliminan sus líneas
    )

    # Integer: orden de la línea
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de la mercancía en la lista'
    )

    # Many2one: clave producto SAT
    product_sat_id = fields.Many2one(
        'tms.sat.clave.prod',
        string='Clave Producto SAT',
        help='Clave del catálogo ClaveProdServCP del SAT'
    )

    # Char: descripción de la mercancía
    description = fields.Char(
        string='Descripción',
        required=True,
        help='Descripción de la mercancía transportada'
    )

    # Float: cantidad
    quantity = fields.Float(
        string='Cantidad',
        digits=(10, 2),
        default=1.0,
        help='Cantidad de unidades'
    )

    # Many2one: unidad de medida SAT
    uom_sat_id = fields.Many2one(
        'tms.sat.clave.unidad',
        string='Unidad SAT',
        help='Unidad de medida según catálogo SAT'
    )

    # Float: peso en kilogramos
    weight_kg = fields.Float(
        string='Peso (Kg)',
        digits=(10, 2),
        help='Peso total de la mercancía en kilogramos'
    )

    # Char: dimensiones (opcional)
    dimensions = fields.Char(
        string='Dimensiones',
        help='Dimensiones de la mercancía (ej: 1.2m x 0.8m x 0.5m)'
    )

    # Boolean: es material peligroso
    is_dangerous = fields.Boolean(
        string='Material Peligroso',
        default=False,
        help='Indica si la mercancía es material peligroso'
    )

    def action_send_email(self):
        """ Abre el wizard de correo con la plantilla pre-cargada """
        self.ensure_one()
        # Referencia a la plantilla creada en data/mail_template_data.xml
        template = self.env.ref('tms.email_template_tms_waybill')

        ctx = {
            'default_model': 'tms.waybill',
            'default_res_ids': self.ids,
            'default_use_template': bool(template),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'force_email': True,
        }

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
