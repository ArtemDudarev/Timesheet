/* ============ SCREEN: Отсутствия — живые данные (absence_service) ============ */

// Иконки по коду типа (каталог отдаёт code/name/color)
const ABS_TYPE_ICON = { VACATION:'calendar', SICK:'shield', TRIP:'briefcase', DAY_OFF:'clock' };
// hex-цвет каталога → мягкий фон
const absTypeBg = (color)=>color+'22';

// Статусы заявки (русские значения enum бэка)
const ABS_ST_UI = {
  'Черновик':        { cls:''      },
  'На согласовании': { cls:'amber' },
  'Согласована':     { cls:'green' },
  'Отклонена':       { cls:'red'   },
  'Отменена':        { cls:''      },
};

function AbsencesScreen({ userId, isManager, showToast }){
  const [data,setData]=useState(null); // {types, absences, empMap, balance}
  const [error,setError]=useState(null);
  const [createOpen,setCreateOpen]=useState(false);
  const [filter,setFilter]=useState('all');
  const [selected,setSelected]=useState(null); // absence id — сам объект берём из свежего списка

  const load=()=>Promise.all([
    API.absence.getTypes(),
    API.absence.getAbsences(),
    isManager ? API.management.getEmployees().catch(()=>[]) : Promise.resolve([]),
    !isManager ? API.absence.getVacationBalance(userId).catch(()=>null) : Promise.resolve(null),
  ]).then(([types, absences, emps, balance])=>{
    const empMap={};
    emps.forEach(e=>{ empMap[e.id]=`${e.first_name} ${e.last_name}`; });
    absences.sort((a,b)=>(b.date_from<a.date_from?-1:b.date_from>a.date_from?1:0));
    setData({ types, absences, empMap, balance });
  });
  useEffect(()=>{ load().catch(err=>setError(err.detail||'Не удалось загрузить отсутствия')); },[userId]);
  const reload=()=>load().catch(err=>showToast(err.detail||'Не удалось обновить данные'));

  if(error) return <ErrorCard text={error}/>;
  if(!data) return (
    <div className="fade-in" style={{display:'flex',flexDirection:'column',gap:18}}>
      <div><div className="skel" style={{width:180,height:26,marginBottom:8}}/><div className="skel" style={{width:300,height:14}}/></div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:14}}>{[0,1,2,3].map(i=><div key={i} className="skel" style={{height:86}}/>)}</div>
      <div className="card" style={{padding:18}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:40,marginBottom:10}}/>)}</div>
    </div>
  );

  const { types, absences, empMap, balance } = data;
  const today=new Date(); today.setHours(0,0,0,0);
  const year=today.getFullYear();
  const inYear=(a)=>new Date(a.date_from).getFullYear()===year||new Date(a.date_to).getFullYear()===year;
  const ongoing=(a)=>a.status==='Согласована'&&new Date(a.date_from)<=today&&new Date(a.date_to)>=today;
  const code=(a)=>a.absence_type.code;

  const tabs=[
    {id:'all',      label:'Все'},
    {id:'pending',  label:'На согласовании'},
    {id:'approved', label:'Утверждённые'},
    {id:'upcoming', label:'Предстоящие'},
  ];
  const list=absences.filter(a=>{
    if(filter==='pending')  return a.status==='На согласовании';
    if(filter==='approved') return a.status==='Согласована';
    if(filter==='upcoming') return a.status==='Согласована'&&new Date(a.date_from)>today;
    return true;
  });

  const upcoming=absences.filter(a=>a.status==='Согласована'&&new Date(a.date_to)>=today);
  const selectedAbs=selected?absences.find(a=>a.id===selected):null;

  return (
    <div className="fade-in" style={{display:'flex',flexDirection:'column',gap:18}}>
      <PageHead title="Отсутствия" subtitle="Отпуска, больничные и командировки"
        actions={<button className="btn sm primary" onClick={()=>setCreateOpen(true)}><Icon d={IC.plus} size={15}/>Подать заявку</button>}/>

      {/* stat cards */}
      {isManager ? (
        <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:14}}>
          <StatCard label="Ждут согласования" value={absences.filter(a=>a.status==='На согласовании').length} sub="активных заявок" icon="clock" accent/>
          <StatCard label="Сейчас в отпуске" value={absences.filter(a=>code(a)==='VACATION'&&ongoing(a)).length+' чел.'} sub="из команды" icon="calendar"/>
          <StatCard label="В командировках" value={absences.filter(a=>code(a)==='TRIP'&&ongoing(a)).length+' чел.'} sub="прямо сейчас" icon="briefcase"/>
          <StatCard label="На больничном" value={absences.filter(a=>code(a)==='SICK'&&ongoing(a)).length+' чел.'} sub="из команды" icon="shield"/>
        </div>
      ) : (
        <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:14}}>
          <StatCard label="Остаток отпуска" value={(balance?balance.remaining_days:'—')+' дн.'}
            sub={balance?`Использовано ${balance.used_days} из ${balance.entitled_days}`:'нет данных'} icon="calendar" accent/>
          <StatCard label="Больничных в году" value={absences.filter(a=>code(a)==='SICK'&&a.status==='Согласована'&&inYear(a)).reduce((s,a)=>s+a.days_count,0)+' дн.'} sub={year+' год'} icon="shield"/>
          <StatCard label="Командировок" value={absences.filter(a=>code(a)==='TRIP'&&a.status==='Согласована'&&inYear(a)).length} sub="в этом году" icon="briefcase"/>
          <StatCard label="На согласовании" value={absences.filter(a=>a.status==='На согласовании').length} sub="ждут ответа" icon="clock"/>
        </div>
      )}

      {/* ближайшие утверждённые периоды */}
      {upcoming.length>0 && (
        <div className="card" style={{padding:'16px 20px'}}>
          <SectionTitle title="Ближайшие периоды"/>
          <div style={{display:'flex',gap:12,marginTop:14,flexWrap:'wrap'}}>
            {upcoming.map(a=>{
              const tp=a.absence_type;
              return (
                <div key={a.id} style={{display:'flex',alignItems:'center',gap:10,padding:'10px 14px',borderRadius:10,
                  background:absTypeBg(tp.color),border:`1px solid ${tp.color}40`,cursor:'pointer'}} onClick={()=>setSelected(a.id)}>
                  <Icon d={IC[ABS_TYPE_ICON[tp.code]]||IC.calendar} size={18} style={{color:tp.color,flexShrink:0}}/>
                  <div>
                    <div style={{fontWeight:700,fontSize:13.5,color:tp.color}}>
                      {tp.name}{isManager&&empMap[a.employee_id]?' · '+empMap[a.employee_id].split(' ')[0]:''}
                    </div>
                    <div className="muted" style={{fontSize:12}}>{fmtDateRange(a.date_from,a.date_to)} · {a.days_count} {plural(a.days_count,'день','дня','дней')}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* list */}
      <div className="card" style={{padding:'16px 20px 8px'}}>
        <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:12}}>
          <div className="seg">
            {tabs.map(t=><button key={t.id} className={filter===t.id?'on':''} onClick={()=>setFilter(t.id)}>{t.label}</button>)}
          </div>
        </div>
        <table className="tbl">
          <thead><tr>{isManager&&<th>Сотрудник</th>}<th>Тип</th><th>Период</th><th>Дней</th><th>Комментарий</th><th>Подана</th><th>Статус</th></tr></thead>
          <tbody>
            {list.length===0&&<tr><td colSpan={isManager?7:6} style={{textAlign:'center',padding:'24px 0',color:'var(--text-3)'}}>Нет заявок</td></tr>}
            {list.map(a=>{
              const tp=a.absence_type;
              const st=ABS_ST_UI[a.status]||{cls:''};
              const empName=empMap[a.employee_id];
              return (
                <tr key={a.id} style={{cursor:'pointer'}} onClick={()=>setSelected(a.id)}>
                  {isManager&&<td><span style={{display:'inline-flex',alignItems:'center',gap:7}}>
                    <Avatar id={a.employee_id} name={empName||'?'} size={26}/>
                    <span style={{fontWeight:600,fontSize:12.5,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap',maxWidth:90}}>{(empName||'—').split(' ')[0]}</span>
                  </span></td>}
                  <td>
                    <span style={{display:'inline-flex',alignItems:'center',gap:8}}>
                      <span style={{width:28,height:28,borderRadius:7,background:absTypeBg(tp.color),color:tp.color,display:'flex',alignItems:'center',justifyContent:'center'}}>
                        <Icon d={IC[ABS_TYPE_ICON[tp.code]]||IC.calendar} size={15}/>
                      </span>
                      <span style={{fontWeight:600}}>{tp.name}</span>
                    </span>
                  </td>
                  <td className="mono muted" style={{fontSize:12.5}}>{fmtDateRange(a.date_from,a.date_to)}</td>
                  <td className="mono" style={{fontWeight:600}}>{a.days_count}</td>
                  <td className="muted" style={{maxWidth:220,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{a.comment||'—'}</td>
                  <td className="muted mono" style={{fontSize:12}}>{a.submitted_at?fmtDateY(a.submitted_at):'—'}</td>
                  <td><span className={'badge '+st.cls}><span className="dot"/>{a.status}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {createOpen&&<CreateAbsenceDrawer types={types} onClose={()=>setCreateOpen(false)} showToast={showToast}
        onSaved={(submitted)=>{ setCreateOpen(false); reload(); showToast(submitted?'Заявка отправлена на согласование':'Черновик сохранён'); }}/>}
      {selectedAbs&&<AbsenceDetailDrawer absence={selectedAbs} isManager={isManager} isOwner={selectedAbs.employee_id===userId}
        empName={empMap[selectedAbs.employee_id]} onClose={()=>setSelected(null)} onChanged={reload} showToast={showToast}/>}
    </div>
  );
}

/* ---- Create absence drawer ---- */
function CreateAbsenceDrawer({ types, onClose, onSaved, showToast }){
  const [typeId,setTypeId]=useState(types[0]?.id);
  const [start,setStart]=useState('');
  const [end,setEnd]=useState('');
  const [comment,setComment]=useState('');
  const [errors,setErrors]=useState({});
  const [busy,setBusy]=useState(false);

  const tp=types.find(t=>t.id===typeId)||types[0];
  const todayIso=new Date().toISOString().slice(0,10);

  // Подсказка по рабочим дням (бэк считает точно так же, по Пн–Пт)
  const calcDays=()=>{
    if(!start||!end) return 0;
    const s=new Date(start),e=new Date(end);
    if(s>e) return 0;
    let d=0,cur=new Date(s);
    while(cur<=e){ const wd=cur.getDay(); if(wd!==0&&wd!==6) d++; cur.setDate(cur.getDate()+1); }
    return d;
  };
  const days=calcDays();

  const validate=()=>{
    const e={};
    if(!start) e.start='Укажите дату начала';
    if(!end)   e.end='Укажите дату окончания';
    if(start&&end&&new Date(start)>new Date(end)) e.end='Дата окончания раньше начала';
    if(days===0&&start&&end) e.end='Нет рабочих дней в выбранном периоде';
    setErrors(e);
    return Object.keys(e).length===0;
  };

  const save=async(submit)=>{
    if(!validate()) return;
    setBusy(true);
    try{
      await API.absence.createAbsence({ type_id:typeId, date_from:start, date_to:end, comment:comment.trim()||null, submit });
      onSaved(submit);
    }catch(err){ showToast(err.detail||'Не удалось создать заявку'); }
    finally{ setBusy(false); }
  };

  return (
    <div style={{position:'fixed',inset:0,zIndex:120,display:'flex',justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.32)',backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative',width:480,maxWidth:'94vw',height:'100%',background:'var(--surface)',
        borderLeft:'1px solid var(--border)',boxShadow:'var(--shadow-lg)',display:'flex',flexDirection:'column'}}>

        <div style={{padding:'22px 26px 18px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
          <span style={{width:44,height:44,borderRadius:11,background:absTypeBg(tp.color),display:'flex',alignItems:'center',justifyContent:'center'}}>
            <Icon d={IC[ABS_TYPE_ICON[tp.code]]||IC.calendar} size={22} style={{color:tp.color}}/>
          </span>
          <div style={{flex:1}}>
            <h2 style={{fontSize:17}}>Новая заявка</h2>
            <div className="muted" style={{fontSize:12.5}}>{tp.name} · {days>0?days+' раб. дн.':'выберите даты'}</div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
        </div>

        <div style={{flex:1,overflowY:'auto',padding:'24px 26px',display:'flex',flexDirection:'column',gap:18}}>

          {/* тип из каталога */}
          <div>
            <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:10}}>Тип отсутствия</div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
              {types.map(t=>(
                <button key={t.id} onClick={()=>setTypeId(t.id)}
                  style={{display:'flex',alignItems:'center',gap:10,padding:'11px 14px',
                    border:`2px solid ${typeId===t.id?t.color:'var(--border)'}`,borderRadius:10,
                    background:typeId===t.id?absTypeBg(t.color):'var(--surface)',cursor:'pointer',textAlign:'left',transition:'.14s'}}>
                  <span style={{width:32,height:32,borderRadius:8,background:absTypeBg(t.color),display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
                    <Icon d={IC[ABS_TYPE_ICON[t.code]]||IC.calendar} size={17} style={{color:t.color}}/>
                  </span>
                  <span style={{fontWeight:600,fontSize:13.5,color:typeId===t.id?t.color:'var(--text)'}}>{t.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* даты: больничный можно подавать задним числом */}
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
            <Field label="Дата начала *">
              <input className="input" type="date" value={start} onChange={e=>{setStart(e.target.value);setErrors(er=>({...er,start:null}));}}
                min={tp.code==='SICK'?undefined:todayIso}/>
              {errors.start&&<div style={{color:'var(--red)',fontSize:11.5,marginTop:4}}>{errors.start}</div>}
            </Field>
            <Field label="Дата окончания *">
              <input className="input" type="date" value={end} onChange={e=>{setEnd(e.target.value);setErrors(er=>({...er,end:null}));}}
                min={start||(tp.code==='SICK'?undefined:todayIso)}/>
              {errors.end&&<div style={{color:'var(--red)',fontSize:11.5,marginTop:4}}>{errors.end}</div>}
            </Field>
          </div>

          {days>0&&(
            <div style={{padding:'12px 16px',borderRadius:10,background:'var(--accent-softer)',border:'1px solid var(--accent-soft)',display:'flex',alignItems:'center',gap:10}}>
              <Icon d={IC.calendar} size={18} style={{color:'var(--accent-strong)',flexShrink:0}}/>
              <div>
                <div style={{fontWeight:700,fontSize:14,color:'var(--accent-strong)'}}>{days} {plural(days,'рабочий день','рабочих дня','рабочих дней')}</div>
                <div className="muted" style={{fontSize:12}}>{fmtDateRange(start,end)}</div>
              </div>
            </div>
          )}

          {tp.code==='SICK'&&(
            <div style={{padding:'12px 14px',borderRadius:10,background:'var(--amber-soft)',border:'1px solid oklch(0.74 0.13 75 / 0.3)',fontSize:13,color:'oklch(0.48 0.12 70)',lineHeight:1.5}}>
              <Icon d={IC.flag} size={15} style={{verticalAlign:'middle',marginRight:6}}/>
              Больничный можно подать задним числом — укажите фактические даты.
            </div>
          )}
          {tp.code==='TRIP'&&(
            <div style={{padding:'12px 14px',borderRadius:10,background:'var(--amber-soft)',border:'1px solid oklch(0.74 0.13 75 / 0.3)',fontSize:13,color:'oklch(0.48 0.12 70)',lineHeight:1.5}}>
              <Icon d={IC.flag} size={15} style={{verticalAlign:'middle',marginRight:6}}/>
              Согласуйте маршрут и расходы с руководителем до выезда.
            </div>
          )}

          <Field label="Комментарий">
            <textarea className="input" value={comment} onChange={e=>setComment(e.target.value)}
              placeholder="Причина, пожелания по замене, дополнительная информация…"
              style={{height:90,resize:'none',padding:'10px 12px',lineHeight:1.5}}/>
          </Field>

          <div className="muted" style={{fontSize:12.5,lineHeight:1.5,padding:'10px 14px',background:'var(--surface-2)',borderRadius:10}}>
            Заявку согласует ваш руководитель. Утверждённое отсутствие появится в табеле, списать часы на эти дни будет нельзя.
          </div>
        </div>

        <div style={{padding:'16px 26px',borderTop:'1px solid var(--border)',display:'flex',gap:10,flexShrink:0}}>
          <button className="btn" onClick={()=>save(false)} disabled={busy} style={{flex:1}}>Сохранить черновик</button>
          <button className="btn primary" onClick={()=>save(true)} disabled={busy} style={{flex:1}}>
            <Icon d={IC.send} size={15}/>{busy?'Отправка…':'Отправить на согласование'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---- Absence Detail Drawer ---- */
function AbsenceDetailDrawer({ absence, isManager, isOwner, empName, onClose, onChanged, showToast }){
  const tp=absence.absence_type;
  const st=ABS_ST_UI[absence.status]||{cls:''};
  const [busy,setBusy]=useState(false);
  const [rejectOpen,setRejectOpen]=useState(false);
  const [rejectComment,setRejectComment]=useState('');

  const act=async(fn, msg)=>{
    setBusy(true);
    try{ await fn(); showToast(msg); onChanged(); onClose(); }
    catch(err){ showToast(err.detail||'Не удалось выполнить действие'); }
    finally{ setBusy(false); }
  };

  const doReject=()=>{
    if(!rejectComment.trim()){ showToast('Укажите причину отклонения'); return; }
    act(()=>API.absence.rejectAbsence(absence.id, rejectComment.trim()), 'Заявка отклонена');
  };

  return (
    <div style={{position:'fixed',inset:0,zIndex:130,display:'flex',justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.35)',backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative',width:460,maxWidth:'94vw',height:'100%',background:'var(--surface)',
        borderLeft:'1px solid var(--border)',boxShadow:'var(--shadow-lg)',overflowY:'auto',padding:26}}>

        {/* header */}
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:6}}>
          <div style={{display:'flex',gap:14,alignItems:'center'}}>
            <span style={{width:50,height:50,borderRadius:13,background:absTypeBg(tp.color),display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
              <Icon d={IC[ABS_TYPE_ICON[tp.code]]||IC.calendar} size={24} style={{color:tp.color}}/>
            </span>
            <div>
              <h2 style={{fontSize:19}}>{tp.name}</h2>
              {(empName||isOwner)&&<div className="muted" style={{fontSize:12.5,marginTop:3}}>{isOwner?'Ваша заявка':empName}</div>}
            </div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
        </div>

        <div style={{marginBottom:20}}>
          <span className={'badge '+st.cls} style={{display:'inline-flex'}}><span className="dot"/>{absence.status}</span>
        </div>

        {/* details grid */}
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
          {[{label:'Дата начала',val:fmtDateY(absence.date_from)},
            {label:'Дата окончания',val:fmtDateY(absence.date_to)},
            {label:'Рабочих дней',val:absence.days_count+' '+plural(absence.days_count,'день','дня','дней')},
            {label:'Подана',val:absence.submitted_at?fmtDateY(absence.submitted_at):'черновик'},
          ].map(({label,val})=>(
            <div key={label} style={{padding:'12px 14px',background:'var(--surface-2)',borderRadius:10,border:'1px solid var(--border)'}}>
              <div className="muted" style={{fontSize:11.5,fontWeight:600,marginBottom:4}}>{label}</div>
              <div style={{fontWeight:700,fontSize:15}}>{val}</div>
            </div>
          ))}
        </div>

        {absence.comment&&(
          <div style={{marginTop:14,padding:'14px 16px',background:'var(--surface-2)',borderRadius:10,border:'1px solid var(--border)'}}>
            <div className="muted" style={{fontSize:11.5,fontWeight:600,marginBottom:6}}>Комментарий</div>
            <div style={{fontSize:14,lineHeight:1.55}}>{absence.comment}</div>
          </div>
        )}

        {absence.status==='Согласована'&&absence.approved_at&&(
          <div style={{marginTop:14,padding:'12px 14px',background:'var(--green-soft)',borderRadius:10,border:'1px solid oklch(0.62 0.13 155 / 0.25)',fontSize:13}}>
            <span style={{fontWeight:600}}>Утверждена</span>
            <span className="muted"> · {fmtDateY(absence.approved_at)}</span>
          </div>
        )}

        {absence.status==='Отклонена'&&(
          <div style={{marginTop:14,padding:'12px 14px',background:'var(--red-soft)',borderRadius:10,border:'1px solid oklch(0.60 0.18 22 / 0.25)',fontSize:13,lineHeight:1.5}}>
            <div style={{fontWeight:700,color:'var(--red)',marginBottom:absence.rejection_comment?4:0}}>Заявка отклонена</div>
            {absence.rejection_comment&&<div>Причина: {absence.rejection_comment}</div>}
          </div>
        )}

        {/* действия владельца */}
        {isOwner&&absence.status==='Черновик'&&(
          <div style={{display:'flex',gap:10,marginTop:24}}>
            <button className="btn" style={{flex:1,color:'var(--red)'}} disabled={busy}
              onClick={()=>act(()=>API.absence.withdrawAbsence(absence.id), 'Черновик удалён')}>
              <Icon d={IC.trash} size={15}/>Удалить
            </button>
            <button className="btn primary" style={{flex:1}} disabled={busy}
              onClick={()=>act(()=>API.absence.submitAbsence(absence.id), 'Заявка отправлена на согласование')}>
              <Icon d={IC.send} size={15}/>Отправить
            </button>
          </div>
        )}
        {isOwner&&absence.status==='На согласовании'&&(
          <button className="btn" style={{width:'100%',marginTop:24,color:'var(--red)'}} disabled={busy}
            onClick={()=>act(()=>API.absence.withdrawAbsence(absence.id), 'Заявка отозвана')}>
            <Icon d={IC.x} size={15}/>Отозвать заявку
          </button>
        )}

        {/* действия менеджера */}
        {isManager&&absence.status==='На согласовании'&&!rejectOpen&&(
          <div style={{display:'flex',gap:10,marginTop:isOwner?10:24}}>
            <button className="btn" style={{flex:1,color:'var(--red)'}} disabled={busy} onClick={()=>setRejectOpen(true)}>
              <Icon d={IC.x} size={15}/>Отклонить
            </button>
            <button className="btn primary" style={{flex:1}} disabled={busy}
              onClick={()=>act(()=>API.absence.approveAbsence(absence.id), 'Заявка утверждена')}>
              <Icon d={IC.check} size={15}/>Утвердить
            </button>
          </div>
        )}
        {isManager&&rejectOpen&&(
          <div style={{marginTop:24,padding:'14px 16px',background:'var(--surface-2)',borderRadius:10,border:'1px solid var(--border)'}}>
            <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:8}}>Причина отклонения *</div>
            <textarea className="input" value={rejectComment} onChange={e=>setRejectComment(e.target.value)}
              placeholder="Сотрудник увидит эту причину в заявке" autoFocus
              style={{height:70,resize:'none',padding:'10px 12px',lineHeight:1.5}}/>
            <div style={{display:'flex',gap:8,marginTop:10}}>
              <button className="btn sm" style={{flex:1}} disabled={busy} onClick={()=>setRejectOpen(false)}>Отмена</button>
              <button className="btn sm primary" style={{flex:1,background:'var(--red)',borderColor:'var(--red)'}} disabled={busy} onClick={doReject}>
                Отклонить
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function fmtDateRange(start,end){
  const s=new Date(start),e=new Date(end);
  const mo=['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
  if(s.getMonth()===e.getMonth()&&s.getFullYear()===e.getFullYear()){
    return s.getDate()+' – '+e.getDate()+' '+mo[e.getMonth()]+' '+e.getFullYear();
  }
  return s.getDate()+' '+mo[s.getMonth()]+' – '+e.getDate()+' '+mo[e.getMonth()]+' '+e.getFullYear();
}

Object.assign(window, { AbsencesScreen });
