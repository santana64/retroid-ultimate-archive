"use strict";
/* IKARIAN v1 — static/offline-friendly personal archive.
 * No claim of emulator-verified achievements. No private credentials are sent anywhere.
 */
(() => {
  const $ = id => document.getElementById(id);
  const STORE = "ikarian:v1:progress";
  const RA_STORE = "ikarian:v1:retroachievements";
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const fold = value => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
  const pictos = {bronze:"◇",silver:"◈",gold:"✦",platinum:"✧",mythic:"♛"};
  const rarityName = {bronze:"BRONZE",silver:"ARGENT",gold:"OR",platinum:"PLATINE",mythic:"MYTHIQUE"};
  const defaultState = () => ({unlocked:{},notes:{},favorites:[]});
  let db = null, byId = new Map(), trophyIndex = new Map(), state = defaultState();
  let current = null, activeTab = "collection", pageSize = 60, muted = true, celebrationTimer = null;
  let storageOK = true, soundContext = null;
  let ra = {username:"",unlocks:[]};

  function getStored() {
    try {
      const raw = JSON.parse(localStorage.getItem(STORE) || "null");
      if (raw && typeof raw === "object") {
        state = {unlocked: raw.unlocked && typeof raw.unlocked === "object" && !Array.isArray(raw.unlocked) ? raw.unlocked : {},
          notes:raw.notes && typeof raw.notes === "object" && !Array.isArray(raw.notes) ? raw.notes : {},
          favorites:Array.isArray(raw.favorites) ? raw.favorites.map(String) : []};
      }
    } catch (err) { storageOK = false; console.warn("Progression locale indisponible",err); }
    try {
      const saved = JSON.parse(localStorage.getItem(RA_STORE) || "null");
      if(saved && typeof saved.username==="string" && Array.isArray(saved.unlocks))
        ra = {username:saved.username,unlocks:saved.unlocks.slice(0,20000)};
    }catch(err){console.warn("Historique RetroAchievements local indisponible",err);}
  }
  function persist() {
    try { localStorage.setItem(STORE, JSON.stringify(state)); storageOK = true; }
    catch (err) { storageOK = false; toast("Stockage indisponible","Exporte une sauvegarde pour conserver tes progrès.", "error"); }
  }
  function dateString(value) {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? "Date inconnue" : d.toLocaleString("fr-FR",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"});
  }
  function isUnlocked(game, trophy) {
    if (trophy.kind === "platinum") return game.trophies.filter(t => t.kind !== "platinum").every(t => !!state.unlocked[t.id]);
    return !!state.unlocked[trophy.id];
  }
  function progress(game) {
    let count = 0;
    for (const t of game.trophies) if (isUnlocked(game,t)) count++;
    return {count,total:game.trophies.length,done:count===game.trophies.length,percent:Math.round(100*count/game.trophies.length)};
  }
  function stats() {
    let xp=0, unlocked=0, platinum=0, played=0;
    for (const game of db.games) {
      const p = progress(game);
      if (p.count > 0) played++;
      if (p.done) platinum++;
      for (const trophy of game.trophies) if (isUnlocked(game,trophy)) {unlocked++;xp+=trophy.xp;}
    }
    let level=1;
    while (level < 500 && xp >= (level * level * 250)) level++;
    const previous = (level-1)*(level-1)*250, next=level*level*250;
    return {xp,unlocked,platinum,played,level,levelPercent:Math.min(100,Math.round(100*(xp-previous)/(next-previous)))};
  }
  function renderStats() {
    const s = stats();
    $("stat-games").textContent = db.games.length.toLocaleString("fr-FR");
    $("stat-trophies").textContent = db.games.reduce((n,g)=>n+g.trophies.length,0).toLocaleString("fr-FR");
    $("stat-unlocks").textContent = s.unlocked.toLocaleString("fr-FR")+" déverrouillés";
    $("stat-platinum").textContent = s.platinum;
    $("stat-level").textContent = s.level;
    $("stat-xp").textContent = s.xp.toLocaleString("fr-FR")+" XP";
    $("level-progress").style.width = s.levelPercent+"%";
  }
  function buildFilters() {
    const select = $("platform");
    const platforms = [...new Set(db.games.map(g=>g.platform))].sort((a,b)=>a.localeCompare(b,"fr"));
    for (const name of platforms) {
      const option=document.createElement("option");
      option.value=name;option.textContent=name;select.append(option);
    }
  }
  function card(game) {
    const p=progress(game),fav=state.favorites.includes(game.id);
    return '<button type="button" class="game '+(p.done?'mastered-card':'')+'" data-game="'+esc(game.id)+'" aria-label="Ouvrir '+esc(game.title)+'">'+
      '<div class="game-top"><span class="platform-pill">'+esc(game.platform)+'</span><span class="game-favorite">'+(fav?'★':'☆')+'</span></div>'+
      '<h3>'+esc(game.title)+'</h3><span class="genre">'+esc(game.genre)+'</span>'+
      '<div class="game-bottom"><span class="game-count '+(p.done?'mastered':'')+'">'+p.count+' / '+p.total+' TROPHÉES</span><div class="progress-rail game-bar"><div style="width:'+p.percent+'%"></div></div></div>'+
      '</button>';
  }
  function filtered() {
    const query=fold($("search").value), platform=$("platform").value, status=$("status").value, sort=$("sort").value;
    const out=db.games.filter(g=>{
      if (query && !fold(g.title+' '+g.platform+' '+g.genre+' '+g.reason).includes(query)) return false;
      if (platform && g.platform!==platform) return false;
      if (status==="favorites" && !state.favorites.includes(g.id)) return false;
      if (["new","started","complete"].includes(status)){
        const p=progress(g);
        if(status==="new" && p.count!==0)return false;
        if(status==="started" && (p.count===0 || p.done))return false;
        if(status==="complete" && !p.done)return false;
      }
      return true;
    });
    if (sort==="title") out.sort((a,b)=>a.title.localeCompare(b.title,"fr"));
    else if (sort==="progress") out.sort((a,b)=>progress(b).percent-progress(a).percent || a.title.localeCompare(b.title,"fr"));
    else if (sort==="platform") out.sort((a,b)=>a.platform.localeCompare(b.platform,"fr") || a.title.localeCompare(b.title,"fr"));
    else out.sort((a,b)=>(a.priority==="Incontournable"?0:1)-(b.priority==="Incontournable"?0:1) || Number(a._order)-Number(b._order));
    return out;
  }
  function renderGames() {
    const list=filtered();
    $("counter").textContent=list.length.toLocaleString("fr-FR")+" jeux";
    $("games").innerHTML=list.slice(0,pageSize).map(card).join("");
    $("empty").classList.toggle("hidden",list.length>0);
    const more=$("more"); more.classList.toggle("hidden",list.length<=pageSize);
    if(list.length>pageSize)more.textContent="Afficher 60 jeux supplémentaires ↓  ("+pageSize+"/"+list.length+")";
  }
  function renderDialog() {
    if(!current)return;
    const game=byId.get(current), p=progress(game), fav=state.favorites.includes(game.id);
    $("dialog-platform").textContent=game.platform+" · "+game.grade;
    $("dialog-title").textContent=game.title;
    $("dialog-summary").textContent=game.reason || game.genre;
    $("dialog-progress-text").textContent=p.count+" trophées sur "+p.total;
    $("dialog-percent").textContent=p.percent+" %";
    $("dialog-progress-bar").style.width=p.percent+"%";
    $("favorite").textContent=fav?"★":"☆";
    $("favorite").setAttribute("aria-label",fav?"Retirer des favoris":"Ajouter aux favoris");
    $("trophy-list").innerHTML=game.trophies.map(t=>{
      const owned=isUnlocked(game,t), auto=t.kind==="platinum",archive=t.kind==="archive";
      return '<button type="button" class="trophy-item rarity-'+esc(t.rarity)+' '+(owned?'unlocked':'locked')+'" data-trophy="'+esc(t.id)+'" '+(auto?'disabled aria-disabled="true"':'')+'>'+
        '<span class="trophy-icon" aria-hidden="true">'+pictos[t.rarity]+'</span>'+
        '<span class="trophy-info"><span class="trophy-title">'+esc(t.name)+'</span><span class="trophy-description">'+esc(t.description)+'</span><span class="trophy-kind">'+(auto?'Calcul automatique':archive?'Carnet requis':'Déclaration personnelle')+'</span></span>'+
        '<span class="trophy-right"><strong>+'+t.xp+' XP</strong><span>'+(owned?'✓ OBTENU':auto?'À CONQUÉRIR':rarityName[t.rarity])+'</span></span></button>';
    }).join("");
    $("notes").value=String(state.notes[game.id]||"");
    $("save-status").textContent="";
    renderGameRA(game);
  }
  function openGame(id) {
    if(!byId.has(String(id))) return;
    current=String(id);
    renderDialog();
    $("game-dialog").showModal();
    document.body.classList.add("modal-open");
  }
  function closeGame() {
    $("game-dialog").close();
    document.body.classList.remove("modal-open");
    current=null;
  }
  function playSound(rare=false) {
    if(muted)return;
    try {
      soundContext ||= new (window.AudioContext || window.webkitAudioContext)();
      const base=soundContext.currentTime;
      (rare?[392,523.25,659.25,880]:[523.25,659.25,783.99]).forEach((freq,i)=>{
        const osc=soundContext.createOscillator(), gain=soundContext.createGain();
        osc.type="sine";osc.frequency.setValueAtTime(freq,base+.075*i);
        gain.gain.setValueAtTime(.0001,base+.075*i);
        gain.gain.exponentialRampToValueAtTime(.06,base+.075*i+.018);
        gain.gain.exponentialRampToValueAtTime(.0001,base+.075*i+.28);
        osc.connect(gain);gain.connect(soundContext.destination);
        osc.start(base+.075*i);osc.stop(base+.075*i+.30);
      });
    }catch(err){console.warn("Sons non disponibles",err);}
  }
  function toast(title,description,kind="info",rarity="bronze") {
    const el=document.createElement("div");
    el.className="toast"+(kind==="error"?" error":"");
    el.innerHTML='<div class="toast-symbol">'+(kind==="error"?'!':pictos[rarity]||"✦")+'</div><div><small>'+(kind==="error"?'ATTENTION':'IKARIAN · NOUVEL ÉVÉNEMENT')+'</small><strong>'+esc(title)+'</strong><span>'+esc(description)+'</span></div>';
    $("toast-stack").prepend(el);
    while($("toast-stack").children.length>4)$("toast-stack").lastChild.remove();
    window.setTimeout(()=>el.remove(),4600);
  }
  function celebrate(title,subtitle) {
    const overlay=$("celebration");
    $("celebration-title").textContent=title;
    $("celebration-subtitle").textContent=subtitle;
    overlay.classList.remove("hidden");overlay.setAttribute("aria-hidden","false");
    clearTimeout(celebrationTimer);
    celebrationTimer=window.setTimeout(()=>{overlay.classList.add("hidden");overlay.setAttribute("aria-hidden","true");},2400);
  }
  function toggleTrophy(id) {
    if(!current)return;
    const game=byId.get(current),t=game.trophies.find(x=>x.id===id);
    if(!t || t.kind==="platinum")return;
    const previous=progress(game).done;
    if (state.unlocked[t.id]) {
      delete state.unlocked[t.id];
      toast("Progression rectifiée",t.name+" retiré de ton carnet.");
    } else {
      if(t.kind==="archive" && !String(state.notes[game.id]||"").trim()){
        toast("Carnet manquant","Écris et enregistre une note avant de valider ce trophée.","error");
        $("notes").focus();
        return;
      }
      state.unlocked[t.id]=new Date().toISOString();
      toast(t.name,game.title+" · +"+t.xp+" XP IKARIAN","info",t.rarity);
      playSound(t.rarity==="mythic");
      if(t.rarity==="mythic")celebrate("Trophée mythique",t.name);
    }
    const mastered=!previous && progress(game).done;
    persist();renderStats();renderGames();renderDialog();renderConstellations();renderJournal();
    if(mastered){toast("Maîtrise totale",game.title+" · Platine obtenu","info","platinum");playSound(true);celebrate("Maîtrise achevée",game.title);}
  }
  function saveNote() {
    if(!current)return;
    const note=$("notes").value.trim().slice(0,8000);
    if(note)state.notes[current]=note;else delete state.notes[current];
    if(!note){const t=byId.get(current).trophies.find(x=>x.kind==="archive");if(t)delete state.unlocked[t.id];}
    persist();renderStats();renderGames();renderDialog();renderConstellations();renderJournal();
    $("save-status").textContent="Carnet enregistré ✓";
    toast("Souvenir consigné",byId.get(current).title);
  }
  function constellations() {
    const s=stats(), completed=db.games.filter(g=>progress(g).done);
    const hack=completed.filter(g=>/ROM hack|hack|fangame|MOD/i.test(g.platform));
    const items=[
      {id:"first",title:"Première étoile",desc:"Maîtriser ton premier jeu.",now:s.platinum,target:1,icon:"✦"},
      {id:"explorer",title:"Architecte des mondes",desc:"Obtenir 100 trophées IKARIAN.",now:s.unlocked,target:100,icon:"◇"},
      {id:"keeper",title:"Le Grand Archiviste",desc:"Maîtriser 25 jeux de toutes générations.",now:s.platinum,target:25,icon:"✧"},
      {id:"legend",title:"L'héritage sans fin",desc:"Atteindre 1 000 trophées dans l'archive.",now:s.unlocked,target:1000,icon:"♛"},
      {id:"hacker",title:"L'autre histoire",desc:"Maîtriser 5 ROM hacks ou fangames.",now:hack.length,target:5,icon:"⟁"}
    ];
    const groups=new Map();
    for(const game of db.games){const base=game.platform.split(" · ")[0];if(!groups.has(base))groups.set(base,[]);groups.get(base).push(game)}
    for(const [platform,games] of groups) {
      if(games.length<3)continue;
      const done=games.filter(g=>progress(g).done).length;
      const target=Math.min(5,games.length);
      items.push({id:"system-"+platform,title:"Gardien · "+platform,desc:"Maîtriser "+target+" jeux de cette collection.",now:done,target,icon:"❖"});
    }
    return items;
  }
  function renderConstellations() {
    $("constellations").innerHTML=constellations().map(c=>{
      const done=c.now>=c.target,per=Math.min(100,Math.round(c.now/c.target*100));
      return '<article class="constellation '+(done?'done':'')+'"><span class="constellation-icon">'+c.icon+'</span><h3>'+esc(c.title)+'</h3><p>'+esc(c.desc)+'</p>'+
        '<div class="constellation-info"><span>'+(done?'CONSTELLATION ACCOMPLIE':'PROGRESSION')+'</span><span>'+c.now+' / '+c.target+'</span></div>'+
        '<div class="progress-rail"><div style="width:'+per+'%"></div></div></article>';
    }).join("");
  }
  function renderJournal() {
    const events=[];
    for(const game of db.games) for(const t of game.trophies) {
      if(t.kind==="platinum")continue;
      const when=state.unlocked[t.id];
      if(when)events.push({time:when,name:t.name,game:game.title,rarity:t.rarity});
    }
    events.sort((a,b)=>String(b.time).localeCompare(String(a.time)));
    $("journal").innerHTML=events.length?events.slice(0,120).map(e=>
      '<div class="journal-item"><span class="journal-symbol">'+pictos[e.rarity]+'</span><div><strong>'+esc(e.name)+'</strong><span>'+esc(e.game)+' · '+rarityName[e.rarity]+'</span></div><time>'+esc(dateString(e.time))+'</time></div>'
    ).join(""):'<p class="empty">Ton premier trophée apparaîtra ici. Choisis un jeu dans la bibliothèque.</p>';
  }

  // RA imports remain a separate source. A local JSON file is not proof that a game
  // automatically verified any IKARIAN objective; the two systems never share XP.
  const canonicalTitle = title => fold(title).replace(/[^a-z0-9]+/g," ").trim();
  function matchedGameForRA(entry) {
    const title = canonicalTitle(entry.gameTitle);
    const matches = db.games.filter(g => canonicalTitle(g.title) === title);
    return matches.length===1 ? matches[0] : null;
  }
  function renderGameRA(game) {
    const el=$("ra-game");
    const matching=ra.unlocks.filter(e=>{
      const mapped=matchedGameForRA(e);
      return mapped && mapped.id===game.id;
    });
    el.classList.toggle("hidden",matching.length===0);
    if(!matching.length){el.innerHTML="";return;}
    el.innerHTML='<div class="ra-game-heading"><strong>✪ RetroAchievements · '+matching.length+' succès importés</strong><small>Historique API séparé des trophées IKARIAN</small></div>'+
      matching.slice(0,30).map(e=>'<div class="ra-game-row"><span>✪</span><div><strong>'+esc(e.title)+'</strong><small>'+esc(e.description)+'</small></div><small>'+esc(e.hardcore?"HARDCORE":"SOFTCORE")+'</small></div>').join("");
  }
  function renderRA() {
    $("ra-user").textContent=ra.username?"Compte : "+ra.username:"Aucun compte importé";
    $("ra-summary").textContent=ra.unlocks.length?ra.unlocks.length+" succès importés (échantillon temporel cumulatif). Les titres ambigus restent non associés.":"Pour commencer, exécute le script local ikarian/ra_sync.py, puis importe son JSON ici.";
    const out=ra.unlocks.slice().sort((a,b)=>String(b.date).localeCompare(String(a.date))).slice(0,150);
    $("ra-list").innerHTML=out.length?out.map(e=>{
      const game=matchedGameForRA(e);
      return '<div class="journal-item"><span class="journal-symbol">✪</span><div><strong>'+esc(e.title)+'</strong>'+
        '<span>'+esc(e.gameTitle)+' · '+esc(e.consoleName||"Plateforme non indiquée")+' · '+(game?'Associé au catalogue':'Association à confirmer')+
        ' · '+(e.hardcore?'Hardcore':'Softcore')+'</span></div><time>'+esc(e.date||"Date inconnue")+'</time></div>';
    }).join(""):'<p class="empty">Aucun succès RetroAchievements importé pour le moment.</p>';
  }
  async function importRA(file) {
    if(!file || file.size>8_000_000){toast("Import RA impossible","Fichier absent ou trop volumineux.","error");return;}
    try {
      const payload=JSON.parse(await file.text());
      if(payload.schema!=="ikarian-ra-import.v1" || payload.source!=="retroachievements-api" ||
         typeof payload.username!=="string" || !Array.isArray(payload.unlocks))throw Error("Format d'export RA incorrect");
      const username=payload.username.slice(0,100);
      if(!username)throw Error("Compte RA manquant");
      const dedup=new Map();
      if(ra.username===username)for(const e of ra.unlocks)dedup.set(String(e.achievementId)+":"+(e.hardcore?1:0),e);
      for(const e of payload.unlocks){
        if(!e || typeof e!=="object" || !Number.isSafeInteger(e.achievementId) || !Number.isSafeInteger(e.gameId) || typeof e.title!=="string" || typeof e.gameTitle!=="string")continue;
        const normalized={
          achievementId:e.achievementId,gameId:e.gameId,gameTitle:e.gameTitle.slice(0,200),
          consoleName:String(e.consoleName||"").slice(0,100),title:e.title.slice(0,200),
          description:String(e.description||"").slice(0,600),date:String(e.date||"").slice(0,40),
          points:Number(e.points)||0,hardcore:Boolean(e.hardcore)
        };
        dedup.set(normalized.achievementId+":"+(normalized.hardcore?1:0),normalized);
      }
      ra={username,unlocks:[...dedup.values()].slice(0,20000)};
      localStorage.setItem(RA_STORE,JSON.stringify(ra));
      renderRA();if(current)renderGameRA(byId.get(current));
      toast("RetroAchievements importé",ra.unlocks.length+" succès conservés dans un espace séparé.","info","gold");
    }catch(err){toast("Import RA impossible",err.message||"Fichier non reconnu.","error");}
  }

  function showTab(tab) {
    if(!["collection","constellations","journal","retroachievements"].includes(tab))return;
    activeTab=tab;
    document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));
    for(const name of ["collection","constellations","journal","retroachievements"])$(name+"-page").classList.toggle("hidden",name!==tab);
    if(tab==="constellations")renderConstellations();
    if(tab==="journal")renderJournal();
    if(tab==="retroachievements")renderRA();
  }
  function refresh() {renderStats();renderGames();renderConstellations();renderJournal();renderRA();}
  function exportBackup() {
    const backup={schema:"ikarian-save.v1",createdAt:new Date().toISOString(),unlocked:state.unlocked,notes:state.notes,favorites:state.favorites};
    const blob=new Blob([JSON.stringify(backup,null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download="IKARIAN-backup-"+new Date().toISOString().slice(0,10)+".json";
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
    toast("Sauvegarde exportée","Conserve ce fichier dans un emplacement privé.");
  }
  async function importBackup(file) {
    if(!file || file.size>6_000_000){toast("Import impossible","Le fichier est trop volumineux ou absent.","error");return;}
    try{
      const content=JSON.parse(await file.text());
      if(content.schema!=="ikarian-save.v1" || typeof content.unlocked!=="object" || content.unlocked===null || Array.isArray(content.unlocked))throw Error("Format de sauvegarde invalide");
      let count=0;
      for(const [id,date] of Object.entries(content.unlocked)){
        if(!trophyIndex.has(id) || trophyIndex.get(id).kind==="platinum" || typeof date!=="string" || Number.isNaN(Date.parse(date)))continue;
        if(!state.unlocked[id]){state.unlocked[id]=date;count++;}
      }
      if(content.notes && typeof content.notes==="object"&&!Array.isArray(content.notes))for(const [id,note] of Object.entries(content.notes)){
        if(byId.has(id) && typeof note==="string" && note.length<=8000 && !state.notes[id])state.notes[id]=note;
      }
      if(Array.isArray(content.favorites))for(const id of content.favorites){
        if(byId.has(String(id)) && !state.favorites.includes(String(id)))state.favorites.push(String(id));
      }
      persist();refresh();if(current)renderDialog();
      toast("Archive restaurée",count+" nouveaux trophées importés.");
    }catch(err){toast("Import impossible",err.message || "Fichier incorrect.","error");}
  }
  function wire() {
    $("search").addEventListener("input",()=>{pageSize=60;renderGames();});
    for(const id of ["platform","status","sort"])$(id).addEventListener("change",()=>{pageSize=60;renderGames();});
    $("more").addEventListener("click",()=>{pageSize+=60;renderGames();});
    $("games").addEventListener("click",e=>{const b=e.target.closest("[data-game]");if(b)openGame(b.dataset.game);});
    $("close-dialog").addEventListener("click",closeGame);
    $("game-dialog").addEventListener("close",()=>{document.body.classList.remove("modal-open");current=null;});
    $("game-dialog").addEventListener("click",e=>{if(e.target===$("game-dialog"))closeGame();});
    $("favorite").addEventListener("click",()=>{
      if(!current)return;const i=state.favorites.indexOf(current);if(i>=0)state.favorites.splice(i,1);else state.favorites.push(current);
      persist();renderDialog();renderGames();
    });
    $("trophy-list").addEventListener("click",e=>{const b=e.target.closest("[data-trophy]");if(b)toggleTrophy(b.dataset.trophy);});
    $("save-note").addEventListener("click",saveNote);
    document.querySelectorAll(".tab").forEach(b=>b.addEventListener("click",()=>showTab(b.dataset.tab)));
    $("ra-import").addEventListener("click",()=>$("ra-file").click());
    $("ra-file").addEventListener("change",async e=>{await importRA(e.target.files?.[0]);e.target.value="";});
    $("export").addEventListener("click",exportBackup);
    $("import").addEventListener("click",()=>$("importfile").click());
    $("importfile").addEventListener("change",async e=>{await importBackup(e.target.files?.[0]);e.target.value="";});
    $("sound").addEventListener("click",()=>{muted=!muted;$("sound").textContent=muted?"♫":"♪";$("sound").setAttribute("aria-label",muted?"Activer les sons":"Désactiver les sons");if(!muted)playSound();});
    $("celebration").addEventListener("click",()=>{$("celebration").classList.add("hidden");$("celebration").setAttribute("aria-hidden","true");});
    document.addEventListener("keydown",e=>{if(e.key==="/" && !["INPUT","TEXTAREA"].includes(document.activeElement.tagName)){e.preventDefault();showTab("collection");$("search").focus();}});
  }
  async function main(){
    getStored();
    wire();
    try {
      const response=await fetch("./data.json",{cache:"no-cache"});
      if(!response.ok)throw Error("Impossible de charger le catalogue ("+response.status+").");
      db=await response.json();
      if(db.schema!=="ikarian.v1" || !Array.isArray(db.games) || db.games.length!==899)throw Error("Le manifeste IKARIAN ne contient pas les 899 jeux attendus.");
      db.games.forEach((g,i)=>{g.id=String(g.id);g._order=i;byId.set(g.id,g);for(const t of g.trophies)trophyIndex.set(t.id,t);});
      buildFilters();refresh();
      if(!storageOK)toast("Stockage local limité","Utilise l'export pour ne pas perdre ta progression.","error");
    }catch(err){
      $("games").innerHTML='<p class="empty">'+esc(err.message)+' Ouvre IKARIAN via un serveur web (exemple : python -m http.server).</p>';
      $("counter").textContent="Chargement impossible";
    }
  }
  main();
})();