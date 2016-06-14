class Payment():
    def __init__(self, cost, date, journeys=None, warning=None,
                 autocompleted=None, capped=None):
        self.cost = cost
        self.date = date
        self.journeys = journeys
        self.warning = warning
        self.autocompleted = autocompleted
        self.capped = capped

    def __repr__(self):
        return "Payment({} {})".format(self.cost, self.date)


class Journey():
    def __init__(self, station_from, station_to, time, cost, notes=None):
        self.station_from = station_from
        self.station_to = station_to
        self.time = time
        self.cost = cost
        self.fare = cost * -1
        self.notes = notes

    def __repr__(self):
        return "<Journey ({}) {} -> {} >".format(
            self.time, self.station_from, self.station_to)
