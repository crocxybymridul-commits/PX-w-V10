"""PX-9 Father PADMIN web panel and per-Son-Bot configuration builder."""
import os, hmac, hashlib, secrets, threading, time, datetime, html, sqlite3, urllib.request, urllib.parse, json, base64
from pathlib import Path
from flask import Flask, request, session, redirect, url_for, render_template_string
from waitress import serve
import config, database as db, provisioner

app=Flask(__name__)
_LOGIN_ATTEMPTS={}
_BUILDER_ATTEMPTS={}
app.secret_key=os.getenv('FATHER_WEB_SECRET','')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SECURE=True,SESSION_COOKIE_SAMESITE='Lax',PERMANENT_SESSION_LIFETIME=datetime.timedelta(minutes=30))

STYLE=r'''<style>
:root{--bg:#080d19;--panel:#111a2b;--panel2:#0d1422;--line:#24334c;--txt:#e9f0ff;--muted:#94a6c4;--acc:#7967f5;--green:#30c991;--red:#e45b76;--gold:#e8bd68}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 10% 0,#182343 0,transparent 35%),var(--bg);color:var(--txt);font:15px Inter,system-ui,sans-serif}header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:18px 24px;border-bottom:1px solid var(--line);background:#0b1323cc}h1{font-size:20px;margin:0}h2{margin:0 0 14px;font-size:19px}h3{font-size:16px;margin:0 0 12px}.layout{display:grid;grid-template-columns:230px minmax(0,1fr);min-height:calc(100vh - 66px)}nav{padding:18px;background:#0b1322;border-right:1px solid var(--line)}nav a{display:block;padding:11px 12px;margin:3px 0;border-radius:10px;text-decoration:none;color:var(--muted)}nav a:hover{background:#1a2740;color:white}.main{padding:24px;max-width:1500px;width:100%}.cards{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:12px}.card,.section,.panel{background:linear-gradient(145deg,var(--panel),#101827);border:1px solid var(--line);border-radius:15px;padding:17px}.section{margin-top:18px}.metric{font-size:28px;font-weight:800;margin-top:7px}.muted{color:var(--muted)}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.fields label,.field{font-size:13px;color:var(--muted)}input,select,textarea{width:100%;padding:11px 12px;margin-top:6px;background:var(--panel2);border:1px solid var(--line);border-radius:9px;color:var(--txt);font:inherit}textarea{min-height:100px;resize:vertical}button{border:0;border-radius:9px;padding:10px 14px;background:var(--acc);color:white;font-weight:700;cursor:pointer}button:hover{filter:brightness(1.12)}button.danger{background:#a63b53}button.secondary{background:#263653}button.small{padding:7px 10px;font-size:12px}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:640px}td,th{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase}.pill{padding:4px 9px;border-radius:50px;background:#253650;font-size:12px}.pill.ok{background:#174a3b;color:#94e6c4}.pill.off{background:#4c2533;color:#ffb2c1}.flash{padding:12px;border:1px solid #3b5b82;background:#142943;border-radius:10px;margin-bottom:12px;white-space:pre-wrap;word-break:break-word}.inline{display:inline}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.bottom{color:var(--muted);font-size:12px;margin:20px 0}.keybox{font-family:monospace;background:#0a1220;padding:12px;border-radius:9px;word-break:break-all}.dynamic-row{display:grid;grid-template-columns:55px 1fr 1fr 100px auto;gap:8px;align-items:center;margin:9px 0}.dynamic-row.menu{grid-template-columns:55px 1fr 2fr 100px auto}.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}.tabs a{padding:9px 12px;border:1px solid var(--line);border-radius:9px;color:#c6c2ff;text-decoration:none}.tab-section{scroll-margin-top:12px}.hint{font-size:12px;color:var(--muted)}@media(max-width:850px){.layout{grid-template-columns:1fr}nav{display:flex;flex-wrap:wrap;border:0;border-bottom:1px solid var(--line);padding:8px}nav a{padding:8px}.main{padding:13px}.cards{grid-template-columns:repeat(2,minmax(130px,1fr))}.two,.fields{grid-template-columns:1fr}header{padding:14px}.dynamic-row,.dynamic-row.menu{grid-template-columns:45px 1fr 1fr}.dynamic-row select{grid-column:2}.dynamic-row button{grid-column:3}}
</style>'''

