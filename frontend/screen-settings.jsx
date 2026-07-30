/* ============ SCREEN: Настройки — живые данные (profile/notification/auth) ============ */
const ACCENTS_KEYS = ['Сине-стальной','Индиго','Бирюзовый','Графит'];
const ACCENT_HUES  = { 'Сине-стальной':250,'Индиго':272,'Бирюзовый':200,'Графит':255 };
const ACCENT_CHROMA2={ 'Графит':0.03 };

function SettingsScreen({ t, setTweak, userId, showToast }){
  const [tab,setTab]=useState('profile');

  const tabs=[
    { id:'profile',  label:'Профиль',       icon:'user'     },
    { id:'notif',    label:'Уведомления',    icon:'bell'     },
    { id:'appear',   label:'Оформление',     icon:'grid'     },
    { id:'security', label:'Безопасность',   icon:'shield'   },
  ];

  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <PageHead title="Настройки" subtitle="Персональные настройки аккаунта и интерфейса"/>

      <div style={{display:'grid', gridTemplateColumns:'220px 1fr', gap:18, alignItems:'start'}}>
        {/* left nav */}
        <div className="card" style={{padding:8}}>
          {tabs.map(tb=>{
            const on=tab===tb.id;
            return (
              <button key={tb.id} onClick={()=>setTab(tb.id)} style={{display:'flex', alignItems:'center', gap:11, padding:'10px 12px',
                width:'100%', border:'none', borderRadius:9, cursor:'pointer', fontSize:13.5, fontWeight:600,
                background: on?'var(--accent-soft)':'transparent', color: on?'var(--accent-strong)':'var(--text-2)', transition:'.13s', textAlign:'left'}}
                onMouseEnter={e=>{ if(!on) e.currentTarget.style.background='var(--surface-2)'; }}
                onMouseLeave={e=>{ if(!on) e.currentTarget.style.background='transparent'; }}>
                <Icon d={IC[tb.icon]} size={17} stroke={on?2.1:1.8}/>
                {tb.label}
              </button>
            );
          })}
        </div>

        {/* content */}
        <div>
          {tab==='profile'  && <ProfileTab userId={userId} showToast={showToast}/>}
          {tab==='notif'    && <NotifTab showToast={showToast}/>}
          {tab==='appear'   && <AppearTab t={t} setTweak={setTweak} showToast={showToast}/>}
          {tab==='security' && <SecurityTab showToast={showToast}/>}
        </div>
      </div>
    </div>
  );
}

/* ---- toggle ---- */
function Toggle({ value, onChange }){
  return (
    <button onClick={()=>onChange(!value)} style={{width:42, height:24, borderRadius:999, border:'none', cursor:'pointer', flexShrink:0,
      background: value?'var(--accent)':'var(--surface-3)', position:'relative', transition:'background .2s', padding:0}}>
      <span style={{width:18, height:18, borderRadius:50, background:'var(--surface)', position:'absolute', top:3,
        left: value?21:3, transition:'left .2s', boxShadow:'var(--shadow-sm)'}}/>
    </button>
  );
}

function ToggleRow({ label, sub, value, onChange }){
  return (
    <div style={{display:'flex', alignItems:'center', gap:14}}>
      <div style={{flex:1}}>
        <div style={{fontWeight:600, fontSize:14}}>{label}</div>
        {sub && <div className="muted" style={{fontSize:12.5, marginTop:2}}>{sub}</div>}
      </div>
      <Toggle value={value} onChange={onChange}/>
    </div>
  );
}

