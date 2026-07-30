/* ============ SCREEN: Панель администратора — живые данные (auth admin-API + management roles) ============ */

// Категория полномочия по префиксу кода
const PERM_CAT_BY_PREFIX = {
  user:'Пользователи', employee:'Профиль', project:'Проекты',
  directory:'Система', system:'Система', calendar:'Система',
  timesheet:'Табель', overtime:'Переработки', summary:'Сводка',
  report:'Отчётность', absence:'Отсутствия', document:'Документы',
};
const permCat=(code)=>PERM_CAT_BY_PREFIX[code.split(':')[0]]||'Прочее';

// Бэк не хранит цвет роли — базовым даём фиксированные, остальным из палитры по имени
const ROLE_COLOR_KNOWN = {
  'Сотрудник':     { color:'var(--green)',         soft:'var(--green-soft)'    },
  'Тимлид':        { color:'oklch(0.55 0.13 195)', soft:'oklch(0.94 0.04 195)' },
  'HR':            { color:'var(--violet)',        soft:'var(--violet-soft)'   },
  'Менеджер':      { color:'var(--accent)',        soft:'var(--accent-soft)'   },
  'Администратор': { color:'var(--red)',           soft:'var(--red-soft)'      },
};
const ROLE_COLOR_POOL = [
  { color:'oklch(0.60 0.14 68)',  soft:'oklch(0.93 0.05 68)'  },
  { color:'oklch(0.58 0.15 355)', soft:'oklch(0.93 0.04 355)' },
  { color:'oklch(0.55 0.13 250)', soft:'oklch(0.93 0.03 250)' },
  { color:'oklch(0.48 0.02 255)', soft:'oklch(0.93 0.01 255)' },
];
function roleColor(name){
  if(ROLE_COLOR_KNOWN[name]) return ROLE_COLOR_KNOWN[name];
  let h=0; for(const ch of name) h=(h*31+ch.charCodeAt(0))>>>0;
  return ROLE_COLOR_POOL[h%ROLE_COLOR_POOL.length];
}
const ROLE_ORDER = ['Сотрудник','Тимлид','HR','Менеджер','Администратор'];
const roleSort=(a,b)=>{
  const ia=ROLE_ORDER.indexOf(a.name), ib=ROLE_ORDER.indexOf(b.name);
  return (ia<0?99:ia)-(ib<0?99:ib) || a.name.localeCompare(b.name);
};

function RoleBadge({ name, style }){
  const c=roleColor(name);
  return <span className="badge" style={{background:c.soft,color:c.color,height:22,fontSize:11,...style}}>{name}</span>;
}

