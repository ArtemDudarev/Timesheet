/* ============ SCREEN: Чат — живые данные (chat_service + WebSocket) ============ */

const CH_EMOJI = ['👍','🔥','🎉','😀','😅','😂','🤝','👌','🙏','💪','🚀','✅','❌','👀','🤔','😴','☕','🍕','❤️','🎯','📎','📌','⏰','💡'];

// Метки для сообщений-ссылок на согласования (ApprovalRefType бэка)
const CH_APPROVAL_LABEL = {
  TIMESHEET: 'Табель',
  OVERTIME: 'Переработка',
  ABSENCE: 'Отсутствие',
};

// naive UTC от бэка → локальное время
function chDate(iso){ return new Date(/[Zz]$|[+-]\d\d:\d\d$/.test(iso)?iso:iso+'Z'); }
function chTime(iso){ return chDate(iso).toLocaleTimeString('ru',{hour:'2-digit',minute:'2-digit'}); }
function chDay(iso){
  const d=chDate(iso), now=new Date();
  const today=now.toDateString()===d.toDateString();
  const yest=new Date(now.getTime()-864e5).toDateString()===d.toDateString();
  if(today) return 'Сегодня';
  if(yest) return 'Вчера';
  return d.toLocaleDateString('ru',{day:'numeric',month:'long'});
}

