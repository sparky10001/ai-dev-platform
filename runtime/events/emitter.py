class EventEmitter:

    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)

    def export(self):
        return list(self.events)