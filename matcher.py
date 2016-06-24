from contextlib import suppress
from emoji import emojize
from bisect import bisect_right
from tfl import TflDataAccess
from flask_app import tfl_username, tfl_password


def update_old_transactions_with_journeys(account):
    tfl = TflDataAccess(tfl_username, tfl_password)
    payments = tfl.all_payments()
    tfl_transactions = [x for x in account.transactions if is_tfl(x)]
    matches = find_matches(tfl_transactions, payments)

    for (transaction, payment) in (x for x in matches if x[1] is not None and x[0].notes is not None):
        journey = journey_string(payment.journeys)
        unit_separator = chr(31)
        existing_notes = transaction.notes.split(unit_separator)[0]
        updated_notes = '{}{}\n{}'.format(existing_notes, unit_separator, journey)

        transaction.add_metadata(
            {'journey_info': journey,
             'notes': updated_notes})


def journey_string(journeys):
    def format_journey(j):
        if j.station_from.startswith('Bus'):
            return emojize(':bus:  ({}) {}'.format(j.time, j.station_from.strip('Bus Journey,')))
        return emojize(':train:  ({}) {} -> {}'.format(j.time, j.station_from, j.station_to))

    return '\n'.join([format_journey(x) for x in journeys])


def find_matches(tfl_transactions, payments):
    sorted_keys = sorted(payments.keys())
    tfl_transactions.sort(key=lambda t: t.created)
    matches = []
    for tran in tfl_transactions:
        found = None
        stop = bisect_right(sorted_keys, tran.created.date())
        start = max(stop - 3, 0)

        for i in range(start, stop):
            if payments[sorted_keys[i]].cost == int(tran.amount.value * 100):
                found = payments[sorted_keys.pop(i)]
                break

        matches.append((tran, found))
    return matches


def is_tfl(transaction):
    with suppress(AttributeError):
        if transaction.merchant.group_id == 'grp_000092JYbUJtEgP9xND1Iv':
            return True
    return False