LOGIN=r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PX-9 PADMIN Login</title>''' + STYLE + r'''</head><body style="min-height:100vh;display:grid;place-items:center"><form class="panel" method="post" style="width:min(440px,94vw);padding:28px"><h1>⚡ PX-9 PADMIN</h1><p class="muted">Father control center · secure access</p>{% if error %}<div class="flash">{{error}}</div>{% endif %}<input type="hidden" name="csrf" value="{{csrf}}"><label>Username<input name="username" autocomplete="username" required></label><label>Password<input type="password" name="password" autocomplete="current-password" required></label><button style="width:100%;margin-top:14px">LOGIN</button></form></body></html>'''

DASH=r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PX-9 PADMIN</title>''' + STYLE + r'''</head><body><header><h1>⚡ PX-9 PADMIN</h1><div class="row"><span class="muted">Father Bot owner panel</span><a href="{{url_for('logout')}}">Logout</a></div></header><div class="layout"><nav><a href="#overview">▦ Overview</a><a href="#actions">⚡ Quick Actions</a><a href="#bots">🤖 Active Bots</a><a href="#keys">🎟 Premium Keys</a><a href="#premium">💎 Premium Users</a><a href="#login">🔐 Login</a></nav><main class="main">{% for message in messages %}<div class="flash"><span>{{message}}</span> <button class="small secondary" type="button" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText)">COPY</button></div>{% endfor %}
<section id="overview"><h2>Dashboard</h2><div class="cards"><div class="card"><div class="muted">TOTAL BOT</div><div class="metric">{{stats.bots}}</div></div><div class="card"><div class="muted">TOTAL USER · ALL SON BOTS</div><div class="metric">{{stats.users}}</div></div><div class="card"><div class="muted">TOTAL REVENUE</div><div class="metric">₹{{stats.revenue}}</div></div><div class="card"><div class="muted">TODAY REVENUE</div><div class="metric">₹{{stats.today_revenue}}</div></div></div></section>
<section class="section" id="bots"><h2>🤖 Active Son Bots</h2><p class="muted">Sorted by recorded bot users, highest first. Each bot has a separate builder page.</p><div class="tablewrap"><table><thead><tr><th>Bot</th><th>Admin</th><th>Users</th><th>Payments</th><th>Revenue</th><th>Status</th><th>Builder Password</th><th>Action</th></tr></thead><tbody>{% for b in bots %}<tr><td><b>@{{b.bot_username or 'unknown'}}</b><br><span class="muted">#{{b.id}}</span></td><td>{{b.admin_id}}</td><td>{{b.users}}</td><td>{{b.payments}}</td><td>₹{{b.revenue}}</td><td><span class="pill {% if b.status=='RUNNING' %}ok{% else %}off{% endif %}">{{b.status}}</span></td><td>{% if b.status!='REVOKED' %}<form method="post" action="{{url_for('builder_password',bot_id=b.id)}}"><input type="hidden" name="csrf" value="{{csrf}}"><button class="small">Generate 5-min Password</button></form>{% else %}—{% endif %}</td><td>{% if b.status!='REVOKED' %}<form method="post" action="{{url_for('revoke_bot',bot_id=b.id)}}"><input type="hidden" name="csrf" value="{{csrf}}"><button class="small danger" onclick="return confirm('Revoke this bot?')">Revoke</button></form>{% endif %}</td></tr>{% endfor %}</tbody></table></div></section>
<section class="section" id="actions"><h2>⚡ Quick Actions</h2><div class="two"><form class="panel" method="post" action="{{url_for('create_premium_key')}}"><input type="hidden" name="csrf" value="{{csrf}}"><h3>Generate key</h3><div class="fields"><label>Plan<input name="plan" value="ELITE" maxlength="50" required></label><label>Redeem users<input type="number" name="users" value="1" min="1" required></label><label>Bots per user<input type="number" name="bots" value="1" min="1" required></label><label>Duration days<input type="number" name="days" value="30" min="1" required></label><label>Price ₹<input type="number" name="price" value="0" min="0" required></label></div><p><button>GENERATE PREMIUM KEY</button></p></form><form class="panel" method="post" action="{{url_for('remove_premium')}}"><input type="hidden" name="csrf" value="{{csrf}}"><h3>Remove premium access</h3><label>User Telegram ID<input name="user_id" type="number" min="1" required></label><button class="danger" style="margin-top:10px">REMOVE PREMIUM</button></form></div></section>
<section class="section" id="keys"><h2>🎟 Premium Keys</h2><div class="tablewrap" style="margin-top:14px"><table><thead><tr><th>Key ID</th><th>Key hint</th><th>Plan</th><th>Usage</th><th>Bot slots</th><th>Duration</th><th>Price</th><th>Status</th><th>Toggle</th></tr></thead><tbody>{% for k in keys %}<tr><td>#{{k.id}}</td><td>••••{{k.key_hint}}</td><td>{{k.plan_name}}</td><td>{{k.redeemed_count}}/{{k.max_users}}</td><td>{{k.bots_per_user}}</td><td>{{k.duration_days}} days</td><td>₹{{k.price}}</td><td><span class="pill {% if k.status=='ACTIVE' %}ok{% else %}off{% endif %}">{{k.status}}</span></td><td><form method="post" action="{{url_for('key_toggle',key_id=k.id)}}"><input type="hidden" name="csrf" value="{{csrf}}"><button class="small secondary">{% if k.status=='ACTIVE' %}Deactivate{% else %}Activate{% endif %}</button></form></td></tr>{% endfor %}</tbody></table></div></section>
<section class="section" id="premium"><h2>💎 Premium Users</h2><div class="tablewrap" style="margin-top:14px"><table><thead><tr><th>User</th><th>Plan</th><th>Bot limit</th><th>Expiry</th><th>Status</th><th>Remove</th></tr></thead><tbody>{% for s in subs %}<tr><td>{{s.user_id}}</td><td>{{s.plan_name}}</td><td>{{s.bot_limit}}</td><td>{{s.expires_at}}</td><td>{{s.status}}</td><td><form method="post" action="{{url_for('remove_premium')}}"><input type="hidden" name="csrf" value="{{csrf}}"><input type="hidden" name="user_id" value="{{s.user_id}}"><button class="small danger">Remove</button></form></td></tr>{% endfor %}</tbody></table></div></section>
<section class="section" id="login"><h2>🔐 PADMIN Login</h2><p class="muted">Change the web login username and password. The password is stored as a hash.</p><form method="post" action="{{url_for('change_login')}}" class="panel"><input type="hidden" name="csrf" value="{{csrf}}"><div class="fields"><label>New username<input name="username" minlength="3" maxlength="60" value="{{web_username}}" required></label><label>New password<input type="password" name="password" minlength="12" placeholder="12+ characters" required></label><label>Confirm password<input type="password" name="confirm" minlength="12" required></label></div><button style="margin-top:12px">SAVE LOGIN</button></form><form method="post" action="{{url_for('reset_login')}}" class="panel" style="margin-top:12px"><input type="hidden" name="csrf" value="{{csrf}}"><h3>Reset login from web</h3><p class="muted">Generates new default credentials for recovery.</p><button class="secondary">GENERATE DEFAULT CREDENTIALS</button></form></section><div class="bottom">Payment credentials and bot tokens are not exposed. Bot statistics are aggregated from each bot's own database.</div></main></div></body></html>'''


