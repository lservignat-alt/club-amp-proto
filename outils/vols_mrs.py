"""Récupère les vols du jour de l'aéroport Marseille Provence et écrit data/vols.json pour l'app.

Source : l'API de la page « Départs / Arrivées du jour » de marseille.aeroport.fr (mise à jour en continu par
l'aéroport, avec porte, statut d'embarquement et tapis à bagages). On ne garde que les vols autour d'aujourd'hui
(de 3 h avant à 36 h après maintenant) et les champs utiles à l'app.
Lancé toutes les 10 minutes par GitHub Actions (.github/workflows/vols.yml) ; aussi lançable à la main :
    python3 outils/vols_mrs.py
"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo('Europe/Paris')
API = 'https://www.marseille.aeroport.fr/api-vols/vol/{}/data'
SORTIE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'vols.json')


def lire(mode):
    req = urllib.request.Request(API.format(mode), headers={
        'User-Agent': 'Mozilla/5.0 (prototype etudiant Club AMP, non officiel)', 'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://www.marseille.aeroport.fr/vols-et-destinations/vols/departs-du-jour'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode('utf-8'))


def nettoyer(v, sens, debut, fin):
    t = datetime.fromisoformat(v['time']).replace(tzinfo=PARIS)
    if not (debut <= t <= fin):
        return None
    q = {'id': v.get('flightId'), 'num': (v.get('flightNb') or '').strip(), 'cie': (v.get('companyName') or '').strip().title(),
         'date': t.strftime('%Y-%m-%d'), 'h': t.strftime('%H:%M'), 'ville': ' '.join((v.get('location') or '').split()),
         'code': v.get('code_location') or '', 'term': v.get('terminal') or '', 'statut': (v.get('status_fr') or '').strip()}
    if sens == 'dep':
        if v.get('Porte'): q['porte'] = str(v['Porte']).strip()
        if v.get('StatutEmbarquement_fr'): q['emb'] = v['StatutEmbarquement_fr'].strip()
        if v.get('NumBanqueEnregistrement'): q['banques'] = str(v['NumBanqueEnregistrement']).strip()
    elif v.get('tapis_Livraison_Bagage'):
        q['tapis'] = str(v['tapis_Livraison_Bagage']).lstrip('0') or '0'
    return q


def construire():
    """Vols autour de maintenant, au format de l'app (utilisé aussi par le serveur Railway, main.py)."""
    maintenant = datetime.now(PARIS)
    debut, fin = maintenant - timedelta(hours=3), maintenant + timedelta(hours=36)
    sortie = {'maj': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'source': 'marseille.aeroport.fr'}
    for sens, mode, cle in [('dep', 'departures', 'Departures'), ('arr', 'arrivals', 'Arrivals')]:
        d = lire(mode)
        vols = [q for q in (nettoyer(v, sens, debut, fin) for v in (d.get(cle) or {}).get('Vol') or []) if q]
        sortie[sens] = sorted(vols, key=lambda q: (q['date'], q['h']))
        sortie['maj_site'] = d.get('lastUpdate')
    return sortie


def main():
    sortie = construire()
    if not sortie['dep'] and not sortie['arr']:
        sys.exit('Aucun vol reçu : fichier inchangé')
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    try:  # rien de nouveau (hors horodatage) : on ne touche pas au fichier, donc pas de publication
        ancien = json.load(open(SORTIE))
        if all(ancien.get(k) == sortie.get(k) for k in ('dep', 'arr', 'maj_site')):
            return print('Vols inchangés')
    except (OSError, ValueError):
        pass
    with open(SORTIE, 'w') as f:
        json.dump(sortie, f, ensure_ascii=False, separators=(',', ':'))
    print(f"{len(sortie['dep'])} départs, {len(sortie['arr'])} arrivées → {os.path.normpath(SORTIE)}")


if __name__ == '__main__':
    main()