function ChatScreen({ showToast }){
  const myId=(API.session()||{}).userId;
  const [channels,setChannels]=useState(null);
  const [error,setError]=useState(null);
  const [empList,setEmpList]=useState([]);      // management (менеджер) — для нового DM и имён
  const [active,setActive]=useState(null);
  const [store,setStore]=useState({});          // channelId → {list, hasMore, members:{id→name}}
  const [unread,setUnread]=useState({});
  const [typing,setTyping]=useState({});        // channelId → {empId: ts}
  const [wsOnline,setWsOnline]=useState(false);
  const [q,setQ]=useState('');
  const [msgSearch,setMsgSearch]=useState('');
  const [draft,setDraft]=useState('');
  const [replyTo,setReplyTo]=useState(null);
  const [editingMsg,setEditingMsg]=useState(null);
  const [msgMenuId,setMsgMenuId]=useState(null);
  const [emojiOpen,setEmojiOpen]=useState(false);
  const [newDmOpen,setNewDmOpen]=useState(false);
  const [myLead,setMyLead]=useState(null);
  const [tick,setTick]=useState(0);             // перерисовка «печатает…»

  const wsRef=useRef(null);
  const scrollRef=useRef(null);
  const draftRef=useRef(null);
  const emojiRef=useRef(null);
  const menuRef=useRef(null);
  const activeRef=useRef(null);
  const lastTypingSent=useRef(0);
  activeRef.current=active;

  /* ── загрузка ── */
  const loadChannels=()=>API.chat.getChannels().then(chs=>{ setChannels(chs); return chs; });

  useEffect(()=>{
    loadChannels().then(chs=>{ if(chs.length&&!activeRef.current) openChannel(chs[0].id); })
      .catch(err=>setError(err.detail||'Не удалось загрузить чаты'));
    API.management.getEmployees()
      .then(list=>setEmpList(list.map(e=>({ id:e.id, name:`${e.first_name} ${e.last_name}` }))))
      .catch(()=>{ // у сотрудника нет employee:list — предложим диалог с руководителем
        API.profile.getEmployee(myId).then(p=>{ if(p.lead_id) setMyLead(p.lead_id); }).catch(()=>{});
      });

    wsRef.current=API.chat.connect({
      onStatus:(s)=>setWsOnline(s==='online'),
      onMessage:(data)=>{
        const chId=data.channel_id, msg=data.message;
        setStore(st=>{
          if(!st[chId]) return st; // канал ещё не открывали — история подтянется при открытии
          if(st[chId].list.some(m=>m.id===msg.id)) return st;
          return { ...st, [chId]:{ ...st[chId], list:[...st[chId].list, msg] } };
        });
        if(activeRef.current===chId){
          wsRef.current&&wsRef.current.send({ event:'read', channel_id:chId });
        }else{
          setUnread(u=>({ ...u, [chId]:(u[chId]||0)+1 }));
        }
        // новый DM от незнакомого канала — обновляем список
        setChannels(chs=>{ if(chs&&!chs.some(c=>c.id===chId)) loadChannels().catch(()=>{}); return chs; });
      },
      onTyping:(data)=>setTyping(t=>({ ...t, [data.channel_id]:{ ...(t[data.channel_id]||{}), [data.employee_id]:Date.now() } })),
    });
    const timer=setInterval(()=>setTick(x=>x+1), 2000);
    return ()=>{ wsRef.current&&wsRef.current.close(); clearInterval(timer); };
  },[]);

  const openChannel=(chId)=>{
    setActive(chId); setReplyTo(null); setEditingMsg(null); setDraft(''); setMsgSearch(''); setMsgMenuId(null); setNewDmOpen(false);
    setUnread(u=>{ const n={...u}; delete n[chId]; return n; });
    wsRef.current&&wsRef.current.send({ event:'read', channel_id:chId });
    setStore(st=>{
      if(st[chId]) return st;
      Promise.all([ API.chat.getMessages(chId), API.chat.getMembers(chId).catch(()=>[]) ])
        .then(([msgs, members])=>{
          const mMap={}; members.forEach(m=>{ mMap[m.id]=`${m.first_name} ${m.last_name}`; });
          setStore(s2=>({ ...s2, [chId]:{ list:[...msgs].reverse(), hasMore:msgs.length===50, members:mMap } }));
        })
        .catch(err=>showToast(err.detail||'Не удалось загрузить сообщения'));
      return st;
    });
  };

  const loadMore=()=>{
    const cur=store[active]; if(!cur||!cur.list.length) return;
    API.chat.getMessages(active, cur.list[0].created_at).then(older=>{
      setStore(st=>({ ...st, [active]:{ ...st[active], list:[...[...older].reverse(), ...st[active].list], hasMore:older.length===50 } }));
    }).catch(err=>showToast(err.detail||'Не удалось загрузить историю'));
  };

  /* ── имена ── */
  const empMap=useMemo(()=>{ const m={}; empList.forEach(e=>{ m[e.id]=e.name; }); return m; },[empList]);
  const nameFor=(chId, empId)=>{
    if(empId===myId) return 'Вы';
    const ch=(channels||[]).find(c=>c.id===chId);
    if(ch&&ch.companion&&ch.companion.id===empId) return `${ch.companion.first_name} ${ch.companion.last_name}`;
    return (store[chId]&&store[chId].members[empId])||empMap[empId]||'Участник';
  };
  const channelTitle=(c)=>c.type==='DM'
    ? (c.companion?`${c.companion.first_name} ${c.companion.last_name}`:'Диалог')
    : (c.name||'Канал');

  /* ── действия ── */
  const send=async()=>{
    const txt=draft.trim(); if(!txt||!active) return;
    try{
      if(editingMsg){
        const upd=await API.chat.updateMessage(editingMsg.id, txt);
        setStore(st=>({ ...st, [active]:{ ...st[active], list:st[active].list.map(m=>m.id===upd.id?upd:m) } }));
        setEditingMsg(null);
      }else{
        const msg=await API.chat.sendMessage(active, { text:txt, reply_to_id:replyTo?replyTo.id:undefined });
        setStore(st=>({ ...st, [active]:{ ...st[active], list:[...st[active].list, msg] } }));
        setReplyTo(null);
      }
      setDraft(''); setEmojiOpen(false);
    }catch(err){ showToast(err.detail||'Не удалось отправить сообщение'); }
  };
  const removeMsg=async(m)=>{
    setMsgMenuId(null);
    try{
      await API.chat.deleteMessage(m.id);
      setStore(st=>({ ...st, [active]:{ ...st[active], list:st[active].list.filter(x=>x.id!==m.id) } }));
    }catch(err){ showToast(err.detail||'Не удалось удалить'); }
  };
  const togglePin=async(chId, ev)=>{
    ev&&ev.stopPropagation();
    try{ const upd=await API.chat.togglePin(chId); setChannels(chs=>chs.map(c=>c.id===chId?upd:c)); }
    catch(err){ showToast(err.detail||'Ошибка'); }
  };
  const toggleMute=async(chId)=>{
    try{ const upd=await API.chat.toggleMute(chId); setChannels(chs=>chs.map(c=>c.id===chId?upd:c)); }
    catch(err){ showToast(err.detail||'Ошибка'); }
  };
  const startDm=async(empId)=>{
    setNewDmOpen(false);
    try{
      const ch=await API.chat.createDm(empId);
      setChannels(chs=>chs&&chs.some(c=>c.id===ch.id)?chs:[...(chs||[]),ch]);
      openChannel(ch.id);
    }catch(err){ showToast(err.detail||'Не удалось открыть диалог'); }
  };
  const onDraftChange=(v)=>{
    setDraft(v);
    // typing не чаще раза в 2.5с
    if(active&&Date.now()-lastTypingSent.current>2500){
      lastTypingSent.current=Date.now();
      wsRef.current&&wsRef.current.send({ event:'typing', channel_id:active });
    }
  };
  const doReply=(m)=>{ setReplyTo(m); setEditingMsg(null); setMsgMenuId(null); setTimeout(()=>draftRef.current?.focus(),50); };
  const doEdit=(m)=>{ setEditingMsg(m); setReplyTo(null); setDraft(m.text||''); setMsgMenuId(null); setTimeout(()=>draftRef.current?.focus(),50); };

  /* ── закрытие поповеров ── */
  useEffect(()=>{
    if(!emojiOpen) return;
    const h=(e)=>{ if(emojiRef.current&&!emojiRef.current.contains(e.target)) setEmojiOpen(false); };
    document.addEventListener('mousedown',h); return ()=>document.removeEventListener('mousedown',h);
  },[emojiOpen]);
  useEffect(()=>{
    if(!msgMenuId) return;
    const h=(e)=>{ if(menuRef.current&&!menuRef.current.contains(e.target)) setMsgMenuId(null); };
    document.addEventListener('mousedown',h); return ()=>document.removeEventListener('mousedown',h);
  },[msgMenuId]);

  const thread=(store[active]&&store[active].list)||[];
  useEffect(()=>{ if(scrollRef.current) scrollRef.current.scrollTop=scrollRef.current.scrollHeight; },[active,thread.length]);

  if(error) return <ErrorCard text={error}/>;
  if(channels===null) return (
    <div className="fade-in" style={{display:'flex',gap:16}}>
      <div style={{width:290}}>{[0,1,2,3].map(i=><div key={i} className="skel" style={{height:56,marginBottom:8}}/>)}</div>
      <div style={{flex:1}} className="skel"/>
    </div>
  );

  const activeCh=channels.find(c=>c.id===active);
  const pinnedChs=channels.filter(c=>c.pinned);
  const restChs=channels.filter(c=>!c.pinned);
  const chFilter=(c)=>!q.trim()||channelTitle(c).toLowerCase().includes(q.toLowerCase());

  // «печатает…» — свежие typing-события активного канала
  const typingNames=active?Object.entries(typing[active]||{})
    .filter(([id,ts])=>Date.now()-ts<4000&&id!==myId)
    .map(([id])=>nameFor(active,id)):[];

  const visibleThread=msgSearch.trim()
    ? thread.filter(m=>m.text&&m.text.toLowerCase().includes(msgSearch.toLowerCase()))
    : thread;

  // Кандидаты для нового диалога
  const dmCandidates=empList.length
    ? empList.filter(e=>e.id!==myId)
    : (myLead?[{ id:myLead, name:'Ваш руководитель' }]:[]);

  const ConvRow=({ c })=>{
    const on=active===c.id;
    const un=unread[c.id];
    const title=channelTitle(c);
    return (
      <button onClick={()=>openChannel(c.id)}
        style={{display:'flex',alignItems:'center',gap:11,width:'100%',padding:'10px 12px',border:'none',textAlign:'left',
          background:on?'var(--accent-softer)':'transparent',borderRadius:10,cursor:'pointer',transition:'.12s'}}
        onMouseEnter={e=>{ if(!on) e.currentTarget.style.background='var(--surface-2)'; }}
        onMouseLeave={e=>{ if(!on) e.currentTarget.style.background='transparent'; }}>
        {c.type==='DM'
          ? <Avatar id={c.companion?c.companion.id:c.id} name={title} size={38}/>
          : <span style={{width:38,height:38,borderRadius:10,background:'var(--accent)',color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:12,flexShrink:0}}>
              {title.replace(/[^A-Za-zА-Яа-я0-9 ]/g,'').split(' ').map(w=>w[0]).slice(0,2).join('').toUpperCase()}
            </span>}
        <div style={{flex:1,minWidth:0}}>
          <div style={{display:'flex',alignItems:'center',gap:6}}>
            <span style={{fontWeight:700,fontSize:13.5,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{title}</span>
            {c.muted&&<Icon d={IC.bellOff||IC.bell} size={12} style={{color:'var(--text-3)',flexShrink:0}}/>}
          </div>
          <div className="muted" style={{fontSize:11.5,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
            {c.type==='DM'?'Личные сообщения':'Канал проекта'}
          </div>
        </div>
        {un>0&&!c.muted&&<span style={{minWidth:19,height:19,borderRadius:50,background:'var(--accent)',color:'#fff',fontSize:10.5,fontWeight:700,display:'inline-flex',alignItems:'center',justifyContent:'center',padding:'0 5px',flexShrink:0}}>{un}</span>}
        <span onClick={(e)=>togglePin(c.id,e)} title={c.pinned?'Открепить':'Закрепить'}
          style={{color:c.pinned?'var(--accent)':'var(--text-3)',opacity:c.pinned?1:0.4,flexShrink:0,cursor:'pointer',display:'flex'}}>
          <Icon d={IC.pin||IC.flag} size={13}/>
        </span>
      </button>
    );
  };

  return (
    <div className="fade-in" style={{display:'flex',gap:16,height:'calc(100vh - 130px)',minHeight:420}}>

      {/* ── сайдбар каналов ── */}
      <div className="card" style={{width:300,flexShrink:0,padding:12,display:'flex',flexDirection:'column',gap:8,overflow:'hidden'}}>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <div style={{position:'relative',flex:1}}>
            <span style={{position:'absolute',left:10,top:8,color:'var(--text-3)'}}><Icon d={IC.search} size={15}/></span>
            <input className="input" value={q} onChange={e=>setQ(e.target.value)} style={{height:32,paddingLeft:31,fontSize:12.5}} placeholder="Поиск чата…"/>
          </div>
          {dmCandidates.length>0&&(
            <button className="btn sm icon primary" title="Новое сообщение" onClick={()=>setNewDmOpen(o=>!o)} style={{width:32,height:32,flexShrink:0}}>
              <Icon d={IC.plus} size={15}/>
            </button>
          )}
        </div>

        {newDmOpen&&(
          <div className="card" style={{padding:6,maxHeight:220,overflowY:'auto',boxShadow:'var(--shadow-md)'}}>
            <div className="muted" style={{padding:'4px 8px',fontSize:10.5,fontWeight:700,textTransform:'uppercase',letterSpacing:'.05em'}}>Новое сообщение</div>
            {dmCandidates.map(e=>(
              <button key={e.id} onClick={()=>startDm(e.id)}
                style={{display:'flex',alignItems:'center',gap:9,width:'100%',padding:'7px 9px',border:'none',background:'transparent',borderRadius:8,cursor:'pointer',textAlign:'left'}}
                onMouseEnter={ev=>ev.currentTarget.style.background='var(--surface-2)'}
                onMouseLeave={ev=>ev.currentTarget.style.background='transparent'}>
                <Avatar id={e.id} name={e.name} size={26}/>
                <span style={{fontWeight:600,fontSize:13}}>{e.name}</span>
              </button>
            ))}
          </div>
        )}

        <div style={{flex:1,overflowY:'auto',display:'flex',flexDirection:'column',gap:2}}>
          {pinnedChs.filter(chFilter).length>0&&<div className="muted" style={{fontSize:10.5,fontWeight:700,letterSpacing:'.05em',textTransform:'uppercase',padding:'4px 10px'}}>Закреплённые</div>}
          {pinnedChs.filter(chFilter).map(c=><ConvRow key={c.id} c={c}/>)}
          {pinnedChs.length>0&&restChs.filter(chFilter).length>0&&<div className="muted" style={{fontSize:10.5,fontWeight:700,letterSpacing:'.05em',textTransform:'uppercase',padding:'8px 10px 4px'}}>Все чаты</div>}
          {restChs.filter(chFilter).map(c=><ConvRow key={c.id} c={c}/>)}
          {channels.length===0&&(
            <div className="muted" style={{fontSize:12.5,padding:'20px 12px',textAlign:'center',lineHeight:1.5}}>
              Чатов пока нет.{dmCandidates.length>0?' Начните диалог кнопкой «+».':' Каналы появятся при назначении на проект.'}
            </div>
          )}
        </div>
        <div style={{display:'flex',alignItems:'center',gap:6,padding:'4px 8px 0',borderTop:'1px solid var(--border)'}}>
          <span style={{width:8,height:8,borderRadius:50,background:wsOnline?'var(--green)':'var(--amber)',flexShrink:0}}/>
          <span className="muted" style={{fontSize:11}}>{wsOnline?'Соединение активно':'Переподключение…'}</span>
        </div>
      </div>

      {/* ── лента ── */}
      <div className="card" style={{flex:1,padding:0,display:'flex',flexDirection:'column',overflow:'hidden',minWidth:0}}>
        {!activeCh&&<div className="muted" style={{margin:'auto',fontSize:14}}>Выберите чат слева</div>}
        {activeCh&&<>
          {/* шапка */}
          <div style={{padding:'13px 18px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
            {activeCh.type==='DM'
              ? <Avatar id={activeCh.companion?.id||activeCh.id} name={channelTitle(activeCh)} size={38}/>
              : <span style={{width:38,height:38,borderRadius:10,background:'var(--accent)',color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:12}}>
                  {channelTitle(activeCh).slice(0,2).toUpperCase()}
                </span>}
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontWeight:800,fontSize:15}}>{channelTitle(activeCh)}</div>
              <div className="muted" style={{fontSize:12}}>
                {typingNames.length>0
                  ? <span style={{color:'var(--accent-strong)',fontWeight:600}}>{typingNames.join(', ')} печатает…</span>
                  : activeCh.type==='DM' ? 'личные сообщения'
                    : `${Object.keys(store[active]?.members||{}).length||'—'} ${plural(Object.keys(store[active]?.members||{}).length,'участник','участника','участников')}`}
              </div>
            </div>
            <div style={{position:'relative',width:200}}>
              <span style={{position:'absolute',left:10,top:8,color:'var(--text-3)'}}><Icon d={IC.search} size={14}/></span>
              <input className="input" value={msgSearch} onChange={e=>setMsgSearch(e.target.value)} style={{height:31,paddingLeft:30,fontSize:12.5}} placeholder="Поиск сообщений…"/>
            </div>
            <button className="btn ghost sm icon" title={activeCh.muted?'Включить уведомления':'Отключить уведомления'} onClick={()=>toggleMute(active)}>
              <Icon d={IC.bell} size={16} style={{color:activeCh.muted?'var(--text-3)':'var(--text)'}}/>
            </button>
          </div>

          {/* сообщения */}
          <div ref={scrollRef} style={{flex:1,overflowY:'auto',padding:'14px 18px',display:'flex',flexDirection:'column',gap:2}}>
            {store[active]?.hasMore&&!msgSearch&&(
              <button className="btn ghost sm" style={{alignSelf:'center',marginBottom:8}} onClick={loadMore}>Показать ещё</button>
            )}
            {!store[active]&&<div style={{display:'flex',flexDirection:'column',gap:10}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:44,width:'60%'}}/>)}</div>}
            {visibleThread.map((m,i)=>{
              const mine=m.author_id===myId;
              const prev=visibleThread[i-1];
              const newDay=!prev||chDay(prev.created_at)!==chDay(m.created_at);
              const replied=m.reply_to_id?thread.find(x=>x.id===m.reply_to_id):null;
              return (
                <React.Fragment key={m.id}>
                  {newDay&&(
                    <div style={{display:'flex',alignItems:'center',gap:10,margin:'12px 0 8px'}}>
                      <span style={{flex:1,height:1,background:'var(--border)'}}/>
                      <span className="muted" style={{fontSize:11,fontWeight:600}}>{chDay(m.created_at)}</span>
                      <span style={{flex:1,height:1,background:'var(--border)'}}/>
                    </div>
                  )}
                  <div style={{display:'flex',gap:9,justifyContent:mine?'flex-end':'flex-start',marginBottom:6,position:'relative'}}>
                    {!mine&&<Avatar id={m.author_id} name={nameFor(active,m.author_id)} size={30}/>}
                    <div style={{maxWidth:'68%',minWidth:0}}>
                      {!mine&&activeCh.type!=='DM'&&<div style={{fontSize:11.5,fontWeight:700,color:'var(--accent-strong)',marginBottom:2}}>{nameFor(active,m.author_id)}</div>}
                      <div onDoubleClick={()=>mine&&doEdit(m)}
                        style={{padding:'8px 12px',borderRadius:mine?'12px 12px 3px 12px':'12px 12px 12px 3px',
                          background:mine?'var(--accent)':'var(--surface-2)',color:mine?'#fff':'var(--text)',
                          border:mine?'none':'1px solid var(--border)',position:'relative',cursor:'default'}}>
                        {replied&&(
                          <div style={{borderLeft:`3px solid ${mine?'rgba(255,255,255,0.6)':'var(--accent)'}`,padding:'3px 8px',marginBottom:6,
                            background:mine?'rgba(255,255,255,0.12)':'var(--surface-3)',borderRadius:6,fontSize:12}}>
                            <div style={{fontWeight:700,fontSize:11}}>{nameFor(active,replied.author_id)}</div>
                            <div style={{opacity:0.85,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{replied.text||'…'}</div>
                          </div>
                        )}
                        {m.related_approval_type&&(
                          <div style={{display:'inline-flex',alignItems:'center',gap:6,padding:'3px 9px',borderRadius:999,marginBottom:m.text?6:0,
                            background:mine?'rgba(255,255,255,0.16)':'var(--amber-soft)',fontSize:11.5,fontWeight:700,
                            color:mine?'#fff':'oklch(0.48 0.12 70)'}}>
                            <Icon d={IC.check} size={12}/>Согласование · {CH_APPROVAL_LABEL[m.related_approval_type]||m.related_approval_type}
                          </div>
                        )}
                        {m.text&&<div style={{fontSize:13.5,lineHeight:1.45,whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{m.text}</div>}
                        <div style={{fontSize:10,opacity:0.65,marginTop:3,textAlign:'right'}}>
                          {m.edited&&'изм. · '}{chTime(m.created_at)}
                        </div>
                      </div>
                      {mine&&(
                        <div style={{position:'relative',display:'flex',justifyContent:'flex-end'}}>
                          <button onClick={()=>setMsgMenuId(msgMenuId===m.id?null:m.id)}
                            style={{border:'none',background:'transparent',cursor:'pointer',color:'var(--text-3)',fontSize:11,padding:'2px 4px'}}>⋯</button>
                          {msgMenuId===m.id&&(
                            <div ref={menuRef} className="card fade-in" style={{position:'absolute',top:'100%',right:0,zIndex:50,padding:4,boxShadow:'var(--shadow-lg)',minWidth:150}}>
                              <button className="btn ghost sm" style={{width:'100%',justifyContent:'flex-start'}} onClick={()=>doReply(m)}><Icon d={IC.chat} size={13}/>Ответить</button>
                              <button className="btn ghost sm" style={{width:'100%',justifyContent:'flex-start'}} onClick={()=>doEdit(m)}><Icon d={IC.edit} size={13}/>Редактировать</button>
                              <button className="btn ghost sm" style={{width:'100%',justifyContent:'flex-start',color:'var(--red)'}} onClick={()=>removeMsg(m)}><Icon d={IC.trash} size={13}/>Удалить</button>
                            </div>
                          )}
                        </div>
                      )}
                      {!mine&&(
                        <button onClick={()=>doReply(m)}
                          style={{border:'none',background:'transparent',cursor:'pointer',color:'var(--text-3)',fontSize:11,padding:'2px 4px'}}>Ответить</button>
                      )}
                    </div>
                  </div>
                </React.Fragment>
              );
            })}
            {store[active]&&visibleThread.length===0&&(
              <div className="muted" style={{margin:'auto',fontSize:13}}>{msgSearch?'Ничего не найдено':'Сообщений пока нет — напишите первым!'}</div>
            )}
          </div>

          {/* композер */}
          <div style={{borderTop:'1px solid var(--border)',padding:'10px 14px',flexShrink:0}}>
            {(replyTo||editingMsg)&&(
              <div style={{display:'flex',alignItems:'center',gap:8,padding:'6px 10px',marginBottom:8,background:'var(--surface-2)',borderRadius:8,borderLeft:'3px solid var(--accent)'}}>
                <Icon d={editingMsg?IC.edit:IC.chat} size={14} style={{color:'var(--accent)',flexShrink:0}}/>
                <div style={{flex:1,minWidth:0,fontSize:12}}>
                  <div style={{fontWeight:700}}>{editingMsg?'Редактирование':'Ответ: '+nameFor(active,replyTo.author_id)}</div>
                  <div className="muted" style={{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{(editingMsg||replyTo).text}</div>
                </div>
                <button className="btn ghost sm icon" style={{width:24,height:24}} onClick={()=>{setReplyTo(null);setEditingMsg(null);setDraft('');}}><Icon d={IC.x} size={13}/></button>
              </div>
            )}
            <div style={{display:'flex',gap:8,alignItems:'flex-end'}}>
              <div style={{position:'relative'}} ref={emojiRef}>
                <button className="btn ghost sm icon" onClick={()=>setEmojiOpen(o=>!o)} style={{fontSize:16}}>🙂</button>
                {emojiOpen&&(
                  <div className="card fade-in" style={{position:'absolute',bottom:'110%',left:0,zIndex:60,padding:8,boxShadow:'var(--shadow-lg)',
                    display:'grid',gridTemplateColumns:'repeat(6,1fr)',gap:2,width:220}}>
                    {CH_EMOJI.map(em=>(
                      <button key={em} onClick={()=>{setDraft(d=>d+em);setEmojiOpen(false);draftRef.current?.focus();}}
                        style={{border:'none',background:'transparent',cursor:'pointer',fontSize:18,padding:4,borderRadius:6}}
                        onMouseEnter={e=>e.currentTarget.style.background='var(--surface-2)'}
                        onMouseLeave={e=>e.currentTarget.style.background='transparent'}>{em}</button>
                    ))}
                  </div>
                )}
              </div>
              <textarea ref={draftRef} className="input" value={draft} rows={1}
                onChange={e=>onDraftChange(e.target.value)}
                onKeyDown={e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); send(); } if(e.key==='Escape'){ setReplyTo(null); setEditingMsg(null); setDraft(''); } }}
                placeholder={`Сообщение… (Enter — отправить)`}
                style={{flex:1,resize:'none',minHeight:38,maxHeight:120,padding:'9px 12px',lineHeight:1.4,fontSize:13.5}}/>
              <button className="btn primary sm icon" onClick={send} disabled={!draft.trim()} style={{width:38,height:38}}>
                <Icon d={IC.send} size={16}/>
              </button>
            </div>
          </div>
        </>}
      </div>
    </div>
  );
}

Object.assign(window, { ChatScreen });