BUILDER_LOGIN=r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Son Bot Login</title>''' + STYLE + r'''</head><body style="min-height:100vh;display:grid;place-items:center"><form class="panel" method="post" style="width:min(440px,94vw);padding:28px"><h1>🛠 Son Bot Builder</h1><p class="muted">@{{bot_username}} · Bot-specific login</p>{% if error %}<div class="flash">{{error}}</div>{% endif %}<input type="hidden" name="csrf" value="{{csrf}}"><label>Username<input name="username" required></label><label>Password<input type="password" name="password" required></label><button style="width:100%;margin-top:14px">LOGIN</button></form></body></html>'''

BUILDER=r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Son Bot Builder</title>''' + STYLE + r'''</head><body><header><h1>🛠 Son Bot Builder</h1><div>@{{bot_username}} · Owner {{admin_name}} ({{admin_id}}) · <a href="{{url_for('builder_logout',bot_id=bot_id)}}">Logout</a></div></header><main class="main" style="max-width:1400px;margin:auto">{% for message in messages %}<div class="flash"><span>{{message}}</span> <button class="small secondary" type="button" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText)">COPY</button></div>{% endfor %}<div class="tabs"><a href="#dashboard">Dashboard</a><a href="#theme">Theme</a><a href="#welcome">Welcome</a><a href="#premium-message">Set Premium</a><a href="#plans">Premium</a><a href="#menu">Menu Buttons</a><a href="#approval">Approval Media</a><a href="#proof">Proof Channel & Note</a><a href="#upi">UPI</a><a href="#gateway">Payment Gateway</a><a href="#colors">Colors</a><a href="#protect">Protection</a><a href="#password">Change Password</a></div><form method="post" action="{{url_for('builder_save',bot_id=bot_id)}}"><input type="hidden" name="csrf" value="{{csrf}}">
<section class="section tab-section" id="dashboard"><h2>Dashboard Statistics</h2><div class="cards"><div class="card"><div class="muted">TOTAL USER</div><div class="metric">{{stats.users}}</div></div><div class="card"><div class="muted">TODAY JOIN</div><div class="metric">{{stats.today_join}}</div></div><div class="card"><div class="muted">ORDERS / APPROVED PAYMENTS</div><div class="metric">{{stats.orders}}</div></div><div class="card"><div class="muted">TOTAL REVENUE</div><div class="metric">₹{{stats.revenue}}</div></div><div class="card"><div class="muted">TODAY REVENUE</div><div class="metric">₹{{stats.today_revenue}}</div></div></div></section>
<section class="section tab-section" id="theme"><h2>🎨 Theme</h2><label>Theme<select name="theme" id="theme-select" onchange="this.form.submit()"><option value="1" {% if theme=='1' %}selected{% endif %}>Theme 1</option><option value="2" {% if theme=='2' %}selected{% endif %}>Theme 2</option><option value="3" {% if theme=='3' %}selected{% endif %}>Theme 3</option></select></label><p class="hint">Theme 1 displays the Premium Message and premium plans as a submenu; Theme 2/3 display plans directly.</p></section>
<section class="section tab-section" id="welcome"><h2>👋 Welcome Message</h2><div class="fields"><label>Media type<select name="welcome_type"><option value="none" {% if welcome_type=='none' %}selected{% endif %}>No media / text only</option><option value="photo" {% if welcome_type=='photo' %}selected{% endif %}>Image URL</option><option value="video" {% if welcome_type=='video' %}selected{% endif %}>Video URL</option></select></label><label>Auto-delete seconds (0 = off)<input name="welcome_delete" type="number" min="0" max="86400" value="{{welcome_delete}}"></label><label style="grid-column:1/-1">Image/video URL<input name="welcome_url" value="{{welcome_url}}" placeholder="https://... (Telegram-accessible media URL)"></label></div><label>Welcome text<textarea name="welcome_text" placeholder="Hello {username}\nWelcome to {botname}\nYour text...">{{welcome_text}}</textarea></label><button type="button" class="secondary" onclick="document.querySelector('[name=welcome_url]').value='';document.querySelector('[name=welcome_type]').value='none'">REMOVE MEDIA</button></section>
<section class="section tab-section" id="premium-message"><h2>💎 Set Premium Message (Theme 1 only)</h2><div class="fields"><label>Media type<select name="premium_type"><option value="none" {% if premium_type=='none' %}selected{% endif %}>Text only</option><option value="photo" {% if premium_type=='photo' %}selected{% endif %}>Image URL</option><option value="video" {% if premium_type=='video' %}selected{% endif %}>Video URL</option></select></label><label>Media URL<input name="premium_url" value="{{premium_url}}"></label></div><label>Premium message<textarea name="premium_text">{{premium_text}}</textarea></label><button type="button" class="secondary" onclick="document.querySelector('[name=premium_url]').value='';document.querySelector('[name=premium_type]').value='none'">REMOVE MEDIA</button></section>
<section class="section tab-section" id="plans"><h2>💎 Premium Plans</h2><p class="hint">Six plan slots are shown by default. Add more rows only after all six are occupied. Row colors cycle Red → Green → Blue.</p><div id="plans-list">{% for row in plans %}<div class="dynamic-row plan"><input value="{{loop.index}}" disabled><input name="plan_name_{{loop.index}}" value="{{row.name}}" placeholder="Plan name"><input name="plan_price_{{loop.index}}" type="number" min="0" value="{{row.price}}" placeholder="Price ₹"><select name="plan_color_{{loop.index}}"><option value="R" {% if row.color=='R' %}selected{% endif %}>Red</option><option value="G" {% if row.color=='G' %}selected{% endif %}>Green</option><option value="B" {% if row.color=='B' %}selected{% endif %}>Blue</option></select><button type="button" class="danger small" onclick="this.parentElement.remove();renumber('plans-list','plan')">Remove</button></div>{% endfor %}</div><button id="add-plan" type="button" class="secondary" onclick="addRow('plans-list','plan')" style="display:none">+ ADD PLAN</button></section>
<section class="section tab-section" id="menu"><h2>🔘 Menu Buttons</h2><p class="hint">Six rows are displayed. Row colors cycle Red → Green → Blue.</p><div id="menu-list">{% for row in menu %}<div class="dynamic-row menu"><input value="{{loop.index}}" disabled><input name="menu_name_{{loop.index}}" value="{{row.name}}" placeholder="Button name"><input name="menu_link_{{loop.index}}" value="{{row.link}}" placeholder="URL or link"><select name="menu_color_{{loop.index}}"><option value="R" {% if row.color=='R' %}selected{% endif %}>Red</option><option value="G" {% if row.color=='G' %}selected{% endif %}>Green</option><option value="B" {% if row.color=='B' %}selected{% endif %}>Blue</option></select><button type="button" class="danger small" onclick="this.parentElement.remove();renumber('menu-list','menu')">Remove</button></div>{% endfor %}</div><button id="add-menu" type="button" class="secondary" onclick="addRow('menu-list','menu')" style="display:none">+ ADD BUTTON</button></section>
<section class="section tab-section" id="approval"><h2>🖼 Approval Media</h2><div class="fields"><label>Media type<select name="approve_type"><option value="none" {% if approve_type=='none' %}selected{% endif %}>Text only</option><option value="photo" {% if approve_type=='photo' %}selected{% endif %}>Image URL</option><option value="video" {% if approve_type=='video' %}selected{% endif %}>Video URL</option></select></label><label>Media URL<input name="approve_url" value="{{approve_url}}"></label></div><label>Approval text (links allowed as plain URL)<textarea name="approve_text">{{approve_text}}</textarea></label><button type="button" class="secondary" onclick="document.querySelector('[name=approve_url]').value='';document.querySelector('[name=approve_type]').value='none'">REMOVE MEDIA</button></section>
<section class="section tab-section" id="proof"><h2>📡 Proof Channel & Note</h2><label>Proof / Log Channel<input name="proof_channel" value="{{proof_channel}}" placeholder="@channel or -100..."></label><label>Note<textarea name="proof_note">{{proof_note}}</textarea></label></section>
<section class="section tab-section" id="upi"><h2>🏦 UPI</h2><div class="fields"><label>UPI ID<input name="upi" value="{{upi}}"></label><label>Permanent UPI ID<input name="permanent_upi" value="{{permanent_upi}}"></label><label>Demo link<input name="demo" value="{{demo}}"></label><label>Contact link<input name="contact" value="{{contact}}"></label></div></section>
<section class="section tab-section" id="gateway"><h2>💳 Payment Gateway</h2><p>Current status: <b>{{gateway_status}}</b>. Enter credentials only if you are setting them now. Stored credentials are never read back into the form.</p><div class="fields"><label>Merchant ID (MID)<input name="gateway_mid" value="" autocomplete="off"></label><label>Merchant Key<input name="gateway_key" value="" type="password" autocomplete="new-password"></label><label>Website name<input name="gateway_website" value="DEFAULT" placeholder="DEFAULT"></label><label>Environment<select name="gateway_environment"><option value="TEST">TEST</option><option value="PRODUCTION">PRODUCTION</option></select></label></div><p class="hint">Automatic payment verification is not enabled in this build. This form stores Paytm credentials encrypted for the Son Bot only.</p><label><input type="checkbox" name="remove_gateway" value="1" style="width:auto"> Remove stored gateway credentials</label></section>
<section class="section tab-section" id="colors"><h2>🎨 Button Colors</h2><p class="hint">Plan and menu row colors are set in their respective sections. Default colors apply if a row is left blank.</p></section>
<section class="section tab-section" id="protect"><h2>🛡 Content Protection</h2><label>Protect bot-sent content<select name="restrict"><option value="0" {% if restrict!='1' %}selected{% endif %}>OFF</option><option value="1" {% if restrict=='1' %}selected{% endif %}>ON</option></select></label></section>
<section class="section tab-section" id="password"><h2>🔑 Change Builder Password</h2><p class="hint">Generate a new single-use login password valid for five minutes. It invalidates any previous un-used password.</p><button class="secondary" type="submit" formmethod="post" formaction="{{url_for('builder_password_change',bot_id=bot_id)}}">GENERATE NEW 5-MIN PASSWORD</button></section><section class="section"><h2>💾 Apply Settings</h2><p>Settings are written to this Son Bot's database. Dynamic bot settings are used on the next interaction; media URLs require Telegram to be able to fetch them.</p><button> SAVE CONFIGURATION</button></section></form><script>
function isFilled(container,type){return Array.from(document.querySelectorAll('#'+container+' .dynamic-row')).every(r=>{let inputs=Array.from(r.querySelectorAll('input:not([disabled])'));return inputs.length&&inputs[0].value.trim()!==''&&(type==='plan'||inputs[1].value.trim()!=='' )})}
function refreshAdd(container,type){let btn=document.getElementById(type==='plan'?'add-plan':'add-menu');if(btn)btn.style.display=(document.querySelectorAll('#'+container+' .dynamic-row').length>=6&&isFilled(container,type))?'inline-block':'none'}
function renumber(container,type){let rows=document.querySelectorAll('#'+container+' .dynamic-row');rows.forEach((r,i)=>{let idx=i+1;r.querySelector('input[disabled]').value=idx;r.querySelectorAll('input,select').forEach(el=>{if(el.name){let base=el.name.replace(/_\d+$/,'');el.name=base+'_'+idx}})});refreshAdd(container,type)}
function addRow(container,type){let rows=document.querySelectorAll('#'+container+' .dynamic-row');if(rows.length>=30||rows.length<6||!isFilled(container,type))return;let idx=rows.length+1;let d=document.createElement('div');d.className='dynamic-row '+type;if(type==='plan'){d.innerHTML=`<input value="${idx}" disabled><input name="plan_name_${idx}" placeholder="Plan name"><input name="plan_price_${idx}" type="number" min="0" placeholder="Price ₹"><select name="plan_color_${idx}"><option value="R">Red</option><option value="G">Green</option><option value="B">Blue</option></select><button type="button" class="danger small" onclick="this.parentElement.remove();renumber('${container}','${type}')">Remove</button>`}else{d.innerHTML=`<input value="${idx}" disabled><input name="menu_name_${idx}" placeholder="Button name"><input name="menu_link_${idx}" placeholder="URL or link"><select name="menu_color_${idx}"><option value="R">Red</option><option value="G">Green</option><option value="B">Blue</option></select><button type="button" class="danger small" onclick="this.parentElement.remove();renumber('${container}','${type}')">Remove</button>`}document.getElementById(container).appendChild(d);d.querySelectorAll('input,select').forEach(el=>el.addEventListener('input',()=>refreshAdd(container,type)));refreshAdd(container,type)}
document.addEventListener('DOMContentLoaded',()=>{['plans-list','menu-list'].forEach(id=>{document.querySelectorAll('#'+id+' input:not([disabled]), #'+id+' select').forEach(el=>el.addEventListener('input',()=>refreshAdd(id,id==='plans-list'?'plan':'menu')))});refreshAdd('plans-list','plan');refreshAdd('menu-list','menu')});
document.addEventListener('DOMContentLoaded',()=>{const theme=document.getElementById('theme-select');const section=document.getElementById('premium-message');function toggle(){section.style.display=theme.value==='1'?'':'none'}toggle();theme.addEventListener('change',toggle)});
</script></main></body></html>'''

