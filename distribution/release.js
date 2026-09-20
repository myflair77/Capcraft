fetch('release.json', {cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{
    const url=new URL(data.installer_url || 'https://github.com/myflair77/Capcraft/releases');
    if(!data.ready || url.protocol!=='https:' || url.hostname!=='github.com' || !url.pathname.startsWith('/myflair77/Capcraft/releases/download/'))return;
    const button=document.getElementById('download');button.href=url.href;button.textContent='Windows용 다운로드 ↓';
    document.getElementById('release-meta').textContent=`Capcraft ${data.display_version || data.version} · Windows 64비트 · ${data.size}`;
    if(/^[a-f0-9]{64}$/i.test(data.sha256)){document.getElementById('checksum').hidden=false;document.getElementById('hash').textContent=data.sha256;}
}).catch(()=>{});
