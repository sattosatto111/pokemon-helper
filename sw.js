// 배틀 도감 오프라인 캐시. 앱 파일을 바꿔서 배포할 때 VERSION을 올리면 새 캐시로 교체돼.
const VERSION = 'bd-v1';
const CORE = [
  './', 'index.html', 'dex.js', 'dex.css', 'meta-tab.js', 'meta-tab.css',
  'meta/ko.js', 'gens/common.js', 'gens/ch.js', 'favicon.svg',
  'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION && k !== VERSION + '-ext').map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // 인게임 랭크 데이터 API는 캐시하지 않음 (출처 규칙: 미러링 금지, 앱이 자체 6시간 캐시를 씀)
  if (url.hostname.endsWith('championsbattledata.com') || url.hostname.endsWith('pokemonbattledata.pages.dev')) return;

  // 페이지 이동: 네트워크 우선, 오프라인이면 캐시
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone(); caches.open(VERSION).then(c => c.put('index.html', copy));
      return res;
    }).catch(() => caches.match('index.html')));
    return;
  }

  // 같은 사이트 파일: 캐시를 먼저 보여주고 뒤에서 갱신
  if (url.origin === location.origin) {
    e.respondWith(caches.open(VERSION).then(async c => {
      const hit = await c.match(req);
      const net = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => hit);
      return hit || net;
    }));
    return;
  }

  // 포켓몬 이미지·글꼴: 캐시 우선
  if (/cdn\.jsdelivr\.net|raw\.githubusercontent\.com|fonts\.(googleapis|gstatic)\.com/.test(url.hostname)) {
    e.respondWith(caches.open(VERSION + '-ext').then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res.ok || res.type === 'opaque') c.put(req, res.clone());
      return res;
    }));
  }
});
