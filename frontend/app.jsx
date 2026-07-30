/* ============ APP SHELL + ROUTING + TWEAKS ============ */
const { useState:uS } = React;

const ACCENTS = {
  'Сине-стальной': 250,
  'Индиго':        272,
  'Бирюзовый':     200,
  'Графит':        255,
};
const ACCENT_CHROMA = { 'Графит':0.03 };

function applyAccent(root, name, theme){
  const h = ACCENTS[name] ?? 250;
  const c = ACCENT_CHROMA[name] ?? 0.13;
  const dark = theme === 'dark';
  root.style.setProperty('--accent',        `oklch(0.57 ${c} ${h})`);
  root.style.setProperty('--accent-strong',  dark ? `oklch(0.75 ${c} ${h})` : `oklch(0.47 ${c+0.01} ${h})`);
  root.style.setProperty('--accent-soft',    dark ? `oklch(0.27 ${Math.min(c*0.65,0.085)} ${h})` : `oklch(0.95 ${Math.min(c*0.25,0.04)} ${h})`);
  root.style.setProperty('--accent-softer',  dark ? `oklch(0.21 ${Math.min(c*0.45,0.06)} ${h})` : `oklch(0.975 ${Math.min(c*0.15,0.022)} ${h})`);
  root.style.setProperty('--accent-ring',    `oklch(0.57 ${c} ${h} / 0.35)`);
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "Сине-стальной",
  "density": "regular",
  "nav": "sidebar",
  "radius": 12,
  "theme": "light"
}/*EDITMODE-END*/;

const NAV = {
  admin:[
    { group:'Основное', items:[
      { id:'profile',   label:'Профиль',   icon:'user'     },
      { id:'timesheet', label:'Таймшит',   icon:'calendar' },
      { id:'manager',   label:'Управление',icon:'users'    },
      { id:'reports',   label:'Отчётность',icon:'chart'    },
    ]},
    { group:'Сервисы', items:[
      { id:'docs',     label:'Документы',  icon:'fileText' },
      { id:'absences', label:'Отсутствия', icon:'calendar' },
      { id:'chat',     label:'Чат',        icon:'chat'     },
    ]},
    { group:'Администрирование', items:[
      { id:'admin', label:'Панель администратора', icon:'shield' },
    ]},
  ],
  employee:[
    { group:'Основное', items:[
      { id:'profile',   label:'Профиль',   icon:'user' },
      { id:'timesheet', label:'Таймшит',   icon:'calendar' },
    ]},
    { group:'Сервисы', items:[
      { id:'docs',     label:'Документы',  icon:'fileText' },
      { id:'absences', label:'Отсутствия', icon:'calendar' },
      { id:'chat',     label:'Чат',        icon:'chat'     },
    ]},
  ],
  manager:[
    { group:'Основное', items:[
      { id:'profile',   label:'Профиль',   icon:'user' },
      { id:'timesheet', label:'Таймшит',   icon:'calendar' },
      { id:'manager',   label:'Управление',icon:'users' },
      { id:'reports',   label:'Отчётность',icon:'chart' },
    ]},
    { group:'Сервисы', items:[
      { id:'docs',     label:'Документы',  icon:'fileText' },
      { id:'absences', label:'Отсутствия', icon:'calendar' },
      { id:'chat',     label:'Чат',        icon:'chat'     },
    ]},
  ],
};

