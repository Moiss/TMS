# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class TMSCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'waybill_count' in counters:
            # Contar viajes del usuario (opcional, si quisieras listarlos en el home)
            values['waybill_count'] = request.env['tms.waybill'].search_count([])
        return values

    # ------------------------------------------------------------
    # VISTA DE DETALLE (COTIZACIÓN)
    # ------------------------------------------------------------
    @http.route(['/my/waybills/<int:waybill_id>'], type='http', auth="public", website=True)
    def portal_my_waybill(self, waybill_id, access_token=None, **kw):
        try:
            # 1. Buscar y Validar Acceso (Token)
            # check_access=True lanza error si el token es inválido o no tiene permisos
            waybill_sudo = self._document_check_access('tms.waybill', waybill_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # 2. Preparar Valores para la Vista
        values = {
            'waybill': waybill_sudo,
            'page_name': 'waybill',
            'token': access_token,
            'report_type': 'html',
        }

        # 3. Renderizar
        return request.render("tms.portal_my_waybill", values)

    # ------------------------------------------------------------
    # ACCIÓN DE FIRMA (POST)
    # ------------------------------------------------------------
    @http.route(['/my/waybills/<int:waybill_id>/sign'], type='http', auth="public", methods=['POST'], website=True)
    def portal_waybill_sign(self, waybill_id, access_token=None, name=None, signature=None):
        try:
            waybill_sudo = self._document_check_access('tms.waybill', waybill_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if not signature:
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=missing_signature'))

        # Guardar Firma
        try:
            waybill_sudo.write({
                'signature': signature,
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'state': 'assigned', # Cambiar estado a Por Asignar (assigned en modelo) o 'confirmed' según user request, pero el user dijo 'confirmed' -> 'Por Asignar'.
                # Re-reading user request: "state': 'confirmed', # Cambiar estado a Por Asignar"
                # Looking at tms_waybill.py: 'assigned' is 'Por Asignar'. 'confirmed' is NOT in the selection list shown in tms_waybill.py (lines 78-86).
                # Selection is: draft, en_pedido, assigned, waybill, in_transit, arrived, closed, cancel.
                # Assuming 'assigned' corresponds to 'Por Asignar'.
                # However, the user provided code snippet specifically had 'confirmed'.
                # Wait, looking at the user snippet: "'state': 'confirmed', # Cambiar estado a Por Asignar"
                # The tms_waybill.py file has: ('assigned', 'Por Asignar')
                # It does NOT have 'confirmed'.
                # I should probably use 'assigned' to match the model definition I saw in tms_waybill.py
                # Or maybe add 'confirmed' to the selection?
                # User instructions said: "Usa este código que implementa correctamente..." and the code had 'confirmed'.
                # BUT, I must ensure it works. If I put 'confirmed' and it's not in selection, it might fail if strict.
                # Actually, in Odoo selection fields generally enforce the keys.
                # Let's check the model definition in tms_waybill.py again.
                # Lines 77-86:
                # ('draft', 'Solicitud'),
                # ('en_pedido', 'En Pedido'),
                # ('assigned', 'Por Asignar'),
                # ('waybill', 'Carta Porte Lista'),
                # ...
                # There is NO 'confirmed'.
                # The user's code snippet comment says "# Cambiar estado a Por Asignar".
                # 'Por Asignar' maps to 'assigned'.
                # So I will use 'assigned' instead of 'confirmed' to be correct with the existing model.
            })
            # Log en el chatter
            waybill_sudo.message_post(body=_('Cotización firmada digitalmente por %s') % (name))
        except Exception as e:
            return request.redirect(waybill_sudo.get_portal_url(query_string='&error=save_error'))

        # Recargar página con mensaje de éxito
        return request.redirect(waybill_sudo.get_portal_url(query_string='&success=true'))
