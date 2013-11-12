class Mode:
    def __init__(self, app):
        self._app = app
        self._key_handler_map = None
        self._force_change_mode = False

    def init_key_handler_map_if_not_already(self):
        raise NotImplementedError

    def now_handle_key(self, value):
        callback = value[0]
        if len(value) == 1:
            callback()
        else:
            args = value[1]
            callback(*(args))
