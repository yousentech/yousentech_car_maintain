"""Vehicles become shared between branches (company_id empty).

A vehicle is made shared only when its plate identity (country, type, plate) is unique in the
whole table. Vehicles registered with the same plate in more than one branch are left as they
are (branch-bound) and listed in the server log so they can be merged manually; until then the
new database-wide plate constraint cannot be created and the Python check guards new records.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("ALTER TABLE yt_reception_vehicle DROP CONSTRAINT IF EXISTS yt_reception_vehicle_plate_unique")
    cr.execute("""
        UPDATE yt_reception_vehicle v SET company_id = NULL
         WHERE company_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM yt_reception_vehicle o
                WHERE o.id != v.id AND o.plate = v.plate
                  AND o.plate_country = v.plate_country AND o.plate_type = v.plate_type)
    """)
    _logger.info('yousentech_car_maintain: %s vehicles are now shared between branches.', cr.rowcount)
    cr.execute("""
        SELECT plate_country, plate_type, plate, array_agg(id ORDER BY id), array_agg(company_id ORDER BY id)
          FROM yt_reception_vehicle GROUP BY plate_country, plate_type, plate HAVING count(*) > 1
    """)
    for country, plate_type, plate, ids, companies in cr.fetchall():
        _logger.warning('yousentech_car_maintain: plate %s/%s/%s is registered more than once '
                        '(vehicle ids %s, companies %s); left branch-bound, merge manually.',
                        country, plate_type, plate, ids, companies)
