from odoo import models, fields

class TmsVehicleType(models.Model):
    _name = 'tms.vehicle.type'
    _description = 'Tipo de Vehículo TMS'
    _order = 'sequence, name'

    name = fields.Char('Nombre', required=True, translate=True)
    sequence = fields.Integer(default=10)

    # Flags de Comportamiento
    is_trailer = fields.Boolean('Es Remolque/Caja', help="Marca si este tipo se comporta como un remolque (sin motor)")
    is_motorized = fields.Boolean('Es Motorizado', default=True)
