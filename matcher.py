from datetime import datetime, timedelta
from contextlib import suppress
from emoji import emojize
from bisect import bisect_right
from tfl import TflDataAccess
from flask_app import tfl_username, tfl_password, db, client_id, client_secret
from mondo import MondoClient
from mondo.exceptions import MondoApiException
from mondo.authorization import refresh_access_token
from mondo.mondo import BasicFeedItem
from db_models import MondoAccount
import asyncio


def update_old_transactions_with_journeys(account_id):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_old_transactions_with_journeys_async(account_id))

async def update_old_transactions_with_journeys_async(account_id):
    client = client_from_account_id(account_id)
    transactions = await client.list_transactions_async(client.default_account.id)
    tfl = TflDataAccess(tfl_username, tfl_password)
    payments = tfl.all_payments()
    tfl_transactions = (x for x in transactions if is_tfl(x))
    matches = find_matches(tfl_transactions, payments)
    update_found_matches(matches)
    return len(matches)


def update_found_matches(matches):
    for (transaction, payment) in (x for x in matches if x[1] is not None and x[0].notes is not None):
        update_transaction(transaction, payment)


def update_transaction(transaction, payment):
    journey_str = '{}\n{}'.format(payment.date, journey_string(payment.journeys))
    unit_separator = chr(31)
    existing_notes = transaction.notes.split(unit_separator)[0]
    updated_notes = '{}{}\n{}'.format(existing_notes, unit_separator, journey_str)
    transaction.add_metadata({'journey_info': journey_str, 'notes': updated_notes})


def journey_string(journeys):
    def format_journey(j):
        if j.station_from.startswith('Bus'):
            return emojize(':bus:  ({}) {}'.format(j.time, j.station_from.strip('Bus Journey,')))
        return emojize(':train:  ({}) {} -> {}'.format(j.time, j.station_from, j.station_to))

    return '\n'.join([format_journey(x) for x in journeys])


def find_matches(tfl_transactions, payments):
    sorted_keys = sorted(payments.keys())
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


def client_from_account_id(account_id):
    account = db.session.query(MondoAccount).filter_by(account_id=account_id).one()
    try:
        client = MondoClient(account.token.access_token)
        client.whoami()
        return client
    except MondoApiException:
        print('refreshing access token', flush=True)
        new_access = refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=account.token.refresh_token)

        account.token.access_token = new_access.access_token
        account.token.refresh_token = new_access.refresh_token
        account.token.expires_in = datetime.now() + timedelta(seconds=new_access.expires_in)
        db.session.commit()

        return MondoClient(new_access.access_token)


def update_webhook_transaction(transaction, account_id):

    if not is_tfl(transaction):
        return

    print(transaction, flush=True)
    print('is tfl transaction', flush=True)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(update_webhook_transaction_async(transaction, account_id))


async def update_webhook_transaction_async(transaction, account_id):
    transaction.__client = client_from_account_id(account_id)
    tfl = TflDataAccess(tfl_username, tfl_password)
    payments = tfl.recent_payments()
    matches = find_matches([transaction], payments)
    update_found_matches(matches)
    print(matches, flush=True)
    if (tfl.has_incomplete_journeys()):
        b = BasicFeedItem('You have an incomplete journey', transaction.merchant.logo,
                          body='Log on to contactless.tfl.gov.uk to reclaim', url='https://contactless.tfl.gov.uk')
        transaction.__client.create_feed_item(account_id, b)