function AdminScreen({ showToast }){
  const [tab,setTab]=useState('users');
  const [data,setData]=useState(null); // {roles, perms, employees}
  const [error,setError]=useState(null);
  const [createOpen,setCreateOpen]=useState(false);

  const canManage=(API.session()?.permissions||[]).includes('system:manage');

  const load=()=>Promise.all([
    API.auth.getRolesWithPermissions(),
    API.auth.getPermissions(),
    API.management.getEmployees(),
  ]).then(([roles, perms, employees])=>setData({ roles:[...roles].sort(roleSort), perms, employees }));

  useEffect(()=>{ if(canManage) load().catch(err=>setError(err.detail||'Не удалось загрузить данные')); },[]);
  const reload=()=>load().catch(err=>showToast(err.detail||'Не удалось обновить данные'));

  if(!canManage) return <ErrorCard text="Нужны права администратора (system:manage)"/>;
  if(error) return <ErrorCard text={error}/>;
  if(!data) return (
    <div className="fade-in" style={{display:'flex',flexDirection:'column',gap:18}}>
      <div><div className="skel" style={{width:260,height:26,marginBottom:8}}/><div className="skel" style={{width:340,height:14}}/></div>
      <div className="card" style={{padding:18}}>{[0,1,2,3].map(i=><div key={i} className="skel" style={{height:44,marginBottom:10}}/>)}</div>
    </div>
  );

  const TABS=[
    {id:'users', label:'Пользователи', icon:'users' },
    {id:'roles', label:'Роли',         icon:'shield'},
    {id:'perms', label:'Полномочия',   icon:'key'   },
  ];

  return (
    <div className="fade-in" style={{display:'flex',flexDirection:'column',gap:18}}>
      <PageHead title="Панель администратора" subtitle="Управление доступом: роли и полномочия"
        actions={<span className="badge" style={{gap:6,height:28}}><Icon d={IC.shield} size={13}/>Роли применяются при следующем входе (JWT)</span>}/>
      <div style={{display:'flex',borderBottom:'1px solid var(--border)',gap:0,marginBottom:2}}>
        {TABS.map(tb=>{ const on=tab===tb.id; return (
          <button key={tb.id} onClick={()=>setTab(tb.id)} style={{display:'flex',alignItems:'center',gap:7,padding:'10px 18px',border:'none',background:'transparent',cursor:'pointer',fontSize:13.5,fontWeight:600,color:on?'var(--accent-strong)':'var(--text-2)',borderBottom:on?'2px solid var(--accent)':'2px solid transparent',marginBottom:-1,transition:'.13s'}}>
            <Icon d={IC[tb.icon]} size={15} stroke={on?2.1:1.7}/>{tb.label}
          </button>
        );})}
      </div>
      {tab==='users' && <AdminUsersTab employees={data.employees} roles={data.roles} onChanged={reload} showToast={showToast}/>}
      {tab==='roles' && <AdminRolesTab roles={data.roles} employees={data.employees} onCreate={()=>setCreateOpen(true)} onChanged={reload} showToast={showToast}/>}
      {tab==='perms' && <AdminPermsTab roles={data.roles} perms={data.perms} onChanged={reload} showToast={showToast}/>}
      {createOpen && <CreateRoleModal onClose={()=>setCreateOpen(false)}
        onSaved={()=>{ setCreateOpen(false); reload(); setTab('roles'); }} showToast={showToast}/>}
    </div>
  );
}