def _csrf():
    if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(32)
    return session['csrf']
def _check_csrf(): return hmac.compare_digest(str(request.form.get('csrf','')),str(session.get('csrf','')))
def _auth(): return bool(session.get('father_admin_authenticated'))
def _default_username(): return os.getenv('FATHER_WEB_USERNAME','ADMIN').strip() or 'ADMIN'
def _password(): return os.getenv('FATHER_WEB_PASSWORD','')
def _login_hash(): return db.setting('father_web_password_hash')
def _current_username(): return db.setting('father_web_username') or _default_username()
def reset_web_credentials():
    username='ADMIN'; password=secrets.token_urlsafe(16)
    db.setting('father_web_username',username)
    db.setting('father_web_password_hash',hashlib.sha256(password.encode()).hexdigest())
    return username,password
def _login_limiter(ip):
    now=time.time(); bucket=_LOGIN_ATTEMPTS.get(ip,[])
    bucket=[t for t in bucket if now-t<600]
    _LOGIN_ATTEMPTS[ip]=bucket
    return len(bucket)<8
def _login_fail(ip):
    now=time.time(); bucket=[t for t in _LOGIN_ATTEMPTS.get(ip,[]) if now-t<600]; bucket.append(now); _LOGIN_ATTEMPTS[ip]=bucket
