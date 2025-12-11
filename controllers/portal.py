# -*- coding: utf-8 -*-

"""
Controlador del Portal Web para Firma Digital de Cotizaciones.

¿QUÉ HACE ESTE ARCHIVO?
- Expone rutas HTTP para que los clientes accedan a sus cotizaciones desde el portal
- Permite que los clientes firmen digitalmente las cotizaciones
- Valida el aislamiento SaaS (cada empresa solo ve sus propios waybills)

ARQUITECTURA:
- Hereda de CustomerPortal (módulo nativo de Odoo)
- Usa decoradores @http.route para definir URLs
- Valida company_id antes de mostrar datos (seguridad SaaS)
"""

# Importaciones estándar de Odoo
from odoo import http
# request: objeto que contiene la petición HTTP actual
from odoo.http import request
# CustomerPortal: clase base para controladores de portal
from odoo.addons.portal.controllers.portal import CustomerPortal
# NotFound: excepción HTTP 404 para cuando no se encuentra un recurso
from werkzeug.exceptions import NotFound


class TmsPortalController(CustomerPortal):
    """
    Controlador del Portal para Cotizaciones TMS.

    HEREDA DE:
    - CustomerPortal: Proporciona métodos base como _prepare_portal_layout_values()

    RESPONSABILIDADES:
    1. Mostrar cotizaciones al cliente en el portal web
    2. Validar que el cliente solo vea cotizaciones de su empresa (SaaS)
    3. Procesar la firma digital del cliente
    4. Redirigir después de firmar
    """

    # ============================================================
    # RUTA 1: VISTA DE COTIZACIÓN EN EL PORTAL
    # ============================================================

    @http.route(
        ['/my/waybills/<model("tms.waybill"):waybill>'],
        type='http',
        auth='user',
        website=True
    )
    def portal_waybill_detail(self, waybill, **kw):
        """
        Muestra el detalle de una cotización en el portal web.

        RUTA:
        /my/waybills/<id>
        Ejemplo: /my/waybills/5

        PARÁMETROS:
        - waybill: Objeto tms.waybill obtenido automáticamente por Odoo
                   usando <model("tms.waybill"):waybill>
        - **kw: Argumentos adicionales de la URL (query string)

        VALIDACIÓN SAAS (CRÍTICO):
        - Verifica que waybill.company_id == request.env.company
        - Si no coincide, lanza NotFound (404)
        - Esto garantiza que un cliente de Empresa A NO pueda ver
          cotizaciones de Empresa B

        RENDERIZA:
        - Plantilla: tms.portal_my_waybill
        - Contexto: {'waybill': waybill}
        """
        # VALIDACIÓN SAAS: Verificar que la cotización pertenece a la empresa del usuario
        # request.env.company: empresa actual del usuario autenticado
        # waybill.company_id: empresa propietaria de la cotización
        if waybill.company_id.id != request.env.company.id:
            # Si no coincide, lanzar 404 (No encontrado)
            # Esto previene que usuarios de una empresa vean datos de otra
            raise NotFound()

        # Preparar valores para la plantilla
        # Estos valores estarán disponibles en el template XML
        values = {
            'waybill': waybill,  # Objeto completo de la cotización
            'page_name': 'waybill_detail',  # Nombre de la página (para breadcrumbs)
        }

        # Renderizar la plantilla XML
        # tms.portal_my_waybill: ID externo de la plantilla (definida en tms_portal_templates.xml)
        return request.render('tms.portal_my_waybill', values)

    # ============================================================
    # RUTA 2: PROCESAR FIRMA DIGITAL
    # ============================================================

    @http.route(
        ['/my/waybills/<model("tms.waybill"):waybill>/sign'],
        type='http',
        auth='user',
        methods=['POST'],
        website=True,
        csrf=True
    )
    def portal_waybill_sign(self, waybill, **post):
        """
        Procesa la firma digital de una cotización desde el portal.

        RUTA:
        POST /my/waybills/<id>/sign
        Ejemplo: POST /my/waybills/5/sign

        PARÁMETROS (POST):
        - signature: String base64 con la imagen de la firma
        - signed_by: String con el nombre de la persona que firma

        VALIDACIÓN SAAS (CRÍTICO):
        - Verifica nuevamente que waybill.company_id == request.env.company
        - Doble validación para seguridad extra

        PROCESO:
        1. Valida que la cotización pertenece a la empresa del usuario
        2. Extrae signature y signed_by del formulario POST
        3. Llama a waybill._action_sign() para guardar la firma
        4. Redirige al detalle de la cotización

        RESPUESTA:
        - Redirección HTTP 302 a /my/waybills/<id>
        - O JSON si hay error
        """
        # VALIDACIÓN SAAS: Doble verificación de empresa
        # Esto previene que alguien intente firmar cotizaciones de otra empresa
        if waybill.company_id.id != request.env.company.id:
            raise NotFound()

        # Extraer datos del formulario POST
        # post es un diccionario con todos los campos del formulario
        signature = post.get('signature')  # Imagen base64 de la firma
        signed_by = post.get('signed_by')  # Nombre de quien firma

        # Validar que los datos requeridos estén presentes
        if not signature:
            # Si falta la firma, mostrar error
            return request.render('portal.portal_message', {
                'message': 'Error: La firma es requerida.',
                'redirect': '/my/waybills/%s' % waybill.id,
            })

        if not signed_by:
            # Si falta el nombre, mostrar error
            return request.render('portal.portal_message', {
                'message': 'Error: El nombre del firmante es requerido.',
                'redirect': '/my/waybills/%s' % waybill.id,
            })

        try:
            # Ejecutar la acción de firma
            # sudo(): Ejecuta con permisos elevados (necesario para escribir)
            # _action_sign(): Método del modelo que guarda la firma y cambia el estado
            waybill.sudo()._action_sign(signature, signed_by)

            # Redirigir al detalle de la cotización después de firmar
            # HTTP 302: Redirección temporal
            return request.redirect('/my/waybills/%s' % waybill.id)

        except Exception as e:
            # Si hay algún error, mostrar mensaje y redirigir
            # Esto captura errores como: estado incorrecto, validaciones fallidas, etc.
            return request.render('portal.portal_message', {
                'message': 'Error al procesar la firma: %s' % str(e),
                'redirect': '/my/waybills/%s' % waybill.id,
            })

