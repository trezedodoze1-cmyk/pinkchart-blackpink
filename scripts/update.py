#!/usr/bin/env python3
"""Atualizador do PINKCHART.

Coleta informações publicamente visíveis em páginas de terceiros (quando acessíveis)
e, opcionalmente, seguidores via API oficial do Spotify. Use respeitando os termos
as fontes, a frequência de acesso e eventuais bloqueios dessas páginas.

Nunca cria valores fictícios. Em falhas, conserva o último snapshot conhecido.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
ARTIST_ID = '41MozSoPIsD1dJM0CLPjZF'
BASE_KWORB = f'https://kworb.net/spotify/artist/{ARTIST_ID}'
URL_SONGS = BASE_KWORB + '_songs.html'
URL_ALBUMS = BASE_KWORB + '_albums.html'
URL_SPOTIFY_TOP = 'https://spotify-top.com/artist/blackpink'
TODAY = datetime.now(ZoneInfo('America/Cuiaba')).date().isoformat()
COUNTRIES = {
    'global': ('Global', 'GLOBAL'),
    'us': ('Estados Unidos', 'US'),
    'br': ('Brasil', 'BR'),
    'kr': ('Coreia do Sul', 'KR'),
    'jp': ('Japão', 'JP'),
}
HEADERS = {'User-Agent': 'PinkChart-Blackpink-Stats/1.0 (+fan statistics dashboard; daily updates; contact via GitHub repo)', 'Accept-Language': 'en-US,en;q=0.9'}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
NOTES = []


def as_int(value):
    if isinstance(value, (int, float)):
        return int(value)
    s = re.sub(r'[^\d]', '', str(value or ''))
    return int(s) if s else None


def load(name, default):
    path = DATA / (name+'.json')
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else default


def save(name, obj):
    path = DATA / (name+'.json')
    p = path.with_suffix('.tmp')
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    p.replace(path)


def fetch_soup(url):
    response = SESSION.get(url, timeout=24)
    response.raise_for_status()
    if len(response.content) < 500:
        raise ValueError('Resposta HTML pequena demais; possivel bloqueio')
    return BeautifulSoup(response.text, 'html.parser')


def source_date(soup):
    # Kworb escreve explicitamente 'Last updated: YYYY/MM/DD'.
    s = soup.get_text(' ', strip=True)
    m = re.search(r'Last updated:\s*(\d{4})[/-](\d{2})[/-](\d{2})', s, re.I)
    if m:
        return '-'.join(m.groups())
    chart_date = re.search(r'Spotify\s+(?:Daily|Weekly)\s+Chart\s*[-–].*?[-–]\s*(\d{4})[/-](\d{2})[/-](\d{2})',s,re.I)
    return '-'.join(chart_date.groups()) if chart_date else TODAY


def update_metric(latest, key, value, stamp, source, approximate=False):
    if value is None or value < 0:
        return False
    # Evita atualizar um registro mais recente com dados de uma data anterior.
    old = latest['metrics'].get(key)
    if old and old.get('date','') > stamp:
        return False
    latest['metrics'][key] = dict(value=value, date=stamp, source=source, approximate=approximate)
    return True


def table_rows(soup):
    for table in soup.find_all('table'):
        for tr in table.find_all('tr'):
            cells = tr.find_all(['th','td'], recursive=False)
            if cells:
                yield tr, cells


def read_kworb_songs(latest):
    soup = fetch_soup(URL_SONGS)
    date_stamp=source_date(soup)
    if latest.get('songsDate','') > date_stamp:
        print('Kworb songs: pagina mais antiga que a coleta salva; mantidos dados existentes')
        return
    summary = {}
    songs = []
    for tr,cells in table_rows(soup):
        content=[c.get_text(' ', strip=True) for c in cells]
        if len(content)>=2 and content[0].strip().lower() in ('streams','daily','tracks'):
            k=content[0].strip().lower()
            if as_int(content[1]) is not None:
                summary[k]=as_int(content[1])
        if len(cells)<3 or not tr.find('a',href=re.compile(r'spotify\.com',re.I)):
            continue
        title=cells[0].get_text(' ',strip=True).lstrip('* ').strip()
        # Captura as duas primeiras colunas numéricas; ignora links sem dados.
        number_values=[as_int(c.get_text(' ',strip=True)) for c in cells[1:3]]
        if title and all(x is not None for x in number_values):
            songs.append([title,number_values[0],number_values[1]])
    if not songs or not summary.get('streams'):
        raise ValueError('Formato da tabela de streams mudou; nenhum dado substituido')
    latest['songs']=songs
    latest['songsDate']=date_stamp
    update_metric(latest,'streams',summary['streams'],date_stamp,'Kworb')
    update_metric(latest,'dailyStreams',summary.get('daily'),date_stamp,'Kworb')
    update_metric(latest,'tracks',summary.get('tracks'),date_stamp,'Kworb')
    print(f'Kworb songs: {len(songs)} faixas, {summary["streams"]} streams ({date_stamp})')


def read_kworb_albums(latest):
    soup = fetch_soup(URL_ALBUMS)
    stamp=source_date(soup)
    if latest.get('albumsDate','') > stamp:
        print('Kworb albums: pagina mais antiga que a coleta salva; mantidos dados existentes')
        return
    albums=[]
    for tr,cells in table_rows(soup):
        if len(cells)<3 or not cells[0].find('a',href=re.compile(r'spotify\.com',re.I)):
            continue
        name=cells[0].get_text(' ',strip=True)
        a,b=as_int(cells[1].get_text(' ',strip=True)),as_int(cells[2].get_text(' ',strip=True))
        if name and a is not None and b is not None:
            albums.append([name,a,b])
    if not albums:
        raise ValueError('Lista de albuns nao encontrada')
    latest['albums']=albums
    latest['albumsDate']=stamp
    print(f'Kworb albums: {len(albums)} ({stamp})')


def read_spotify_top(latest):
    soup=fetch_soup(URL_SPOTIFY_TOP)
    text=soup.get_text(' ',strip=True)
    m=re.search(r'Monthly\s+listeners\s+[\d.,]+\s*[MK]?\s*\(([\d,]+)\)',text,re.I)
    if not m:
        raise ValueError('Nao foi encontrado o valor exato de ouvintes mensais')
    monthly=as_int(m.group(1))
    if monthly is None or monthly<100000:
        raise ValueError('Ouvintes invalidos')
    update_metric(latest,'monthlyListeners',monthly,TODAY,'Spotify Top')
    # A tabela "On the Spotify charts today" lista apenas músicas presentes.
    heading=soup.find(string=re.compile(r'On the Spotify charts today',re.I))
    rows=[]
    if heading:
        parent=heading.parent
        chart_table=parent.find_next('table') if parent else None
        if chart_table:
            for tr in chart_table.find_all('tr'):
                tds=tr.find_all('td',recursive=False)
                if len(tds)<4:
                    continue
                texts=[td.get_text(' ',strip=True) for td in tds]
                pos=re.search(r'#?(\d+)',texts[2])
                if not pos:
                    continue
                streams=as_int(texts[4]) if len(texts)>=5 else None
                country=texts[0].replace('chart','').strip()
                code={'South Korea':'KR','Brazil':'BR','United States':'US','Global':'GLOBAL','Japan':'JP'}.get(country, 'OTHER')
                rows.append({'country':{'KR':'Coreia do Sul','BR':'Brasil','US':'Estados Unidos','GLOBAL':'Global','JP':'Japão'}.get(code,country),
                             'code':code,'period':'daily','title':texts[1], 'position':int(pos.group(1)),
                             'streams':streams,'date':TODAY,'source':'Spotify Top'})
    # Não substitui charts em casos de layout inesperado; kworb ainda pode atualizar.
    if rows:
        fresh_codes={x['code'] for x in rows}
        previous=[x for x in latest.get('charts',[]) if not (x.get('period')=='daily' and x.get('code') in fresh_codes)]
        latest['charts']=previous+rows
        latest['chartsDate']=TODAY
    print(f'Spotify Top: {monthly} ouvintes, {len(rows)} chart entries ({TODAY})')


def read_spotify_followers(latest):
    client_id=os.environ.get('SPOTIFY_CLIENT_ID','').strip()
    client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET','').strip()
    if not (client_id and client_secret):
        NOTES.append('Seguidores: sem credenciais API, estimativa anterior preservada')
        print('Spotify API: credenciais nao definidas; seguidores preservados')
        return
    tok=SESSION.post('https://accounts.spotify.com/api/token',
                     data={'grant_type':'client_credentials'},auth=(client_id,client_secret),timeout=25)
    tok.raise_for_status()
    access=tok.json()['access_token']
    r=SESSION.get('https://api.spotify.com/v1/artists/'+ARTIST_ID,
                  headers={'Authorization':'Bearer '+access},timeout=25)
    r.raise_for_status()
    artist=r.json()
    followers=(artist.get('followers') or {}).get('total')
    if followers is None:
        raise ValueError('API do Spotify nao retornou seguidores')
    update_metric(latest,'followers',int(followers),TODAY,'Spotify Web API',approximate=False)
    print(f'Spotify API: {followers} seguidores ({TODAY})')


def read_kworb_country(latest,period,slug,name,code):
    url=f'https://kworb.net/spotify/country/{slug}_{period}.html'
    soup=fetch_soup(url)
    stamp=source_date(soup)
    found=[]
    saw_chart=False
    for table in soup.find_all('table'):
        headers=[th.get_text(' ',strip=True).lower() for th in table.find_all('th')]
        header=' '.join(headers)
        if 'pos' not in header or ('artist' not in header and 'title' not in header):
            continue
        saw_chart=True
        i_stream=next((i for i,x in enumerate(headers) if x=='streams'),None)
        for tr in table.find_all('tr'):
            tds=tr.find_all('td',recursive=False)
            if len(tds)<3:
                continue
            cells=[c.get_text(' ',strip=True) for c in tds]
            line=' '.join(cells)
            m=re.search(r'(?<![\w])BLACKPINK\s*[-–]\s*(.+)',line,re.I)
            if not m:
                continue
            title=m.group(1).strip()
            # Extrai título apenas da célula de artista/título, não dos campos numéricos.
            item=next((c for c in cells if re.search(r'BLACKPINK\s*[-–]',c,re.I)),None)
            if item:
                title=re.sub(r'^.*?BLACKPINK\s*[-–]\s*','',item,flags=re.I).strip()
            if not title:
                continue
            position=as_int(cells[0])
            if position is None or not 1<=position<=200:
                continue
            # O índice de heading pode diferir do índice de td se houver células especiais.
            value=as_int(cells[i_stream]) if i_stream is not None and i_stream<len(cells) else None
            found.append({'country':name,'code':code,'period':period,'title':title,'position':position,
                          'streams':value,'date':stamp,'source':'Kworb'})
        break
    if not saw_chart:
        raise ValueError('Tabela de chart nao encontrada')
    # Se a página do país estiver atrasada, conserva a entrada de uma fonte mais recente.
    existing=[x for x in latest.get('charts',[]) if x.get('period')==period and x.get('code')==code]
    if existing and max(x.get('date','') for x in existing)>stamp:
        print(f'Kworb {name}: chart anterior ao snapshot salvo, ignorado ({stamp})')
        return
    # O chart foi analisado: se não havia músicas, remove as entradas antigas desse chart.
    latest['charts']=[x for x in latest.get('charts',[]) if not (x.get('period')==period and x.get('code')==code)] + found
    latest['chartsDate']=max(latest.get('chartsDate',''),stamp)
    print(f'Kworb {name} {period}: {len(found)} charts em {stamp}')


def update_history(latest):
    old=load('history',[])
    by_date={item['date']:item for item in old if item.get('date')}
    for key,item in latest['metrics'].items():
        if key not in ('streams','dailyStreams','monthlyListeners','followers'):
            continue
        stamp=item.get('date')
        if not stamp:
            continue
        row=by_date.setdefault(stamp,{'date':stamp})
        row[key]=item['value']
        if key=='followers':
            row['followersApproximate']=bool(item.get('approximate'))
    result=sorted(by_date.values(),key=lambda x:x['date'])
    save('history',result)
    return result


def update_charts_history(latest):
    old=load('charts-history',[])
    keyed={(x['date'],x['code'],x['period'],x['title']):x for x in old}
    for chart in latest.get('charts',[]):
        identity=tuple(chart.get(k) for k in ('date','code','period','title'))
        if all(identity):keyed[identity]=chart
    # Pequeno arquivo, histórico mantido integralmente.
    save('charts-history',sorted(keyed.values(),key=lambda c:(c['date'],c['country'],c['title'])))


def weekly_report(latest,history):
    current={key:latest['metrics'].get(key,{}).get('value') for key in ('streams','dailyStreams','monthlyListeners','followers')}
    change={}
    for key in current:
        p=[x for x in history if key in x]
        if len(p)<2:
            change[key]=None
            continue
        end=p[-1]
        prior_target=(date.fromisoformat(end['date'])-timedelta(days=7))
        prior=next((x for x in reversed(p) if date.fromisoformat(x['date'])<=prior_target),None)
        change[key]=end[key]-prior[key] if prior else None
    report={'generated':TODAY,'message':'Relatorio construido a partir de coletas reais (sem estimativas para lacunas).',
            'current':current,'change':change,
            'charts':[x for x in latest.get('charts',[]) if x.get('period')=='weekly']}
    save('weekly',report)
    print('Relatorio semanal salvo')


def safe(label,fn,*args):
    try:fn(*args)
    except (requests.RequestException,ValueError,KeyError,IndexError,AttributeError) as error:
        msg=f'{label}: {type(error).__name__}: {error}'
        NOTES.append(msg)
        print('AVISO:',msg,file=sys.stderr)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('daily','weekly','all'),default='daily')
    opt=parser.parse_args()
    latest=load('latest',None)
    if latest is None:
        raise SystemExit('Inicialize o arquivo data/latest.json antes de usar o atualizador')

    if opt.mode in ('daily','all'):
        safe('Kworb músicas',read_kworb_songs,latest)
        safe('Kworb álbuns',read_kworb_albums,latest)
        safe('Spotify Top',read_spotify_top,latest)
        safe('API seguidores',read_spotify_followers,latest)
    period='weekly' if opt.mode=='weekly' else 'daily'
    for slug,(name,code) in COUNTRIES.items():
        safe(f'Chart {name} {period}',read_kworb_country,latest,period,slug,name,code)
        time.sleep(0.8) # Baixa frequência e acessos corteses às fontes.
    latest['collectionNotes']=NOTES
    save('latest',latest)
    history=update_history(latest)
    update_charts_history(latest)
    if opt.mode in ('weekly','all'):
        weekly_report(latest,history)
    # Nenhum dado de fonte inventado. Falha de uma fonte não impede as demais.
    print(f'Finalizado. {len(NOTES)} aviso(s).')

if __name__=='__main__':
    main()
