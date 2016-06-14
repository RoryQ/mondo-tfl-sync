import requests
from lxml import html
from models import Payment, Journey
from util import text_at_xpath, first, text_to_cost
from datetime import datetime
from collections import OrderedDict


class TflDataAccess():
    LOGIN_ENDPOINT = "https://account.tfl.gov.uk/Login"
    BASE_URL = "https://contactless.tfl.gov.uk"
    MYCARDS_ENDPOINT = BASE_URL + "/MyCards"
    VIEW_CARD_ENDPOINT = BASE_URL + "/Card/View"
    STATEMENTS_ENDPOINT = BASE_URL + "/Statements/TravelStatement"
    STATEMENTS_FILTER_ENDPOINT = BASE_URL + "/Statements/Refresh"
    CARD_ID_PARAM = "pi"
    MONDO_CARD_NICKNAME = "Mondo"

    def __init__(self, username, password):
        self.session_requests = requests.session()
        self.username = username
        self.password = password
        self.auth_token = None
        self.mondo_card_id = None

        self._login()

    # Public Methods
    def has_incomplete_journeys(self):
        result = self.session_requests.get(
            self.VIEW_CARD_ENDPOINT,
            params={self.CARD_ID_PARAM: self.mondo_card_id},
            headers=dict(referer=self.MYCARDS_ENDPOINT))

        incomplete_journey_xpath = (
            '//div[@data-pageobject="card-notification"]/h5[@class='
            '"text-warning" and contains(., "Incomplete Journey")]')

        tree = html.fromstring(result.content)
        incomplete_journey = first(tree.xpath(incomplete_journey_xpath))

        return incomplete_journey is not None

    def all_payments(self):
        # get statements
        result = self.session_requests.get(
            self.STATEMENTS_ENDPOINT,
            params={self.CARD_ID_PARAM: self.mondo_card_id},
            headers=dict(referer=self.MYCARDS_ENDPOINT))
        tree = html.fromstring(result.content)

        refresh_token_xpath = (
            '//form[@id="filters"]/input[@name="'
            '__RequestVerificationToken"]/@value')
        filter_token = first(tree.xpath(refresh_token_xpath))

        periods_xpath = ('//select[@id="SelectedStatementPeriod"]'
                         '/option/@value[not(.="7")]')
        periods = tree.xpath(periods_xpath)

        def create_payload(period):
            return {
                "__RequestVerificationToken": filter_token,
                "SelectedStatementType": "Payments",
                "SelectedStatementPeriod": period,
                "PaymentCardId": self.mondo_card_id
            }

        def payments_from_statements(statements_payload):
            result = self.session_requests.post(
                self.STATEMENTS_FILTER_ENDPOINT,
                data=statements_payload,
                headers=dict(referer=self.STATEMENTS_ENDPOINT))
            tree = html.fromstring(result.content)
            statements_xpath = \
                '//div[@data-pageobject="travelstatement-paymentsummary"]'
            statement_divs = tree.xpath(statements_xpath)
            payments = (self._div_to_payment(div) for div in statement_divs)
            return ((p.date, p) for p in payments)

        payments_dict = OrderedDict()
        for period in periods:
            payments = payments_from_statements(create_payload(period))
            payments_dict.update(payments)

        return payments_dict

    # Private Methods
    def _login(self):
        result = self.session_requests.get(self.BASE_URL)
        tree = html.fromstring(result.text)
        self.auth_token = tree.xpath("//input[@name='AppId']/@value")[0]

        payload = {
            "UserName": self.username,
            "Password": self.password,
            "AppId": self.auth_token
        }

        result = self.session_requests.post(
            self.LOGIN_ENDPOINT,
            data=payload,
            headers=dict(referer=self.BASE_URL))
        tree = html.fromstring(result.content)

        # bad password
        password_xpath = '//div[@class="field-validation-error"]'
        error = first(tree.xpath(password_xpath))
        if error is not None:
            raise ValueError(error.text_content().strip())

        self._find_mondo_card()

    def _find_mondo_card(self):
        result = self.session_requests.get(
            self.MYCARDS_ENDPOINT,
            headers=dict(referer=self.BASE_URL))
        tree = html.fromstring(result.content)
        mondo_card_xpath = (
            '//a[@data-pageobject="mycards-card-cardlink" '
            'and .//span[@class="view-card-nickname" and '
            'contains(.,"' + self.MONDO_CARD_NICKNAME + '")]]/@href')

        mondo_card = first(tree.xpath(mondo_card_xpath))
        if mondo_card is None:
            raise ValueError(
                'Cannot find card with nickname ' + self.MONDO_CARD_NICKNAME)

        self.mondo_card_id = mondo_card.split(self.CARD_ID_PARAM + "=")[1]

    def _div_to_journeys(self, div):
        detail_xpath = './/a[@data-pageobject="statement-detaillink"]'
        return [self._div_to_journey(j) for j in div.xpath(detail_xpath)]

    def _div_to_journey(self, j):
        journey_from = text_at_xpath(
            j, './/span[@data-pageobject="journey-from"]')
        journey_to = text_at_xpath(
            j, './/span[@data-pageobject="journey-to"]')
        journey_time_str = text_at_xpath(
            j, './/span[@data-pageobject="journey-time"]')
        journey_fare_str = text_at_xpath(
            j, './/span[@data-pageobject="journey-fare"]')

        journey_fare = text_to_cost(journey_fare_str)
        notes = text_at_xpath(
            j, './/span[@data-pageobject="journey-to-from"]')

        return Journey(journey_from, journey_to, journey_time_str,
                       journey_fare, notes)

    def _div_to_payment(self, div):
        price_xpath = './/span[contains(@data-pageobject,"price")]'
        cost_str = text_at_xpath(div, price_xpath)
        cost = text_to_cost(cost_str)

        def parse_date(date_str, format_str):
            return datetime.strptime(date_str, format_str).date()

        date_xpath = './/span[@data-pageobject="statement-date"]'
        date_str = text_at_xpath(div, date_xpath)
        date = parse_date(date_str, "%d/%m/%Y")

        p = Payment(cost, date)

        def has_element(d, xpath_str):
            return first(d.xpath(xpath_str)) is not None

        warning_xpath = './/img[contains(@class, "warning-icon")]'
        p.warning = has_element(div, warning_xpath)

        autocompleted_xpath = './/img[contains(@class, "autocompleted")]'
        p.autocompleted = has_element(div, autocompleted_xpath)

        capped_xpath = './/img[contains(@class, "capped")]'
        p.capped = has_element(div, capped_xpath)

        p.journeys = self._div_to_journeys(div)
        return p
