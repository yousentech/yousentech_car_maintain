from datetime import timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_amount

from .maintenance import PERIODIC_GROUP

REPORT_GROUP = 'yousentech_car_maintain.group_workshop_followup_reports'
STATUS_CLASS = {'ok': 'b-ok', 'soon': 'b-soon', 'due': 'b-due', 'na': 'b-na', 'sold': 'b-na'}
ORDER_STATE_CLASS = {'draft': 'b-na', 'approved': 'b-old', 'in_progress': 'b-soon', 'done': 'b-ok', 'cancelled': 'b-na'}


def _num(value):
    return '{:,}'.format(int(round(value or 0)))


def _date(value):
    return value.strftime('%d/%m/%Y') if value else ''


class WorkshopMaintenanceReport(models.AbstractModel):
    """Data provider for the customer follow-up & periodic maintenance reports (section 11).
    Reads run under the user's access rights and company rules; labels are prepared here
    so the OWL page only renders."""
    _name = 'yt.maintenance.report'
    _description = 'تقارير متابعة العملاء والصيانة الدورية'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _check_report_access(self):
        if not (self.env.user.has_group(REPORT_GROUP) or self.env.user.has_group('base.group_system')):
            raise AccessError(_('عرض تقارير متابعة العملاء يتطلب صلاحية «عرض تقارير متابعة العملاء».'))

    def _today(self):
        return fields.Date.context_today(self)

    def _local_date(self, value):
        return fields.Datetime.context_timestamp(self, value).date() if value else False

    def _thresholds(self, company):
        settings = self.env['yt.workshop.finance.settings'].sudo().search(
            [('company_id', '=', company.id)], limit=1)
        return (settings.due_soon_days if settings else 15), (settings.due_soon_km if settings else 500.0)

    def _last_odometers(self, vehicles):
        """Last valid odometer per vehicle from its completed orders (out > 0, else in > 0)."""
        result = {}
        orders = self.env['yt.reception.order'].search(
            [('vehicle_id', 'in', vehicles.ids), ('state', '=', 'done')],
            order='arrival_at desc, id desc')
        for order in orders:
            if order.vehicle_id.id in result:
                continue
            value = order.odometer_out if order.odometer_out > 0 else order.odometer_in
            if value and value > 0:
                result[order.vehicle_id.id] = (value, self._local_date(order.done_at or order.arrival_at))
        return result

    def _sold_vehicle_ids(self, vehicles):
        """Vehicles whose latest follow-up for the current owner is «باع السيارة»."""
        sold = set()
        followups = self.env['yt.vehicle.followup'].search(
            [('vehicle_id', 'in', vehicles.ids)], order='date desc, id desc')
        seen = set()
        for followup in followups:
            vehicle = followup.vehicle_id
            if vehicle.id in seen or followup.partner_id != vehicle.partner_id:
                continue
            seen.add(vehicle.id)
            if followup.result == 'sold':
                sold.add(vehicle.id)
        return sold

    def _track_status(self, event, last_odo, today, soon_days, soon_km):
        if not event:
            return 'na', _('لا توجد بيانات')
        remaining_days = (event.next_due_date - today).days if event.next_due_date else None
        remaining_km = (event.next_due_km - last_odo) if (event.next_due_km and last_odo) else None
        if remaining_km is not None and remaining_km < 0:
            return 'due', _('متأخر %s كم') % _num(-remaining_km)
        if remaining_days is not None and remaining_days < 0:
            return 'due', _('متأخر %s يوم') % -remaining_days
        if remaining_days is None and remaining_km is None:
            return 'na', _('الممشى غير متوفر')
        parts = []
        if remaining_km is not None:
            parts.append(_('%s كم') % _num(remaining_km))
        if remaining_days is not None:
            parts.append(_('%s يوم') % remaining_days)
        soon = ((remaining_days is not None and remaining_days <= soon_days)
                or (remaining_km is not None and remaining_km <= soon_km))
        return ('soon' if soon else 'ok'), _('متبقي ') + _(' أو ').join(parts)

    def _next_label(self, event):
        parts = []
        if event.next_due_km:
            parts.append(_('%s كم') % _num(event.next_due_km))
        if event.next_due_date:
            parts.append(_date(event.next_due_date))
        return _(' أو ').join(parts) or _('غير متوفر')

    def _interval_label(self, event):
        parts = []
        if event.interval_km:
            parts.append(_('%s كم') % _num(event.interval_km))
        if event.interval_days:
            parts.append(_('%s يوم') % event.interval_days)
        source = dict(event._fields['interval_source']._description_selection(self.env)).get(event.interval_source, '')
        return _(' أو ').join(parts) + (' (%s)' % source if source else '')

    def _vehicle_tracks(self, vehicles, include_empty_oils=True):
        """Current track list per vehicle: periodic + one entry per oil type."""
        today = self._today()
        odometers = self._last_odometers(vehicles)
        sold = self._sold_vehicle_ids(vehicles)
        events = self.env['yt.vehicle.service.event'].search(
            [('vehicle_id', 'in', vehicles.ids), ('state', '=', 'active')],
            order='done_date desc, id desc')
        by_vehicle = {}
        for event in events:
            by_vehicle.setdefault(event.vehicle_id.id, []).append(event)
        oil_types = self.env['yt.oil.type'].search([])
        thresholds = {}
        result = {}
        for vehicle in vehicles:
            if vehicle.company_id.id not in thresholds:
                thresholds[vehicle.company_id.id] = self._thresholds(vehicle.company_id)
            soon_days, soon_km = thresholds[vehicle.company_id.id]
            last_odo = odometers.get(vehicle.id, (0.0, False))[0]
            vehicle_events = by_vehicle.get(vehicle.id, [])
            keys = [('periodic', _('الصيانة الدورية'), False)]
            used_oils = {e.oil_type_id.id for e in vehicle_events if e.track_type == 'oil'}
            for oil_type in oil_types:
                if include_empty_oils or oil_type.id in used_oils:
                    keys.append(('oil:%s' % oil_type.id, oil_type.name, oil_type))
            tracks = []
            for key, name, oil_type in keys:
                history = [e for e in vehicle_events if e.track_key == key]
                current = history[0] if history else False
                if vehicle.id in sold:
                    status, label = 'sold', _('باع السيارة')
                else:
                    status, label = self._track_status(current, last_odo, today, soon_days, soon_km)
                tracks.append({
                    'key': key,
                    'name': name,
                    'is_oil': bool(oil_type),
                    'status': status,
                    'cls': STATUS_CLASS[status],
                    'label': label,
                    'last': ('%s · %s' % (_date(current.done_date), _('%s كم') % _num(current.done_odometer)
                                          if current.has_odometer else _('الممشى غير متوفر'))) if current else _('لم يُسجل'),
                    'product': current.product_id.display_name if current and current.product_id else '',
                    'interval': self._interval_label(current) if current else '',
                    'next': self._next_label(current) if current else _('غير متوفر'),
                    'next_date': _date(current.next_due_date) if current else '',
                    'log': [{
                        'date': _date(e.done_date),
                        'odo': _('%s كم') % _num(e.done_odometer) if e.has_odometer else '—',
                        'product': e.product_id.display_name or '',
                        'history': e.interval_source == 'history',
                    } for e in history[:10]],
                    'order_id': current.order_id.id if current else False,
                })
            result[vehicle.id] = tracks
        return result

    def _vehicle_card(self, vehicle, tracks, odometers, visits=0, orders=0, last_visit=False):
        odo = odometers.get(vehicle.id)
        title = ' '.join(filter(None, [vehicle.make_id.name, vehicle.model_id.name,
                                       str(vehicle.year) if vehicle.year else '']))
        return {
            'id': vehicle.id,
            'title': title or vehicle.display_name,
            'plate': vehicle.plate_spaced or vehicle.plate or '',
            'vin': vehicle.vin or '',
            'color': vehicle.color or '',
            'odo': _('%s كم') % _num(odo[0]) if odo else _('الممشى غير متوفر'),
            'odo_date': _date(odo[1]) if odo else '',
            'visits': visits,
            'orders': orders,
            'last_visit': _date(last_visit) if last_visit else '',
            'tracks': tracks,
        }

    def _visits(self, orders):
        """Visit = same customer + same branch + same local arrival day (approved rule)."""
        return {(o.partner_id.id, o.branch_id.id, self._local_date(o.arrival_at)) for o in orders}

    def _order_domain(self, date_from=False, date_to=False, branch_ids=False):
        domain = []
        if date_from:
            domain.append(('arrival_at', '>=', fields.Datetime.to_datetime(date_from)))
        if date_to:
            domain.append(('arrival_at', '<', fields.Datetime.to_datetime(date_to) + timedelta(days=1)))
        if branch_ids:
            domain.append(('branch_id', 'in', branch_ids))
        return domain

    def _partner_header(self, partner):
        mobile = partner.mobile or partner.phone or ''
        digits = ''.join(ch for ch in mobile if ch.isdigit())
        return {
            'id': partner.id,
            'name': partner.display_name,
            'initials': ''.join(w[:1] for w in (partner.name or '').split()[:2]),
            'type': _('شركة') if partner.commercial_partner_id.is_company else _('فرد'),
            'mobile': mobile,
            'tel': 'tel:%s' % mobile.replace(' ', '') if mobile else '',
            'whatsapp': 'https://wa.me/%s' % digits if digits else '',
        }

    # ------------------------------------------------------------------
    # Report 1: customer vehicles maintenance history
    # ------------------------------------------------------------------
    @api.model
    def get_customer_report(self, params):
        self._check_report_access()
        partner = self.env['res.partner'].browse(int(params.get('partner_id') or 0)).exists()
        if not partner:
            raise UserError(_('اختر العميل.'))
        partner.check_access_rule('read')
        vehicle_domain = [('partner_id', '=', partner.id)]
        if params.get('vehicle_id'):
            vehicle_domain.append(('id', '=', int(params['vehicle_id'])))
        vehicles = self.env['yt.reception.vehicle'].search(vehicle_domain)
        Order = self.env['yt.reception.order']
        period = self._order_domain(params.get('date_from'), params.get('date_to'), params.get('branch_ids'))
        partner_orders = Order.search([('partner_id', '=', partner.id), ('state', '!=', 'cancelled')] + period)
        if params.get('vehicle_id'):
            partner_orders = partner_orders.filtered(lambda o: o.vehicle_id in vehicles)
        tracks = self._vehicle_tracks(vehicles)
        odometers = self._last_odometers(vehicles)
        cards, alerts = [], []
        for vehicle in vehicles:
            v_orders = partner_orders.filtered(lambda o: o.vehicle_id == vehicle)
            last_visit = max([self._local_date(o.arrival_at) for o in v_orders], default=False)
            card = self._vehicle_card(vehicle, tracks[vehicle.id], odometers,
                                      visits=len(self._visits(v_orders)),
                                      orders=len(v_orders.filtered(lambda o: o.state == 'done')),
                                      last_visit=last_visit)
            cards.append(card)
            for track in card['tracks']:
                if track['status'] in ('due', 'soon'):
                    alerts.append({'vehicle_id': vehicle.id, 'plate': card['plate'], 'track': track['name'],
                                   'track_key': track['key'], 'next': track['next'],
                                   'status': track['status'], 'cls': track['cls'], 'label': track['label']})
        alerts.sort(key=lambda a: 0 if a['status'] == 'due' else 1)
        return {
            'partner': self._partner_header(partner),
            'filters': self._filters_label(params),
            'today': _date(self._today()),
            'stats': {
                'vehicles': len(vehicles),
                'visits': len(self._visits(partner_orders)),
                'orders': len(partner_orders.filtered(lambda o: o.state == 'done')),
            },
            'alerts': alerts,
            'vehicles': cards,
        }

    @api.model
    def get_vehicle_detail(self, params):
        self._check_report_access()
        vehicle = self.env['yt.reception.vehicle'].browse(int(params.get('vehicle_id') or 0)).exists()
        if not vehicle:
            raise UserError(_('السيارة غير موجودة.'))
        vehicle.check_access_rule('read')
        Order = self.env['yt.reception.order']
        period = self._order_domain(params.get('date_from'), params.get('date_to'), params.get('branch_ids'))
        orders = Order.search([('vehicle_id', '=', vehicle.id)] + period, order='arrival_at desc, id desc')
        states = dict(Order._fields['state']._description_selection(self.env))
        timeline = []
        for order in orders:
            services = order.sale_line_ids.filtered(lambda l: l.product_id.type == 'service')
            technicians = services.mapped('technician_ids.name')
            meta = [_('دخول %s كم') % _num(order.odometer_in) if order.odometer_in else '',
                    _('خروج %s كم') % _num(order.odometer_out) if order.odometer_out else '',
                    '، '.join(technicians)]
            if order.partner_id != vehicle.partner_id:
                meta.append(_('المالك وقت الأمر: %s') % order.partner_id.display_name)
            if order.state == 'cancelled':
                meta.append(_('لا يدخل في الحساب'))
            timeline.append({
                'id': order.id, 'name': order.name or '',
                'date': _date(self._local_date(order.arrival_at)),
                'state': states.get(order.state, ''), 'cls': ORDER_STATE_CLASS.get(order.state, 'b-na'),
                'services': ' · '.join(order.sale_line_ids.mapped('name')) or _('بدون بنود'),
                'meta': ' · '.join(filter(None, meta)),
            })
        inspected = Order.search([('vehicle_id', '=', vehicle.id), ('inspection_state', '=', 'done'),
                                  ('state', '!=', 'cancelled')], order='inspection_at desc, id desc', limit=1)
        conditions = dict(self.env['yt.inspection.line']._fields['condition']._description_selection(self.env))
        inspection = {
            'date': _date(self._local_date(inspected.inspection_at)) if inspected else '',
            'order': inspected.name or '', 'order_id': inspected.id,
            'employee': inspected.inspection_employee_id.name or '',
            'lines': [{'name': l.component_name or l.component_id.name, 'note': l.notes or '',
                       'status': conditions.get(l.condition, ''),
                       'cls': 'b-due' if l.condition == 'bad' else 'b-soon'}
                      for l in inspected.inspection_line_ids.filtered(lambda l: l.condition in ('follow_up', 'bad'))],
        }
        results = dict(self.env['yt.vehicle.followup']._fields['result']._description_selection(self.env))
        followups = [{
            'result': results.get(f.result, ''),
            'track': (f.oil_type_id.name if f.track_type == 'oil' else (_('الصيانة الدورية') if f.track_type else '')),
            'date': _date(self._local_date(f.date)), 'user': f.user_id.name,
            'note': f.note or '', 'next': _('المتابعة القادمة: %s') % _date(f.next_date) if f.next_date else '',
        } for f in vehicle.followup_ids.sorted(lambda f: (f.date, f.id), reverse=True)[:30]]
        odometers = self._last_odometers(vehicle)
        card = self._vehicle_card(vehicle, self._vehicle_tracks(vehicle)[vehicle.id], odometers)
        card.update({'owner': vehicle.partner_id.display_name, 'partner_id': vehicle.partner_id.id,
                     'timeline': timeline, 'inspection': inspection, 'followups': followups})
        return card

    def _filters_label(self, params):
        parts = []
        if params.get('branch_ids'):
            parts.append('، '.join(self.env['res.company'].browse(params['branch_ids']).mapped('name')))
        else:
            parts.append(_('جميع الفروع المسموحة'))
        if params.get('date_from') or params.get('date_to'):
            parts.append('%s – %s' % (_date(fields.Date.to_date(params.get('date_from'))) or '…',
                                      _date(fields.Date.to_date(params.get('date_to'))) or '…'))
        return ' · '.join(parts)

    # ------------------------------------------------------------------
    # Report 2/3: upcoming and overdue dues (replaces 9.3.6)
    # ------------------------------------------------------------------
    @api.model
    def get_dues_report(self, params):
        self._check_report_access()
        statuses = params.get('statuses') or ['due', 'soon']
        domain = [('state', '=', 'active')]
        if params.get('branch_ids'):
            domain.append(('company_id', 'in', params['branch_ids']))
        if params.get('track') == 'periodic':
            domain.append(('track_type', '=', 'periodic'))
        elif params.get('track') == 'oil':
            domain.append(('track_type', '=', 'oil'))
        vehicles = self.env['yt.vehicle.service.event'].search(domain).mapped('vehicle_id')
        tracks = self._vehicle_tracks(vehicles, include_empty_oils=False)
        rows = []
        counts = {'due': 0, 'soon': 0}
        for vehicle in vehicles:
            header = self._partner_header(vehicle.partner_id)
            for track in tracks[vehicle.id]:
                if track['status'] not in statuses:
                    continue
                if params.get('track') == 'periodic' and track['is_oil']:
                    continue
                if params.get('track') == 'oil' and not track['is_oil']:
                    continue
                counts[track['status']] = counts.get(track['status'], 0) + 1
                rows.append({
                    'vehicle_id': vehicle.id, 'partner_id': vehicle.partner_id.id,
                    'plate': vehicle.plate_spaced or vehicle.plate or '',
                    'vehicle': ' '.join(filter(None, [vehicle.make_id.name, vehicle.model_id.name])),
                    'customer': header['name'], 'mobile': header['mobile'],
                    'tel': header['tel'], 'whatsapp': header['whatsapp'],
                    'track': track['name'], 'track_key': track['key'], 'next': track['next'],
                    'status': track['status'], 'cls': track['cls'], 'label': track['label'],
                    'branch': vehicle.company_id.name,
                })
        rows.sort(key=lambda r: (0 if r['status'] == 'due' else 1, r['customer']))
        return {'title': params.get('title') or _('الاستحقاقات'), 'filters': self._filters_label(params),
                'today': _date(self._today()), 'counts': counts, 'rows': rows}

    # ------------------------------------------------------------------
    # Report 4: lapsed customers
    # ------------------------------------------------------------------
    @api.model
    def get_lapsed_report(self, params):
        self._check_report_access()
        days = int(params.get('lapsed_days') or 180)
        cutoff = fields.Datetime.now() - timedelta(days=days)
        domain = [('state', '=', 'done')]
        if params.get('branch_ids'):
            domain.append(('branch_id', 'in', params['branch_ids']))
        data = self.env['yt.reception.order']._read_group(
            domain, ['partner_id'], ['arrival_at:max', '__count'])
        today = self._today()
        rows = []
        for partner, last_arrival, count in data:
            if not partner or not last_arrival or last_arrival >= cutoff:
                continue
            header = self._partner_header(partner)
            last_date = self._local_date(last_arrival)
            rows.append({
                'partner_id': partner.id, 'customer': header['name'], 'mobile': header['mobile'],
                'tel': header['tel'], 'whatsapp': header['whatsapp'],
                'last_visit': _date(last_date), 'days': (today - last_date).days,
                'orders': count,
                'vehicles': self.env['yt.reception.vehicle'].search_count([('partner_id', '=', partner.id)]),
            })
        rows.sort(key=lambda r: -r['days'])
        return {'filters': self._filters_label(params), 'lapsed_days': days,
                'today': _date(today), 'rows': rows}

    # ------------------------------------------------------------------
    # Report 5: customer statement at the workshop (rules of 7.1.1)
    # ------------------------------------------------------------------
    @api.model
    def get_statement_report(self, params):
        self._check_report_access()
        partner = self.env['res.partner'].browse(int(params.get('partner_id') or 0)).exists()
        if not partner:
            raise UserError(_('اختر العميل.'))
        partner.check_access_rule('read')
        domain = [('partner_id', '=', partner.id), ('state', '!=', 'draft')]
        if params.get('branch_ids'):
            domain.append(('branch_id', 'in', params['branch_ids']))
        orders = self.env['yt.reception.order'].search(domain, order='arrival_at desc, id desc')
        date_from = fields.Date.to_date(params.get('date_from')) if params.get('date_from') else False
        date_to = fields.Date.to_date(params.get('date_to')) if params.get('date_to') else False

        def in_period(value):
            return value and (not date_from or value >= date_from) and (not date_to or value <= date_to)

        movements, seen_moves, seen_payments = [], set(), set()
        totals = {'invoiced': 0.0, 'credited': 0.0, 'received': 0.0, 'refunded': 0.0}
        currency = self.env.company.currency_id
        order_rows = []
        for order in orders:
            currency = order.currency_id or currency
            for move in order.finance_invoice_ids.filtered(lambda m: m.state == 'posted'):
                if move.id in seen_moves or not in_period(move.invoice_date or move.date):
                    continue
                seen_moves.add(move.id)
                is_invoice = move.move_type == 'out_invoice'
                totals['invoiced' if is_invoice else 'credited'] += move.amount_total
                movements.append({'date': move.invoice_date or move.date, 'type': _('فاتورة') if is_invoice else _('إشعار دائن'),
                                  'ref': move.name, 'order': order.name, 'amount': move.amount_total,
                                  'sign': 1 if is_invoice else -1})
            for payment in order.finance_payment_ids:
                if payment.id in seen_payments or not in_period(payment.date):
                    continue
                seen_payments.add(payment.id)
                inbound = payment.payment_type == 'inbound'
                amount = payment.currency_id._convert(payment.amount, currency, order.company_id, payment.date)
                totals['received' if inbound else 'refunded'] += amount
                movements.append({'date': payment.date, 'type': _('تحصيل') if inbound else _('رد مبلغ'),
                                  'ref': payment.name, 'order': order.name, 'amount': amount,
                                  'sign': -1 if inbound else 1})
            if order.state != 'cancelled':
                order_rows.append({'id': order.id, 'name': order.name or '',
                                   'date': _date(self._local_date(order.arrival_at)),
                                   'vehicle': order.vehicle_id.plate_spaced or order.vehicle_id.plate or '',
                                   'invoiced': order.finance_invoiced - order.finance_credited,
                                   'due': order.finance_due, 'to_refund': order.finance_to_refund})
        movements.sort(key=lambda m: m['date'], reverse=True)
        fmt = lambda amount: format_amount(self.env, amount, currency)
        outstanding = sum(r['due'] for r in order_rows)
        to_refund = sum(r['to_refund'] for r in order_rows)
        for row in order_rows:
            row.update({'invoiced': fmt(row['invoiced']), 'due': fmt(row['due'])})
        for move in movements:
            move.update({'date': _date(move['date']), 'amount': fmt(move['amount'])})
        return {
            'partner': self._partner_header(partner), 'filters': self._filters_label(params),
            'today': _date(self._today()),
            'kpis': [
                {'label': _('الفواتير'), 'value': fmt(totals['invoiced']), 'hint': _('بتاريخ الفاتورة ضمن الفترة')},
                {'label': _('التحصيل'), 'value': fmt(totals['received']), 'hint': _('بتاريخ التحصيل ضمن الفترة')},
                {'label': _('المرتجعات'), 'value': fmt(totals['credited']), 'hint': _('إشعارات دائنة ضمن الفترة')},
                {'label': _('الرصيد المستحق'), 'value': fmt(outstanding), 'hint': _('رصيد قائم حتى اليوم، ليس حركة فترة')},
            ],
            'to_refund': fmt(to_refund) if to_refund else '',
            'refunded': fmt(totals['refunded']) if totals['refunded'] else '',
            'movements': movements,
            'orders': order_rows,
        }

    # ------------------------------------------------------------------
    # Customer PDF (no amounts, no previous-owner data)
    # ------------------------------------------------------------------
    @api.model
    def get_customer_pdf_data(self, vehicle_id):
        self._check_report_access()
        detail = self.get_vehicle_detail({'vehicle_id': vehicle_id})
        owner = detail['partner_id']
        orders = self.env['yt.reception.order'].search(
            [('vehicle_id', '=', vehicle_id), ('state', '=', 'done'), ('partner_id', '=', owner)],
            order='arrival_at desc, id desc')
        detail['history'] = [{
            'date': _date(self._local_date(o.arrival_at)), 'name': o.name or '',
            'odo': _num(o.odometer_out if o.odometer_out > 0 else o.odometer_in) if (o.odometer_out or o.odometer_in) else '—',
            'work': '، '.join(o.sale_line_ids.mapped('name')),
        } for o in orders]
        detail['tracks'] = [t for t in detail['tracks'] if t['status'] != 'na' or not t['is_oil']]
        return detail