def _login_ok(user,pw):
    stored=_login_hash()
    if stored:
        return user==_current_username() and hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(),stored)
    return user==_default_username() and hmac.compare_digest(pw,_password())

def _flash(msg): session.setdefault('flash_messages',[]).append(str(msg))
def _valid_post(): return _auth() and _check_csrf()
def _bots_with_metrics():
    output=[]
    for row in db.list_bots():
        b=dict(row); users=payments=revenue=today_revenue=0
        try:
            path=Path(row['instance_path'])/'bot_database.db'
            c=sqlite3.connect(path,timeout=3)
            users=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            payments=c.execute("SELECT COUNT(*) FROM payment_records WHERE status='approved'").fetchone()[0]
            revenue=c.execute("SELECT COALESCE(SUM(amount),0) FROM payment_records WHERE status='approved'").fetchone()[0]
            today_revenue=c.execute("SELECT COALESCE(SUM(amount),0) FROM payment_records WHERE status='approved' AND date(approved_at,'+5 hours','+30 minutes')=date('now','+5 hours','+30 minutes')").fetchone()[0]
            c.close()
        except Exception: pass
        b.update(users=int(users),payments=int(payments),revenue=int(revenue),today_revenue=int(today_revenue))
        output.append(b)
    output.sort(key=lambda x:(x['status']=='RUNNING',x['users']),reverse=True)
    return output

def _father_stats(bots):
    return {'bots':sum(1 for b in bots if b['status']!='REVOKED'),'users':sum(b['users'] for b in bots if b['status']!='REVOKED'),'revenue':sum(b['revenue'] for b in bots if b['status']!='REVOKED'),'today_revenue':sum(b['today_revenue'] for b in bots if b['status']!='REVOKED')}

def _builder_key(bot_id,suffix): return f'builder_{int(bot_id)}_{suffix}'
def _active_bot(bot_id):
    row=db.get_bot_by_id(int(bot_id)); return row if row and row['status']=='RUNNING' else None
def _bot_db_path(row): return Path(row['instance_path'])/'bot_database.db'
def _open_bot_db(row):
    path=_bot_db_path(row)
    if not path.exists(): raise RuntimeError('Bot database not found.')
    c=sqlite3.connect(path,timeout=5); c.row_factory=sqlite3.Row
    return c
def _builder_read(row):
    c=_open_bot_db(row)
    settings={r['key']:r['value'] for r in c.execute('SELECT key,value FROM settings').fetchall()}
    plans=[]; menus=[]
    max_plan=c.execute('SELECT COALESCE(MAX(btn_id),0) FROM buttons').fetchone()[0]
    max_menu=c.execute('SELECT COALESCE(MAX(btn_id),0) FROM menu_buttons').fetchone()[0]
    plan_count=max(6,min(30,max_plan)); menu_count=max(6,min(30,max_menu))
    for i in range(1,max(plan_count,menu_count)+1):
        p=c.execute('SELECT text,price FROM buttons WHERE btn_id=?',(i,)).fetchone()
        plans.append({'name':p['text'] if p else '', 'price':p['price'] if p else 0, 'color':settings.get(f'btn_color_{i}','RGB'[(i-1)%3])})
        m=c.execute('SELECT text,link FROM menu_buttons WHERE btn_id=?',(i,)).fetchone()
        menus.append({'name':m['text'] if m else '', 'link':m['link'] if m else '', 'color':settings.get(f'menu_color_{i}','RGB'[(i-1)%3])})
    try: users=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    except Exception: users=0
    try: today_join=c.execute("SELECT COUNT(*) FROM users WHERE date(created_at,'+5 hours','+30 minutes')=date('now','+5 hours','+30 minutes')").fetchone()[0]
    except Exception: today_join=0
    try: orders=c.execute("SELECT COUNT(*) FROM payment_records WHERE status='approved'").fetchone()[0]
    except Exception: orders=0
    try: revenue=c.execute("SELECT COALESCE(SUM(amount),0) FROM payment_records WHERE status='approved'").fetchone()[0]
    except Exception: revenue=0
    try: today_revenue=c.execute("SELECT COALESCE(SUM(amount),0) FROM payment_records WHERE status='approved' AND date(approved_at,'+5 hours','+30 minutes')=date('now','+5 hours','+30 minutes')").fetchone()[0]
    except Exception: today_revenue=0
    c.close()
    stats={'users':users,'today_join':today_join,'orders':orders,'revenue':revenue,'today_revenue':today_revenue}
    return settings,plans,menus,stats

def _valid_url_or_empty(v,maxlen=600):
    v=(v or '').strip()[:maxlen]
    if v and not (v.startswith('https://') or v.startswith('http://') or v.startswith('tg://')): raise ValueError('Links must start with https://, http://, or tg://')
    return v

