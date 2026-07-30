# -*- coding: utf-8 -*-
"""Dev-сервер фронта: http.server + Cache-Control: no-cache.

Без него браузер кэширует .jsx (Babel тянет их XHR-ом), и правки
не доезжают до клиента без Ctrl+F5.

Запуск:  python serve.py  (порт 3000)
"""
import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("", PORT), NoCacheHandler).serve_forever()
