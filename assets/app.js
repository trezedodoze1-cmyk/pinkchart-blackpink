(()=>{'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const KEY_ORDER=['blackpink','jennie','lisa','rose','jisoo'];
const NAMES={blackpink:'BLACKPINK',jennie:'JENNIE',lisa:'LISA',rose:'ROSÉ',jisoo:'JISOO'};
const metricNames={streams:'Streams',dailyStreams:'Daily',monthlyListeners:'Ouvintes mensais',followers:'Seguidores'};
const st={artist:'blackpink',album:'all',view:'overview',songPage:0,chartPage:0,overallPage:0,overallSearch:'',overallSort:'total',overallArtist:'all',overallHideVersions:false,chartPeriod:'daily',artists:{},catalog:{},history:{},songHistory:{},charts:[],search:'',sort:'total',hideVersions:true};
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function num(n){return n==null||!Number.isFinite(Number(n))?'—':Number(n).toLocaleString('pt-BR')}
function short(n){if(n==null||!Number.isFinite(Number(n)))return '—';n=Number(n);for(const [size,sfx] of [[1e12,'tri'],[1e9,'bi'],[1e6,'mi'],[1e3,'mil']])if(Math.abs(n)>=size)return (n/size).toLocaleString('pt-BR',{maximumFractionDigits:2})+' '+sfx;return num(n)}
function when(d){return d?new Date(d+'T12:00:00').toLocaleDateString('pt-BR',{day:'2-digit',month:'short',year:'numeric'}):'Sem coleta'}
function norm(s){return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/ig,' ').trim().toLowerCase()}
function matchTitle(s,expected){const a=norm(s),b=norm(expected);if(a===b)return true;const extra=a.startsWith(b+' ')?a.slice(b.length+1):b.startsWith(a+' ')?b.slice(a.length+1):null;return !!(extra&&/^(feat|ft|featuring|with|from|the game|blackpink the game)/.test(extra))}
function ver(s){return /(remix|live|japanese|acoustic|instrumental|sped up|slowed| extended|0\.5x|2x\b|just jennie|arena tour|tokyo dome)/i.test(s)}
function data(k){return st.artists[k]||{metrics:{},songs:[],albums:[],charts:[]}}
// Se o Kworb nao publicar o total de um EP/single, somamos somente as
// faixas principais catalogadas. Isso nao representa streams de outras edicoes.
function albumTotalsFromTracks(k,name){
 const expected=(st.catalog[k]||{})[name]||[];
 if(!expected.length)return null;
 const songs=data(k).songs||[],used=new Set();
 let total=0,daily=0,matched=0,dailyMatched=0;
 for(const title of expected){
  const candidates=songs.map((song,i)=>({song,i})).filter(x=>!used.has(x.i)&&matchTitle(x.song[0],title)&&!ver(x.song[0])&&Number.isFinite(x.song[1]));
  // Preferir o titulo canonico e a faixa normal, nunca remix/live/instrumental.
  candidates.sort((a,b)=>(norm(a.song[0])===norm(title)?0:1)-(norm(b.song[0])===norm(title)?0:1)||a.song[0].length-b.song[0].length);
  if(!candidates.length)continue;
  const chosen=candidates[0];used.add(chosen.i);
  total+=chosen.song[1];matched++;
  if(Number.isFinite(chosen.song[2])){daily+=chosen.song[2];dailyMatched++}
 }
 if(!matched)return null;
 return {total,daily:dailyMatched===matched?daily:null,matched,expected:expected.length,partial:matched<expected.length};
}
function artistAlbumEntries(k){const p=data(k),seen=new Set(),out=[];
 for(const [name,titles] of Object.entries(st.catalog[k]||{})){
  const values=(p.albums||[]).filter(a=>norm(a[0])===norm(name));
  const best=values.sort((a,b)=>b[1]-a[1])[0];
  const sum=best?null:albumTotalsFromTracks(k,name);
  out.push({key:k,name,total:best?.[1]??sum?.total??null,daily:best?.[2]??sum?.daily??null,
   count:titles.length,measured:!!best,derived:!!sum,partial:sum?.partial??false,matched:sum?.matched??null});
  seen.add(norm(name));
 }
 for(const a of p.albums||[]){if(seen.has(norm(a[0])))continue;if(/\b(live|japanese|jp ver|complete edition|complete collection|greatest hits|tour|remix)\b/i.test(a[0]))continue;seen.add(norm(a[0]));out.push({key:k,name:a[0],total:a[1],daily:a[2],count:null,measured:true,derived:false,partial:false})}
 return out;
}
function albums(){return (st.artist==='all'?KEY_ORDER:[st.artist]).flatMap(artistAlbumEntries)}
function albumOf(k,title){for(const [name,titles] of Object.entries(st.catalog[k]||{}))if(titles.some(t=>matchTitle(title,t)))return name;return 'Outras faixas / versões'}
function tracks(){const keys=st.artist==='all'?KEY_ORDER:[st.artist];let rows=[];
 for(const k of keys){for(const [title,total,daily] of data(k).songs||[]){const alb=albumOf(k,title);if(st.album!=='all'&&st.album!==k+'|'+alb)continue;if(st.hideVersions&&ver(title))continue;if(st.search&&!norm(title+' '+NAMES[k]+' '+alb).includes(norm(st.search)))continue;rows.push({key:k,title,total,daily,album:alb,date:data(k).songsDate})}
  if(st.album!=='all' && st.album.startsWith(k+'|')){const chosen=st.album.split('|').slice(1).join('|');const expected=(st.catalog[k]||{})[chosen]||[];for(const title of expected){if(rows.some(r=>r.key===k&&r.album===chosen&&matchTitle(r.title,title)))continue;if(st.hideVersions&&ver(title))continue;if(st.search&&!norm(title+' '+NAMES[k]+' '+chosen).includes(norm(st.search)))continue;rows.push({key:k,title,total:null,daily:null,album:chosen,date:null})}}}
 rows.sort(st.sort==='title'?(a,b)=>a.title.localeCompare(b.title,'pt'):st.sort==='daily'?(a,b)=>(b.daily??-1)-(a.daily??-1):(a,b)=>(b.total??-1)-(a.total??-1));return rows;
}

// Os deltas de streams diarios dependem de duas medições REAIS da mesma faixa.
// Mantemos versões e remixes separados: o título completo identifica cada registro.
function dailyChange(k,title,currentDate,currentDaily){
 if(!Number.isFinite(currentDaily)||!currentDate)return null;
 const snapshots=(st.songHistory[k]||[]).filter(s=>s.date&&s.date<currentDate).sort((a,b)=>b.date.localeCompare(a.date));
 for(const snap of snapshots){
  const old=(snap.songs||[]).find(song=>song[0]===title);
  if(old&&Number.isFinite(old[2]))return {delta:currentDaily-old[2],previousDate:snap.date,previousDaily:old[2]};
 }
 return null;
}
function dailyMarkup(t){
 if(!Number.isFinite(t.daily))return '<span class="muted-delta">—</span>';
 const change=dailyChange(t.key,t.title,t.date,t.daily);
 const changeText=change?((change.delta>0?'+':'')+num(change.delta)):'—';
 const cls=!change?'no-delta':change.delta>0?'delta-up':change.delta<0?'delta-down':'delta-flat';
 const explanation=change?`Variação em relação a ${when(change.previousDate)}: ${num(change.previousDaily)} streams diários anteriores`:'Variação indisponível até existir uma medição anterior da mesma música';
 return `<span class="daily-value">+${num(t.daily)}</span> <span class="daily-change ${cls}" title="${esc(explanation)}">(${changeText})</span>`;
}
function fullRanking(){
 const keys=st.overallArtist==='all'?KEY_ORDER:[st.overallArtist];
 const result=[];
 for(const k of keys)for(const [title,total,daily] of data(k).songs||[]){
  if(st.overallHideVersions&&ver(title))continue;
  const album=albumOf(k,title);
  if(st.overallSearch&&!norm(title+' '+NAMES[k]+' '+album).includes(norm(st.overallSearch)))continue;
  result.push({key:k,title,total,daily,album,date:data(k).songsDate});
 }
 const sorting=st.overallSort;
 result.sort((a,b)=>{
  if(sorting==='title')return a.title.localeCompare(b.title,'pt')||KEY_ORDER.indexOf(a.key)-KEY_ORDER.indexOf(b.key);
  if(sorting==='change'){
   const da=dailyChange(a.key,a.title,a.date,a.daily)?.delta??-Infinity;
   const db=dailyChange(b.key,b.title,b.date,b.daily)?.delta??-Infinity;
   return db-da||(b.total??0)-(a.total??0);
  }
  if(sorting==='daily')return (b.daily??-1)-(a.daily??-1)||(b.total??0)-(a.total??0);
  return (b.total??-1)-(a.total??-1)||(b.daily??0)-(a.daily??0);
 });
 return result;
}

function profileHistory(k){return (st.history[k]||[]).slice().sort((a,b)=>a.date.localeCompare(b.date))}
function lastDiff(k,metric){const rows=profileHistory(k).filter(x=>x[metric]!=null);if(rows.length<2)return null;const last=rows.at(-1),target=new Date(last.date+'T12:00:00');target.setDate(target.getDate()-1);const previous=[...rows].reverse().find(r=>new Date(r.date+'T12:00:00')<=target);return previous?last[metric]-previous[metric]:null}
function selectedAlbum(){if(st.album==='all')return null;const [key,name]=st.album.split('|');return artistAlbumEntries(key).find(a=>a.name===name)||null}
function renderMetrics(){const album=selectedAlbum(),p=st.artist==='all'?null:data(st.artist),pkey=st.artist;
 for(const key of Object.keys(metricNames)){
  let metric=p?.metrics?.[key],val=metric?.value??null,desc=metric?`${when(metric.date)} · ${metric.source||'Fonte'}`:'Sem medição';
  if(album){if(key==='streams'||key==='dailyStreams'){val=key==='streams'?album.total:album.daily;desc=album.measured?`Álbum · Kworb · ${when(data(album.key).albumsDate)}`:album.derived?`Soma ${album.matched}/${album.count} faixas · ${when(data(album.key).songsDate)}`:'Álbum · sem total coletado'}else desc=metric?`Perfil de ${NAMES[pkey]} · ${when(metric.date)}`:'Perfil · sem medição'}
  else if(pkey==='all'){desc='Selecione um artista — totais não somados'}
  const change=!album&&pkey!=='all'?lastDiff(pkey,key):null;
  let changeText=change==null?'':` · ${change>=0?'+':''}${num(change)} vs dia anterior`;
  $('#metric-'+key).textContent=(metric?.approximate&&!album?'≈ ':'')+short(val);
  $('#metric-'+key).title=val!=null?`${num(val)} · ${desc}`:desc;
  $('#sub-'+key).textContent=desc+changeText;
 }
 const dates=(st.artist==='all'?KEY_ORDER:[st.artist]).flatMap(k=>Object.values(data(k).metrics||{}).map(x=>x.date).filter(Boolean)).sort();
 $('#latestDate').textContent='Último registro: '+when(dates.at(-1));
 const notice=$('#notice');if(st.artist==='all'){notice.textContent='Todos os artistas: compare músicas e álbuns; os indicadores não são somados, pois participações podem aparecer em perfis diferentes.';notice.hidden=false}
 else if(album&&album.derived){notice.textContent=`${album.name}: ${album.partial?'soma parcial':'soma'} de ${album.matched}/${album.count} faixas catalogadas, usando os streams individuais do Kworb. Não é uma contagem oficial separada do álbum.`;notice.hidden=false}
 else if(album&&!album.measured){notice.textContent=`${album.name}: ainda não há streams suficientes para calcular a soma das faixas. Isso não significa zero streams.`;notice.hidden=false}
 else{notice.hidden=true}
}
function fillAlbumPicker(){const selector=$('#albumSelect');const old=st.album;const list=albums();selector.innerHTML='<option value="all">Todos os álbuns / singles</option>'+list.map(a=>`<option value="${esc(a.key+'|'+a.name)}">${st.artist==='all'?esc(NAMES[a.key]+' · '):''}${esc(a.name)}</option>`).join('');if(list.some(a=>a.key+'|'+a.name===old)){selector.value=old}else{st.album='all';selector.value='all'}}
function topTrackMarkup(t,i){return `<div class="short-item"><span class="rank">${String(i+1).padStart(2,'0')}</span><div style="min-width:0"><div class="short-name" title="${esc(t.title)}">${esc(t.title)}</div><div class="short-meta">${esc(NAMES[t.key])} · ${esc(t.album)}</div></div><div class="short-value" title="${num(t.total)}">${short(t.total)}<div class="short-daily">${dailyMarkup(t)}</div></div></div>`}
function renderOverview(){const rows=tracks().filter(t=>!ver(t.title)).sort((a,b)=>b.total-a.total);$('#overviewHeading').textContent=st.album==='all'?'Top músicas':'Faixas do álbum';$('#overviewSub').textContent=st.artist==='all'?'BLACKPINK + as quatro carreiras solo':NAMES[st.artist]+' · '+(selectedAlbum()?.name||'discografia completa');$('#topTracks').innerHTML=rows.slice(0,5).map(topTrackMarkup).join('')||'<div class="empty">Nenhuma faixa disponível com esses filtros.</div>';
const sorted=albums().sort((a,b)=>(b.total??0)-(a.total??0));$('#albumHighlights').innerHTML=sorted.slice(0,5).map((a,i)=>`<div class="short-item clickable" role="button" tabindex="0" data-pick-album="${esc(a.key+'|'+a.name)}"><span class="rank">${String(i+1).padStart(2,'0')}</span><div style="min-width:0"><div class="short-name">${esc(a.name)}</div><div class="short-meta">${esc(NAMES[a.key])} · ${a.count??'—'} faixas catalogadas${a.derived?' · Σ faixas':''}</div></div><div class="short-value">${short(a.total)}</div></div>`).join('')||'<div class="empty">Sem álbuns cadastrados.</div>';
$('#overviewStatus').textContent=rows.filter(t=>t.total!=null).length+' músicas com dados · '+albums().length+' lançamentos';
}
const PAGE_SIZE=7;
function renderTracks(){const rows=tracks();const total=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));st.songPage=Math.min(st.songPage,total-1);const slice=rows.slice(st.songPage*PAGE_SIZE,(st.songPage+1)*PAGE_SIZE);$('#songTable').innerHTML=slice.map((t,i)=>`<tr><td class="label-mini">${st.songPage*PAGE_SIZE+i+1}</td><td class="songtitle">${esc(t.title)} <a href="https://open.spotify.com/search/${encodeURIComponent(NAMES[t.key]+' '+t.title)}" target="_blank" rel="noopener" aria-label="Abrir busca no Spotify">↗</a></td><td><div>${esc(NAMES[t.key])}</div><div class="label-mini">${esc(t.album)}</div></td><td class="num">${num(t.total)}</td><td class="num daily-td">${dailyMarkup(t)}</td></tr>`).join('')||'<tr><td colspan="5" class="empty">Nenhuma música encontrada para este álbum ou pesquisa. Datas e dados dependem das fontes.</td></tr>';
$('#trackCount').textContent=rows.length+' faixas listadas ('+rows.filter(x=>x.total!=null).length+' com streams coletados) · '+(selectedAlbum()?.name||'Todos os lançamentos');$('#songsPageInfo').textContent=`Página ${st.songPage+1} de ${total}`;$('#songPrev').disabled=st.songPage===0;$('#songNext').disabled=st.songPage>=total-1;
}