def _builder_write(row,form):
    c=_open_bot_db(row)
    c.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS buttons(btn_id INTEGER PRIMARY KEY,text TEXT,price INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS menu_buttons(btn_id INTEGER PRIMARY KEY,text TEXT,link TEXT)')
    theme=str(form.get('theme','1'))
    if theme not in {'1','2','3'}: raise ValueError('Theme must be 1, 2, or 3.')
    def setv(k,v): c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',(k,str(v)))
    setv('selected_theme',theme); setv('restrict_content','1' if form.get('restrict')=='1' else '0'); setv('setup_complete','1')
    text_settings={'welcome_text':form.get('welcome_text','')[:3500], 'welcome_media_type':form.get('welcome_type','none'),'welcome_media_url':_valid_url_or_empty(form.get('welcome_url')),'welcome_auto_delete':str(max(0,min(86400,int(form.get('welcome_delete',0))))),'premium_text':form.get('premium_text','')[:3500],'premium_media_type':form.get('premium_type','none'),'premium_media_url':_valid_url_or_empty(form.get('premium_url')),'approval_text':form.get('approve_text','')[:3500],'approval_media_type':form.get('approve_type','none'),'approval_media_url':_valid_url_or_empty(form.get('approve_url')),'proof_channel':form.get('proof_channel','')[:200],'proof_note':form.get('proof_note','')[:1000],'upi_id':form.get('upi','')[:160],'permanent_upi_id':form.get('permanent_upi','')[:160],'demo_link':_valid_url_or_empty(form.get('demo')),'contact_link':_valid_url_or_empty(form.get('contact'))}
    for k,v in text_settings.items(): setv(k,v)
    setv('log_payment_note',text_settings['proof_note'])
    setv('approval_broadcast_note',text_settings['proof_note'])
    if form.get('remove_gateway')=='1':
        c.execute("DELETE FROM settings WHERE key IN ('payment_gateway_blob','payment_gateway_provider','payment_gateway_environment')")
    else:
        mid=form.get('gateway_mid','').strip(); merchant_key=form.get('gateway_key','').strip()
        if mid or merchant_key:
            if not mid or not merchant_key: raise ValueError('Both Merchant ID and Merchant Key are required to save gateway credentials.')
            if len(mid)>80 or len(merchant_key)>300: raise ValueError('Gateway credential field length is too long.')
            env=form.get('gateway_environment','TEST').upper()
            if env not in ('TEST','PRODUCTION'): raise ValueError('Invalid payment gateway environment.')
            payload={'mid':mid,'merchant_key':merchant_key,'website_name':(form.get('gateway_website','DEFAULT').strip() or 'DEFAULT'),'environment':env}
            instance_id=Path(row['instance_path']).parent.name
            derived=base64.urlsafe_b64encode(hmac.new(config.MASTER_INSTANCE_KEY.encode(),instance_id.encode(),hashlib.sha256).digest()).decode()
            try:
                from cryptography.fernet import Fernet
                encrypted=Fernet(derived.encode()).encrypt(json.dumps(payload).encode()).decode()
            except Exception as exc: raise ValueError('Gateway encryption failed. Check the master encryption key.') from exc
            setv('payment_gateway_blob',encrypted); setv('payment_gateway_provider','paytm'); setv('payment_gateway_environment',env)
    setv('approval_broadcast_note',text_settings['proof_note'])
    proof_channel=text_settings['proof_channel'].strip()
    if proof_channel.startswith('https://t.me/'):
        parts=proof_channel.rstrip('/').split('/')
        if len(parts)>=5 and parts[-2]=='c' and parts[-1].isdigit(): proof_channel='-100'+parts[-1]
        elif len(parts)>=4 and parts[-1] and not parts[-1].startswith('+'): proof_channel='@'+parts[-1]
        else: raise ValueError('Private/invite Telegram links are not valid log-channel targets. Use channel ID or @username.')
        setv('proof_channel',proof_channel)
    if proof_channel and not (proof_channel.startswith('@') or (proof_channel.startswith('-100') and proof_channel[4:].isdigit())): raise ValueError('Proof channel should be @channelusername or a numeric -100 chat ID')
    c.execute('CREATE TABLE IF NOT EXISTS admin_log_channels(user_id INTEGER PRIMARY KEY,channel TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    if proof_channel:
        c.execute('INSERT OR REPLACE INTO admin_log_channels(user_id,channel,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)',(int(row['admin_id']),proof_channel))
    else:
        c.execute('DELETE FROM admin_log_channels WHERE user_id=?',(int(row['admin_id']),))
    # Rebuild the builder-managed button rows to make Remove truly remove and shift rows.
    c.execute('DELETE FROM buttons WHERE btn_id BETWEEN 1 AND 30')
    c.execute('DELETE FROM menu_buttons WHERE btn_id BETWEEN 1 AND 30')
    for i in range(1,31):
        name=form.get(f'plan_name_{i}','').strip()[:60]; price=form.get(f'plan_price_{i}','0').strip() or '0'; color=form.get(f'plan_color_{i}','R')
        if not price.isdigit(): raise ValueError('Plan prices must be non-negative integers.')
        if color not in {'R','G','B'}: color='R'
        if i<=6 or name:
            if name: c.execute('INSERT OR REPLACE INTO buttons(btn_id,text,price) VALUES(?,?,?)',(i,name,int(price)))
            else: c.execute('DELETE FROM buttons WHERE btn_id=?',(i,))
            setv(f'btn_color_{i}',color)
        mn=form.get(f'menu_name_{i}','').strip()[:80]; link=_valid_url_or_empty(form.get(f'menu_link_{i}')); mcolor=form.get(f'menu_color_{i}','R')
        if mcolor not in {'R','G','B'}: mcolor='R'
        if i<=6 or mn:
            if mn: c.execute('INSERT OR REPLACE INTO menu_buttons(btn_id,text,link) VALUES(?,?,?)',(i,mn,link))
            else: c.execute('DELETE FROM menu_buttons WHERE btn_id=?',(i,))
            setv(f'menu_color_{i}',mcolor)
    c.commit(); c.close()

def _csrf_guard(): return _auth() and _check_csrf()
def _admin_username(admin_id):
    try:
        token=config.BOT_TOKEN; url=f'https://api.telegram.org/bot{token}/getChat?chat_id={urllib.parse.quote(str(admin_id))}'
        with urllib.request.urlopen(url,timeout=3) as resp: data=json.loads(resp.read().decode('utf-8'))
        return data.get('result',{}).get('username','') or ''
    except Exception: return ''
def _admin_display_name(admin_id):
    try:
        token=config.BOT_TOKEN
        url=f'https://api.telegram.org/bot{token}/getChat?chat_id={urllib.parse.quote(str(admin_id))}'
        with urllib.request.urlopen(url,timeout=3) as resp: data=json.loads(resp.read().decode('utf-8'))
        chat=data.get('result',{}); name=' '.join(x for x in (chat.get('first_name',''),chat.get('last_name','')) if x).strip()
        return ('@'+chat['username']) if chat.get('username') else (name or str(admin_id))
    except Exception: return str(admin_id)

@app.route('/',methods=['GET','POST'])
def index():
    if _auth(): return redirect(url_for('dashboard'))
    error=''
    if request.method=='POST':
        if not _check_csrf(): return 'Invalid CSRF',403
        ip=request.remote_addr or 'unknown'
        if not _login_limiter(ip): return 'Too many login attempts. Try again after 10 minutes.',429
        if _login_ok(request.form.get('username','').strip(),request.form.get('password','')):
            _LOGIN_ATTEMPTS.pop(ip,None); session.clear(); session['father_admin_authenticated']=True; session['csrf']=secrets.token_urlsafe(32); session.permanent=True; return redirect(url_for('dashboard'))
        _login_fail(ip); error='Username or password incorrect.'
    return render_template_string(LOGIN,error=error,csrf=_csrf())
@app.route('/health')
def health(): return 'ok',200
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('index'))
@app.route('/dashboard')
def dashboard():
    if not _auth(): return redirect(url_for('index'))
    bots=_bots_with_metrics(); stats=_father_stats(bots); subs=db.premium_users()
    c=db.conn(); keys=c.execute('SELECT * FROM father_premium_keys ORDER BY id DESC LIMIT 200').fetchall(); c.close()
    return render_template_string(DASH,bots=bots,stats=stats,subs=subs,keys=keys,csrf=_csrf(),messages=list(session.pop('flash_messages',[])),web_username=_current_username())
@app.post('/keys/create')
def create_premium_key():
    if not _csrf_guard(): return 'Unauthorized',403
    try:
        plan=request.form.get('plan','ELITE').strip()[:50]; users=int(request.form.get('users',1)); slots=int(request.form.get('bots',1)); days=int(request.form.get('days',30)); price=int(request.form.get('price',0))
        if not (1<=users<=10000 and 1<=slots<=100 and 1<=days<=3650 and 0<=price<=10000000): raise ValueError('Values out of range.')
        raw=db.create_premium_key(config.ADMIN_ID,plan,users,slots,days,price)
        _flash('NEW KEY (copy it now — full key is shown only at creation):\n'+raw)
    except Exception as e: _flash('Key creation failed: '+str(e)[:160])
    return redirect(url_for('dashboard')+'#keys')
@app.post('/keys/<int:key_id>/toggle')
def key_toggle(key_id):
    if not _csrf_guard(): return 'Unauthorized',403
    c=db.conn(); row=c.execute('SELECT status FROM father_premium_keys WHERE id=?',(key_id,)).fetchone()
    if row: c.execute('UPDATE father_premium_keys SET status=? WHERE id=?',('INACTIVE' if row['status']=='ACTIVE' else 'ACTIVE',key_id)); c.commit()
    c.close(); _flash('Key status updated.'); return redirect(url_for('dashboard')+'#keys')
@app.post('/premium/remove')
def remove_premium():
    if not _csrf_guard(): return 'Unauthorized',403
    try: uid=int(request.form.get('user_id',0)); ok=db.remove_premium(uid); _flash(f'Premium removed for user {uid}.' if ok else 'No active premium found for that ID.')
    except Exception: _flash('Invalid user ID.')
    return redirect(url_for('dashboard')+'#premium')
@app.post('/bots/<int:bot_id>/revoke')
def revoke_bot(bot_id):
    if not _csrf_guard(): return 'Unauthorized',403
    row=db.get_bot_by_id(bot_id)
    if row and row['status']!='REVOKED':
        try: provisioner.stop_bot(row); _flash(f'Bot @{row["bot_username"]} revoked.')
        except Exception: _flash('Bot could not be revoked; inspect runtime logs.')
    return redirect(url_for('dashboard')+'#bots')
@app.post('/login/change')
def change_login():
    if not _csrf_guard(): return 'Unauthorized',403
    username=request.form.get('username','').strip()[:60]; password=request.form.get('password',''); confirm=request.form.get('confirm','')
    if len(username)<3 or len(password)<12 or password!=confirm: _flash('Username must be 3+ chars; password 12+ chars and confirmation must match.')
    else: db.setting('father_web_username',username); db.setting('father_web_password_hash',hashlib.sha256(password.encode()).hexdigest()); _flash('Login updated. Use new credentials at next login.')
    return redirect(url_for('dashboard')+'#login')
@app.post('/login/reset')
def reset_login():
    if not _csrf_guard(): return 'Unauthorized',403
    username,password=reset_web_credentials()
    _flash(f'Generated recovery credentials (copy now): Username: {username} | Password: {password}')
    return redirect(url_for('dashboard')+'#login')
@app.post('/api/builder/password')
def builder_password_api():
    secret=os.getenv('FATHER_BUILDER_API_SECRET','') or config.MASTER_INSTANCE_KEY
    if not secret or secret.startswith('CHANGE_THIS'): return {'error':'builder API not configured'},503
    supplied=request.headers.get('X-PX9-Builder-Key','')
    if not hmac.compare_digest(supplied,secret): return {'error':'unauthorized'},401
    payload=request.get_json(silent=True) or {}; instance_id=str(payload.get('instance_id',''))
    if not instance_id or len(instance_id)>40 or any(ch not in '0123456789abcdef' for ch in instance_id.lower()): return {'error':'invalid instance'},400
    row=None
    for candidate in db.list_bots():
        try:
            if Path(candidate['instance_path']).parent.name==instance_id and candidate['status']=='RUNNING': row=candidate; break
        except Exception: continue
    if not row: return {'error':'bot unavailable'},404
    raw=secrets.token_urlsafe(14); expiry=time.time()+300
    db.setting(_builder_key(row['id'],'password_hash'),hashlib.sha256(raw.encode()).hexdigest())
    db.setting(_builder_key(row['id'],'expires'),str(expiry))
    base=(os.getenv('FATHER_WEB_URL','https://px-9v-v8-production.up.railway.app').strip().rstrip('/'))
    return {'url':f'{base}/builder/{row["id"]}','username':'ADMIN','admin_id':str(row['admin_id']),'admin_username':_admin_username(row['admin_id']),'bot_username':row['bot_username'],'password':raw,'expires_in':300}

@app.post('/bots/<int:bot_id>/builder-password')
def builder_password(bot_id):
    if not _csrf_guard(): return 'Unauthorized',403
    row=_active_bot(bot_id)
    if not row: _flash('Bot is inactive.'); return redirect(url_for('dashboard')+'#bots')
    raw=secrets.token_urlsafe(14); expiry=time.time()+300
    db.setting(_builder_key(bot_id,'password_hash'),hashlib.sha256(raw.encode()).hexdigest()); db.setting(_builder_key(bot_id,'expires'),str(expiry))
    _flash(f'Builder URL: {request.url_root.rstrip("/")}/builder/{bot_id}\nUsername: ADMIN or {row["admin_id"]}\n5-minute one-time password: {raw}')
    return redirect(url_for('dashboard')+'#bots')
@app.route('/builder/<int:bot_id>',methods=['GET','POST'])
def builder_login(bot_id):
    row=_active_bot(bot_id)
    if not row: return 'Bot inactive/not found',404
    if session.get('builder_auth_bot')==int(bot_id) and session.get('builder_session_exp',0)>time.time(): return redirect(url_for('builder_page',bot_id=bot_id))
    error=''
    if request.method=='POST':
        if not _check_csrf(): return 'Invalid CSRF',403
        ip=request.remote_addr or 'unknown'; attempt_key=f'{ip}:{bot_id}'
        bucket=[t for t in _BUILDER_ATTEMPTS.get(attempt_key,[]) if time.time()-t<600]; _BUILDER_ATTEMPTS[attempt_key]=bucket
        if len(bucket)>=5: return 'Too many login attempts. Wait 10 minutes.',429
        username=request.form.get('username','').strip(); pw=request.form.get('password','')
        expires=float(db.setting(_builder_key(bot_id,'expires')) or 0); stored=db.setting(_builder_key(bot_id,'password_hash')) or ''
        username_ok=username.upper()=='ADMIN' or username==str(row['admin_id']) or username.lstrip('@').lower()==str(row['bot_username'] or '').lower() or username.lstrip('@').lower()==_admin_username(row['admin_id']).lower()
        if username_ok and expires>time.time() and stored and hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(),stored):
            _BUILDER_ATTEMPTS.pop(attempt_key,None)
            session['builder_auth_bot']=int(bot_id); session['builder_session_exp']=time.time()+1800; session['csrf']=secrets.token_urlsafe(32); session.permanent=True
            db.setting(_builder_key(bot_id,'password_hash'),''); db.setting(_builder_key(bot_id,'expires'),'0'); return redirect(url_for('builder_page',bot_id=bot_id))
        bucket.append(time.time()); _BUILDER_ATTEMPTS[attempt_key]=bucket
        error='Invalid username/password or the five-minute password has expired.'
    return render_template_string(BUILDER_LOGIN,error=error,csrf=_csrf(),bot_username=row['bot_username'],admin_id=row['admin_id'])
