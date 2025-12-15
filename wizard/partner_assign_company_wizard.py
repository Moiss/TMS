# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PartnerAssignCompanyWizard(models.TransientModel):
    """
    Wizard para asignación masiva de company_id a partners sin empresa.

    USO:
    - Seleccionar empresa destino
    - Filtrar partners sin company_id (opcionalmente por otros criterios)
    - Asignar company_id masivamente a los partners seleccionados
    """
    _name = 'partner.assign.company.wizard'
    _description = 'Wizard: Asignar Empresa a Partners'

    company_id = fields.Many2one(
        'res.company',
        string='Empresa Destino',
        required=True,
        help='Empresa que se asignará a los partners seleccionados'
    )

    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners a Asignar',
        domain=[('company_id', '=', False)],
        help='Partners que serán asignados a la empresa seleccionada'
    )

    filter_domain = fields.Char(
        string='Dominio de Filtrado',
        default="[('company_id', '=', False)]",
        help='Dominio para filtrar partners (por defecto: sin company_id)'
    )

    @api.model
    def default_get(self, fields_list):
        """No pre-llenar partners automáticamente - el usuario debe seleccionarlos"""
        res = super().default_get(fields_list)
        # No pre-llenar partners por defecto para evitar cargas innecesarias
        # El usuario seleccionará manualmente los partners que necesita asignar
        return res

    def action_assign_company(self):
        """Asigna company_id a los partners seleccionados"""
        if not self.company_id:
            raise UserError(_('Debe seleccionar una empresa destino.'))

        if not self.partner_ids:
            raise UserError(_('No hay partners seleccionados para asignar.'))

        # Verificar que los partners no tengan company_id
        partners_with_company = self.partner_ids.filtered(lambda p: p.company_id)
        if partners_with_company:
            raise UserError(
                _('Los siguientes partners ya tienen empresa asignada: %s')
                % ', '.join(partners_with_company.mapped('name'))
            )

        # Asignar company_id masivamente
        try:
            self.partner_ids.write({'company_id': self.company_id.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Se asignó la empresa "%s" a %d partner(s).') % (
                        self.company_id.name,
                        len(self.partner_ids)
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error al asignar empresa: %s') % str(e))