class WorkshopCustomerMaintenancePdf(models.AbstractModel):
    _name = 'report.yousentech_car_maintain.report_customer_maintenance'
    _description = 'PDF سجل صيانة السيارة للعميل'

    @api.model
    def _get_report_values(self, docids, data=None):
        vehicle_id = (data or {}).get('vehicle_id') or (docids[0] if docids else False)
        payload = self.env['yt.maintenance.report'].get_customer_pdf_data(int(vehicle_id))
        return {'doc_ids': docids, 'doc_model': 'yt.reception.vehicle',
                'docs': self.env['yt.reception.vehicle'].browse(int(vehicle_id)),
                'payload': payload, 'company': self.env.company}


class WorkshopMaintenanceReportWizard(models.TransientModel):
    """Filter window for the follow-up reports; opens the OWL page."""
    _name = 'yt.maintenance.report.wizard'
    _description = 'فلاتر تقارير متابعة العملاء'

    report_type = fields.Selection([
        ('customer', 'سجل صيانة سيارات العميل'), ('upcoming', 'الاستحقاقات القادمة'),
        ('overdue', 'الاستحقاقات الفائتة والمتأخرة'), ('lapsed', 'العملاء المنقطعون'),
        ('statement', 'كشف حساب العميل لدى الورشة'),
    ], required=True, default='customer')
    partner_id = fields.Many2one('res.partner', string='العميل')
    vehicle_id = fields.Many2one('yt.reception.vehicle', string='السيارة',
                                 domain="[('partner_id', '=', partner_id)]")
    branch_ids = fields.Many2many('res.company', string='الفروع', domain=lambda self: [('id', 'in', self.env.companies.ids)])
    date_from = fields.Date(string='من تاريخ')
    date_to = fields.Date(string='إلى تاريخ')
    track = fields.Selection([('all', 'الكل'), ('periodic', 'الصيانة الدورية'), ('oil', 'الزيوت')],
                             string='المسار', default='all')
    lapsed_days = fields.Integer(string='منقطع منذ (يوم)', default=180)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.vehicle_id and self.vehicle_id.partner_id != self.partner_id:
            self.vehicle_id = False

    def action_open_report(self):
        self.ensure_one()
        if self.report_type in ('customer', 'statement') and not self.partner_id:
            raise UserError(_('اختر العميل.'))
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_('تاريخ البداية يجب أن يسبق تاريخ النهاية.'))
        params = {
            'report_type': self.report_type,
            'partner_id': self.partner_id.id or False,
            'vehicle_id': self.vehicle_id.id or False,
            'branch_ids': self.branch_ids.ids,
            'date_from': fields.Date.to_string(self.date_from) if self.date_from else False,
            'date_to': fields.Date.to_string(self.date_to) if self.date_to else False,
            'track': self.track if self.track != 'all' else False,
            'lapsed_days': self.lapsed_days,
        }
        if self.report_type == 'upcoming':
            params.update(statuses=['soon'], title=_('الاستحقاقات القادمة'))
        elif self.report_type == 'overdue':
            params.update(statuses=['due'], title=_('الاستحقاقات الفائتة والمتأخرة'))
        return {'type': 'ir.actions.client', 'tag': 'yt_maintenance_report',
                'name': dict(self._fields['report_type']._description_selection(self.env))[self.report_type],
                'params': params}


