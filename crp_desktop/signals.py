
from PySide6.QtCore import QObject, Signal

class Signals(QObject):
    new_result = Signal(dict)
    status = Signal(str)

# module-level variable to be initialized by main
signals = None

def init_signals():
    global signals
    if signals is None:
        signals = Signals()
    return signals
