# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 🔒 SEGURIDAD SAAS
    # default=lambda self: self.env.company -> Asigna la empresa del usuario logueado.
    company_id = fields.Many2one(
        'res.company',
        'Compañía',
        default=lambda self: self.env.company,
        required=True,
        index=True,
        help="El contacto pertenece exclusivamente a esta empresa."
    )

    tms_cp_id = fields.Many2one('tms.sat.codigo.postal', string='Código Postal SAT')

    # Campo Auxiliar para Dominios XML (Store=False es suficiente si es compute on the fly, o True si prefieres búsquedas)
    tms_sat_state_code = fields.Char(compute='_compute_tms_sat_state_code', store=True)

    # Campos SAT
    l10n_mx_edi_colonia_sat_id = fields.Many2one('tms.sat.colonia', string='Colonia')
    l10n_mx_edi_municipio_sat_id = fields.Many2one('tms.sat.municipio', string='Municipio')
    l10n_mx_edi_localidad_sat_id = fields.Many2one('tms.sat.localidad', string='Localidad')

    @api.depends('state_id', 'state_id.code')
    def _compute_tms_sat_state_code(self):
        """Limpia el código de estado para coincidir con catálogos SAT (MX-JAL -> JAL)"""
        for record in self:
            if record.state_id and record.state_id.code:
                record.tms_sat_state_code = record.state_id.code.replace('MX-', '')
            else:
                record.tms_sat_state_code = False

    @api.onchange('tms_cp_id')
    def _on_cp_change(self):
        """Solo lógica de asignación y autocompletado"""
        if not self.tms_cp_id: return

        cp = self.tms_cp_id
        self.zip = cp.code

        # Asignar Estado (Esto disparará el compute de tms_sat_state_code)
        if cp.estado:
            domain = ['|', ('code', '=', cp.estado), ('code', '=', f'MX-{cp.estado}')]
            state = self.env['res.country.state'].search(domain + [('country_id.code', '=', 'MX')], limit=1)
            if state: self.state_id = state

        # Limpiar dependientes
        self.l10n_mx_edi_colonia_sat_id = False
        self.l10n_mx_edi_municipio_sat_id = False
        self.l10n_mx_edi_localidad_sat_id = False

        # Pre-llenado si el CP es específico
        if self.tms_sat_state_code:
            state_code = self.tms_sat_state_code
            if cp.municipio:
                # Intento match por nombre (lo más probable en CP -> Muni)
                muni = self.env['tms.sat.municipio'].search([('name', '=', cp.municipio), ('estado', '=', state_code)], limit=1)
                # Fallback por código si existiera
                if not muni:
                     muni = self.env['tms.sat.municipio'].search([('code', '=', cp.municipio), ('estado', '=', state_code)], limit=1)

                if muni:
                    self.l10n_mx_edi_municipio_sat_id = muni
                    self.city = muni.name

            if cp.localidad:
                loc = self.env['tms.sat.localidad'].search([('name', '=', cp.localidad), ('estado', '=', state_code)], limit=1)
                if not loc:
                    loc = self.env['tms.sat.localidad'].search([('code', '=', cp.localidad), ('estado', '=', state_code)], limit=1)

                if loc: self.l10n_mx_edi_localidad_sat_id = loc

    @api.onchange('l10n_mx_edi_municipio_sat_id', 'l10n_mx_edi_localidad_sat_id')
    def _on_geo_change(self):
        """Sync Ciudad nativa al elegir Mun/Loc"""
        if self.l10n_mx_edi_localidad_sat_id:
            self.city = self.l10n_mx_edi_localidad_sat_id.name
        elif self.l10n_mx_edi_municipio_sat_id:
            self.city = self.l10n_mx_edi_municipio_sat_id.name
