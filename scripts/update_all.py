#!/usr/bin/env python3
"""BLACKPINK + SOLOS: atualiza perfis individuais, discografia e charts.

Preserva snapshots existentes e não preenche lacunas com estimativas.
As páginas de terceiros podem mudar formato ou bloquear scraping.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import timedelta, date
from pathlib import Path
from html import unescape
from typing import Optional
import update as legacy
from public_metrics import spotify_top_monthly, chartmasters_metrics

ARTISTS={
 'blackpink':('BLACKPINK','41MozSoPIsD1dJM0CLPjZF','blackpink'),
 'jennie':('JENNIE','250b0Wlc5Vk0CoUsaCY84M','jennie'),
 'lisa':('LISA','5L1lO4eRHmJ7a0Q6csE5cT','lisa'),
 'rose':('ROSÉ','3eVa5w3URK5duf6eyVDbu9','rose'),
 'jisoo':('JISOO','6UZ0ba50XreR4TM8u322gs','jisoo'),
}
DATA=legacy.DATA
NOTES=[]

def get(name,fallback):return legacy.load(name,fallback)
def put(name,payload):legacy.save(name,payload)

def safe(key,step,fn,*args):
 try:
  fn(*args)
 except Exception as error:
  NOTES.append(f'{key} · {step}: {type(error).__name__}: {error}')
  print('AVISO',NOTES[-1],file=sys.stderr)

def setup_legacy(key):
 name,aid,slug=ARTISTS[key]
 legacy.ARTIST_ID=aid
 legacy.BASE_KWORB=f'https://kworb.net/spotify/artist/{aid}'
 legacy.URL_SONGS=legacy.BASE_KWORB+'_songs.html'
 legacy.URL_ALBUMS=legacy.BASE_KWORB+'_albums.html'
 legacy.URL_SPOTIFY_TOP='https://spotify-top.com/artist/'+slug

def read_listeners(key,p):
 name,_,slug=ARTISTS[key]
 exact_ok=False
 try:
  soup=legacy.fetch_soup('https://spotify-top.com/artist/'+slug)
  n=spotify_top_monthly(soup,name)
  legacy.update_metric(p,'monthlyListeners',n,legacy.TODAY,'Spotify Top')
  exact_ok=True
  print(key,'ouvintes exatos:',n)
 except Exception as e:
  print('AVISO',key,'Spotify Top:',e,file=sys.stderr)
 url=p.get('sourceLinks',{}).get('chartmasters') or 'https://chartmasters.org/artist/'+('Black-Pink' if key=='blackpink' else name)+'/'
 try:
  soup=legacy.fetch_soup(url)
  metrics=chartmasters_metrics(soup,name)
  p.setdefault('sourceLinks',{})['chartmasters']=url
  for metric,value in metrics.items():
   prev=p.get('metrics',{}).get(metric)
   if metric=='monthlyListeners' and exact_ok:continue
   if prev and prev.get('date','')>=legacy.TODAY and not prev.get('approximate',False):continue
   legacy.update_metric(p,metric,value,legacy.TODAY,'ChartMasters (aproximado)',approximate=True)
   print(key,metric,'aproximado:',value)
 except Exception as e:
  NOTES.append(f'{key} - ChartMasters: {e}')
  print('AVISO',NOTES[-1],file=sys.stderr)

def read_followers_batch(all_artists):
 cid=os.getenv('SPOTIFY_CLIENT_ID','').strip()
 secret=os.getenv('SPOTIFY_CLIENT_SECRET','').strip()
 if not(cid and secret):
  NOTES.append('Seguidores: sem credenciais Spotify API; últimos valores preservados')
  return
 response=legacy.SESSION.post('https://accounts.spotify.com/api/token',data={'grant_type':'client_credentials'},auth=(cid,secret),timeout=25)
 response.raise_for_status()
 token=response.json()['access_token']
 ids=','.join(x[1] for x in ARTISTS.values())
 response=legacy.SESSION.get('https://api.spotify.com/v1/artists',params={'ids':ids},headers={'Authorization':'Bearer '+token},timeout=25)
 response.raise_for_status()
 artists=response.json().get('artists',[])
 by_id={a['id']:a for a in artists if a and a.get('id')}
 for k,(_,aid,_) in ARTISTS.items():
  n=(by_id.get(aid,{}).get('followers') or {}).get('total')
  if n is not None:legacy.update_metric(all_artists[k],'followers',int(n),legacy.TODAY,'Spotify Web API')

def detect_artist_and_song(text):
 # A célula do Kworb tem formato "Artist - Song". Usamos o mesmo escopo
 # do título do chart, não o nome do feat no título.
 text=unescape(text).strip()
 for k,(artist,_,_) in ARTISTS.items():
  m=re.search(r'^\s*'+re.escape(artist)+r'\s*[-–]\s*(.+)',text,re.I)
  if m:return k,m.group(1).strip()
 return None,None

def read_chart(all_artists,period,slug,name,code,all_history):
 soup=legacy.fetch_soup(f'https://kworb.net/spotify/country/{slug}_{period}.html')
 stamp=legacy.source_date(soup)
 matched={k:[] for k in ARTISTS};parsed=False
 for table in soup.find_all('table'):
  headers=[t.get_text(' ',strip=True).lower() for t in table.find_all('th')]
  if not ('pos' in ' '.join(headers) and ('artist' in ' '.join(headers) or 'title' in ' '.join(headers))):continue
  parsed=True
  stream_pos=next((i for i,x in enumerate(headers) if x.strip()=='streams'),None)
  for tr in table.find_all('tr'):
   cells=tr.find_all('td',recursive=False)
   if len(cells)<2:continue
   texts=[x.get_text(' ',strip=True) for x in cells]
   pos=legacy.as_int(texts[0])
   if pos is None or not 1<=pos<=200:continue
   key,title=None,None
   for value in texts[1:]:
    key,title=detect_artist_and_song(value)
    if key:break
   if not key or not title:continue
   streams=legacy.as_int(texts[stream_pos]) if stream_pos is not None and stream_pos<len(texts) else None
   matched[key].append({'artistKey':key,'country':name,'code':code,'period':period,'title':title,'position':pos,'streams':streams,'date':stamp,'source':'Kworb'})
  break
 if not parsed:raise ValueError('Tabela de chart não identificada; snapshot anterior preservado')
 for key,p in all_artists.items():
  existing=[c for c in p.get('charts',[]) if c.get('code')==code and c.get('period')==period]
  if existing and max(c.get('date','') for c in existing)>stamp:continue
  p['charts']=[c for c in p.get('charts',[]) if not(c.get('code')==code and c.get('period')==period)]+matched[key]
  p['chartsDate']=max(p.get('chartsDate') or '',stamp)
  for c in matched[key]:
   ident=(c['artistKey'],c['date'],c['code'],c['period'],c['title'])
   all_history[ident]=c
 print(f'Chart {period} {name}: '+', '.join(f'{key} {len(v)}' for key,v in matched.items()))

def write_seeds():
 payload={'artists':get('artists',{}),'catalog':get('catalog',{}),'artistHistory':get('artist-history',{}),'chartHistoryAll':get('charts-history-all',[])}
 path=legacy.ROOT/'assets'/'seed.js'
 path.write_text('window.__PINKCHART_SEED = '+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf8')

def update_histories(people):
 hist=get('artist-history',{})
 for k,p in people.items():
  by_date={r['date']:r for r in hist.get(k,[]) if r.get('date')}
  for metric,meta in p.get('metrics',{}).items():
   if metric not in ('streams','dailyStreams','followers','monthlyListeners'):continue
   stamp=meta.get('date')
   if not stamp or meta.get('value') is None:continue
   by_date.setdefault(stamp,{'date':stamp})[metric]=meta['value']
   if metric=='followers':by_date[stamp]['followersApproximate']=bool(meta.get('approximate'))
  hist[k]=sorted(by_date.values(),key=lambda x:x['date'])
 put('artist-history',hist)
 # Backward compatibility: preserva os dados antigos do grupo.
 put('history',hist['blackpink'])
 return hist

def weekly_report(people,hist):
 weekly={}
 for k,p in people.items():
  change={}
  for metric in ('streams','dailyStreams','monthlyListeners','followers'):
   points=[row for row in hist.get(k,[]) if metric in row]
   last=points[-1] if points else None
   prev=next((row for row in reversed(points[:-1]) if date.fromisoformat(row['date'])<=date.fromisoformat(last['date'])-timedelta(days=7)),None) if last else None
   change[metric]=last[metric]-prev[metric] if prev else None
  weekly[k]={'change':change,'current':{m:meta.get('value') for m,meta in p.get('metrics',{}).items()},'charts':[c for c in p.get('charts',[]) if c.get('period')=='weekly']}
 put('weekly-all',{'generated':legacy.TODAY,'artists':weekly,'description':'Somente comparações entre coletas reais.'})
 put('weekly',{'generated':legacy.TODAY,'current':weekly['blackpink']['current'],'change':weekly['blackpink']['change'],'charts':weekly['blackpink']['charts']})

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--mode',choices=['daily','weekly','all'],default='daily')
 args=parser.parse_args()
 people=get('artists',{})
 if not people:raise SystemExit('data/artists.json ausente')
 for k,(name,aid,_) in ARTISTS.items():
  if k not in people:raise SystemExit('Artista ausente: '+k)
  people[k]['artist']=name;people[k]['artistId']=aid
  setup_legacy(k)
  if args.mode in ('daily','all'):
   safe(k,'músicas',legacy.read_kworb_songs,people[k]);time.sleep(.7)
   safe(k,'álbuns',legacy.read_kworb_albums,people[k]);time.sleep(.7)
   safe(k,'ouvintes',read_listeners,k,people[k]);time.sleep(.7)
 if args.mode in ('daily','all'):safe('spotify','seguidores API',read_followers_batch,people)
 period='weekly' if args.mode=='weekly' else 'daily'
 old_charts=get('charts-history-all',[])
 indexed={(c.get('artistKey','blackpink'),c.get('date'),c.get('code'),c.get('period'),c.get('title')):c for c in old_charts}
 for slug,(name,code) in legacy.COUNTRIES.items():
  safe(name,'charts '+period,read_chart,people,period,slug,name,code,indexed)
  time.sleep(.8)
 for k,p in people.items():
  p['collectionNotes']=[note for note in NOTES if note.startswith(k+' ·')]
 put('artists',people)
 put('latest',people['blackpink'])
 put('charts-history-all',sorted(indexed.values(),key=lambda c:(c.get('date') or '',c.get('artistKey',''),c.get('code',''),c.get('title',''))))
 put('charts-history',[c for c in indexed.values() if c.get('artistKey')=='blackpink'])
 hist=update_histories(people)
 if args.mode in ('weekly','all'):weekly_report(people,hist)
 write_seeds()
 print('Pronto: 5 artistas; '+str(len(NOTES))+' avisos. Nenhum número simulado.')

if __name__=='__main__':main()