class WorkshopOilHistoryWizard(models.TransientModel):
    """Phase B: one-time, re-runnable creation of oil events from past completed orders."""
    _name = 'yt.oil.history.wizard'
    _description = 'ترحيل تاريخي لأحداث الزيوت'

    company_id = fields.Many2one('res.company', string='الشركة', required=True,
                                 default=lambda self: self.env.company,
                                 domain=lambda self: [('id', 'in', self.env.companies.ids)])
    date_from = fields.Date(string='من تاريخ وصول')
    result_message = fields.Text(readonly=True)

    def action_run(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('الترحيل التاريخي متاح لمدير النظام فقط.'))
        if not self.env['product.template'].sudo().search_count([('yt_is_oil', '=', True)]):
            raise UserError(_('عرّف أصناف الزيت وأنواعها في بطاقات الأصناف قبل تشغيل الترحيل.'))
        Order = self.env['yt.reception.order'].sudo()
        Event = self.env['yt.vehicle.service.event'].sudo()
        domain = [('state', '=', 'done'), ('company_id', '=', self.company_id.id)]
        if self.date_from:
            domain.append(('arrival_at', '>=', fields.Datetime.to_datetime(self.date_from)))
        orders = Order.search(domain, order='arrival_at, id')
        created = skipped = 0
        for start in range(0, len(orders), 200):
            batch = orders[start:start + 200]
            existing = set(Event.with_context(active_test=False).search(
                [('order_id', 'in', batch.ids), ('track_type', '=', 'oil')]).mapped(
                lambda e: (e.order_id.id, e.track_key)))
            vals_list = []
            for order in batch:
                done_date = fields.Date.context_today(order, order.done_at or order.arrival_at)
                for vals in order._yt_oil_event_values('history', done_date=done_date):
                    if (order.id, vals['track_key']) in existing:
                        skipped += 1
                        continue
                    vals_list.append(vals)
            if vals_list:
                Event.create(vals_list)
                created += len(vals_list)
        self.result_message = _('تم إنشاء %(created)s حدث زيت، وتجاوز %(skipped)s حدث موجود مسبقاً، من %(orders)s أمر عمل مكتمل.') % {
            'created': created, 'skipped': skipped, 'orders': len(orders)}
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'new'}


