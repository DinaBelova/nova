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

import webob

from nova.api.openstack import common
from nova.api.openstack import extensions
from nova.api.openstack import wsgi
from nova import compute
from nova import exception
from nova.openstack.common import log as logging


LOG = logging.getLogger(__name__)
authorize = extensions.extension_authorizer('compute', 'reservation')


class ReservationController(wsgi.Controller):
    """Reservation controller to support VMs wake up."""
    def __init__(self, *args, **kwargs):
        super(ReservationController, self).__init__(*args, **kwargs)
        self.compute_api = compute.API()

    @wsgi.action('wakeUp')
    def _wake_up(self, req, id, body):
        """Support for wake-up action for reserved instance."""
        context = req.environ["nova.context"]
        authorize(context)
        instance = self.compute_api.get(context, id)
        try:
            self.compute_api.wake_up(context, instance)
        except exception.QuotaError as error:
            raise webob.exc.HTTPRequestEntityTooLarge(
                explanation=error.format_message(),
                headers={'Retry-After': 0}
            )
        except exception.InstanceInvalidState as state_error:
            common.raise_http_conflict_for_instance_invalid_state(
                state_error,
                'wake_up'
            )

        return webob.Response(status_int=202)


class Reservation(extensions.ExtensionDescriptor):
    """Instance reservation system."""

    name = "Reservation"
    alias = "os-instance-reservation"

    def get_controller_extensions(self):
        controller = ReservationController()
        extension = extensions.ControllerExtension(self, 'servers', controller)
        return [extension]