/* ──────────────────── ПОЛЬЗОВАТЕЛИ ──────────────────── */
function AdminUsersTab({ employees, roles, onChanged, showToast }){
  const [q,setQ]=useState('');
  const [editing,setEditing]=useState(null);   // employee id
  const [draft,setDraft]=useState(new Set());  // role ids
  const [busy,setBusy]=useState(false);
  const popRef=useRef(null);

  useEffect(()=>{
    if(!editing) return;
    const h=(e)=>{ if(popRef.current&&!popRef.current.contains(e.target)) setEditing(null); };
    document.addEventListener('mousedown',h); return ()=>document.removeEventListener('mousedown',h);
  },[editing]);

  const list=employees.filter(e=>{
    if(!q.trim()) return true;
    const lo=q.toLowerCase();
    return (`${e.first_name} ${e.last_name}`).toLowerCase().includes(lo)||e.user.email.toLowerCase().includes(lo);
  });

  const startEdit=(e)=>{
    setEditing(e.id);
    setDraft(new Set((e.user.roles||[]).map(r=>r.id)));
  };
  const save=async(empId)=>{
    if(draft.size===0){ showToast('У пользователя должна остаться хотя бы одна роль'); return; }
    setBusy(true);
    try{
      await API.management.setRoles(empId, [...draft]);
      showToast('Роли обновлены — применятся при следующем входе пользователя');
      setEditing(null);
      onChanged();
    }catch(err){ showToast(err.detail||'Не удалось обновить роли'); }
    finally{ setBusy(false); }
  };

  return (
    <div className="card" style={{padding:'16px 20px 8px'}}>
      <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:10}}>
        <div style={{position:'relative',width:280}}>
          <span style={{position:'absolute',left:11,top:9,color:'var(--text-3)'}}><Icon d={IC.search} size={16}/></span>
          <input className="input" value={q} onChange={e=>setQ(e.target.value)} style={{height:34,paddingLeft:34,fontSize:13}} placeholder="Поиск по имени или почте…"/>
        </div>
        <div style={{flex:1}}/>
        <span className="muted" style={{fontSize:12.5}}>{employees.length} {plural(employees.length,'пользователь','пользователя','пользователей')}</span>
      </div>
      <table className="tbl">
        <thead><tr><th>Пользователь</th><th>Почта</th><th>Табельный</th><th>Роли</th><th/></tr></thead>
        <tbody>
          {list.map(e=>{
            const name=`${e.first_name} ${e.last_name}`;
            return (
              <tr key={e.id}>
                <td><span style={{display:'inline-flex',alignItems:'center',gap:9}}><Avatar id={e.id} name={name} size={30}/><span style={{fontWeight:600}}>{name}</span></span></td>
                <td className="muted" style={{fontSize:12.5}}>{e.user.email}</td>
                <td className="muted mono" style={{fontSize:12}}>{e.user.number}</td>
                <td><div style={{display:'flex',gap:6,flexWrap:'wrap'}}>{(e.user.roles||[]).map(r=><RoleBadge key={r.id} name={r.name}/>)}</div></td>
                <td style={{position:'relative',width:44}}>
                  <button className="btn ghost sm icon" onClick={()=>startEdit(e)} title="Изменить роли"><Icon d={IC.edit} size={14}/></button>
                  {editing===e.id&&(
                    <div ref={popRef} className="card fade-in" style={{position:'absolute',right:0,top:'100%',zIndex:60,minWidth:230,padding:10,boxShadow:'var(--shadow-lg)'}}>
                      <div className="muted" style={{fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:'.05em',marginBottom:8}}>Роли пользователя</div>
                      {roles.map(r=>{
                        const on=draft.has(r.id);
                        return (
                          <label key={r.id} style={{display:'flex',alignItems:'center',gap:9,padding:'6px 4px',cursor:'pointer',borderRadius:7}}
                            onMouseEnter={ev=>ev.currentTarget.style.background='var(--surface-2)'}
                            onMouseLeave={ev=>ev.currentTarget.style.background='transparent'}>
                            <input type="checkbox" checked={on} style={{accentColor:'var(--accent)',width:15,height:15}}
                              onChange={()=>setDraft(d=>{ const n=new Set(d); on?n.delete(r.id):n.add(r.id); return n; })}/>
                            <RoleBadge name={r.name}/>
                          </label>
                        );
                      })}
                      <div style={{display:'flex',gap:6,marginTop:10}}>
                        <button className="btn sm" style={{flex:1}} onClick={()=>setEditing(null)}>Отмена</button>
                        <button className="btn sm primary" style={{flex:1}} disabled={busy} onClick={()=>save(e.id)}>{busy?'…':'Сохранить'}</button>
                      </div>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
          {list.length===0&&<tr><td colSpan={5} style={{textAlign:'center',padding:'24px 0',color:'var(--text-3)'}}>Никого не нашлось</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

/* ──────────────────── РОЛИ ──────────────────── */
function AdminRolesTab({ roles, employees, onCreate, onChanged, showToast }){
  const [editingId,setEditingId]=useState(null);
  const [descDraft,setDescDraft]=useState('');
  const [busy,setBusy]=useState(false);

  const usersOf=(role)=>employees.filter(e=>(e.user.roles||[]).some(r=>r.id===role.id)).length;

  const saveDesc=async(role)=>{
    setBusy(true);
    try{
      await API.management.updateRole(role.id, { description: descDraft.trim()||null });
      showToast('Описание обновлено');
      setEditingId(null);
      onChanged();
    }catch(err){ showToast(err.detail||'Не удалось сохранить'); }
    finally{ setBusy(false); }
  };
  const remove=async(role)=>{
    try{
      await API.management.deleteRole(role.id);
      showToast(`Роль «${role.name}» удалена`);
      onChanged();
    }catch(err){ showToast(err.detail||'Не удалось удалить роль'); }
  };

  return (
    <div style={{display:'flex',flexDirection:'column',gap:14}}>
      <div style={{display:'flex',justifyContent:'flex-end'}}>
        <button className="btn sm primary" onClick={onCreate}><Icon d={IC.plus} size={15}/>Создать роль</button>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:14}}>
        {roles.map(role=>{
          const c=roleColor(role.name);
          const base=ROLE_ORDER.includes(role.name);
          return (
            <div key={role.id} className="card" style={{padding:18,display:'flex',flexDirection:'column',gap:10}}>
              <div style={{display:'flex',alignItems:'center',gap:10}}>
                <span style={{width:36,height:36,borderRadius:9,background:c.soft,color:c.color,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
                  <Icon d={IC.shield} size={17}/>
                </span>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontWeight:800,fontSize:15}}>{role.name}</div>
                  <div className="muted" style={{fontSize:11.5}}>{base?'Системная роль':'Пользовательская роль'}</div>
                </div>
                <button className="btn ghost sm icon" title="Изменить описание"
                  onClick={()=>{ setEditingId(role.id); setDescDraft(role.description||''); }}>
                  <Icon d={IC.edit} size={14}/>
                </button>
                {!base&&(
                  <button className="btn ghost sm icon" title="Удалить (нельзя, если назначена)" style={{color:'var(--red)'}} onClick={()=>remove(role)}>
                    <Icon d={IC.trash} size={14}/>
                  </button>
                )}
              </div>
              {editingId===role.id?(
                <div>
                  <textarea className="input" value={descDraft} onChange={e=>setDescDraft(e.target.value)} autoFocus
                    placeholder="Описание роли…" style={{height:64,resize:'none',padding:'8px 10px',fontSize:12.5,lineHeight:1.45,width:'100%'}}/>
                  <div style={{display:'flex',gap:6,marginTop:6}}>
                    <button className="btn sm" style={{flex:1}} onClick={()=>setEditingId(null)}>Отмена</button>
                    <button className="btn sm primary" style={{flex:1}} disabled={busy} onClick={()=>saveDesc(role)}>Сохранить</button>
                  </div>
                </div>
              ):(
                <div className="muted" style={{fontSize:12.5,lineHeight:1.5,minHeight:36}}>{role.description||'Без описания'}</div>
              )}
              <div style={{display:'flex',gap:14,marginTop:'auto',paddingTop:6,borderTop:'1px solid var(--border)'}}>
                <span style={{display:'inline-flex',alignItems:'center',gap:6,fontSize:12.5,color:'var(--text-2)'}}>
                  <Icon d={IC.users} size={14}/>{usersOf(role)} {plural(usersOf(role),'пользователь','пользователя','пользователей')}
                </span>
                <span style={{display:'inline-flex',alignItems:'center',gap:6,fontSize:12.5,color:'var(--text-2)'}}>
                  <Icon d={IC.key} size={14}/>{role.permissions.length} {plural(role.permissions.length,'полномочие','полномочия','полномочий')}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ──────────────────── ПОЛНОМОЧИЯ (матрица) ──────────────────── */
function AdminPermsTab({ roles, perms, onChanged, showToast }){
  // roleId → Set(codes); локальное состояние для мгновенных тумблеров
  const [rolePerms,setRolePerms]=useState({});
  useEffect(()=>{
    const m={}; roles.forEach(r=>{ m[r.id]=new Set(r.permissions.map(p=>p.code)); });
    setRolePerms(m);
  },[roles]);

  const cats=useMemo(()=>{
    const by={};
    perms.forEach(p=>{ const cat=permCat(p.code); (by[cat]=by[cat]||[]).push(p); });
    return Object.entries(by);
  },[perms]);

  const toggle=async(role, code)=>{
    const cur=rolePerms[role.id]; if(!cur) return;
    const next=new Set(cur); next.has(code)?next.delete(code):next.add(code);
    setRolePerms(m=>({ ...m, [role.id]:next })); // оптимистично
    try{
      await API.auth.setRolePermissions(role.id, [...next]);
    }catch(err){
      setRolePerms(m=>({ ...m, [role.id]:cur })); // откат (например, защита system:manage)
      showToast(err.detail||'Не удалось изменить полномочия');
    }
  };

  return (
    <div className="card" style={{padding:'14px 18px',overflowX:'auto'}}>
      <table style={{borderCollapse:'collapse',width:'100%',minWidth:640}}>
        <thead>
          <tr>
            <th style={{textAlign:'left',padding:'8px 10px',fontSize:12,color:'var(--text-3)',fontWeight:700}}>Полномочие</th>
            {roles.map(r=>(
              <th key={r.id} style={{padding:'8px 6px',textAlign:'center'}}><RoleBadge name={r.name}/></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cats.map(([cat, list])=>(
            <React.Fragment key={cat}>
              <tr><td colSpan={roles.length+1} style={{padding:'12px 10px 5px',fontSize:11,fontWeight:800,color:'var(--text-3)',textTransform:'uppercase',letterSpacing:'.05em'}}>{cat}</td></tr>
              {list.map(p=>(
                <tr key={p.code} style={{borderTop:'1px solid var(--border)'}}>
                  <td style={{padding:'8px 10px'}}>
                    <div style={{fontWeight:600,fontSize:13}}>{p.name}</div>
                    <div className="muted mono" style={{fontSize:10.5}}>{p.code}</div>
                  </td>
                  {roles.map(r=>{
                    const on=rolePerms[r.id]?.has(p.code);
                    return (
                      <td key={r.id} style={{textAlign:'center',padding:'6px'}}>
                        <button onClick={()=>toggle(r,p.code)} title={`${r.name}: ${on?'отобрать':'выдать'} ${p.code}`}
                          style={{width:34,height:20,borderRadius:999,border:'none',cursor:'pointer',position:'relative',transition:'.15s',
                            background:on?'var(--accent)':'var(--surface-3)'}}>
                          <span style={{position:'absolute',top:2,left:on?16:2,width:16,height:16,borderRadius:50,background:'#fff',
                            boxShadow:'0 1px 3px rgba(0,0,0,0.25)',transition:'.15s'}}/>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </React.Fragment>
          ))}
        </tbody>
      </table>
      <div className="muted" style={{fontSize:12,padding:'10px 10px 4px'}}>
        Изменения сохраняются сразу и попадут в JWT при следующем входе пользователей. Снять system:manage у последней роли-носителя бэкенд не даст.
      </div>
    </div>
  );
}

/* ──────────────────── СОЗДАНИЕ РОЛИ ──────────────────── */
function CreateRoleModal({ onClose, onSaved, showToast }){
  const [name,setName]=useState('');
  const [description,setDescription]=useState('');
  const [saving,setSaving]=useState(false);

  const save=async()=>{
    if(!name.trim()){ showToast('Введите название роли'); return; }
    setSaving(true);
    try{
      await API.management.createRole({ name:name.trim(), description:description.trim()||null });
      // Kafka разносит роль в auth — дожидаемся реплики, чтобы вкладка «Полномочия» её сразу увидела
      for(let i=0;i<15;i++){
        const roles=await API.auth.getRolesWithPermissions();
        if(roles.some(r=>r.name===name.trim())) break;
        await new Promise(r=>setTimeout(r,700));
      }
      showToast(`Роль «${name.trim()}» создана — выдайте ей полномочия на вкладке «Полномочия»`);
      onSaved();
    }catch(err){ showToast(err.detail||'Не удалось создать роль'); }
    finally{ setSaving(false); }
  };

  return (
    <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',background:'oklch(0.25 0.02 255 / 0.5)',backdropFilter:'blur(3px)'}}
      onClick={e=>{ if(e.target===e.currentTarget) onClose(); }}>
      <div className="card fade-in" style={{width:440,maxWidth:'94vw',padding:24,boxShadow:'var(--shadow-lg)'}}>
        <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:18}}>
          <span style={{width:40,height:40,borderRadius:10,background:'var(--accent-soft)',color:'var(--accent-strong)',display:'flex',alignItems:'center',justifyContent:'center'}}>
            <Icon d={IC.shield} size={19}/>
          </span>
          <div style={{flex:1}}>
            <h3 style={{fontSize:16}}>Новая роль</h3>
            <div className="muted" style={{fontSize:12}}>Полномочия выдаются после создания</div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={16}/></button>
        </div>
        <div style={{display:'flex',flexDirection:'column',gap:14}}>
          <Field label="Название *">
            <input className="input" value={name} onChange={e=>setName(e.target.value)} placeholder="Стажёр" autoFocus/>
          </Field>
          <Field label="Описание">
            <textarea className="input" value={description} onChange={e=>setDescription(e.target.value)}
              placeholder="Для чего эта роль…" style={{height:70,resize:'none',padding:'9px 11px',lineHeight:1.45}}/>
          </Field>
        </div>
        <div style={{display:'flex',gap:8,marginTop:20}}>
          <button className="btn" style={{flex:1}} onClick={onClose}>Отмена</button>
          <button className="btn primary" style={{flex:1}} disabled={saving} onClick={save}>
            <Icon d={IC.check} size={15}/>{saving?'Создание…':'Создать'}
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { AdminScreen });
