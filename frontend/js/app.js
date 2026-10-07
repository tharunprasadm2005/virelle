/* Virelle shared client. Token in localStorage. No secrets bundled. */
const API = "";
function token(){return localStorage.getItem("tf_token")||"";}
function setToken(t){localStorage.setItem("tf_token",t);}
function logout(){localStorage.removeItem("tf_token");location.href="auth.html";}
async function api(path,opts={}){
  const ctrl=new AbortController();const to=setTimeout(()=>ctrl.abort(),30000);
  try{const r=await fetch(API+path,{...opts,signal:ctrl.signal,headers:{...(opts.headers||{}),"Content-Type":"application/json",...(token()?{Authorization:"Bearer "+token()}:{})}});
  if(r.status===401){if(!location.pathname.endsWith("auth.html"))location.href="auth.html";throw new Error("Login required");}
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(body.detail||("Request failed ("+r.status+")"));
  return body;}finally{clearTimeout(to);}}
function esc(s){return String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function toast(msg,ok=true){let t=document.getElementById("tf-toast");
if(!t){t=document.createElement("div");t.id="tf-toast";document.body.appendChild(t);}
t.textContent=msg;t.className="show "+(ok?"ok":"err");clearTimeout(t._h);t._h=setTimeout(()=>t.className="",3500);}
function setLoading(el,msg){const n=document.getElementById(el);if(n)n.innerHTML=`<p class="muted">${esc(msg||"Loading…")}</p>`;}
async function withBtn(btn,fn){const b=(typeof btn==="string")?document.getElementById(btn):btn;
if(b){b.disabled=true;const t=b.textContent;b.textContent="Working…";
try{return await fn();}catch(e){toast(e.message,false);throw e;}finally{b.disabled=false;b.textContent=t;}}
else{try{return await fn();}catch(e){toast(e.message,false);throw e;}}}
function greeting(){const h=new Date().getHours();return h<12?"Good morning":h<17?"Good afternoon":"Good evening";}
function imgHtml(c,cls="dish"){const initial=(c.name||"?").trim().charAt(0).toUpperCase();
if(!c.image_url)return `<div class="${cls} dish-fallback" aria-label="${esc(c.name)}"><span>${esc(initial)}</span></div>`;
return `<img class="${cls}" src="${esc(c.image_url)}" alt="${esc(c.name)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.outerHTML='<div class=&quot;${cls} dish-fallback&quot;><span>${esc(initial)}</span></div>'">`;}
function metaLine(c){const p=[];if(c.rating)p.push(`<span class="stars">★</span> ${Number(c.rating).toFixed(1)}${c.review_count?` (${c.review_count})`:""}`);if(c.minutes!=null)p.push(`⏱ ${c.minutes} min`);if(c.servings)p.push(`🍽 ${Math.round(c.servings)} servings`);return `<div class="meta-row">${p.join("<span>·</span>")}</div>`;}
function recipeCard(c,opts={}){
  const id=`c${c.recipe_id}_${Math.random().toString(36).slice(2,7)}`;
  return `<div class="rcard" id="${id}">${imgHtml(c)}<div class="body">
    <a class="title" href="recipe.html?id=${c.recipe_id}" style="color:inherit;text-decoration:none">${esc(c.name)}</a>
    ${metaLine(c)}
    ${c.match_score!=null?`<div class="small muted">Matches you: ${(c.match_score*100).toFixed(0)}%</div>`:""}
    ${(c.tags||[]).slice(0,3).map(t=>`<span class="tagchip">${esc(t)}</span>`).join("")}
    <div class="actions">
      <button class="icon" title="Save" onclick="act(${c.recipe_id},'SAVE','${id}')">♡</button>
      <button class="icon" title="Like" onclick="act(${c.recipe_id},'LIKE','${id}')">👍</button>
      <button class="icon" title="Not for me" onclick="act(${c.recipe_id},'DISLIKE','${id}')">👎</button>
      ${opts.cook?`<button class="icon" title="I cooked this" onclick="act(${c.recipe_id},'COOKED','${id}')">🍳</button>`:""}
    </div></div></div>`;
}
async function act(recipe_id,kind,el){
  try{await api(`/api/interactions/${recipe_id}`,{method:"POST",body:JSON.stringify({interaction_type:kind})});
    if(kind==="DISLIKE"&&el){document.getElementById(el)?.remove();}
    else if(el){const b=document.querySelector(`#${el} button[title="${kind==="SAVE"?"Save":kind==="LIKE"?"Like":"Not for me"}"]`);if(b)b.classList.add("on");}
    toast(kind==="SAVE"?"Saved to favorites":kind==="LIKE"?"Liked — we'll recommend more like this":kind==="DISLIKE"?"Got it — fewer like this":"Marked as cooked");
  }catch(e){toast(e.message,false);}
}
function nav(active){
  const items=[["home.html","Home"],["discover.html","Discover"],["pantry.html","Pantry"],["meals.html","Meal Planner"],["shopping.html","Shopping List"],["taste.html","My Taste"]];
  const links=items.map(([h,l])=>`<a href="${h}" class="${active===h?"active":""}">${l}</a>`).join("");
  document.querySelectorAll("nav.mainnav").forEach(n=>n.innerHTML=links+`<a href="research.html" class="${active==="research.html"?"active":""}">Research</a>`);
  document.querySelectorAll(".bottomnav").forEach(n=>n.innerHTML=items.map(([h,l])=>`<a href="${h}" class="${active===h?"active":""}">${l}</a>`).join(""));
}
async function requireUser(){
  try{return await api("/api/auth/me");}catch(e){location.href="auth.html";throw e;}
}