const OVERALL_PAGE_SIZE=20;
function renderOverall(){
 const rows=fullRanking(),pageCount=Math.max(1,Math.ceil(rows.length/OVERALL_PAGE_SIZE));
 st.overallPage=Math.min(st.overallPage,pageCount-1);
 const first=st.overallPage*OVERALL_PAGE_SIZE;
 $('#overallTable').innerHTML=rows.slice(first,first+OVERALL_PAGE_SIZE).map((t,i)=>`<tr>
  <td class="label-mini">${first+i+1}</td>
  <td class="songtitle">${esc(t.title)} <a href="https://open.spotify.com/search/${encodeURIComponent(NAMES[t.key]+' '+t.title)}" target="_blank" rel="noopener" aria-label="Buscar no Spotify">↗</a>
   <div class="label-mini">${esc(NAMES[t.key])} · ${esc(t.album)} · ${when(t.date)}</div></td>
  <td class="num">${num(t.total)}</td><td class="num daily-td">${dailyMarkup(t)}</td>
 </tr>`).join('')||'<tr><td colspan="4" class="empty">Nenhuma música corresponde aos filtros.</td></tr>';
 const allCount=KEY_ORDER.reduce((n,k)=>n+(data(k).songs||[]).length,0);
 $('#overallCount').textContent=`${rows.length} registros exibidos · ${allCount} no catálogo completo dos 5 perfis`;
 $('#overallPageInfo').textContent=`Página ${st.overallPage+1} de ${pageCount}`;
 $('#overallPrev').disabled=st.overallPage===0;
 $('#overallNext').disabled=st.overallPage>=pageCount-1;
}
function downloadCSV(rows,filename){
 const headings=['Posição','Artista','Álbum','Música','Streams totais','Daily streams','Δ Daily','Data atual','Data anterior'];
 const dataRows=rows.map((r,i)=>{
  const diff=dailyChange(r.key,r.title,r.date,r.daily);
  return [i+1,NAMES[r.key],r.album,r.title,r.total,r.daily,diff?.delta??'',r.date,diff?.previousDate??''];
 });
 const csv=[headings,...dataRows].map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(';')).join('\r\n');
 const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),3000);toast('Ranking completo exportado em CSV');
}

