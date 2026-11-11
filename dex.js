(function(){
'use strict';
let mvAll=false,pushed=false,rerender=null,back=null,prevFocus=null,sortKey='p',sortDir=-1,moves=[];
const CAT=['물리','특수','변화'];
const STN=['HP','공격','방어','특공','특방','스피드'];
function barColor(v){return v>=130?'#2aa876':v>=100?'#5bb552':v>=70?'#d9b200':v>=50?'#e8862a':'#d9544d'}
const metaCbs=[];
let cur=-1;
const gm=()=>typeof getMode==='function'?getMode():(document.documentElement.dataset.mode==='champions'?'ch':'g9');
const gen=()=>typeof GEN==='function'?GEN():(gm()==='ch'?9:+String(gm()).slice(1)||9);
const isCh=()=>typeof CH==='function'?CH():gm()==='ch';
const modeLbl=()=>isCh()?'챔피언스 기준':gen()+'세대 기준';
const aT=i=>typeof pT==='function'?pT(i):ptypes(PK[i]);
const aS=i=>typeof pS==='function'?pS(i):PK[i].slice(3,9);
const aL=i=>typeof pL==='function'?pL(i):(PK[i][10]||[]);
const aA=i=>typeof pA==='function'?pA(i):PK[i][9];
const aAv=i=>typeof avail==='function'?avail(i):true;
const mT=j=>typeof mvT==='function'?mvT(j):MV[j][1];
const mP=j=>typeof mvP==='function'?mvP(j):MV[j][2];
const mC=j=>typeof mvC==='function'?mvC(j):MV[j][3];
const tOK=t=>typeof typeOK==='function'?typeOK(t):true;
function mFmt(){try{return localStorage.getItem('metaFmt')==='vgc'?'vgc':'bss'}catch(e){return 'bss'}}
function mData(f){return window.META&&window.META[f]||null}
const mIdx={};
function mFind(f,i){
  const d=mData(f); if(!d||!PK[i])return null;
  if(!mIdx[f]||mIdx[f].d!==d){const m=new Map();(d.mons||[]).forEach(e=>{if(PK[e.i]&&!m.has(PK[e.i][0]))m.set(PK[e.i][0],e)});mIdx[f]={d,m}}
  return mIdx[f].m.get(PK[i][0])||null;
}
function mToggle(){const f=mFmt();return `<div class="mfmt" role="group" aria-label="포맷">${[['bss','싱글'],['vgc','더블']].map(([k,t])=>`<button type="button" data-fmt="${k}" class="${f===k?'on':''}" aria-pressed="${f===k}">${t}</button>`).join('')}</div>`}
function mSource(f){const d=mData(f);return d?`Smogon 포켓몬 챔피언스 통계 · ${esc(d.month||'')} · 1630+ 기준`:''}
window.metaUI={fmt:mFmt,data:mData,find:mFind,toggleHTML:mToggle,source:mSource,has:()=>!!(window.META&&(META.bss||META.vgc)),
  setFmt(f){try{localStorage.setItem('metaFmt',f)}catch(e){} metaCbs.forEach(c=>c())},onChange(c){metaCbs.push(c)}};
function mRows(a){const top=Math.max(...a.map(x=>x[1]),1);return a.slice(0,6).map(([n,v])=>`<div class="dx-mr"><span>${esc(n)}</span><div class="dx-bar"><i style="width:${Math.min(100,v/top*100)}%;background:var(--accent)"></i></div><b>${v}%</b></div>`).join('')}
function metaHTML(i){
  if(!metaUI.has())return '';
  const f=mFmt(), d=mData(f), tog=mToggle();
  let b;
  if(!d)b='<div class="dx-mn">이 포맷의 실전 데이터가 아직 없어.</div>';
  else{
    const e=mFind(f,i);
    if(!e)b='<div class="dx-mn">이 포맷에선 거의 안 쓰여.</div>';
    else{
      const sec=(t,a)=>a&&a.length?`<h4>${t}</h4>${mRows(a)}`:'';
      const ms=(e.mates||[]).filter(m=>PK[m[0]]).slice(0,8);
      b=`<div class="dx-mu"><b>${e.rank?e.rank+'위':''}</b> 사용률 ${e.u}%<span> · ${esc(d.month||'')}${d.battles?' · '+Number(d.battles).toLocaleString()+'경기':''}</span></div>
${sec('자주 쓰는 기술',e.moves)}${sec('도구',e.items)}${sec('특성',e.abilities)}${sec('자주 쓰는 스탯 포인트 배분 (H/A/B/C/D/S)',e.spreads)}
${ms.length?`<h4>같이 많이 쓰는 포켓몬</h4><div class="dx-mates">${ms.map(([j,v])=>`<button type="button" class="dx-mate" data-mate="${j}">${spr(j,'s').replace(' data-i=',' data-x=')}<span>${esc(PK[j][0])}</span><small>${v}%</small></button>`).join('')}</div>`:''}
<p class="dx-src">${mSource(f)}</p>`;
    }
  }
  return `<h3>실전 데이터</h3>${tog}${b}`;
}
function metaBlock(i){
  if(!isCh())return '<p class="dx-hint">실전 데이터는 챔피언스 모드에서 볼 수 있어</p>';
  if(!metaUI.has()){
    const lm=n=>window.loadMeta?window.loadMeta(n):new Promise(r=>addEventListener('DOMContentLoaded',r,{once:true})).then(()=>window.loadMeta&&window.loadMeta(n));
    lm(['bss','vgc']).then(()=>{const m=document.getElementById('dx-meta');if(m&&m.querySelector('.dx-ld'))m.innerHTML=metaHTML(i)});
    return '<p class="dx-hint dx-ld">실전 데이터 불러오는 중…</p>';
  }
  return metaHTML(i);
}
function render(i){
  const p=PK[i], types=aT(i), L=LV(), G=gen(), old=G<=2&&!isCh();
  const ab=G<3&&!isCh()?[]:aA(i).filter((a,k,x)=>x.indexOf(a)===k).map(a=>AB[a]);
  const one=ab.length===1?ab[0]:'';
  const base=aS(i), tot=base.reduce((a,b)=>a+b,0);
  const c1=TC[types[0]], c2=TC[types[types.length-1]];
  const art=SPR_URL+'other/official-artwork/'+SPR[i]+'.png';
  const px=SPR_URL+SPR[i]+'.png';
  const ec=old?['노력0','노력MAX','']:evCols();
  let st=`<div class="dx-st"><span></span><span></span><span></span>${ec.map(c=>`<span class="h"${old&&c?' title="개체값 DV15 기준. 노력0은 노력치 0, 노력MAX는 노력치 최대"':''}>${c}</span>`).join('')}</div>`;
  const names=G===1&&!isCh()?['HP','공격','방어','특수','','스피드']:STN;
  base.forEach((b,k)=>{
    if(!names[k])return;
    const M=G<=2?65535:252, a=k?stat(b,0,1,L):hpStat(b,0,L), e=k?stat(b,M,1,L):hpStat(b,M,L), u=k?stat(b,M,1.1,L):e;
    st+=`<div class="dx-st"><span>${names[k]}</span><b>${b}</b><div class="dx-bar"><i style="width:${Math.min(100,b/200*100)}%;background:${barColor(b)}"></i></div><span class="n">${a}</span><span class="n">${e}</span><span class="n">${old?'':u}</span></div>`;
  });
  st+=`<div class="dx-st"><span>합계</span><b>${tot}</b><span></span><span></span><span></span><span></span></div>`;
  const g=new Map();
  for(let t=0;t<18;t++){if(!tOK(t))continue;const m=eff(t,types,one); if(m!==1){if(!g.has(m))g.set(m,[]); g.get(m).push(t)}}
  const order=[4,2,.5,.25,0], lab={4:'×4',2:'×2',.5:'×½',.25:'×¼',0:'무효'};
  const ef=order.filter(m=>g.has(m)).concat([...g.keys()].filter(m=>!order.includes(m)))
    .map(m=>`<div class="dx-ef"><b>${lab[m]||'×'+mtxt(m)}</b><div>${g.get(m).map(chip).join('')}</div></div>`).join('');
  moves=aL(i).filter(k=>MV[k]).map(k=>[MV[k][0],mT(k),mP(k),mC(k)]);
  return `<button class="dx-x" aria-label="닫기">✕</button>
<div class="dx-head" style="--c1:${c1};--c2:${c2}"><img src="${art}" alt="" onerror="this.onerror=null;this.src='${px}'"><h2 id="dx-t">${esc(p[0])}</h2><div>${types.map(chip).join('')}</div><span class="dx-gen">${modeLbl()}</span></div>
<div class="dx-body">
${aAv(i)?'':'<div class="dx-na">이 세대엔 등장하지 않아</div>'}
<h3>능력치 · Lv.${L}${old?' (종족값 → 실수치)':''}</h3>${st}
${G<3&&!isCh()?'':`<h3>특성</h3><div class="dx-ab">${ab.map(a=>`<span>${esc(a)}</span>`).join('')||'<span>없음</span>'}</div>`}
<div id="dx-meta">${metaBlock(i)}</div>
<h3>상성 · 받는 데미지${one?` (특성 ${esc(one)} 반영)`:''}</h3>${ef||'<div class="dx-ef">약점·저항 없음</div>'}
<h3>배우는 공격 기술 ${moves.length}개</h3>
<input class="dx-mv-in" type="search" placeholder="기술 이름·타입·분류로 찾기" autocomplete="off">
<div class="dx-mvw"><table><thead><tr><th data-k="n">기술</th><th data-k="t">타입</th><th data-k="c">분류</th><th data-k="p">위력</th></tr></thead><tbody></tbody></table></div>
<button type="button" class="dx-more" hidden></button>
<div class="dx-act"><button class="p" data-a="ty">상성 보기</button><button data-a="da">공격하는 쪽으로</button><button data-a="dd">맞는 쪽으로</button><button data-a="sp">스피드 비교</button><button data-a="pt">파티에 넣기</button></div>
</div>`;
}
function paintMoves(){
  const q=back.querySelector('.dx-mv-in').value.trim().toLowerCase();
  const v={n:m=>m[0],t:m=>m[1],c:m=>m[3],p:m=>m[2]};
  const rows=moves.filter(m=>!q||m[0].toLowerCase().includes(q)||TN[m[1]].includes(q)||(CAT[m[3]]||'변화').includes(q))
    .sort((a,b)=>{const x=v[sortKey](a),y=v[sortKey](b);return (typeof x==='string'?x.localeCompare(y,'ko'):x-y)*sortDir||a[0].localeCompare(b[0],'ko')});
  const lim=mvAll||!matchMedia('(max-width:640px)').matches?rows.length:20;
  back.querySelector('tbody').innerHTML=rows.slice(0,lim).map(m=>`<tr><td>${esc(m[0])}</td><td>${chip(m[1])}</td><td>${CAT[m[3]]||'변화'}</td><td>${m[2]||'-'}</td></tr>`).join('')||'<tr><td colspan="4">찾는 기술이 없어</td></tr>';
  const mb=back.querySelector('.dx-more');
  mb.hidden=rows.length<=lim; mb.textContent='더 보기 ('+(rows.length-lim)+')';
}
function go(i,pre,h){const was=pushed;closeDex(true);try{demo[pre]=false}catch(e){}setPk(pre,i,true);
  if(was){history.replaceState(null,'','#'+h);window.dispatchEvent(new HashChangeEvent('hashchange'))}
  else if(location.hash==='#'+h)update();else location.hash='#'+h}
function addParty(i){
  if(partyDemo){party=party.map(()=>-1);ptBox.forEach(b=>b.set(-1));partyDemo=false}
  const k=party.indexOf(-1); if(k<0)return false;
  party[k]=i; ptBox[k].set(i); saveParty(); update(); return true;
}
function openDex(i){
  if(!(i>=0&&PK[i]))return;
  const keep=pushed;
  if(back)closeDex(true);
  prevFocus=document.activeElement;
  back=document.createElement('div'); back.id='dx-back';
  cur=i; mvAll=false;
  if(keep){pushed=true;history.replaceState({dex:i},'')}
  else if(!/^#dex=/.test(location.hash)){history.pushState({dex:i},'');pushed=true}
  back.innerHTML='<div id="dx" role="dialog" aria-modal="true" aria-labelledby="dx-t" tabindex="-1">'+render(i)+'</div>';
  document.body.appendChild(back); document.body.classList.add('dx-lock');
  const dlg=back.firstChild; paintMoves();
  const fix=()=>{if(party.indexOf(-1)<0&&!partyDemo){const pb=back.querySelector('[data-a=pt]');pb.disabled=true;pb.textContent='파티가 가득 찼어'}};
  fix();
  let down=false;
  back.addEventListener('mousedown',e=>{down=e.target===back});
  back.addEventListener('click',e=>{
    if(e.target===back)return down&&closeDex();
    if(e.target.closest('.dx-x'))return closeDex();
    const ft=e.target.closest('[data-fmt]');
    if(ft){metaUI.setFmt(ft.dataset.fmt);return}
    if(e.target.closest('.dx-more')){mvAll=true;return paintMoves()}
    const mt=e.target.closest('[data-mate]'); if(mt)return openDex(+mt.dataset.mate);
    const th=e.target.closest('th[data-k]');
    if(th){const k=th.dataset.k; if(k===sortKey)sortDir=-sortDir; else{sortKey=k;sortDir=k==='p'?-1:1} return paintMoves()}
    const b=e.target.closest('[data-a]'); if(!b)return;
    if(b.dataset.a==='ty')go(i,'ty','types');
    else if(b.dataset.a==='da')go(i,'da','damage');
    else if(b.dataset.a==='dd')go(i,'dd','damage');
    else if(b.dataset.a==='sp')go(i,'sa','speed');
    else if(addParty(i)){closeDex(true);location.hash='#party'}
  });
  const bind=()=>back.querySelector('.dx-mv-in').addEventListener('input',paintMoves);
  bind();
  rerender=()=>{const sc=dlg.scrollTop;dlg.innerHTML=render(i);paintMoves();fix();bind();dlg.scrollTop=sc};
  dlg.addEventListener('keydown',e=>{
    if(e.key!=='Tab')return;
    const f=[...dlg.querySelectorAll('button:not(:disabled),input')];
    const a=document.activeElement,fi=f[0],la=f[f.length-1];
    if(e.shiftKey&&(a===fi||a===dlg)){la.focus();e.preventDefault()}
    else if(!e.shiftKey&&a===la){fi.focus();e.preventDefault()}
  });
  const mc=()=>{if(!back||!back.contains(dlg))return;const m=dlg.querySelector('#dx-meta');if(m)m.innerHTML=metaHTML(i)};
  metaCbs.push(mc);
  dlg.focus();
}
function closeDex(quiet){
  if(!back)return;
  const was=pushed; pushed=false;
  if(was&&!quiet&&history.state&&history.state.dex!=null){history.back()}
  rerender=null;
  back.remove(); back=null; document.body.classList.remove('dx-lock');
  if(/^#dex=/.test(location.hash))history.replaceState(null,'',location.pathname+location.search+'#'+tab);
  if(!quiet&&prevFocus&&prevFocus.focus&&document.contains(prevFocus))prevFocus.focus();
}
document.addEventListener('keydown',e=>{if(back&&e.key==='Escape'){e.preventDefault();closeDex()}});
document.addEventListener('click',e=>{
  const t=e.target.closest&&e.target.closest('img.spr[data-i]');
  if(!t||t.closest('.list,input,#dx-back'))return;
  openDex(+t.dataset.i);
});
function fromHash(){const m=/^#dex=(\d+)$/.exec(location.hash); if(m)openDex(+m[1])}
document.addEventListener('modechange',()=>{if(back&&rerender)rerender()});
window.addEventListener('hashchange',fromHash);
window.addEventListener('popstate',()=>{if(back)closeDex(true)});
fromHash();
window.openDex=openDex;
})();