/* ---- Skills Editor: только навыки из каталога (бэк принимает skill_ids) ---- */
function SkillsEditor({ skills, catalog, onChange }){
  const [q,setQ]=useState('');
  const [open,setOpen]=useState(false);
  const inputRef=useRef(null);

  const suggestions=useMemo(()=>{
    const have=new Set(skills.map(s=>s.id));
    const lo=q.trim().toLowerCase();
    return catalog.filter(s=>!have.has(s.id)&&(!lo||s.name.toLowerCase().includes(lo))).slice(0,10);
  },[q,skills,catalog]);

  const add=(skill)=>{ onChange([...skills, skill]); setQ(''); inputRef.current?.focus(); };
  const remove=(s)=>onChange(skills.filter(x=>x.id!==s.id));

  return (
    <div style={{position:'relative'}}>
      <div onClick={()=>{ setOpen(true); inputRef.current?.focus(); }}
        style={{minHeight:42, padding:'6px 8px', border:'1px solid var(--border-strong)', borderRadius:'var(--radius-sm)',
          background:'var(--surface)', display:'flex', flexWrap:'wrap', gap:6, alignItems:'center', cursor:'text'}}>
        {skills.map(s=>(
          <span key={s.id} style={{display:'inline-flex', alignItems:'center', gap:5, height:26, padding:'0 8px 0 10px',
            borderRadius:999, background:'var(--accent-soft)', color:'var(--accent-strong)', fontSize:12.5, fontWeight:600, whiteSpace:'nowrap'}}>
            {s.name}
            <button onClick={e=>{ e.stopPropagation(); remove(s); }}
              style={{width:16,height:16,borderRadius:50,border:'none',background:'var(--accent-softer)',
                color:'var(--accent-strong)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',padding:0}}>
              <Icon d={IC.x} size={10} stroke={2.5}/>
            </button>
          </span>
        ))}
        <input ref={inputRef} value={q} onChange={e=>{ setQ(e.target.value); setOpen(true); }}
          onKeyDown={e=>{ if(e.key==='Backspace'&&!q&&skills.length) remove(skills[skills.length-1]); else if(e.key==='Escape'){ setOpen(false); setQ(''); } }}
          onFocus={()=>setOpen(true)} onBlur={()=>setTimeout(()=>setOpen(false),150)}
          placeholder={skills.length?'':'Выберите навыки из справочника…'}
          style={{border:'none', outline:'none', background:'transparent', fontSize:13.5, minWidth:160, flex:1, padding:'2px 4px'}}/>
      </div>

      {open && suggestions.length>0 && (
        <div className="card fade-in" style={{position:'absolute', top:'100%', left:0, right:0, zIndex:40, marginTop:4,
          boxShadow:'var(--shadow-lg)', padding:6, maxHeight:240, overflowY:'auto'}}>
          {!q.trim() && <div className="muted" style={{fontSize:11, fontWeight:700, letterSpacing:'.05em', textTransform:'uppercase', padding:'4px 10px 6px'}}>Из справочника</div>}
          {suggestions.map(s=>(
            <button key={s.id} onMouseDown={e=>{ e.preventDefault(); add(s); }}
              style={{display:'flex',alignItems:'center',gap:9,width:'100%',padding:'8px 10px',border:'none',
                background:'transparent',borderRadius:8,cursor:'pointer',fontSize:13.5,textAlign:'left',color:'var(--text)'}}
              onMouseEnter={e=>e.currentTarget.style.background='var(--surface-2)'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <Icon d={IC.plus} size={14} style={{color:'var(--accent)',flexShrink:0}}/>{s.name}
            </button>
          ))}
        </div>
      )}
      <div className="muted" style={{fontSize:11.5, marginTop:6}}>Навыки выбираются из общего справочника компании</div>
    </div>
  );
}

/* ---- Profile tab: свой профиль (PATCH) + навыки (PUT) ---- */
function ProfileTab({ userId, showToast }){
  const [emp,setEmp]=useState(null);
  const [catalog,setCatalog]=useState([]);
  const [error,setError]=useState(null);
  const [form,setForm]=useState(null);
  const [skills,setSkills]=useState([]);
  const [saving,setSaving]=useState(false);

  useEffect(()=>{
    Promise.all([ API.profile.getEmployee(userId), API.profile.getSkills().catch(()=>[]) ])
      .then(([p, cat])=>{
        setEmp(p); setCatalog(cat); setSkills(p.skills||[]);
        setForm({
          first_name:p.first_name||'', last_name:p.last_name||'', phone:p.phone||'',
          address:p.address||'', birthday:p.birthday||'', position:p.position||'',
        });
      })
      .catch(err=>setError(err.detail||'Не удалось загрузить профиль'));
  },[userId]);

  if(error) return <ErrorCard text={error}/>;
  if(!emp||!form) return <div className="card" style={{padding:28}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:44,marginBottom:12}}/>)}</div>;

  const set=(k,v)=>setForm(f=>({...f,[k]:v}));
  const name=`${emp.first_name} ${emp.last_name}`;

  const saveProfile=async(e)=>{
    e.preventDefault();
    if(!form.first_name.trim()||!form.last_name.trim()){ showToast('Имя и фамилия обязательны'); return; }
    setSaving(true);
    try{
      const upd=await API.profile.updateEmployee(userId, {
        first_name:form.first_name.trim(),
        last_name:form.last_name.trim(),
        phone:form.phone.trim()||null,
        address:form.address.trim()||null,
        birthday:form.birthday||null,
        position:form.position.trim()||null,
      });
      setEmp(upd);
      showToast('Профиль сохранён');
    }catch(err){ showToast(err.detail||'Не удалось сохранить профиль'); }
    finally{ setSaving(false); }
  };
  const saveSkills=async()=>{
    setSaving(true);
    try{
      await API.profile.updateSkills(userId, skills.map(s=>s.id));
      showToast('Навыки сохранены');
    }catch(err){ showToast(err.detail||'Не удалось сохранить навыки'); }
    finally{ setSaving(false); }
  };

  return (
    <div style={{display:'flex', flexDirection:'column', gap:14}}>
      <div className="card" style={{padding:28}}>
        <SectionTitle title="Личные данные"/>
        <div style={{display:'flex', gap:20, alignItems:'flex-start', marginTop:20}}>
          <Avatar id={emp.id} name={name} size={80} imageUrl={emp.image_url}/>
          <form onSubmit={saveProfile} style={{flex:1, display:'grid', gridTemplateColumns:'1fr 1fr', gap:16}}>
            <Field label="Имя *">
              <input className="input" value={form.first_name} onChange={e=>set('first_name',e.target.value)} placeholder="Иван"/>
            </Field>
            <Field label="Фамилия *">
              <input className="input" value={form.last_name} onChange={e=>set('last_name',e.target.value)} placeholder="Иванов"/>
            </Field>
            <Field label="Рабочая почта">
              <input className="input" value={emp.user.email} disabled style={{opacity:.6,cursor:'not-allowed'}} title="Почта задаётся при регистрации"/>
            </Field>
            <Field label="Телефон">
              <input className="input" value={form.phone} onChange={e=>set('phone',e.target.value)} placeholder="+7 (XXX) XXX-XX-XX"/>
            </Field>
            <Field label="Дата рождения">
              <input className="input" type="date" value={form.birthday} onChange={e=>set('birthday',e.target.value)}/>
            </Field>
            <Field label="Должность">
              <input className="input" value={form.position} onChange={e=>set('position',e.target.value)}/>
            </Field>
            <Field label="Адрес" >
              <input className="input" value={form.address} onChange={e=>set('address',e.target.value)} placeholder="Город, улица, дом"/>
            </Field>
            <Field label="Отдел">
              <input className="input" value={emp.department?.name||'—'} disabled style={{opacity:.6,cursor:'not-allowed'}} title="Меняет менеджер или HR"/>
            </Field>
            <Field label="Грейд">
              <input className="input" value={emp.grade?.name||'—'} disabled style={{opacity:.6,cursor:'not-allowed'}} title="Меняет менеджер или HR"/>
            </Field>
            <div/>
            <div style={{gridColumn:'1/-1', display:'flex', justifyContent:'flex-end', gap:8, marginTop:4}}>
              <button className="btn primary" type="submit" disabled={saving}><Icon d={IC.check} size={15}/>{saving?'Сохранение…':'Сохранить'}</button>
            </div>
          </form>
        </div>
      </div>

      <div className="card" style={{padding:24}}>
        <SectionTitle title="Навыки и компетенции"
          right={<span className="muted" style={{fontSize:12}}>{skills.length} {plural(skills.length,'навык','навыка','навыков')}</span>}/>
        <div style={{marginTop:16}}>
          <SkillsEditor skills={skills} catalog={catalog} onChange={setSkills}/>
        </div>
        <div style={{display:'flex', justifyContent:'flex-end', marginTop:16}}>
          <button className="btn primary sm" disabled={saving} onClick={saveSkills}><Icon d={IC.check} size={14}/>Сохранить навыки</button>
        </div>
      </div>
    </div>
  );
}

