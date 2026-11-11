const C="pl-v1",S=["./","index.html","manifest.json","icon-192.png"];
self.addEventListener("install",e=>e.waitUntil(caches.open(C).then(c=>c.addAll(S))));
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);if(u.origin!==location.origin||e.request.method!=="GET")return;
  e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(C).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)));
});
