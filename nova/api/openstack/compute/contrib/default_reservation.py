# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime
from oslo.config import cfg

from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova import utils

reservation_opts = [
    cfg.StrOpt('reservation_start_date',
               default='now',
               help='Specify date for all leases to be started for every VM'),
    cfg.IntOpt('reservation_length_days',
               default=30,
               help='Number of days for VM to be reserved.'),
    cfg.IntOpt('reservation_length_hours',
               default=0,
               help='Number of hours for VM to be reserved.'),
    cfg.IntOpt('reservation_length_minutes',
               default=0,
               help='Number of minutes for VM to be reserved.')
]

CONF = cfg.CONF
CONF.register_opts(reservation_opts)

LOG = logging.getLogger(__name__)
authorize = extensions.extension_authorizer('compute', 'default_reservation')


class DefaultReservationController(wsgi.Controller):
    """Add default reservation flags to every VM started."""

    @wsgi.extends
    def create(self, req, body):

        default_hints = {}

        delta_days = datetime.timedelta(days=CONF.reservation_length_days)
        delta_hours = datetime.timedelta(hours=CONF.reservation_length_hours)
        delta_minutes = datetime.timedelta(minutes=CONF.reservation_length_minutes)
        default_hints['reserved'] = True
        if CONF.reservation_start_date == 'now':
            base = datetime.datetime.utcnow()
        else:
            base = datetime.datetime.strptime(CONF.reservation_start_date,
                                              "%Y-%m-%d %H:%M")
        default_hints['lease_params'] = jsonutils.dumps({
            'name': utils.generate_uid('lease', size=6),
            'start': CONF.reservation_start_date, 
            'end': (base + delta_days + delta_hours + delta_minutes).strftime('%Y-%m-%d %H:%M')
        })
        if 'server' in body:
            if 'scheduler_hints' in body['server']:
                if not 'lease_params' in body['server']['scheduler_hints']:
                    body['server']['scheduler_hints'].update(default_hints)
            else:
                body['server']['scheduler_hints'] = default_hints
        else:
            attr = '%s:scheduler_hints' % 'OS-SCH-HNT'
            if 'os:scheduler_hints' in body and \
                    not 'lease_params' in body['os:scheduler_hints']:
                body['os:scheduler_hints'].update(default_hints)
            elif attr in body and not 'lease_params' in body[attr]:
                body[attr].update(default_hints)
        yield


class Default_reservation(extensions.ExtensionDescriptor):
    """Instance reservation system."""

    name = "DefaultReservation"
    alias = "os-default-instance-reservation"

    def get_controller_extensions(self):
        controller = DefaultReservationController()
        extension = extensions.ControllerExtension(self, 'servers', controller)
        return [extension]