/* ---- Notifications tab: живые preferences ---- */
const NOTIF_TYPE_META = {
  APPROVAL:      { label:'Согласования',            sub:'Табели, переработки и отсутствия: отправка и решения', icon:'check'    },
  DOC:           { label:'Документооборот',          sub:'Когда документ ждёт подписи или подписан',             icon:'fileText' },
  CHAT:          { label:'Сообщения в чате',         sub:'Новые сообщения в каналах и личке',                    icon:'chat'     },
  DEADLINE:      { label:'Дедлайны проектов',        sub:'Напоминания о приближении сроков',                     icon:'flag'     },
  MENTION:       { label:'Упоминания @имя',          sub:'Когда вас упоминают в каналах',                        icon:'hash'     },
  WEEKLY_DIGEST: { label:'Еженедельный дайджест',    sub:'Сводка по проектам и загрузке',                        icon:'chart'    },
};

function NotifTab({ showToast }){
  const [prefs,setPrefs]=useState(null);
  const [error,setError]=useState(null);

  useEffect(()=>{
    API.notification.getPreferences().then(setPrefs)
      .catch(err=>setError(err.detail||'Не удалось загрузить настройки уведомлений'));
  },[]);

  if(error) return <ErrorCard text={error}/>;
  if(!prefs) return <div className="card" style={{padding:24}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:40,marginBottom:12}}/>)}</div>;

  // Оптимистичный частичный PATCH с откатом
  const patch=(body, revert)=>{
    API.notification.updatePreferences(body).then(setPrefs)
      .catch(err=>{ setPrefs(revert); showToast(err.detail||'Не удалось сохранить'); });
  };
  const setChannel=(k,v)=>{ const prev=prefs; setPrefs(p=>({...p,[k]:v})); patch({ [k]:v }, prev); };
  const setType=(code,v)=>{
    const prev=prefs;
    setPrefs(p=>({ ...p, type_toggles:{ ...p.type_toggles, [code]:v } }));
    patch({ type_toggles:{ [code]:v } }, prev);
  };

  const typeCodes=Object.keys(NOTIF_TYPE_META).filter(c=>c in prefs.type_toggles);

  return (
    <div style={{display:'flex', flexDirection:'column', gap:14}}>
      <div className="card" style={{padding:24}}>
        <SectionTitle title="Каналы доставки"/>
        <div style={{display:'flex', flexDirection:'column', gap:16, marginTop:18}}>
          <ToggleRow label="Email-уведомления" sub="Отправлять на корпоративную почту" value={prefs.email_enabled} onChange={v=>setChannel('email_enabled',v)}/>
          <div className="divider"/>
          <ToggleRow label="Push-уведомления в браузере" sub="Всплывающие сообщения при новых событиях" value={prefs.push_enabled} onChange={v=>setChannel('push_enabled',v)}/>
        </div>
      </div>
      <div className="card" style={{padding:24}}>
        <SectionTitle title="Типы уведомлений"/>
        <div style={{display:'flex', flexDirection:'column', gap:16, marginTop:18}}>
          {typeCodes.map((code,i)=>{
            const tp=NOTIF_TYPE_META[code];
            return (
              <React.Fragment key={code}>
                {i>0 && <div className="divider"/>}
                <div style={{display:'flex', alignItems:'center', gap:14}}>
                  <span style={{width:36,height:36,borderRadius:9,background:'var(--surface-2)',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text-2)',flex:'none'}}><Icon d={IC[tp.icon]} size={17}/></span>
                  <div style={{flex:1}}>
                    <div style={{fontWeight:600, fontSize:14}}>{tp.label}</div>
                    <div className="muted" style={{fontSize:12.5, marginTop:2}}>{tp.sub}</div>
                  </div>
                  <Toggle value={!!prefs.type_toggles[code]} onChange={v=>setType(code,v)}/>
                </div>
              </React.Fragment>
            );
          })}
        </div>
        <div className="muted" style={{fontSize:12, marginTop:16}}>Выключенный тип не создаёт уведомлений — колокольчик останется пустым для таких событий</div>
      </div>
    </div>
  );
}

