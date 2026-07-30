/* ============ SCREEN: Авторизация ============ */
function LoginScreen({ onLogin }){
  const [email,setEmail]=useState('');
  const [pass,setPass]=useState('');
  const [loading,setLoading]=useState(false);
  const [resetSent,setResetSent]=useState(false);
  const [error,setError]=useState(null);
  // Временный пароль (из reset-заявки): бэк требует сменить его до входа в систему
  const [forceChange,setForceChange]=useState(null); // { tempPassword } | null

  const submit=async(e)=>{
    e && e.preventDefault();
    if(!email.trim() || !pass){ setError('Укажите почту и пароль'); return; }
    setError(null); setResetSent(false); setLoading(true);
    try{
      const data=await API.auth.login(email.trim(), pass);
      if(data.must_change_password){
        setForceChange({ tempPassword:pass });
      }else{
        onLogin(API.uiRole());
      }
    }catch(err){
      setError(err.detail || 'Не удалось войти');
    }finally{
      setLoading(false);
    }
  };

  const cancelForceChange=async()=>{
    await API.auth.logout().catch(()=>{});
    setForceChange(null); setPass('');
  };

  const forgotPassword=async(e)=>{
    e.preventDefault();
    if(!email.trim()){ setError('Укажите почту или табельный номер — по нему менеджер найдёт вашу учётку'); return; }
    setError(null);
    try{
      await API.auth.requestPasswordReset(email.trim());
      setResetSent(true);
    }catch(err){
      setError(err.detail || 'Не удалось отправить заявку');
    }
  };

  return (
    <div style={{minHeight:'100%', display:'grid', gridTemplateColumns:'1fr', placeItems:'center', padding:24,
      background:'radial-gradient(1200px 600px at 70% -10%, var(--accent-softer), transparent), var(--bg)'}}>
      <div className="fade-in" style={{width:'100%', maxWidth:920, display:'grid', gridTemplateColumns:'1.05fr 1fr',
        background:'var(--surface)', border:'1px solid var(--border)', borderRadius:20, overflow:'hidden', boxShadow:'var(--shadow-lg)'}}>

        {/* left — brand panel */}
        <div style={{padding:'44px 44px 40px', display:'flex', flexDirection:'column', justifyContent:'space-between',
          background:'linear-gradient(160deg, var(--accent-softer), var(--surface-2))', borderRight:'1px solid var(--border)'}}>
          <Logo big/>
          <div>
            <div style={{fontSize:26, fontWeight:800, letterSpacing:'-.02em', lineHeight:1.18, marginBottom:14}}>
              Учёт трудозатрат<br/>без таблиц и хаоса
            </div>
            <p className="muted" style={{fontSize:14, lineHeight:1.55, maxWidth:330, margin:0}}>
              Списывайте часы по проектам, ведите команду и собирайте отчётность для руководства — в одном окне.
            </p>
            <div style={{display:'flex', gap:22, marginTop:28}}>
              {[['Проектов','24'],['Сотрудников','86'],['Списано за май','12 480 ч']].map((s,i)=>(
                <div key={i}>
                  <div className="tnum" style={{fontSize:19, fontWeight:800}}>{s[1]}</div>
                  <div className="muted" style={{fontSize:11.5}}>{s[0]}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="muted" style={{fontSize:11.5}}>Внутренний портал · только для сотрудников компании</div>
        </div>

        {/* right — form */}
        <div style={{padding:'48px 44px'}}>
          <h2 style={{fontSize:21, marginBottom:6}}>Вход в систему</h2>
          <p className="muted" style={{fontSize:13.5, marginBottom:26, marginTop:0}}>Используйте корпоративную учётную запись</p>

          <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:16}}>
            <Field label="Рабочая почта или табельный номер">
              <div style={{position:'relative'}}>
                <span style={{position:'absolute', left:11, top:10, color:'var(--text-3)'}}><Icon d={IC.mail} size={18}/></span>
                <input className="input" style={{paddingLeft:38}} value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@company.ru" type="text"/>
              </div>
            </Field>
            <Field label="Пароль">
              <input className="input" value={pass} onChange={e=>setPass(e.target.value)} type="password"/>
            </Field>

            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', fontSize:13}}>
              <label style={{display:'flex', alignItems:'center', gap:8, cursor:'pointer', color:'var(--text-2)'}}>
                <input type="checkbox" defaultChecked style={{accentColor:'var(--accent)', width:15, height:15}}/> Запомнить меня
              </label>
              <a href="#" onClick={forgotPassword} style={{fontWeight:600}}>Забыли пароль?</a>
            </div>

            {error && (
              <div style={{padding:'12px 14px', borderRadius:10, background:'var(--red-soft)', border:'1px solid oklch(0.60 0.18 22 / 0.35)',
                display:'flex', gap:10, alignItems:'flex-start'}}>
                <span style={{color:'var(--red)', flexShrink:0, marginTop:1}}><Icon d={IC.shield} size={17}/></span>
                <div style={{fontSize:13, fontWeight:600, color:'oklch(0.50 0.16 25)'}}>{error}</div>
              </div>
            )}

            {resetSent && (
              <div style={{padding:'12px 14px', borderRadius:10, background:'var(--amber-soft)', border:'1px solid oklch(0.74 0.13 75 / 0.35)',
                display:'flex', gap:10, alignItems:'flex-start'}}>
                <span style={{color:'var(--amber)', flexShrink:0, marginTop:1}}><Icon d={IC.bell} size={17}/></span>
                <div>
                  <div style={{fontWeight:700, fontSize:13, color:'oklch(0.48 0.12 70)'}}>  Заявка отправлена</div>
                  <div style={{fontSize:12.5, color:'oklch(0.48 0.12 70)', marginTop:2, lineHeight:1.4}}>
                    Ваш менеджер получит уведомление и сформирует временный пароль. Ожидайте сообщения в чате портала.
                  </div>
                </div>
              </div>
            )}

            <button className="btn primary" type="submit" style={{height:44, fontSize:14.5, marginTop:4}} disabled={loading}>
              {loading ? 'Входим…' : <>Войти<Icon d={IC.chevR} size={17}/></>}
            </button>
          </form>

          <div style={{display:'flex', alignItems:'center', gap:8, marginTop:22, color:'var(--text-3)', fontSize:12.5}}>
            <Icon d={IC.user} size={15}/> Нет доступа? Обратитесь к системному администратору
          </div>
        </div>
      </div>

      {forceChange && <ForceChangePasswordModal tempPassword={forceChange.tempPassword}
        onDone={()=>onLogin(API.uiRole())} onCancel={cancelForceChange}/>}
    </div>
  );
}

/* ---- Принудительная смена временного пароля перед входом ---- */
function ForceChangePasswordModal({ tempPassword, onDone, onCancel }){
  const [next1,setNext1]=useState('');
  const [next2,setNext2]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState(null);

  const submit=async(e)=>{
    e.preventDefault();
    if(next1!==next2){ setError('Пароли не совпадают'); return; }
    if(next1===tempPassword){ setError('Новый пароль должен отличаться от временного'); return; }
    setError(null); setBusy(true);
    try{
      await API.auth.changePassword(tempPassword, next1);
      onDone();
    }catch(err){
      setError(err.detail || 'Не удалось сменить пароль');
    }finally{
      setBusy(false);
    }
  };

  return (
    <div style={{position:'fixed',inset:0,zIndex:300,display:'flex',alignItems:'center',justifyContent:'center',
      background:'oklch(0.25 0.02 255 / 0.55)',backdropFilter:'blur(3px)'}}>
      <div className="card fade-in" style={{width:440,maxWidth:'94vw',padding:28,boxShadow:'var(--shadow-lg)'}}>
        <div style={{display:'flex',alignItems:'flex-start',gap:14,marginBottom:20}}>
          <span style={{width:44,height:44,borderRadius:11,background:'var(--amber-soft)',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
            <Icon d={IC.key} size={22} style={{color:'oklch(0.48 0.12 70)'}}/>
          </span>
          <div>
            <h2 style={{fontSize:17}}>Нужно сменить пароль</h2>
            <div className="muted" style={{fontSize:12.5,marginTop:3,lineHeight:1.5}}>
              Вы вошли по временному паролю. Установите новый постоянный пароль, чтобы продолжить.
            </div>
          </div>
        </div>

        <form onSubmit={submit} style={{display:'flex',flexDirection:'column',gap:14}}>
          <Field label="Новый пароль">
            <input className="input" type="password" value={next1} onChange={e=>{setNext1(e.target.value);setError(null);}}
              placeholder="Минимум 8 символов" autoComplete="new-password" autoFocus/>
          </Field>
          <Field label="Повторите новый пароль">
            <input className="input" type="password" value={next2} onChange={e=>{setNext2(e.target.value);setError(null);}}
              placeholder="••••••••" autoComplete="new-password"/>
          </Field>
          <div className="muted" style={{fontSize:11.5,marginTop:-6}}>
            Минимум 8 символов, заглавная и строчная буквы, цифра, спецсимвол; не должен совпадать с временным
          </div>

          {error && (
            <div style={{padding:'11px 14px',borderRadius:10,background:'var(--red-soft)',border:'1px solid oklch(0.60 0.18 22 / 0.35)',
              display:'flex',gap:9,alignItems:'flex-start'}}>
              <span style={{color:'var(--red)',flexShrink:0,marginTop:1}}><Icon d={IC.shield} size={16}/></span>
              <div style={{fontSize:12.5,fontWeight:600,color:'oklch(0.50 0.16 25)'}}>{error}</div>
            </div>
          )}

          <button className="btn primary" type="submit" disabled={busy||!next1||!next2} style={{height:42,marginTop:2}}>
            {busy ? 'Сохранение…' : 'Сменить пароль и продолжить'}
          </button>
        </form>

        <button onClick={onCancel} disabled={busy}
          style={{display:'block',margin:'16px auto 0',border:'none',background:'transparent',cursor:'pointer',
            fontSize:12.5,color:'var(--text-3)',fontWeight:600}}>
          Выйти и вернуться к входу
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }){
  return (
    <label style={{display:'block'}}>
      <div className="muted" style={{fontSize:12, fontWeight:600, marginBottom:7}}>{label}</div>
      {children}
    </label>
  );
}

/* logo placeholder — easy to swap for client's brand */
function Logo({ big, light }){
  const s = big ? 34 : 28;
  return (
    <div style={{display:'inline-flex', alignItems:'center', gap:10}}>
      <span style={{width:s, height:s, borderRadius:9, background:'var(--accent)', display:'inline-flex', alignItems:'center', justifyContent:'center',
        color:'#fff', boxShadow:'var(--shadow-sm)'}}>
        <Icon d={IC.clock} size={big?21:18} stroke={2.2}/>
      </span>
      <span style={{fontWeight:800, fontSize:big?20:17, letterSpacing:'-.02em', color:light?'#fff':'var(--text)'}}>Табель</span>
    </div>
  );
}

Object.assign(window, { LoginScreen, Logo, Field });
