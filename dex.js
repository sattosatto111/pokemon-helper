(function(){
'use strict';
let back=null,prevFocus=null,sortKey='p',sortDir=-1,moves=[];
const CAT=['물리','특수','변화'];
const STN=['HP','공격','방어','특공','특방','스피드'];
function barColor(v){return v>=130?'#2aa876':v>=100?'#5bb552':v>=70?'#d9b200':v>=50?'#e8862a':'#d9544d'}
function render(i){
  const p=PK[i], types=ptypes(p), L=LV();
  const ab=p[9].filter((a,k,x)=>x.indexOf(a)===k).map(a=>AB[a]);
  const one=ab.length===1?ab[0]:'';
  const base=p.slice(3,9), tot=base.reduce((a,b)=>a+b,0);
  const c1=TC[types[0]], c2=TC[types[types.length-1]];
  const art=SPR_URL+'other/official-artwork/'+SPR[i]+'.png';
  const px=SPR_URL+SPR[i]+'.png';
  let st='<div class="dx-st"><span></span><span></span><span></span><span class="h">무보정</span><span class="h">252</span><span class="h">252↑</span></div>';
  base.forEach((b,k)=>{
    const a=k?stat(b,0,1,L):hpStat(b,0,L), e=k?stat(b,252,1,L):hpStat(b,252,L), u=k?stat(b,252,1.1,L):e;
    st+=`<div class="dx-st"><span>${STN[k]}</span><b>${b}</b><div class="dx-bar"><i style="width:${Math.min(100,b/200*100)}%;background:${barColor(b)}"></i></div><span class="n">${a}</span><span class="n">${e}</span><span class="n">${u}</span></div>`;
  });
  st+=`<div class="dx-st"><span>합계</span><b>${tot}</b><span></span><span></span><span></span><span></span></div>`;
  const g=new Map();
  for(let t=0;t<18;t++){const m=eff(t,types,one); if(m!==1){if(!g.has(m))g.set(m,[]); g.get(m).push(t)}}
  const order=[4,2,.5,.25,0], lab={4:'×4',2:'×2',.5:'×½',.25:'×¼',0:'무효'};
  const ef=order.filter(m=>g.has(m)).concat([...g.keys()].filter(m=>!order.includes(m)))
    .map(m=>`<div class="dx-ef"><b>${lab[m]||'×'+mtxt(m)}</b><div>${g.get(m).map(chip).join('')}</div></div>`).join('');
  moves=(p[10]||[]).map(k=>MV[k]).filter(Boolean);
  return `<button class="dx-x" aria-label="닫기">✕</button>
<div class="dx-head" style="--c1:${c1};--c2:${c2}"><img src="${art}" alt="" onerror="this.onerror=null;this.src='${px}'"><h2 id="dx-t">${esc(p[0])}</h2><div>${types.map(chip).join('')}</div></div>
<div class="dx-body">
<h3>종족값 · Lv.${L} 실수치</h3>${st}
<h3>특성</h3><div class="dx-ab">${ab.map(a=>`<span>${esc(a)}</span>`).join('')||'<span>없음</span>'}</div>
<h3>받는 데미지${one?` (특성 ${esc(one)} 반영)`:''}</h3>${ef||'<div class="dx-ef">약점·저항 없음</div>'}
<h3>배우는 기술 (${moves.length})</h3>
<input class="dx-mv-in" type="search" placeholder="기술 이름이나 타입으로 찾기" autocomplete="off">
<div class="dx-mvw"><table><thead><tr><th data-k="n">기술</th><th data-k="t">타입</th><th data-k="c">분류</th><th data-k="p">위력</th></tr></thead><tbody></tbody></table></div>
<div class="dx-act"><button class="p" data-a="ty">상성 보기</button><button data-a="da">데미지 공격자로</button><button data-a="pt">파티에 넣기</button></div>
</div>`;
}
function paintMoves(){
  const q=back.querySelector('.dx-mv-in').value.trim().toLowerCase();
  const v={n:m=>m[0],t:m=>m[1],c:m=>m[3],p:m=>m[2]};
  const rows=moves.filter(m=>!q||m[0].toLowerCase().includes(q)||TN[m[1]].includes(q)||(CAT[m[3]]||'변화').includes(q))
    .sort((a,b)=>{const x=v[sortKey](a),y=v[sortKey](b);return (typeof x==='string'?x.localeCompare(y,'ko'):x-y)*sortDir||a[0].localeCompare(b[0],'ko')});
  back.querySelector('tbody').innerHTML=rows.map(m=>`<tr><td>${esc(m[0])}</td><td>${chip(m[1])}</td><td>${CAT[m[3]]||'변화'}</td><td>${m[2]||'-'}</td></tr>`).join('')||'<tr><td colspan="4">결과가 없어</td></tr>';
}
function go(i,pre,h){closeDex(true);setPk(pre,i,true);if(location.hash==='#'+h)update();else location.hash='#'+h}
function addParty(i){
  if(partyDemo){party=party.map(()=>-1);ptBox.forEach(b=>b.set(-1));partyDemo=false}
  const k=party.indexOf(-1); if(k<0)return false;
  party[k]=i; ptBox[k].set(i); saveParty(); update(); return true;
}
function openDex(i){
  if(!(i>=0&&PK[i]))return;
  if(back)closeDex(true);
  prevFocus=document.activeElement;
  back=document.createElement('div'); back.id='dx-back';
  back.innerHTML='<div id="dx" role="dialog" aria-modal="true" aria-labelledby="dx-t" tabindex="-1">'+render(i)+'</div>';
  document.body.appendChild(back); document.body.classList.add('dx-lock');
  const dlg=back.firstChild; paintMoves();
  if(party.indexOf(-1)<0&&!partyDemo){const pb=back.querySelector('[data-a=pt]');pb.disabled=true;pb.textContent='파티가 가득 찼어'}
  let down=false;
  back.addEventListener('mousedown',e=>{down=e.target===back});
  back.addEventListener('click',e=>{
    if(e.target===back)return down&&closeDex();
    if(e.target.closest('.dx-x'))return closeDex();
    const th=e.target.closest('th[data-k]');
    if(th){const k=th.dataset.k; if(k===sortKey)sortDir=-sortDir; else{sortKey=k;sortDir=k==='p'?-1:1} return paintMoves()}
    const b=e.target.closest('[data-a]'); if(!b)return;
    if(b.dataset.a==='ty')go(i,'ty','types');
    else if(b.dataset.a==='da')go(i,'da','damage');
    else if(addParty(i)){closeDex(true);location.hash='#party'}
  });
  back.querySelector('.dx-mv-in').addEventListener('input',paintMoves);
  dlg.addEventListener('keydown',e=>{
    if(e.key!=='Tab')return;
    const f=[...dlg.querySelectorAll('button:not(:disabled),input')];
    const a=document.activeElement,fi=f[0],la=f[f.length-1];
    if(e.shiftKey&&(a===fi||a===dlg)){la.focus();e.preventDefault()}
    else if(!e.shiftKey&&a===la){fi.focus();e.preventDefault()}
  });
  dlg.focus();
}
function closeDex(quiet){
  if(!back)return;
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
window.addEventListener('hashchange',fromHash);
fromHash();
window.openDex=openDex;
})();