/* ---- Appearance tab (клиентские твики — без бэка) ---- */
function AppearTab({ t, setTweak, showToast }){
  return (
    <div style={{display:'flex', flexDirection:'column', gap:14}}>
      {/* theme */}
      <div className="card" style={{padding:24}}>
        <SectionTitle title="Тема оформления"/>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:14, marginTop:18}}>
          {[
            { id:'light', label:'Светлая', bg:'#f8f9fc', surface:'#ffffff', border:'#e2e5ee', text:'#1e2030', accent:'oklch(0.57 0.13 250)' },
            { id:'dark',  label:'Тёмная',  bg:'#171a23', surface:'#1f2330', border:'#323848', text:'#eef0f7', accent:'oklch(0.57 0.13 250)' },
          ].map(m=>(
            <button key={m.id} onClick={()=>setTweak('theme',m.id)}
              style={{padding:0, border:`2px solid ${t.theme===m.id?'var(--accent)':'var(--border)'}`, borderRadius:14, background:'transparent', cursor:'pointer', overflow:'hidden', transition:'border-color .15s'}}>
              {/* mini UI mockup */}
              <div style={{background:m.bg, padding:12, display:'flex', flexDirection:'column', gap:7}}>
                <div style={{display:'flex', gap:8, alignItems:'center'}}>
                  <div style={{width:8,height:8,borderRadius:50,background:m.accent}}/>
                  <div style={{height:6,borderRadius:3,background:m.border,width:60}}/>
                  <div style={{height:6,borderRadius:3,background:m.border,width:40,marginLeft:'auto'}}/>
                </div>
                <div style={{display:'flex', gap:7}}>
                  <div style={{width:40,background:m.surface,borderRadius:5,border:`1px solid ${m.border}`,padding:6,display:'flex',flexDirection:'column',gap:4}}>
                    {[28,20,24,16].map((w,i)=><div key={i} style={{height:4,borderRadius:2,background:i===0?m.accent:m.border,width:w}}/>)}
                  </div>
                  <div style={{flex:1,background:m.surface,borderRadius:5,border:`1px solid ${m.border}`,padding:8,display:'flex',flexDirection:'column',gap:5}}>
                    <div style={{height:5,borderRadius:2,background:m.text,width:'60%',opacity:.7}}/>
                    <div style={{height:4,borderRadius:2,background:m.border,width:'90%'}}/>
                    <div style={{height:4,borderRadius:2,background:m.border,width:'70%'}}/>
                    <div style={{height:22,borderRadius:5,background:m.accent,width:60,marginTop:2}}/>
                  </div>
                </div>
              </div>
              <div style={{padding:'10px 14px', display:'flex', alignItems:'center', justifyContent:'space-between', borderTop:`1px solid ${m.border}`, background:m.surface}}>
                <span style={{fontWeight:700, fontSize:13, color:m.text}}>{m.label}</span>
                {t.theme===m.id && <span style={{width:18,height:18,borderRadius:50,background:'var(--accent)',display:'flex',alignItems:'center',justifyContent:'center'}}><Icon d={IC.check} size={11} stroke={3}/></span>}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* accent */}
      <div className="card" style={{padding:24}}>
        <SectionTitle title="Акцентный цвет"/>
        <div style={{display:'flex', gap:12, marginTop:16, flexWrap:'wrap'}}>
          {ACCENTS_KEYS.map(name=>{
            const h=ACCENT_HUES[name]; const c=ACCENT_CHROMA2[name]??0.13;
            const col=`oklch(0.57 ${c} ${h})`;
            const on=t.accent===name;
            return (
              <button key={name} onClick={()=>setTweak('accent',name)}
                style={{display:'flex', flexDirection:'column', alignItems:'center', gap:8, padding:'12px 16px',
                  border:`2px solid ${on?'var(--accent)':'var(--border)'}`, borderRadius:12, background:on?'var(--accent-soft)':'transparent',
                  cursor:'pointer', transition:'.15s', minWidth:80}}>
                <span style={{width:28,height:28,borderRadius:50,background:col,display:'flex',alignItems:'center',justifyContent:'center'}}>
                  {on && <Icon d={IC.check} size={14} stroke={2.8} style={{color:'#fff'}}/>}
                </span>
                <span style={{fontSize:12.5, fontWeight:600, color: on?'var(--accent-strong)':'var(--text-2)'}}>{name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* layout */}
      <div className="card" style={{padding:24}}>
        <SectionTitle title="Раскладка и плотность"/>
        <div style={{display:'flex', flexDirection:'column', gap:18, marginTop:18}}>
          <div>
            <div style={{fontWeight:600, fontSize:14, marginBottom:10}}>Навигация</div>
            <div className="seg">
              <button className={t.nav==='sidebar'?'on':''} onClick={()=>setTweak('nav','sidebar')}>Боковая панель</button>
              <button className={t.nav==='rail'?'on':''} onClick={()=>setTweak('nav','rail')}>Компактный рейл</button>
            </div>
          </div>
          <div className="divider"/>
          <div>
            <div style={{fontWeight:600, fontSize:14, marginBottom:10}}>Плотность интерфейса</div>
            <div className="seg">
              <button className={t.density==='regular'?'on':''} onClick={()=>setTweak('density','regular')}>Стандартная</button>
              <button className={t.density==='compact'?'on':''} onClick={()=>setTweak('density','compact')}>Компактная</button>
            </div>
          </div>
          <div className="divider"/>
          <div>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10}}>
              <div style={{fontWeight:600, fontSize:14}}>Скругление углов</div>
              <span className="mono muted" style={{fontSize:13}}>{t.radius} px</span>
            </div>
            <input type="range" min={4} max={18} step={1} value={t.radius} onChange={e=>setTweak('radius',+e.target.value)}
              style={{width:'100%', accentColor:'var(--accent)'}}/>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- Security tab: смена пароля + активные сессии ---- */
function SecurityTab({ showToast }){
  const [curr,setCurr]=useState('');
  const [next1,setNext1]=useState('');
  const [next2,setNext2]=useState('');
  const [busy,setBusy]=useState(false);
  const [sessions,setSessions]=useState(null);

  const loadSessions=()=>API.auth.getSessions().then(setSessions).catch(()=>setSessions([]));
  useEffect(()=>{ loadSessions(); },[]);

  const changePass=async(e)=>{
    e.preventDefault();
    if(next1!==next2){ showToast('Пароли не совпадают'); return; }
    setBusy(true);
    try{
      await API.auth.changePassword(curr, next1);
      showToast('Пароль изменён — остальные сессии завершены');
      setCurr(''); setNext1(''); setNext2('');
      loadSessions();
    }catch(err){ showToast(err.detail||'Не удалось сменить пароль'); }
    finally{ setBusy(false); }
  };

  const revoke=async(s)=>{
    try{ await API.auth.revokeSession(s.id); showToast('Сессия завершена'); loadSessions(); }
    catch(err){ showToast(err.detail||'Не удалось завершить сессию'); }
  };
  const revokeAll=async()=>{
    try{ await API.auth.revokeAllSessions(); showToast('Все сессии кроме текущей завершены'); loadSessions(); }
    catch(err){ showToast(err.detail||'Не удалось завершить сессии'); }
  };

  return (
    <div style={{display:'flex', flexDirection:'column', gap:14}}>
      <div className="card" style={{padding:24}}>
        <SectionTitle title="Смена пароля"/>
        <form onSubmit={changePass} style={{display:'flex', flexDirection:'column', gap:14, marginTop:18, maxWidth:400}}>
          <Field label="Текущий пароль">
            <input className="input" type="password" value={curr} onChange={e=>setCurr(e.target.value)} placeholder="••••••••" autoComplete="current-password"/>
          </Field>
          <Field label="Новый пароль">
            <input className="input" type="password" value={next1} onChange={e=>setNext1(e.target.value)} placeholder="Минимум 8 символов" autoComplete="new-password"/>
          </Field>
          <Field label="Повторите новый пароль">
            <input className="input" type="password" value={next2} onChange={e=>setNext2(e.target.value)} placeholder="••••••••" autoComplete="new-password"/>
          </Field>
          <div className="muted" style={{fontSize:11.5,marginTop:-6}}>Минимум 8 символов, заглавная и строчная буквы, цифра, спецсимвол</div>
          <button className="btn primary" type="submit" disabled={busy||!curr||!next1||!next2} style={{alignSelf:'flex-start'}}>
            <Icon d={IC.shield} size={15}/>{busy?'Смена…':'Сменить пароль'}
          </button>
        </form>
      </div>

      <div className="card" style={{padding:24}}>
        <SectionTitle title="Активные сессии"
          right={sessions&&sessions.length>1&&<button className="btn sm" style={{color:'var(--red)'}} onClick={revokeAll}>Завершить все</button>}/>
        <div style={{display:'flex', flexDirection:'column', gap:0, marginTop:14}}>
          {sessions===null&&[0,1].map(i=><div key={i} className="skel" style={{height:44,marginBottom:10}}/>)}
          {sessions&&sessions.length===0&&<div className="muted" style={{fontSize:13,padding:'8px 0'}}>Активных сессий нет</div>}
          {(sessions||[]).map((s,i)=>(
            <div key={s.id} style={{display:'flex', alignItems:'center', gap:14, padding:'13px 0', borderTop: i>0?'1px solid var(--border)':'none'}}>
              <span style={{width:36,height:36,borderRadius:9,background:'var(--surface-2)',display:'flex',alignItems:'center',justifyContent:'center',color:'var(--text-3)',flex:'none'}}><Icon d={IC.user} size={18}/></span>
              <div style={{flex:1}}>
                <div style={{fontWeight:600, fontSize:13.5, display:'flex', alignItems:'center', gap:8}}>
                  {s.device}
                  {s.is_current && <span className="badge green" style={{height:20, fontSize:10}}>текущая</span>}
                </div>
                <div className="muted" style={{fontSize:12, marginTop:2}}>{s.ip_address||'IP неизвестен'} · {fmtDateY(s.created_at)}</div>
              </div>
              {!s.is_current && <button className="btn sm ghost" style={{color:'var(--red)'}} onClick={()=>revoke(s)}><Icon d={IC.logout} size={13}/>Завершить</button>}
            </div>
          ))}
        </div>
        <div className="muted" style={{fontSize:12,marginTop:12}}>Сессия — это выданный при входе refresh-токен. Завершение сессии разлогинит то устройство.</div>
      </div>
    </div>
  );
}

Object.assign(window, { SettingsScreen, Toggle, ToggleRow });