function renderAlbums(){const all=albums();$('#albumCount').textContent=all.length+' lançamentos';$('#albumGrid').innerHTML=all.map(a=>`<button class="album-tile" data-pick-album="${esc(a.key+'|'+a.name)}"><span class="album-icon">♫</span><span class="album-text"><strong title="${esc(a.name)}">${esc(a.name)}</strong><small>${esc(NAMES[a.key])} · ${a.count==null?'catálogo em atualização':a.count+' faixas'}</small><span class="album-count">${short(a.total)} ${a.total==null?'(não coletado)':a.derived?'streams · '+(a.partial?'soma parcial':'soma das faixas'):'streams'}</span></span></button>`).join('')||'<div class="empty">Nenhum álbum encontrado.</div>'}
function allCharts(){const rows=st.charts.length?st.charts:KEY_ORDER.flatMap(k=>(data(k).charts||[]).map(c=>({...c,artistKey:k})));return rows.filter(c=>(st.artist==='all'||c.artistKey===st.artist)&&c.period===st.chartPeriod&&($('#country').value==='ALL'||$('#country').value===c.code)&&(st.album==='all'||c.artistKey===st.album.split('|')[0]&&((st.catalog[c.artistKey]?.[st.album.split('|').slice(1).join('|')]||[]).some(t=>matchTitle(c.title,t))))).sort((a,b)=>(b.date||'').localeCompare(a.date||'')||a.position-b.position)}
function renderCharts(){const rows=allCharts();const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));st.chartPage=Math.min(st.chartPage,pages-1);$('#chartTable').innerHTML=rows.slice(st.chartPage*PAGE_SIZE,(st.chartPage+1)*PAGE_SIZE).map(c=>`<tr><td class="label-mini">${when(c.date)}</td><td class="songtitle">${esc(c.title)}<div class="label-mini">${esc(NAMES[c.artistKey]||'BLACKPINK')}</div></td><td>${esc(c.country)}</td><td class="num number-pink">#${num(c.position)}</td><td class="num">${num(c.streams)}</td></tr>`).join('')||'<tr><td colspan="5" class="empty">Nenhuma posição confirmada nos charts selecionados. Isso não significa que as músicas tenham zero streams.</td></tr>';
$('#chartsPageInfo').textContent=`${rows.length} posições · página ${st.chartPage+1}/${pages}`;$('#chartPrev').disabled=st.chartPage===0;$('#chartNext').disabled=st.chartPage===pages-1;
$('#chartDate').textContent=rows[0]?.date?'Último registro: '+when(rows[0].date):'Aguardando medições';}
function renderHistory(){const keys=st.artist==='all'?KEY_ORDER:[st.artist],metric=$('#historyMetric').value,rows=keys.flatMap(k=>profileHistory(k).map(x=>({...x,artistKey:k}))).sort((a,b)=>b.date.localeCompare(a.date));$('#historyTable').innerHTML=rows.slice(0,30).map(r=>`<tr><td>${when(r.date)}</td><td>${esc(NAMES[r.artistKey])}</td><td class="num">${num(r.streams)}</td><td class="num">${num(r.dailyStreams)}</td><td class="num">${num(r.monthlyListeners)}</td><td class="num">${r.followersApproximate?'≈ ':''}${num(r.followers)}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">Sem histórico disponível.</td></tr>';
const pts=st.artist==='all'?[]:profileHistory(st.artist).filter(x=>x[metric]!=null);const graph=$('#historyGraph');if(pts.length<2){graph.textContent=`${pts.length===1?'1 medição disponível para '+metricNames[metric]+' ('+num(pts[0][metric])+').':'Nenhuma medição para este indicador.'} O gráfico aparecerá depois de duas datas distintas.`;return}
const vals=pts.map(p=>p[metric]),lo=Math.min(...vals),hi=Math.max(...vals),pad=Math.max((hi-lo)*.1,1),y=v=>145-(v-(lo-pad))/(hi-lo+pad*2)*124,x=i=>15+i*(970/(pts.length-1));let path=pts.map((p,i)=>(i?'L':'M')+x(i)+','+y(p[metric])).join(' ');graph.innerHTML=`<svg viewBox="0 0 1000 160" preserveAspectRatio="none" role="img" aria-label="Tendência de ${esc(metricNames[metric])}"><path d="${path}" fill="none" stroke="#ff7eb9" stroke-width="3" vector-effect="non-scaling-stroke"/>${pts.map((p,i)=>`<circle cx="${x(i)}" cy="${y(p[metric])}" r="4" fill="#ffb8d6"><title>${esc(p.date)}: ${num(p[metric])}</title></circle>`).join('')}</svg>`;
}
function renderSources(){const keys=st.artist==='all'?KEY_ORDER:[st.artist];$('#sourcesLinks').innerHTML=keys.map(k=>{const p=data(k);return `<a target="_blank" rel="noopener" href="${esc(p.sourceLinks?.kworbSongs||'https://kworb.net/')}">${esc(NAMES[k])} — músicas e streams ↗</a><a target="_blank" rel="noopener" href="${esc(p.sourceLinks?.kworbAlbums||'https://kworb.net/')}">${esc(NAMES[k])} — álbuns ↗</a><a target="_blank" rel="noopener" href="${esc(p.sourceLinks?.spotify||'https://open.spotify.com/')}">${esc(NAMES[k])} — Spotify ↗</a>`}).join('')}
function renderAll(){renderMetrics();renderOverview();renderTracks();renderOverall();renderAlbums();renderCharts();renderHistory();renderSources();}
function openView(view){st.view=view;$$('.tab').forEach(x=>{x.classList.toggle('active',x.dataset.tab===view);x.setAttribute('aria-current',x.dataset.tab===view?'page':'false')});$$('[data-view]').forEach(x=>{x.hidden=x.dataset.view!==view;x.classList.toggle('visible',!x.hidden)});window.scrollTo({top:0,behavior:'smooth'})}
function chooseAlbum(value){if(value!=='all'){st.hideVersions=false;$('#hideVersions').checked=false;const key=value.split('|')[0];if(st.artist!=='all'&&st.artist!==key){st.artist=key;$$('.artist-chip').forEach(b=>b.classList.toggle('active',b.dataset.artist===key));}}st.album=value;fillAlbumPicker();st.songPage=0;st.chartPage=0;renderAll();openView('tracks')}
function toast(msg){const x=$('#toast');x.textContent=msg;x.classList.add('show');setTimeout(()=>x.classList.remove('show'),2600)}
function exportCSV(){const rows=tracks();const lines=[['Artista','Álbum','Música','Streams totais','Streams diários','Δ Daily','Data da fonte','Data anterior'],...rows.map(r=>[NAMES[r.key],r.album,r.title,r.total,r.daily,dailyChange(r.key,r.title,r.date,r.daily)?.delta??'',r.date,dailyChange(r.key,r.title,r.date,r.daily)?.previousDate??''])];const csv=lines.map(r=>r.map(x=>'"'+String(x??'').replaceAll('"','""')+'"').join(';')).join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));let a=document.createElement('a');a.href=url;a.download=`pinkchart-${st.artist}-${new Date().toISOString().slice(0,10)}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);toast('Ranking exportado em CSV')}
function wire(){document.addEventListener('click',e=>{const pick=e.target.closest('[data-pick-album]');if(pick){chooseAlbum(pick.dataset.pickAlbum);return}const a=e.target.closest('[data-artist]');if(a){st.artist=a.dataset.artist;st.album='all';st.songPage=0;st.chartPage=0;$$('.artist-chip').forEach(b=>b.classList.toggle('active',b===a));fillAlbumPicker();renderAll();return}const tab=e.target.closest('[data-tab]');if(tab){openView(tab.dataset.tab);return}const next=e.target.closest('[data-open]');if(next){openView(next.dataset.open);return}const period=e.target.closest('[data-period]');if(period){st.chartPeriod=period.dataset.period;st.chartPage=0;$$('[data-period]').forEach(b=>b.classList.toggle('active',b===period));renderCharts();}});
 $('#albumSelect').addEventListener('change',e=>{st.album=e.target.value;if(st.album!=='all'){st.hideVersions=false;$('#hideVersions').checked=false;}st.songPage=0;st.chartPage=0;renderAll();openView('tracks')});
 $('#searchSongs').addEventListener('input',e=>{st.search=e.target.value;st.songPage=0;renderTracks()});$('#sortSongs').addEventListener('change',e=>{st.sort=e.target.value;st.songPage=0;renderTracks()});$('#hideVersions').addEventListener('change',e=>{st.hideVersions=e.target.checked;st.songPage=0;renderTracks()});
 $('#overallSearch').addEventListener('input',e=>{st.overallSearch=e.target.value;st.overallPage=0;renderOverall()});
 $('#overallSort').addEventListener('change',e=>{st.overallSort=e.target.value;st.overallPage=0;renderOverall()});
 $('#overallArtist').addEventListener('change',e=>{st.overallArtist=e.target.value;st.overallPage=0;renderOverall()});
 $('#overallHideVersions').addEventListener('change',e=>{st.overallHideVersions=e.target.checked;st.overallPage=0;renderOverall()});
 $('#overallPrev').addEventListener('click',()=>{st.overallPage=Math.max(0,st.overallPage-1);renderOverall()});
 $('#overallNext').addEventListener('click',()=>{st.overallPage++;renderOverall()});
 $('#overallCSV').addEventListener('click',()=>downloadCSV(fullRanking(),'pinkchart-ranking-geral.csv'));
 $('#songPrev').addEventListener('click',()=>{st.songPage=Math.max(0,st.songPage-1);renderTracks()});$('#songNext').addEventListener('click',()=>{st.songPage++;renderTracks()});
 $('#chartPrev').addEventListener('click',()=>{st.chartPage=Math.max(0,st.chartPage-1);renderCharts()});$('#chartNext').addEventListener('click',()=>{st.chartPage++;renderCharts()});
 $('#country').addEventListener('change',()=>{st.chartPage=0;renderCharts()});$('#historyMetric').addEventListener('change',renderHistory);$('#exportCSV').addEventListener('click',exportCSV);
 $('#albumHighlights').addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.closest('[data-pick-album]')){e.preventDefault();chooseAlbum(e.target.closest('[data-pick-album]').dataset.pickAlbum)}});
}
async function fetchOne(path,backup){if(location.protocol==='file:')return backup;try{const r=await fetch(path+'?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(r.status);return await r.json()}catch(e){console.warn('Dados locais usados:',path,e);return backup}}
async function init(){const seed=window.__PINKCHART_SEED||{};const [artists,catalog,history,charts,songHistory]=await Promise.all([fetchOne('data/artists.json',seed.artists),fetchOne('data/catalog.json',seed.catalog),fetchOne('data/artist-history.json',seed.artistHistory),fetchOne('data/charts-history-all.json',seed.chartHistoryAll),fetchOne('data/song-history.json',seed.songHistory)]);
 st.artists=artists||{};st.catalog=catalog||{};st.history=history||{};st.charts=charts||[];st.songHistory=songHistory||{};if(!Object.keys(st.artists).length){$('#notice').textContent='Não foi possível abrir o banco de dados. Verifique os arquivos do projeto.';$('#notice').hidden=false;return}fillAlbumPicker();wire();renderAll();}
document.addEventListener('DOMContentLoaded',init);
})();
