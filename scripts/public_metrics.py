"""Parsers conservadores para métricas públicas do Spotify.
Nenhum valor é gerado artificialmente: métricas abreviadas são aproximadas.
"""
import re
import unicodedata

def normalize(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s))
                   if not unicodedata.combining(c)).casefold().strip()

def check_artist(soup, expected):
    headings = [normalize(h.get_text(' ', strip=True)) for h in soup.find_all('h1')]
    if normalize(expected) not in headings:
        raise ValueError('Fonte não confirmou o perfil correto: ' + str(expected))

def spotify_top_monthly(soup, expected):
    """Retorna número exato quando explicitamente presente no resumo."""
    check_artist(soup, expected)
    txt = soup.get_text(' ', strip=True).replace('\u00a0', ' ')
    for m in re.finditer(r'\bMonthly\s+listeners\b', txt, re.I):
        tail = txt[m.end():m.end()+95]
        exact = re.search(r'\(\s*(\d{1,3}(?:[,\s.]\d{3}){2,})\s*\)', tail)
        if not exact:
            # Algumas páginas exibem a contagem sem parênteses.
            exact = re.search(r'^\s*(\d{1,3}(?:[,\s.]\d{3}){2,})\b', tail)
        if exact:
            val = int(re.sub(r'\D', '', exact.group(1)))
            if 100000 <= val <= 200000000:
                return val
    raise ValueError('Spotify Top não apresentou valor exato verificável')

def abbreviated_number(s):
    m = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*([kmb])\s*', s, re.I)
    if not m:
        raise ValueError('Número abreviado inválido: '+repr(s))
    return round(float(m.group(1).replace(',', '.')) * {'k':1000,'m':1000000,'b':1000000000}[m.group(2).lower()])

def chartmasters_metrics(soup, expected):
    """Lê somente seção Spotify statistics; nunca KPIs genéricos de áudio."""
    check_artist(soup, expected)
    text = soup.get_text(' ', strip=True).replace('\u00a0', ' ')
    start = re.search(r'\bSpotify\s+statistics\b', text, re.I)
    if not start:
        raise ValueError('ChartMasters não apresentou bloco Spotify statistics')
    block = text[start.end():start.end()+800]
    block = re.split(r'Trends\s*&\s*Indicators', block, maxsplit=1, flags=re.I)[0]
    result = {}
    for key, label in [('monthlyListeners', 'Monthly listeners'), ('followers','Followers')]:
        m = re.search(r'\b'+re.escape(label)+r'\s+(\d+(?:[.,]\d+)?\s*[kmb])\b', block, re.I)
        if m:
            value = abbreviated_number(m.group(1))
            if 100000 <= value <= 200000000:
                result[key] = value
    if not result:
        raise ValueError('ChartMasters: métricas Spotify não encontradas')
    return result

if __name__ == '__main__':
    from bs4 import BeautifulSoup
    top = BeautifulSoup('<h1>ROSÉ</h1><div>Monthly listeners 27.84M (27,844,070) #123</div>', 'html.parser')
    assert spotify_top_monthly(top,'ROSÉ') == 27844070
    cm = BeautifulSoup('<h1>ROSÉ</h1><p>On-demand audio streams Monthly listeners 52.2m</p>'
      '<h2>Spotify statistics B-</h2><p>Lead streams 5.7b Monthly listeners 27.2m 15 Followers 16.3m 13</p>'
      '<h2>Trends & Indicators</h2><p>Monthly listeners +/- 200k</p>', 'html.parser')
    assert chartmasters_metrics(cm,'ROSÉ') == {'monthlyListeners':27200000,'followers':16300000}
    try:
        chartmasters_metrics(cm, 'LISA')
        raise AssertionError('Não validou identidade')
    except ValueError:
        pass
    print('Validado: Spotify Top e ChartMasters; sem troca de perfis.')
