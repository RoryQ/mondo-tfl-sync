from decimal import Decimal


def element_at(l, index, default=None):
    try:
        return l[index]
    except:
        return default


def first(l, default=None):
    return element_at(l, 0, default)


def text_at_xpath(d, xpath_str):
    element = element_at(d.xpath(xpath_str), 0)
    if element is None:
        return None
    return element.text.strip()


def write_out(text):
    with open('out', 'w') as textfile:
        textfile.write(text)


def text_to_cost(text):
    credit = text.startswith('+')
    amount_str = text.strip("+-£*")
    amount = int(Decimal(amount_str) * 100)
    if credit:
        return amount
    return amount * -1
