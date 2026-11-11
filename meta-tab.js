(function(){
'use strict';
const M=()=>window.metaUI;
const st={q:'',t:-1,n:50,open:-1};
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
function drawList(){
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
function draw(){
  const el=root(); if(!el)return; const m=M();
  if(!m||!m.has()){el.innerHTML='<div class="card"><h2>메타</h2><div class="sub">실전 데이터를 못 불러왔어. 나중에 다시 와줘.</div></div>';return}
  const f=m.fmt(), d=m.data(f), head=`<div class="card"><h2>실전 사용률 랭킹</h2>${m.toggleHTML()}`;
  if(!d){el.innerHTML=head+'<div class="sub">이 포맷의 실전 데이터가 아직 없어.</div></div>';return}
  el.innerHTML=`${head}
<p class="sub">${m.source(f)}${d.battles?' · '+Number(d.battles).toLocaleString()+'경기':''}</p>
<input type="search" id="mt-q" placeholder="이름으로 찾기" autocomplete="off" value="${esc(st.q)}">
<div class="mt-types"><button type="button" data-ty="-1" class="${st.t<0?'on':''}">전체</button>${TN.map((n,t)=>`<button type="button" data-ty="${t}" class="${st.t===t?'on':''}" style="--tc:${TC[t]}">${n}</button>`).join('')}</div>
<div id="mt-list"></div></div>
<div class="card"><h2>내 파티 기반 추천</h2>${partyRec()}</div>`;
  drawList();
}
function bind(el){
  el.addEventListener('input',e=>{if(e.target.id==='mt-q'){st.q=e.target.value;st.n=50;st.open=-1;drawList()}});
  el.addEventListener('click',e=>{
    const g=s=>e.target.closest(s); let b;
    if(b=g('[data-fmt]')){M().setFmt(b.dataset.fmt);return}
    if(b=g('[data-ty]')){st.t=+b.dataset.ty;st.n=50;st.open=-1;el.querySelectorAll('[data-ty]').forEach(x=>x.classList.toggle('on',x===b));drawList();return}
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