@app.route('/builder/<int:bot_id>/setup')
def builder_page(bot_id):
    if session.get('builder_auth_bot')!=int(bot_id) or session.get('builder_session_exp',0)<=time.time(): return redirect(url_for('builder_login',bot_id=bot_id))
    row=_active_bot(bot_id)
    if not row: return 'Bot inactive/not found',404
    try: s,plans,menu,stats=_builder_read(row)
    except Exception as e: return 'Bot database read failed: '+html.escape(str(e)),500
    try:
        from provisioner import _payment_gateway_status as _x
    except Exception: pass
    gateway=(f"Configured (encrypted · {s.get('payment_gateway_environment','unknown')})" if s.get('payment_gateway_blob') else 'Not configured')
    return render_template_string(BUILDER,bot_id=bot_id,bot_username=row['bot_username'],admin_id=row['admin_id'],admin_name=_admin_display_name(row['admin_id']),stats=stats,theme=s.get('selected_theme','1'),restrict=s.get('restrict_content','0'),welcome_type=s.get('welcome_media_type','none'),welcome_url=s.get('welcome_media_url',''),welcome_text=s.get('welcome_text',''),welcome_delete=s.get('welcome_auto_delete','0'),premium_type=s.get('premium_media_type','none'),premium_url=s.get('premium_media_url',''),premium_text=s.get('premium_text',''),approve_type=s.get('approval_media_type','none'),approve_url=s.get('approval_media_url',''),approve_text=s.get('approval_text',''),proof_channel=s.get('proof_channel',''),proof_note=s.get('proof_note',''),upi=s.get('upi_id',''),permanent_upi=s.get('permanent_upi_id',''),demo=s.get('demo_link',''),contact=s.get('contact_link',''),plans=plans,menu=menu,gateway_status=gateway,csrf=_csrf(),messages=list(session.pop('builder_flash',[])))
