from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_tms_google_maps = fields.Boolean(string="Usar Google Maps (API)")
    tms_google_maps_api_key = fields.Char(string="Google Maps API Key", config_parameter='tms.google_maps_api_key')
    tms_route_provider = fields.Selection([
        ('std', 'Manual / Estándar'),
        ('google', 'Google Maps API'),
    ], string="Proveedor de Rutas", default='std', config_parameter='tms.route_provider')