/* ---- Уведомления: маппинг ответа notification_service под панель ---- */
// Бэк не заполняет target_url — экран (и вкладку внутри Управления) выводим из типа/заголовка
function notifTargetFor(n){
  if(n.type==='PASSWORD') return { screen:'manager', tab:'team' };
  if(n.type==='DOC') return { screen:'docs' };
  const t=n.title;
  if(t==='Табель на согласовании'||t==='Переработка на согласовании') return { screen:'manager', tab:'approvals' };
  if(t.startsWith('Табель')) return { screen:'timesheet' };
  if(t==='Заявка на отсутствие'||t.startsWith('Отсутствие')) return { screen:'absences' };
  return null;
}
function notifRelTime(iso){
  // naive UTC без зоны парсился бы как локальное время
  const d=new Date(/[Zz]$|[+-]\d\d:\d\d$/.test(iso)?iso:iso+'Z');
  const diff=(Date.now()-d.getTime())/60000;
  if(diff<1) return 'только что';
  if(diff<60) return Math.floor(diff)+' мин назад';
  if(diff<24*60) return Math.floor(diff/60)+' ч назад';
  return d.toLocaleDateString('ru',{day:'numeric',month:'short'});
}
function mapNotif(n){
  const d=new Date(/[Zz]$|[+-]\d\d:\d\d$/.test(n.created_at)?n.created_at:n.created_at+'Z');
  return { id:n.id, type:n.type.toLowerCase(), title:n.title, text:n.text,
    time:notifRelTime(n.created_at), read:n.is_read,
    today:d.toDateString()===new Date().toDateString(), target:notifTargetFor(n) };
}