@app.post('/builder/<int:bot_id>/save')
def builder_save(bot_id):
    if session.get('builder_auth_bot')!=int(bot_id) or session.get('builder_session_exp',0)<=time.time(): return redirect(url_for('builder_login',bot_id=bot_id))
    if not _check_csrf(): return 'Invalid CSRF',403
    row=_active_bot(bot_id)
    if not row: return 'Bot inactive/not found',404
    try: _builder_write(row,request.form); session['builder_flash']=['Saved configuration for this bot. Some legacy media workflows still use Telegram file IDs; URL media fields are stored for the new web configuration.']
    except Exception as e: session['builder_flash']=['Save failed: '+str(e)[:180]]
    return redirect(url_for('builder_page',bot_id=bot_id))
@app.post('/builder/<int:bot_id>/password-change')
def builder_password_change(bot_id):
    if session.get('builder_auth_bot')!=int(bot_id) or session.get('builder_session_exp',0)<=time.time(): return redirect(url_for('builder_login',bot_id=bot_id))
    if not _check_csrf(): return 'Invalid CSRF',403
    row=_active_bot(bot_id)
    if not row: return 'Bot inactive/not found',404
    raw=secrets.token_urlsafe(14); db.setting(_builder_key(bot_id,'password_hash'),hashlib.sha256(raw.encode()).hexdigest()); db.setting(_builder_key(bot_id,'expires'),str(time.time()+300))
    session['builder_flash']=[f'New one-time login password (5 minutes): {raw}. Use ADMIN or {row["admin_id"]}.']
    return redirect(url_for('builder_page',bot_id=bot_id)+'#password')

@app.route('/builder/<int:bot_id>/logout')
def builder_logout(bot_id):
    if session.get('builder_auth_bot')==int(bot_id):
        session.pop('builder_auth_bot',None); session.pop('builder_session_exp',None)
    return redirect(url_for('builder_login',bot_id=bot_id))

def run_webpanel():
    pw=_password()
    if not pw: print('Father web panel disabled (FATHER_WEB_PASSWORD not set).'); return
    if len(pw)<12: print('WARNING: FATHER_WEB_PASSWORD should be at least 12 characters.')
    if not app.secret_key:
        key=config.MASTER_INSTANCE_KEY
        if not key or key.startswith('CHANGE_THIS'): raise RuntimeError('Set FATHER_WEB_SECRET or a strong MASTER_INSTANCE_KEY before enabling web panel.')
        app.secret_key=hashlib.sha256((key+'father-web-session').encode()).hexdigest()
    port=int(os.getenv('PORT','8080')); print(f'Father web panel listening on 0.0.0.0:{port}'); serve(app,host='0.0.0.0',port=port,threads=8)
def start_webpanel_thread():
    if not _password(): return None
    return threading.Thread(target=run_webpanel,daemon=True,name='father-webpanel').start()