class WorkshopPeriodicReminderWizard(models.TransientModel):
    _name = 'yt.periodic.reminder.wizard'
    _description = 'تذكير الصيانة الدورية قبل الإكمال'

    order_id = fields.Many2one('yt.reception.order', required=True, readonly=True)
    message = fields.Text(readonly=True)

    def _finish(self):
        result = self.order_id.with_context(yt_skip_periodic_reminder=True).action_finish_workshop_execution()
        return result if isinstance(result, dict) else {'type': 'ir.actions.act_window_close'}

    def action_count_and_finish(self):
        self.ensure_one()
        self.order_id.yt_is_periodic = True
        return self._finish()

    def action_finish_only(self):
        self.ensure_one()
        return self._finish()


class WorkshopOrderDueBanner(models.Model):
    _inherit = 'yt.reception.order'

    yt_due_banner = fields.Html(string='استحقاقات السيارة', compute='_compute_yt_due_banner',
                                sanitize=False, readonly=True)

    @api.depends('vehicle_id', 'state')
    def _compute_yt_due_banner(self):
        Report = self.env['yt.maintenance.report']
        for order in self:
            order.yt_due_banner = False
            if not order.vehicle_id or order.state in ('done', 'cancelled'):
                continue
            tracks = Report._vehicle_tracks(order.vehicle_id, include_empty_oils=False).get(order.vehicle_id.id, [])
            items = [t for t in tracks if t['status'] in ('due', 'soon')]
            if not items:
                continue
            chips = Markup('').join(
                Markup('<span class="yt-due-chip %s">%s · %s</span>') % (t['cls'], escape(t['name']), escape(t['label']))
                for t in items)
            order.yt_due_banner = Markup(
                '<div class="yt-due-banner" role="status"><strong>%s</strong><div class="yt-due-chips">%s</div></div>'
            ) % (_('هذه السيارة عليها استحقاقات'), chips)

    def _yt_needs_periodic_reminder(self):
        self.ensure_one()
        if (self.env.context.get('yt_skip_periodic_reminder') or self.state != 'in_progress'
                or not self.env.user.has_group(PERIODIC_GROUP) or self.yt_is_periodic):
            return False
        tracks = self.env['yt.maintenance.report']._vehicle_tracks(
            self.vehicle_id, include_empty_oils=False).get(self.vehicle_id.id, [])
        periodic = next((t for t in tracks if t['key'] == 'periodic'), None)
        return periodic if periodic and periodic['status'] in ('due', 'soon') else False

    def _yt_check_maintenance_odometer(self):
        """Optional company rule: orders that create maintenance events need a valid odometer."""
        for order in self:
            settings = self.env['yt.workshop.finance.settings'].sudo().search(
                [('company_id', '=', order.company_id.id)], limit=1)
            if not settings.enforce_maintenance_odometer:
                continue
            has_oil = order.sale_line_ids.filtered(lambda l: l.product_id.product_tmpl_id.yt_is_oil)
            if not (order.sudo().yt_is_periodic or has_oil):
                continue
            odometer = order._yt_done_odometer()
            if not odometer:
                raise UserError(_('أدخل عداد الدخول أو الخروج قبل إكمال الأمر؛ متابعة الصيانة والزيوت تحتاج قراءة عداد صحيحة.'))
            previous = self.search([('vehicle_id', '=', order.vehicle_id.id), ('state', '=', 'done'),
                                    ('id', '!=', order.id)])
            readings = [max(o.odometer_out or 0, o.odometer_in or 0) for o in previous]
            last = max(readings, default=0)
            if last and odometer < last:
                raise UserError(_('عداد هذا الأمر (%(current)s كم) أقل من آخر قراءة مسجلة للسيارة (%(last)s كم). صحّح العداد قبل الإكمال.') % {
                    'current': '{:,}'.format(int(odometer)), 'last': '{:,}'.format(int(last))})

    def action_finish_workshop_execution(self):
        self._yt_check_maintenance_odometer()
        if len(self) == 1:
            periodic = self._yt_needs_periodic_reminder()
            if periodic:
                wizard = self.env['yt.periodic.reminder.wizard'].create({
                    'order_id': self.id,
                    'message': _('الصيانة الدورية لهذه السيارة: %s. خيار «احتساب هذا الأمر كصيانة دورية» غير مفعّل. هل تريد احتسابه قبل الإكمال؟') % periodic['label'],
                })
                return {'type': 'ir.actions.act_window', 'name': _('السيارة مستحقة صيانة دورية'),
                        'res_model': wizard._name, 'res_id': wizard.id, 'view_mode': 'form', 'target': 'new'}
        return super().action_finish_workshop_execution()