function App(){
  const [t,setTweak]=useTweaks(TWEAK_DEFAULTS);
  // Сессия восстанавливается из сохранённого JWT
  const [authed,setAuthed]=uS(()=>!!API.session());
  const [role,setRole]=uS(()=>API.uiRole());
  const [screen,setScreen]=uS(()=>{ const r=API.uiRole(); return r==='manager'?'manager':r==='admin'?'admin':'profile'; });
  const [managerNav,setManagerNav]=uS(null); // {tab, nonce} — переход из уведомления на конкретную вкладку Управления
  const [userMenu,setUserMenu]=uS(false);
  const [notifOpen,setNotifOpen]=uS(false);
  const [notifs,setNotifs]=uS([]);
  const [toastNode,showToast]=useToast();
  const [sidebarOpen,setSidebarOpen]=uS(()=>{ try{ return JSON.parse(localStorage.getItem('_sb')??'true'); }catch{ return true; } });
  const [mobileOpen,setMobileOpen]=uS(false);
  const [isMobile,setIsMobile]=uS(()=>typeof window!=='undefined'&&window.innerWidth<768);
  useEffect(()=>{ localStorage.setItem('_sb',JSON.stringify(sidebarOpen)); },[sidebarOpen]);
  useEffect(()=>{ const h=()=>setIsMobile(window.innerWidth<768); window.addEventListener('resize',h); return ()=>window.removeEventListener('resize',h); },[]);
  useEffect(()=>{ if(!isMobile) setMobileOpen(false); },[isMobile]);
  // api.js шлёт ts:logout, когда сессия протухла и refresh не помог
  useEffect(()=>{ const h=()=>setAuthed(false); window.addEventListener('ts:logout',h); return ()=>window.removeEventListener('ts:logout',h); },[]);

  // Живые данные для шапки и сайдбара
  const [liveMe,setLiveMe]=uS(null);
  const [liveSummary,setLiveSummary]=uS(null);
  useEffect(()=>{
    if(!authed){ setLiveMe(null); setLiveSummary(null); return; }
    const s=API.session(); if(!s) return;
    let alive=true;
    API.profile.getEmployee(s.userId).then(e=>{ if(alive) setLiveMe(e); }).catch(()=>{});
    API.timesheet.getSummary(s.userId).then(sm=>{ if(alive) setLiveSummary(sm); }).catch(()=>{});
    return ()=>{ alive=false; };
  },[authed]);

  // Живые уведомления: загрузка при входе и открытии панели + поллинг раз в 60с
  const loadNotifs=()=>API.notification.getAll().then(list=>setNotifs(list.map(mapNotif))).catch(()=>{});
  useEffect(()=>{
    if(!authed){ setNotifs([]); return; }
    loadNotifs();
    const timer=setInterval(loadNotifs, 60000);
    return ()=>clearInterval(timer);
  },[authed]);
  useEffect(()=>{ if(notifOpen) loadNotifs(); },[notifOpen]);

  const unreadCount=notifs.filter(n=>!n.read).length;
  const readAll=()=>{ setNotifs(ns=>ns.map(n=>({...n,read:true}))); API.notification.markAllRead().catch(()=>{}); };
  const readOne=(id)=>{ setNotifs(ns=>ns.map(n=>n.id===id?{...n,read:true}:n)); API.notification.markRead(id).catch(()=>{}); };
  const openNotif=(target)=>{
    setNotifOpen(false);
    if(!target) return;
    setScreen(target.screen);
    // nonce — чтобы переключение вкладки сработало, даже если Управление уже открыто на другой вкладке
    if(target.tab) setManagerNav({ tab:target.tab, nonce:Date.now() });
  };

  // apply tweaks to root
  useEffect(()=>{
    const r=document.documentElement;
    applyAccent(r, t.accent, t.theme);
    r.setAttribute('data-theme', t.theme);
    r.setAttribute('data-density', t.density);
    r.style.setProperty('--radius', t.radius+'px');
    r.style.setProperty('--radius-sm', Math.max(t.radius-4,4)+'px');
    r.style.setProperty('--radius-lg', (t.radius+4)+'px');
  },[t.accent,t.density,t.radius,t.theme]);

  const login=(r)=>{ setRole(r); setScreen(r==='manager'?'manager':r==='admin'?'admin':'profile'); setAuthed(true); };
  const logout=()=>{ setAuthed(false); setUserMenu(false); API.auth.logout(); };
  const me=DB.emp(DB.currentUserId);
  const sess=API.session();
  const disp=liveMe
    ? { id:liveMe.id, name:`${liveMe.first_name} ${liveMe.last_name}`, email:liveMe.user.email, imageUrl:liveMe.image_url }
    : { id:sess?.userId, name:sess?.email||'…', email:sess?.email||'', imageUrl:null };
  const monthBadge=(()=>{ const s=new Date().toLocaleDateString('ru',{month:'long',year:'numeric'}).replace(' г.',''); return s.charAt(0).toUpperCase()+s.slice(1); })();
  const items=NAV[role];
  const collapsed = !isMobile && !sidebarOpen;
  const navGo=(id)=>{ setScreen(id); if(isMobile) setMobileOpen(false); };

  if(!authed){
    return (<>
      <LoginScreen onLogin={login}/>
      <TweaksUI t={t} setTweak={setTweak}/>
    </>);
  }

  const screens={
    profile:   <ProfileScreen userId={sess?.userId} onNav={setScreen} showToast={showToast}/>,
    admin:     <AdminScreen showToast={showToast}/>,
    timesheet: <TimesheetScreen userId={sess?.userId} role={role} showToast={showToast}/>,
    manager:   <ManagerScreen showToast={showToast} onNav={setScreen} navTab={managerNav}/>,
    reports:   <ReportsScreen showToast={showToast}/>,
    docs:      <DocsScreen showToast={showToast}/>,
    chat:      <ChatScreen showToast={showToast}/>,
    absences:  <AbsencesScreen userId={sess?.userId} isManager={role==='manager'||role==='admin'} showToast={showToast}/>,
    settings:  <SettingsScreen t={t} setTweak={setTweak} userId={sess?.userId} showToast={showToast}/>,
  };

  const sidebarStyle = isMobile ? {
    position:'fixed', top:0, left:0, height:'100%', zIndex:200,
    transform: mobileOpen?'translateX(0)':'translateX(-100%)',
    transition:'transform .25s cubic-bezier(.4,0,.2,1)',
    boxShadow: mobileOpen?'var(--shadow-lg)':'none',
    width:248, padding:'18px 14px',
  } : {
    width: sidebarOpen?228:72,
    transition:'width .22s cubic-bezier(.4,0,.2,1)',
    padding: sidebarOpen?'18px 14px':'18px 10px',
  };

  return (
    <div style={{display:'flex', height:'100%', overflow:'hidden'}}>
      {/* mobile backdrop */}
      {isMobile && mobileOpen && <div onClick={()=>setMobileOpen(false)} style={{position:'fixed',inset:0,zIndex:199,background:'oklch(0.18 0.02 255 / 0.55)',backdropFilter:'blur(3px)'}}/>}

      {/* sidebar */}
      <aside style={{flex:'none', minWidth:0, background:'var(--surface)', borderRight:'1px solid var(--border)',
        display:'flex', flexDirection:'column', overflow:'hidden', ...sidebarStyle}}>

        {/* header: logo + collapse toggle */}
        <div style={{display:'flex', alignItems:'center', justifyContent:collapsed?'center':'space-between', marginBottom:16, minHeight:36, gap:6}}>
          {!collapsed && <Logo/>}
          {!isMobile && (
            <button onClick={()=>setSidebarOpen(o=>!o)} title={sidebarOpen?'Свернуть':'Развернуть'}
              style={{width:30,height:30,border:'none',borderRadius:8,background:'transparent',cursor:'pointer',
                display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text-3)',flexShrink:0,transition:'.14s'}}
              onMouseEnter={e=>e.currentTarget.style.background='var(--surface-2)'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <Icon d={IC[sidebarOpen?'chevL':'chevR']} size={15}/>
            </button>
          )}
          {isMobile && <Logo/>}
        </div>

        <nav style={{display:'flex', flexDirection:'column', gap:3}}>
          {items.map((grp,gi)=>(
            <div key={gi} style={{marginTop:gi?12:0}}>
              {!collapsed && <div className="muted" style={{fontSize:10.5,fontWeight:700,letterSpacing:'.06em',textTransform:'uppercase',padding:'8px 10px 4px'}}>{grp.group}</div>}
              {collapsed && gi>0 && <div className="divider" style={{margin:'6px 8px 8px'}}/>}
              {grp.items.map(it=>{
                const on=screen===it.id;
                return (
                  <button key={it.id} onClick={()=>navGo(it.id)} title={collapsed?it.label:''}
                    style={{display:'flex',alignItems:'center',gap:11,padding:collapsed?'10px':'9px 11px',
                      justifyContent:collapsed?'center':'flex-start',border:'none',borderRadius:9,cursor:'pointer',
                      fontSize:13.5,fontWeight:600,width:'100%',position:'relative',
                      background:on?'var(--accent-soft)':'transparent',color:on?'var(--accent-strong)':'var(--text-2)',
                      transition:'.13s',whiteSpace:'nowrap',overflow:'hidden'}}
                    onMouseEnter={e=>{ if(!on) e.currentTarget.style.background='var(--surface-2)'; }}
                    onMouseLeave={e=>{ if(!on) e.currentTarget.style.background='transparent'; }}>
                    <span style={{position:'relative',display:'flex',flexShrink:0}}>
                      <Icon d={IC[it.icon]} size={18} stroke={on?2.1:1.8}/>
                      {collapsed && it.badge && <span style={{position:'absolute',top:-5,right:-7,minWidth:15,height:15,padding:'0 3px',borderRadius:8,background:'var(--accent)',color:'#fff',fontSize:9.5,fontWeight:700,display:'flex',alignItems:'center',justifyContent:'center',border:'2px solid var(--surface)'}}>{it.badge}</span>}
                    </span>
                    {!collapsed && <span style={{flex:1,textAlign:'left'}}>{it.label}</span>}
                    {!collapsed && it.badge && <span style={{minWidth:18,height:18,padding:'0 5px',borderRadius:9,background:on?'var(--accent)':'var(--surface-3)',color:on?'#fff':'var(--text-2)',fontSize:11,fontWeight:700,display:'flex',alignItems:'center',justifyContent:'center'}}>{it.badge}</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div style={{flex:1}}/>
        <button onClick={()=>navGo('settings')} title={collapsed?'Настройки':''}
          style={{display:'flex',alignItems:'center',gap:11,padding:collapsed?'10px':'9px 11px',
            justifyContent:collapsed?'center':'flex-start',border:'none',borderRadius:9,cursor:'pointer',
            fontSize:13.5,fontWeight:600,width:'100%',marginBottom:6,whiteSpace:'nowrap',overflow:'hidden',
            background:screen==='settings'?'var(--accent-soft)':'transparent',
            color:screen==='settings'?'var(--accent-strong)':'var(--text-3)',transition:'.13s'}}
          onMouseEnter={e=>{ if(screen!=='settings') e.currentTarget.style.background='var(--surface-2)'; }}
          onMouseLeave={e=>{ if(screen!=='settings') e.currentTarget.style.background='transparent'; }}>
          <Icon d={IC.settings} size={17}/>
          {!collapsed && 'Настройки'}
        </button>
        {!collapsed && liveSummary && (
          <div className="card" style={{padding:12,background:'var(--surface-2)',marginBottom:10}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:7}}>
              <span className="muted" style={{fontSize:11.5,fontWeight:600}}>Норма месяца</span>
              <span className="mono" style={{fontSize:11.5,fontWeight:700,color:'var(--accent-strong)'}}>{Number(liveSummary.logged_hours)}/{Number(liveSummary.norm_hours)}</span>
            </div>
            <div className="progress"><span style={{width:Math.min(Number(liveSummary.logged_hours)/Math.max(Number(liveSummary.norm_hours),1)*100,100)+'%'}}/></div>
          </div>
        )}
      </aside>

      {/* main */}
      <div style={{flex:1, display:'flex', flexDirection:'column', minWidth:0}}>
        {/* topbar */}
        <header style={{height:60, flex:'none', borderBottom:'1px solid var(--border)', background:'var(--surface)',
          display:'flex', alignItems:'center', gap:16, padding:'0 24px'}}>
          {isMobile && <button className="btn ghost icon" onClick={()=>setMobileOpen(o=>!o)} style={{flexShrink:0}}><Icon d={IC.menu} size={20}/></button>}
          <div style={{position:'relative', width:300, maxWidth:'34vw'}}>
            <span style={{position:'absolute', left:11, top:9, color:'var(--text-3)'}}><Icon d={IC.search} size={17}/></span>
            <input className="input" style={{height:36, paddingLeft:36, fontSize:13, background:'var(--surface-2)', border:'1px solid var(--border)'}} placeholder="Поиск по проектам и сотрудникам…"/>
          </div>
          <div style={{flex:1}}/>
          <span className="badge" style={{height:30}}><Icon d={IC.calendar} size={14}/>{monthBadge}</span>
          <div style={{position:'relative'}}>
            <button onClick={()=>{ setNotifOpen(o=>!o); setUserMenu(false); }} className="btn icon" style={{position:'relative', width:38, height:38, border:'1px solid var(--border)', background: notifOpen?'var(--surface-2)':'var(--surface)'}} title="Уведомления">
              <Icon d={IC.bell} size={18}/>
              {unreadCount>0 && <span style={{position:'absolute', top:-5, right:-5, minWidth:17, height:17, padding:'0 4px', borderRadius:9, background:'var(--red)', color:'#fff', fontSize:10.5, fontWeight:700, display:'flex', alignItems:'center', justifyContent:'center', border:'2px solid var(--surface)'}}>{unreadCount}</span>}
            </button>
            {notifOpen && <NotificationsPanel items={notifs} onNavigate={openNotif} onReadAll={readAll} onRead={readOne} onClose={()=>setNotifOpen(false)}/>}
          </div>

          <div style={{position:'relative'}}>
            <button onClick={()=>{ setUserMenu(o=>!o); setNotifOpen(false); }} style={{display:'flex', alignItems:'center', gap:9, padding:'4px 8px 4px 4px', border:'1px solid var(--border)', borderRadius:999, background:'var(--surface)', cursor:'pointer'}}>
              <Avatar id={disp.id} name={disp.name} size={30} imageUrl={disp.imageUrl}/>
              <div style={{textAlign:'left', lineHeight:1.15}}>
                <div style={{fontSize:12.5, fontWeight:700}}>{disp.name.split(' ')[0]}</div>
                <div className="muted" style={{fontSize:10.5}}>{role==='manager'?'Менеджер':role==='admin'?'Администратор':'Сотрудник'}</div>
              </div>
              <Icon d={IC.chevD} size={15} style={{color:'var(--text-3)'}}/>
            </button>
            {userMenu && (
              <div className="card fade-in" style={{position:'absolute', top:'100%', right:0, marginTop:8, width:240, zIndex:60, boxShadow:'var(--shadow-lg)', padding:8}}>
                <div style={{padding:'8px 10px 10px', display:'flex', gap:10, alignItems:'center', borderBottom:'1px solid var(--border)', marginBottom:6}}>
                  <Avatar id={disp.id} name={disp.name} size={38} imageUrl={disp.imageUrl}/>
                  <div style={{minWidth:0}}><div style={{fontWeight:700, fontSize:13.5}}>{disp.name}</div><div className="muted" style={{fontSize:11.5, overflow:'hidden', textOverflow:'ellipsis'}}>{disp.email}</div></div>
                </div>
                <button onClick={()=>{setScreen('profile');setUserMenu(false);}} style={menuRow}><Icon d={IC.user} size={16}/>Мой профиль</button>
                <button onClick={()=>{setScreen('settings');setUserMenu(false);}} style={menuRow}><Icon d={IC.settings} size={16}/>Настройки</button>
                <div className="divider" style={{margin:'6px 0'}}/>
                <button onClick={logout} style={{...menuRow, color:'var(--red)'}}><Icon d={IC.logout} size={16}/>Выйти</button>
              </div>
            )}
          </div>
        </header>

        {/* content */}
        <main style={{flex:1, overflowY:'auto', padding:'24px 28px 40px'}}>
          <div style={{maxWidth:1240, margin:'0 auto'}}>
            {screens[screen]}
          </div>
        </main>
      </div>

      {toastNode}
      {userMenu && <div onClick={()=>setUserMenu(false)} style={{position:'fixed', inset:0, zIndex:50}}/>}
      {notifOpen && <div onClick={()=>setNotifOpen(false)} style={{position:'fixed', inset:0, zIndex:50}}/>}
      <TweaksUI t={t} setTweak={setTweak}/>
    </div>
  );
}

const menuRow={ display:'flex', alignItems:'center', gap:11, width:'100%', padding:'9px 10px', border:'none', background:'transparent', borderRadius:8, cursor:'pointer', fontSize:13, fontWeight:600, color:'var(--text-2)', textAlign:'left' };

function TweaksUI({ t, setTweak }){
  return (
    <TweaksPanel title="Tweaks">
      <TweakSection label="Тема" />
      <TweakRadio label="Режим" value={t.theme} options={['light','dark']} onChange={v=>setTweak('theme',v)}/>
      <TweakSection label="Акцент" />
      <TweakRadio label="Палитра" value={t.accent} options={Object.keys(ACCENTS)} onChange={v=>setTweak('accent',v)}/>
      <TweakSection label="Раскладка" />
      <TweakRadio label="Плотность" value={t.density} options={['regular','compact']} onChange={v=>setTweak('density',v)}/>
      <TweakSlider label="Скругление" value={t.radius} min={4} max={18} step={1} unit="px" onChange={v=>setTweak('radius',v)}/>
    </TweaksPanel>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
