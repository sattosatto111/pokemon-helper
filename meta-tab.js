(function(){
'use strict';
const M=()=>window.metaUI;
const st={q:'',t:-1,n:50,open:-1,src:/[?&]mt=team/.test(location.search)?'team':'off',tseason:'',tn:20,season:'Current',seasons:['Current','M7','M6','M5','M4','M3','M2','M1'],notice:'',oo:''};
// ---- 공식 랭크 데이터 (Pokémon Champions Battle Data API) ----
const CBD='https://championsbattledata.com', TTL=6*3600e3, TMO=8000;
const nz=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
const memo={}, bd={};
function cacheGet(k){try{const o=JSON.parse(localStorage.getItem('cbd1:'+k));if(o&&Date.now()-o.t<TTL)return o.d}catch(e){}return null}
function cachePut(k,d){try{localStorage.setItem('cbd1:'+k,JSON.stringify({t:Date.now(),d}))}catch(e){try{Object.keys(localStorage).filter(x=>x.startsWith('cbd1:')).forEach(x=>localStorage.removeItem(x))}catch(_){}}}
async function api(path){
  const c=cacheGet(path); if(c)return c;
  const ac=new AbortController(), tm=setTimeout(()=>ac.abort(),TMO);
  try{const r=await fetch(CBD+path,{signal:ac.signal}); if(!r.ok)throw new Error(r.status); const d=await r.json(); cachePut(path,d); return d}
  finally{clearTimeout(tm)}
}
const sfx=()=>st.season==='Current'?'':'&season='+st.season, sfx1=()=>st.season==='Current'?'':'?season='+st.season;
const apiFmt=()=>M().fmt()==='vgc'?'Doubles':'Singles';
function rankings(){
  const k=apiFmt()+'|'+st.season;
  return memo[k]||(memo[k]=api(`/api/rankings?format=${apiFmt()}&limit=300${sfx()}`).catch(e=>{delete memo[k];throw e}));
}
const seasonLabel=s=>{
  if(s!=='Current')return s+' 시즌';
  const n=Math.max(0,...st.seasons.map(x=>/^M(\d+)$/.test(x)?+x.slice(1):0));
  return n?'M'+(n+1)+' 진행 중':'현재 시즌';
};
const KOm=(t,n)=>{const k=window.KO;return k&&k[t]&&(k[t][nz(n)]||k[t][n])||n};
const monIdx=n=>{const k=window.KO;const v=k&&k.mon?k.mon[nz(n)]:undefined;return v!==undefined&&PK[v]?v:-1};
const STAT_KO={'Attack':'공격','Defense':'방어','Sp. Atk':'특공','Sp. Def':'특방','Speed':'스피드','HP':'HP'};
function loadBattle(o){
  const key=apiFmt()+'/'+o.slug+'/'+st.season;
  if(bd[key])return bd[key];
  const e=bd[key]={s:'load'};
  api(`/api/battle/${apiFmt()}/${encodeURIComponent(o.slug)}${sfx1()}`).then(d=>{e.s='ok';e.d=d}).catch(()=>{e.s='err'}).then(()=>{if(tab==='meta'&&st.src==='off'&&st.open===o.slug)drawList()});
  return e;
}
const root=()=>document.getElementById('v-meta');
const noDi=h=>h.replace(' data-i=',' data-x=');   // 스프라이트 클릭이 도감을 열지 않게

// 데이터 어댑터: META 스키마 -> 화면용 목록 (데이터 출처가 바뀌면 여기만 고치면 됨)
function adapt(d){
  const seen=new Set(), out=[];
  (d.mons||[]).forEach(e=>{const p=PK[e.i]; if(!p||seen.has(p[0]))return; seen.add(p[0]); out.push({i:e.i,p,e})});
  return out.sort((a,b)=>(a.e.rank||999)-(b.e.rank||999)||b.e.u-a.e.u);
}
function rows(a){
  const top=Math.max(...a.map(x=>x[1]),1);
  return a.slice(0,6).map(([n,v])=>`<div class="mt-mr"><span>${esc(n)}</span><div class="mt-bar"><i style="width:${Math.min(100,v/top*100)}%"></i></div><b>${v}%</b></div>`).join('');
}
function detail(o){
  const e=o.e, sec=(t,a)=>a&&a.length?`<h4>${t}</h4>${rows(a)}`:'';
  const ms=(e.mates||[]).filter(m=>PK[m[0]]).slice(0,10);
  return `<div class="mt-det">${sec('자주 쓰는 기술',e.moves)}${sec('도구',e.items)}${sec('특성',e.abilities)}${sec('스탯 포인트 배분 (H/A/B/C/D/S)',e.spreads)}
${ms.length?`<h4>같이 많이 쓰는 포켓몬</h4><div class="mt-mates">${ms.map(([j,v])=>`<button type="button" class="mt-mate" data-dex="${j}">${noDi(spr(j,'s'))}<span>${esc(PK[j][0])}</span><small>${v}%</small></button>`).join('')}</div>`:''}
<button type="button" class="mt-dexbtn" data-dex="${o.i}">도감 열기</button></div>`;
}
function orows(a){
  const top=Math.max(...a.map(x=>x.v),1);
  return a.map(x=>`<div class="mt-mr"><span>${esc(x.n)}${x.s?`<small class="mt-sub"> ${esc(x.s)}</small>`:''}</span><div class="mt-bar"><i style="width:${Math.min(100,x.v/top*100)}%"></i></div><b>${x.v}%</b></div>`).join('');
}
function odetail(o){
  const e=loadBattle(o), dex=o.i>=0?`<button type="button" class="mt-dexbtn" data-dex="${o.i}">도감 열기</button>`:'';
  if(e.s==='load')return '<div class="mt-det"><div class="sub">불러오는 중…</div></div>';
  if(e.s==='err')return `<div class="mt-det"><div class="sub">이 포켓몬 배틀 데이터를 못 불러왔어.</div>${dex}</div>`;
  const R=e.d.rows||[], g=c=>R.filter(r=>r.category===c);
  const pc=r=>r.percentage_value!=null?+r.percentage_value:parseFloat(r.percentage)||0;
  const sec=(t,a)=>a.length?`<h4>${t}</h4>${orows(a)}`:'';
  const mv=g('move').slice(0,8).map(r=>({n:KOm('move',r.name),v:pc(r)}));
  const it=g('held_item').slice(0,6).map(r=>({n:KOm('item',r.name),v:pc(r)}));
  const ab=g('ability').slice(0,3).map(r=>({n:KOm('ability',r.name),v:pc(r)}));
  const na=g('stat_alignment').slice(0,5).map(r=>({n:(window.KO&&KO.nature&&KO.nature[r.name])||r.name,v:pc(r),
    s:r.stat_up&&r.stat_down?`↑${STAT_KO[r.stat_up]||r.stat_up} ↓${STAT_KO[r.stat_down]||r.stat_down}`:'(무보정)'}));
  const sp=g('stat_points').slice(0,5).map(r=>{const v=(a,b)=>r[a]!==undefined&&r[a]!==''?r[a]:(r[b]!==undefined&&r[b]!==''?r[b]:0);
    return {n:`H${v('hp_points')} A${v('attack_points')} B${v('defense_points')} C${v('sp_atk_points','sp_attack_points')} D${v('sp_def_points','sp_defense_points')} S${v('speed_points')}`,v:pc(r)}});
  const tm=g('teammate').slice(0,10).map(r=>({n:r.name,j:monIdx(r.name)}));
  return `<div class="mt-det">${sec('자주 쓰는 기술',mv)}${sec('도구',it)}${sec('특성',ab)}${sec('성격',na)}${sec('스탯 포인트 배분 (H/A/B/C/D/S)',sp)}
${tm.length?`<h4>같이 많이 쓰는 포켓몬 <small class="mt-sub">(순위순)</small></h4><div class="mt-mates">${tm.map(t=>t.j>=0?`<button type="button" class="mt-mate" data-dex="${t.j}">${noDi(spr(t.j,'s'))}<span>${esc(PK[t.j][0])}</span></button>`:`<span class="mt-mate"><span>${esc(t.n)}</span></span>`).join('')}</div>`:''}
${dex}</div>`;
}
let oList=null;
function odrawList(){
  const box=document.getElementById('mt-list'); if(!box||!oList)return;
  const q=st.q.trim().toLowerCase();
  const all=oList.filter(o=>(st.t<0||(o.p&&ptypes(o.p).includes(st.t)))&&(!q||o.name.toLowerCase().includes(q)||o.en.toLowerCase().includes(q)));
  const show=all.slice(0,st.n);
  box.innerHTML=(show.map(o=>{const open=st.open===o.slug;
    return `<div class="mt-row${open?' open':''}"><button type="button" class="mt-h mt-ho" data-orow="${esc(o.slug)}" aria-expanded="${open}">
<span class="mt-rk">${o.pos}</span>${o.i>=0?noDi(spr(o.i,'s')):'<span class="mt-nospr"></span>'}
<span class="mt-nm"><b>${esc(o.name)}</b><span class="chips">${o.p?ptypes(o.p).map(chip).join(''):''}</span></span></button>${open?odetail(o):''}</div>`}).join('')||'<div class="sub">조건에 맞는 포켓몬이 없어.</div>')
  +(all.length>show.length?`<button type="button" class="mt-more" id="mt-more">더 보기 (${show.length}/${all.length})</button>`:'');
}
function fallback(msg){st.src='sim';st.notice=msg;st.open=-1;draw()}
function loadOfficial(){
  const box=document.getElementById('mt-list'); if(box&&!oList)box.innerHTML='<div class="sub">공식 랭크 불러오는 중…</div>';
  const f=apiFmt(), s=st.season;
  rankings().then(d=>{
    if(st.src!=='off'||f!==apiFmt()||s!==st.season)return;
    if(!d||!Array.isArray(d.rankings))throw new Error('bad');
    if(d.seasons&&d.seasons.length&&d.seasons.join()!==st.seasons.join()){st.seasons=d.seasons;const sel=document.getElementById('mt-season');if(sel)sel.innerHTML=st.seasons.map(x=>`<option value="${esc(x)}"${x===st.season?' selected':''}>${esc(seasonLabel(x))}</option>`).join('')}
    st.oo=d.generatedAt||'';
    oList=d.rankings.map(r=>{const i=monIdx(r.showdownId||r.name), p=i>=0?PK[i]:null;
      return {pos:r.position,slug:r.slug,i,p,name:p?p[0]:r.name,en:r.name+' '+(r.battleName||'')}});
    const dt=document.getElementById('mt-date'); if(dt)dt.textContent=st.oo?st.oo.slice(0,10):'';
    odrawList();
  }).catch(()=>{if(st.src!=='off')return;
    if(M().has())fallback('공식 랭크 데이터를 못 불러와서 시뮬레이터 데이터로 보여줄게.');
    else{const b=document.getElementById('mt-list');if(b)b.innerHTML='<div class="sub">공식 데이터를 못 불러왔어. 나중에 다시 와줘.</div>'}});
}
function partyRec(){
  const m=M(), f=m.fmt(), mem=party.filter(i=>i>=0);
  const names=new Set(mem.map(i=>PK[i][0])), sc=new Map(); let found=0;
  mem.forEach(i=>{const e=m.find(f,i); if(!e)return; found++;
    (e.mates||[]).forEach(([j,pc])=>{const p=PK[j]; if(!p||names.has(p[0]))return;
      const o=sc.get(p[0])||{i:j,s:0,by:[]}; o.s+=pc; if(!o.by.includes(PK[i][0]))o.by.push(PK[i][0]); sc.set(p[0],o)})});
  if(!mem.length)return '<div class="sub">파티 탭에서 포켓몬을 넣으면 추천해줄게.</div>';
  if(!found)return '<div class="sub">파티 포켓몬이 이 포맷 실전 데이터에 없어.</div>';
  const list=[...sc.values()].sort((a,b)=>b.s-a.s).slice(0,8);
  if(!list.length)return '<div class="sub">추천할 만한 포켓몬이 없어.</div>';
  return `<div class="rec">${list.map(o=>{const p=PK[o.i], e=m.find(f,o.i);
    return `<button type="button" class="rec-i" data-add="${o.i}">${noDi(spr(o.i,'s'))}<b>${esc(p[0])}</b><span class="chips">${ptypes(p).map(chip).join('')}</span><span class="sub">${e?'사용률 '+e.u+'%':''}</span><span class="sub">같이 많이 쓰는 포켓몬: ${o.by.slice(0,2).map(esc).join(', ')}</span></button>`}).join('')}</div>
<p class="note" id="mt-msg">누르면 파티의 빈 칸에 들어가.</p>`;
}
// ---- 인기 파티 (ポケDB チャンピオンズ 오픈데이터, meta/teams.js) ----
const TD=()=>window.TEAMS;
function teamEntry(){
  const T=TD(); if(!T)return null; const rule=M()&&M().fmt()==='vgc'?'double':'single';
  const ss=[...new Set(T.seasons.map(x=>x.season))];
  if(!ss.includes(st.tseason))st.tseason=ss[0];
  return {T,ss,rule,e:T.seasons.find(x=>x.season===st.tseason&&x.rule===rule)};
}
function coreHTML(a,n){
  return `<div class="tm-cores">${a.slice(0,10).map(([ids,c])=>`<div class="tm-core"><span class="tm-sp">${ids.map(i=>`<span class="tm-m">${spr(i,'s')}<small>${esc(PK[i][0])}</small></span>`).join('')}</span><b>${Math.round(c/n*100)}%</b><span class="sub">${c}팀</span></div>`).join('')}</div>`;
}
function teamsHTML(){
  const x=teamEntry(); if(!x)return '<div class="sub">인기 파티 데이터를 못 불러왔어. 나중에 다시 와줘.</div>';
  const {T,ss,e}=x;
  const sel=`<label class="mt-ss">시즌 <select id="mt-tseason">${ss.map(s=>`<option value="${esc(s)}"${s===st.tseason?' selected':''}>${esc(s)}</option>`).join('')}</select></label>`;
  if(!e)return sel+'<div class="sub">이 시즌·룰 데이터가 없어.</div>';
  const show=e.teams.slice(0,st.tn);
  const list=show.map((t,k)=>`<div class="tm-team"><div class="tm-hd"><b>${t.rank}위</b><span class="sub">${t.rating!=null?'레이팅 '+t.rating:''}</span><button type="button" class="mt-dexbtn tm-put" data-put="${k}">이 팀 파티에 넣기</button></div>
<div class="tm-six">${t.mons.map(([i,it])=>`<span class="tm-m">${spr(i,'s')}<small>${esc(PK[i][0])}</small><small class="tm-it">${it>=0?esc(T.items[it]):'-'}</small></span>`).join('')}</div></div>`).join('');
  return `${sel}<p class="sub">${esc(st.tseason)} · 상위 ${e.n}팀 중 · 기준일 ${esc(e.updated)}</p>
<h3 class="tm-h">자주 쓰는 2마리 조합</h3>${coreHTML(e.cores2,e.n)}
<h3 class="tm-h">자주 쓰는 3마리 조합</h3>${coreHTML(e.cores3,e.n)}
<h3 class="tm-h">상위 랭커 팀</h3><div class="tm-list">${list}</div>
${e.teams.length>show.length?`<button type="button" class="mt-more" id="tm-more">더 보기 (${show.length}/${e.teams.length})</button>`:''}
<p class="note mt-attr">Data: <a href="${esc(T.source.url)}" target="_blank" rel="noopener noreferrer">ポケDB チャンピオンズ (pokedb.tokyo)</a> 오픈데이터 · 시즌이 끝나야 그 시즌 팀이 올라와 (진행 중 시즌은 아직 없어)</p>`;
}
function drawList(){
  if(st.src==='off')return odrawList();
  const m=M(), d=m.data(m.fmt()), box=document.getElementById('mt-list'); if(!box||!d)return;
  const q=st.q.trim().toLowerCase(), base=adapt(d), max=Math.max(base.length?base[0].e.u:1,1);
  const all=base.filter(o=>(st.t<0||ptypes(o.p).includes(st.t))&&(!q||o.p[0].toLowerCase().includes(q)));
  const show=all.slice(0,st.n), top=a=>a&&a[0]?esc(a[0][0]):'-';
  box.innerHTML=(show.map(o=>{
    const e=o.e, open=st.open===o.i;
    return `<div class="mt-row${open?' open':''}"><button type="button" class="mt-h" data-row="${o.i}" aria-expanded="${open}">
<span class="mt-rk">${e.rank||'-'}</span>${noDi(spr(o.i,'s'))}
<span class="mt-nm"><b>${esc(o.p[0])}</b><span class="chips">${ptypes(o.p).map(chip).join('')}</span></span>
<span class="mt-us"><b>${e.u}%</b><span class="mt-bar"><i style="width:${Math.min(100,e.u/max*100)}%"></i></span></span>
<span class="mt-pv sub">${top(e.items)}<br>${top(e.moves)}</span></button>${open?detail(o):''}</div>`}).join('')||'<div class="sub">조건에 맞는 포켓몬이 없어.</div>')
  +(all.length>show.length?`<button type="button" class="mt-more" id="mt-more">더 보기 (${show.length}/${all.length})</button>`:'');
}
function srcHTML(){return `<div class="mfmt mt-src" role="group" aria-label="데이터 출처">${[['off','공식 랭크 데이터'],['team','인기 파티'],['sim','시뮬레이터(Smogon)']].map(([k,t])=>`<button type="button" data-src="${k}" class="${st.src===k?'on':''}" aria-pressed="${st.src===k}">${t}</button>`).join('')}</div>`}
function filtersHTML(){return `<input type="search" id="mt-q" placeholder="이름으로 찾기" autocomplete="off" value="${esc(st.q)}">
<div class="mt-types"><button type="button" data-ty="-1" class="${st.t<0?'on':''}">전체</button>${TN.map((n,t)=>`<button type="button" data-ty="${t}" class="${st.t===t?'on':''}" style="--tc:${TC[t]}">${n}</button>`).join('')}</div>
<div id="mt-list"></div>`}
function recCard(){return M().has()?`<div class="card"><h2>내 파티 기반 추천</h2><p class="sub">시뮬레이터(Smogon) 팀메이트 통계 기준</p>${partyRec()}</div>`:''}
function draw(){
  const el=root(); if(!el)return; const m=M();
  if(st.src==='team'){
    el.innerHTML=`<div class="card"><h2>인기 파티 조합</h2>${srcHTML()}${m.toggleHTML()}<div id="tm-body">${teamsHTML()}</div></div>`;
    return;
  }
  if(st.src==='off'){
    el.innerHTML=`<div class="card"><h2>메타 랭킹</h2>${srcHTML()}${m.toggleHTML()}
<label class="mt-ss">시즌 <select id="mt-season">${st.seasons.map(s=>`<option value="${esc(s)}"${s===st.season?' selected':''}>${esc(seasonLabel(s))}</option>`).join('')}</select></label>
<p class="sub">인게임 배틀 데이터 기준 · 사용 순위는 게임이 공개한 순서 · 기준일 <span id="mt-date">${st.oo?esc(st.oo.slice(0,10)):''}</span></p>
${filtersHTML()}
<p class="note mt-attr">Battle data provided by <a href="https://championsbattledata.com" target="_blank" rel="noopener noreferrer">Pokémon Champions Battle Data</a></p></div>${recCard()}`;
    odrawList(); loadOfficial();
    return;
  }
  if(!m||!m.has()){el.innerHTML=`<div class="card"><h2>메타</h2>${srcHTML()}<div class="sub">실전 데이터를 못 불러왔어. 나중에 다시 와줘.</div></div>`;return}
  const f=m.fmt(), d=m.data(f), notice=st.notice?`<p class="note mt-warn">${esc(st.notice)}</p>`:'', head=`<div class="card"><h2>실전 사용률 랭킹</h2>${srcHTML()}${m.toggleHTML()}${notice}`;
  if(!d){el.innerHTML=head+'<div class="sub">이 포맷의 실전 데이터가 아직 없어.</div></div>';return}
  el.innerHTML=`${head}
<p class="sub">${m.source(f)}${d.battles?' · '+Number(d.battles).toLocaleString()+'경기':''}</p>
${filtersHTML()}</div>${recCard()}`;
  drawList();
}
function bind(el){
  el.addEventListener('input',e=>{if(e.target.id==='mt-q'){st.q=e.target.value;st.n=50;st.open=-1;drawList()}});
  el.addEventListener('change',e=>{if(e.target.id==='mt-tseason'){st.tseason=e.target.value;st.tn=20;draw();return}
    if(e.target.id==='mt-season'){st.season=e.target.value;st.open=-1;st.n=50;oList=null;draw()}});
  el.addEventListener('click',e=>{
    const g=s=>e.target.closest(s); let b;
    if(b=g('[data-fmt]')){st.open=-1;st.n=50;oList=null;M().setFmt(b.dataset.fmt);return}
    if(b=g('[data-src]')){st.src=b.dataset.src;st.notice='';st.open=-1;st.n=50;draw();return}
    if(b=g('[data-orow]')){const k=b.dataset.orow;st.open=st.open===k?-1:k;drawList();return}
    if(b=g('[data-ty]')){st.t=+b.dataset.ty;st.n=50;st.open=-1;el.querySelectorAll('[data-ty]').forEach(x=>x.classList.toggle('on',x===b));drawList();return}
    if(b=g('#tm-more')){st.tn+=20;draw();return}
    if(b=g('[data-put]')){const x=teamEntry(), t=x&&x.e&&x.e.teams[+b.dataset.put]; if(!t)return;
      const ids=[...new Set(t.mons.map(a=>a[0]))].slice(0,6);
      for(let k=0;k<6;k++){party[k]=k<ids.length?ids[k]:-1; ptBox[k].set(party[k])}
      partyDemo=false; saveParty(); b.textContent='파티에 넣었어! 파티 탭 확인'; return}
    if(b=g('[data-dex]')){window.openDex&&openDex(+b.dataset.dex);return}
    if(b=g('#mt-more')){st.n+=50;drawList();return}
    if(b=g('[data-row]')){const i=+b.dataset.row;st.open=st.open===i?-1:i;drawList();return}
    if(b=g('[data-add]')){
      const k=party.indexOf(-1), msg=document.getElementById('mt-msg');
      if(k<0){if(msg)msg.textContent='파티가 꽉 찼어. 파티 탭에서 한 칸을 비우고 눌러줘.';return}
      party[k]=+b.dataset.add; ptBox[k].set(party[k]); partyDemo=false; saveParty(); draw()}
  });
}
try{
  const el=root();
  if(el){
    TABS.meta=draw; bind(el);
    if(M())M().onChange(()=>{if(tab==='meta')draw()});
    if(location.hash==='#meta')route();
  }
}catch(e){console.error(e)}
})();
