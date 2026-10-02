"""Serveur de l'app sur Railway : sert les fichiers du prototype et les vols en direct.

/data/vols.json est construit à la demande à partir de l'API vols de marseille.aeroport.fr (outils/vols_mrs.py),
gardé 2 min en mémoire pour ne pas solliciter le site de l'aéroport à chaque ouverture de l'app.
En secours (site de l'aéroport injoignable) : la dernière version connue, sinon le fichier data/vols.json du dépôt.
Lancement : python3 main.py (Railway fournit le port dans la variable PORT).
"""
import json, os, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, 'outils'))
import vols_mrs  # noqa: E402

CACHE, VERROU, DUREE = {'t': 0, 'corps': None}, threading.Lock(), 120


def vols():
    with VERROU:
        if CACHE['corps'] and time.time() - CACHE['t'] < DUREE:
            return CACHE['corps']
        try:
            corps = json.dumps(vols_mrs.construire(), ensure_ascii=False, separators=(',', ':')).encode()
        except Exception as e:  # site de l'aéroport injoignable : on garde ce qu'on a
            print('Vols indisponibles :', e, flush=True)
            if CACHE['corps']:
                return CACHE['corps']
            corps = open(os.path.join(ICI, 'data', 'vols.json'), 'rb').read()
        CACHE.update(t=time.time(), corps=corps)
        return corps


class Serveur(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.webmanifest': 'application/manifest+json',
                      '.glb': 'model/gltf-binary', '.js': 'text/javascript', '.json': 'application/json'}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ICI, **k)

    def do_GET(self):
        if self.path.split('?')[0].endswith('/data/vols.json'):
            corps = vols()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)
            return
        super().do_GET()

    def log_message(self, *a):  # journal discret
        pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f'Club AMP en ligne sur le port {port}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), Serveur).serve_forever()
