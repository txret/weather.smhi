"""Minimal stand-in for Kodi's xbmcgui module."""

_WINDOWS = {}


class Window:
    def __init__(self, window_id):
        self.props = _WINDOWS.setdefault(window_id, {})

    def setProperty(self, key, value):
        if not isinstance(value, str):  # Kodi raises TypeError for non-str too
            raise TypeError(f'setProperty({key!r}) needs str, got {type(value).__name__}')
        self.props[key] = value

    def getProperty(self, key):
        return self.props.get(key, '')

    def clearProperty(self, key):
        self.props.pop(key, None)


class ListItem:
    def __init__(self, label='', label2=''):
        self.label, self.label2 = label, label2

    def setLabel2(self, label2):
        self.label2 = label2


class Dialog:
    """Scripted dialogs. Tests either set a fixed answer (``input_answer``,
    ``select_answer``) or a queue of answers (``input_answers``,
    ``select_answers``, ``context_answers``) that is consumed in order; an
    exhausted queue answers "cancelled", so dialog loops always end."""
    input_answer = ''
    select_answer = 0
    input_answers = None
    select_answers = None
    context_answers = None
    selects = []      # (heading, [labels], preselect) per select() call
    menus = []        # [labels] per contextmenu() call
    oks = []          # message per ok() call

    @classmethod
    def reset(cls):
        """Forget scripted answers and recorded calls."""
        cls.input_answer, cls.select_answer = '', 0
        cls.input_answers = cls.select_answers = cls.context_answers = None
        cls.selects, cls.menus, cls.oks = [], [], []

    @staticmethod
    def _next(queue, fixed, cancelled):
        """Next answer from ``queue`` if one is scripted, else ``fixed``."""
        if queue is None:
            return fixed
        return queue.pop(0) if queue else cancelled

    def input(self, heading, defaultt='', type=0):
        return Dialog._next(Dialog.input_answers, Dialog.input_answer, '')

    def select(self, heading, items, autoclose=0, preselect=-1, useDetails=False):
        Dialog.last_items = items
        Dialog.selects.append((heading, [i.label for i in items], preselect))
        return Dialog._next(Dialog.select_answers, Dialog.select_answer, -1)

    def contextmenu(self, items):
        Dialog.menus.append(list(items))
        return Dialog._next(Dialog.context_answers, -1, -1)

    def ok(self, heading, message):
        Dialog.last_ok = message
        Dialog.oks.append(message)
        return True


class DialogProgress:
    def create(self, heading, message=''):
        pass

    def close(self):
        pass
