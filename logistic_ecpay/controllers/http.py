# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import json
import logging

from odoo.http import JsonRPCDispatcher, Response
from odoo.tools import date_utils
from .main import WITHOUT_JSONRPC_ROUTES

_logger = logging.getLogger(__name__)


class OverrideJsonRequest(JsonRPCDispatcher):
    def _response(self, result=None, error=None):
        if self.request.httprequest.path in WITHOUT_JSONRPC_ROUTES:
            response = {}

            if error is not None:
                response = error
            if result is not None:
                response = result
        else:
            response = {
                'jsonrpc': '2.0',
                'id': self.jsonrequest.get('id')
            }

            if error is not None:
                response['error'] = error
            if result is not None:
                response['result'] = result

        mime = 'application/json'
        body = json.dumps(response, default=date_utils.json_default)

        return Response(
            body, status=error and error.pop('http_status', 200) or 200,
            headers=[('Content-Type', mime), ('Content-Length', len(body))]
        )


# 因為在 odoo 裡，前底線為受保護成員，但 python 無此規範，所以強制覆寫
JsonRPCDispatcher._response = OverrideJsonRequest._response
