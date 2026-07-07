const {useState, useMemo} = React;

/* ── EMBED / LEAD SOURCE ──────────────────────────
   Один и тот же код обслуживает и отдельный сайт (index.html), и
   встраиваемый виджет (widget.html, EMBED=true). Источник лида
   (standalone / widget) и адрес страницы-хозяина (при встраивании —
   document.referrer внутри iframe равен URL родительской страницы)
   уходят вместе с заявкой, чтобы в Telegram-уведомлении было видно,
   с какого сайта и какой страницы пришёл клиент. */
const EMBED = !!window.PLATFORMA_EMBED;
const LEAD_SOURCE = EMBED ? "widget" : "standalone";
const PAGE_URL = (typeof document !== "undefined" && document.referrer) || (typeof location !== "undefined" ? location.href : "");

/* ── API ──────────────────────────────────────── */
// Если фронт и бэкенд на разных доменах — задайте window.PLATFORMA_API_BASE
// ДО этого скрипта через отдельный тег script в head, например:
// window.PLATFORMA_API_BASE = "https://api.platforma-msk.ru"
// (не пишите здесь буквальный тег "script" с закрывающей частью —
// браузер разберёт его как конец этого блока, даже внутри комментария)
const API_BASE = window.PLATFORMA_API_BASE || "";

async function apiCalculate(calcType, payload){
  const res = await fetch(`${API_BASE}/api/calculate/${calcType}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if(!res.ok){
    let detail = "Не удалось выполнить расчёт";
    try{ const j = await res.json(); if(j.detail) detail = j.detail; }catch(e){}
    throw new Error(detail);
  }
  return res.json();
}

async function apiCreateQuote(calcId, supplierId){
  const res = await fetch(`${API_BASE}/api/quotes?calc_id=${calcId}&supplier_id=${supplierId}`, {
    method: "POST",
  });
  if(!res.ok){
    let detail = "Не удалось сформировать смету";
    try{ const j = await res.json(); if(j.detail) detail = j.detail; }catch(e){}
    throw new Error(detail);
  }
  return res.json();
}

async function apiSendRequest(body){
  const res = await fetch(`${API_BASE}/api/quotes/send-request`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  if(!res.ok) throw new Error("Не удалось отправить заявку");
  return res.json();
}

/* ── UTILS ────────────────────────────────────── */
const fmt = n => new Intl.NumberFormat("ru-RU").format(Math.round(n)) + " ₽";
const CAT_LABELS = {main:"Основной материал",elem:"Элементы и комплектующие",wood:"Деревянные конструкции",fastener:"Крепёж",seal:"Уплотнители"};

// Человекочитаемая дата обновления цен поставщика — "сегодня", "вчера",
// "3 дня назад" или конкретная дата, если давно.
function formatPriceDate(iso){
  if(!iso) return null;
  const d = new Date(iso);
  if(Number.isNaN(d.getTime())) return null;
  const now = new Date();
  const startOfDay = x => new Date(x.getFullYear(),x.getMonth(),x.getDate());
  const days = Math.round((startOfDay(now) - startOfDay(d)) / 86400000);
  if(days<=0) return "сегодня";
  if(days===1) return "вчера";
  if(days<7) return `${days} дн. назад`;
  return d.toLocaleDateString("ru-RU",{day:"numeric",month:"long",year: d.getFullYear()!==now.getFullYear() ? "numeric" : undefined});
}

// Валидация числового поля на лету — понятный текст ошибки вместо просто disabled-кнопки.
function validateNumber(value, {label, min, max, integer}={}){
  if(value===""||value===null||value===undefined||Number.isNaN(value)){
    return `Укажите ${label.toLowerCase()}`;
  }
  if(integer && !Number.isInteger(value)){
    return `${label}: введите целое число`;
  }
  if(min!==undefined && value < min){
    return `${label}: минимум ${min}`;
  }
  if(max!==undefined && value > max){
    return `${label}: максимум ${max}`;
  }
  return null;
}

/* ── SHARED COMPONENTS ────────────────────────── */
function FieldRow({label, children, error}){
  return (
    <div style={{marginBottom:"10px"}}>
      <div style={{display:"grid",gridTemplateColumns:"130px 1fr",gap:"10px",alignItems:"center"}}>
        <label style={{fontSize:"13px",color:"var(--text2)"}}>{label}</label>
        {children}
      </div>
      {error && <div className="field-error">{error}</div>}
    </div>
  );
}

// StepBar: пройденные шаги (i < current) кликабельны — можно вернуться назад
// без потери введённых данных (данные форм живут в состоянии App, а не форм).
function StepBar({steps, current, onStepClick}){
  return (
    <div style={{display:"flex",gap:"0",marginBottom:"1.5rem",position:"relative"}}>
      <div style={{position:"absolute",top:"14px",left:"14px",right:"14px",height:"1px",background:"var(--border2)"}}/>
      {steps.map((s,i) => {
        const clickable = !!onStepClick && i < current;
        const Tag = clickable ? "button" : "div";
        return (
          <Tag key={i}
            onClick={clickable ? () => onStepClick(i) : undefined}
            aria-current={i===current ? "step" : undefined}
            style={{
              flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:"6px",
              position:"relative",zIndex:1,background:"none",border:"none",font:"inherit",
              color:"inherit",padding:"8px 2px",minHeight:"44px",
              cursor: clickable ? "pointer" : "default",
            }}>
            <div style={{
              width:"28px",height:"28px",borderRadius:"50%",
              background: i <= current ? "var(--accent)" : "var(--bg)",
              border: i <= current ? "none" : "1px solid var(--border2)",
              color: i <= current ? "var(--accent-fg)" : "var(--text3)",
              display:"flex",alignItems:"center",justifyContent:"center",
              fontSize:"12px",fontWeight:"500",
            }}>
              {i < current ? "✓" : i+1}
            </div>
            <span style={{fontSize:"11px",color:i===current?"var(--text)":"var(--text3)",textAlign:"center",lineHeight:1.2}}>{s}</span>
          </Tag>
        );
      })}
    </div>
  );
}

// Sticky-блок с итоговой суммой — на мобильном фиксируется снизу экрана,
// чтобы итог и действия были видны сразу, без скролла.
function StickyTotal({label, amount, children}){
  return (
    <React.Fragment>
      <div className="sticky-total">
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",gap:"12px",marginBottom: children ? "10px" : 0}}>
          <span style={{fontSize:"13px",color:"var(--text2)"}}>{label}</span>
          <span style={{fontSize:"20px",fontWeight:"700"}}>{amount}</span>
        </div>
        {children}
      </div>
      <div className="sticky-total-spacer"/>
    </React.Fragment>
  );
}

function InfoBox({children}){
  return (
    <div style={{padding:"10px 12px",background:"var(--surface2)",borderRadius:"var(--r-md)",fontSize:"13px",color:"var(--text2)",marginBottom:"14px"}}>
      {children}
    </div>
  );
}

function ErrorBox({message, onRetry}){
  return (
    <div style={{padding:"12px 14px",background:"var(--red-bg)",border:"0.5px solid var(--red-border)",borderRadius:"var(--r-md)",marginBottom:"14px",display:"flex",justifyContent:"space-between",alignItems:"center",gap:"12px"}}>
      <span style={{fontSize:"13px",color:"var(--red-fg)"}}>{message}</span>
      {onRetry && <button className="btn-ghost" style={{fontSize:"12px",padding:"6px 12px",flexShrink:0}} onClick={onRetry}>Повторить</button>}
    </div>
  );
}

/* ── ROOFING FORM ─────────────────────────────── */
// params/setParams приходят из App — состояние формы переживает переход
// на другие шаги и обратно (кнопка «← Изменить» / клик по StepBar).
function RoofingForm({onResult, params:p, setParams:setP}){
  const[loading,setLoading] = useState(false);
  const[error,setError] = useState(null);
  const up = (k,v) => setP(x=>({...x,[k]:v}));

  const errors = {
    length: validateNumber(p.length, {label:"Длина дома", min:3, max:60}),
    width:  validateNumber(p.width,  {label:"Ширина дома", min:3, max:30}),
    angle:  validateNumber(p.angle,  {label:"Угол ската", min:10, max:60}),
  };
  const hasErrors = Object.values(errors).some(Boolean);

  // Предварительная площадь для наглядности — точные цифры и состав
  // материалов приходят с сервера после нажатия «Рассчитать»
  const slopeLen = (p.width/2) / Math.cos(p.angle*Math.PI/180);
  const areaPreview = hasErrors ? null : Math.round(p.length * slopeLen * 2 * 1.10);

  async function submit(){
    if(hasErrors) return;
    setLoading(true); setError(null);
    try{
      const r = await apiCalculate("roofing", p);
      onResult(r);
    }catch(e){
      setError(e.message);
    }finally{
      setLoading(false);
    }
  }

  return (
    <div>
      <InfoBox>Двускатная крыша. Все размеры — по внешним габаритам.</InfoBox>
      <FieldRow label="Длина дома (м)" error={errors.length}>
        <input type="number" inputMode="decimal" className={errors.length?"field-invalid":""} value={p.length} min="3" max="60" step="0.5" onChange={e=>up("length",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Ширина дома (м)" error={errors.width}>
        <input type="number" inputMode="decimal" className={errors.width?"field-invalid":""} value={p.width} min="3" max="30" step="0.5" onChange={e=>up("width",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Угол ската (°)" error={errors.angle}>
        <input type="number" inputMode="decimal" className={errors.angle?"field-invalid":""} value={p.angle} min="10" max="60" step="5" onChange={e=>up("angle",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Материал">
        <select value={p.material} onChange={e=>up("material",e.target.value)}>
          <option value="metal_tile_grand">Металлочерепица Grand Line</option>
          <option value="metal_tile_monterrey">Металлочерепица Monterrey</option>
          <option value="profnastil_c20">Профнастил С-20</option>
          <option value="soft_roof_shinglas">Мягкая кровля Shinglas</option>
        </select>
      </FieldRow>
      {!hasErrors && (
        <div style={{padding:"12px",background:"var(--green-bg)",borderRadius:"var(--r-md)",marginBottom:"1.25rem",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span style={{fontSize:"13px",color:"var(--green-fg)"}}>Площадь кровли (с нахлёстом 10%)</span>
          <span style={{fontSize:"20px",fontWeight:"600",color:"var(--green-fg)"}}>{areaPreview} м²</span>
        </div>
      )}
      {error && <ErrorBox message={error} onRetry={submit}/>}
      <button className="btn" style={{width:"100%"}} disabled={loading||hasErrors} onClick={submit}>
        {loading && <span className="spin"/>}{loading ? "Считаем..." : "Рассчитать →"}
      </button>
      {hasErrors && !loading && <div className="field-error" style={{textAlign:"center",marginTop:"8px"}}>Исправьте поля выше, чтобы продолжить</div>}
    </div>
  );
}

/* ── FACADE FORM ──────────────────────────────── */
function FacadeForm({onResult, params:p, setParams:setP}){
  const[loading,setLoading] = useState(false);
  const[error,setError] = useState(null);
  const up = (k,v) => setP(x=>({...x,[k]:v}));

  const errors = {
    length:  validateNumber(p.length,  {label:"Длина дома", min:3, max:60}),
    width:   validateNumber(p.width,   {label:"Ширина дома", min:3, max:30}),
    height:  validateNumber(p.height,  {label:"Высота стен", min:2, max:12}),
    windows: validateNumber(p.windows, {label:"Окна", min:0, max:40, integer:true}),
    doors:   validateNumber(p.doors,   {label:"Двери", min:0, max:10, integer:true}),
  };
  const hasErrors = Object.values(errors).some(Boolean);
  const netPreview = hasErrors ? null : Math.round(2*(p.length+p.width)*p.height - (p.windows*1.5+p.doors*2.1));

  async function submit(){
    if(hasErrors) return;
    setLoading(true); setError(null);
    try{
      const r = await apiCalculate("facade", p);
      onResult(r);
    }catch(e){
      setError(e.message);
    }finally{
      setLoading(false);
    }
  }

  return (
    <div>
      <InfoBox>Периметр × высота за вычетом оконных и дверных проёмов.</InfoBox>
      <FieldRow label="Длина дома (м)" error={errors.length}>
        <input type="number" inputMode="decimal" className={errors.length?"field-invalid":""} value={p.length} min="3" max="60" step="0.5" onChange={e=>up("length",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Ширина дома (м)" error={errors.width}>
        <input type="number" inputMode="decimal" className={errors.width?"field-invalid":""} value={p.width} min="3" max="30" step="0.5" onChange={e=>up("width",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Высота стен (м)" error={errors.height}>
        <input type="number" inputMode="decimal" className={errors.height?"field-invalid":""} value={p.height} min="2" max="12" step="0.5" onChange={e=>up("height",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Окна (шт)" error={errors.windows}>
        <input type="number" inputMode="numeric" className={errors.windows?"field-invalid":""} value={p.windows} min="0" max="40" onChange={e=>up("windows",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Двери (шт)" error={errors.doors}>
        <input type="number" inputMode="numeric" className={errors.doors?"field-invalid":""} value={p.doors} min="0" max="10" onChange={e=>up("doors",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Материал">
        <select value={p.material} onChange={e=>up("material",e.target.value)}>
          <option value="siding">Виниловый сайдинг Döcke</option>
          <option value="facade_panel">Фасадная панель Döcke</option>
          <option value="fiber">Хаубер (фиброцемент)</option>
        </select>
      </FieldRow>
      {!hasErrors && (
        <div style={{padding:"12px",background:"var(--green-bg)",borderRadius:"var(--r-md)",marginBottom:"1.25rem",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span style={{fontSize:"13px",color:"var(--green-fg)"}}>Площадь фасада (чистая)</span>
          <span style={{fontSize:"20px",fontWeight:"600",color:"var(--green-fg)"}}>{netPreview} м²</span>
        </div>
      )}
      {error && <ErrorBox message={error} onRetry={submit}/>}
      <button className="btn" style={{width:"100%"}} disabled={loading||hasErrors} onClick={submit}>
        {loading && <span className="spin"/>}{loading ? "Считаем..." : "Рассчитать →"}
      </button>
      {hasErrors && !loading && <div className="field-error" style={{textAlign:"center",marginTop:"8px"}}>Исправьте поля выше, чтобы продолжить</div>}
    </div>
  );
}

/* ── INSULATION FORM ──────────────────────────── */
function InsulationForm({onResult, params:p, setParams:setP}){
  const[loading,setLoading] = useState(false);
  const[error,setError] = useState(null);
  const up = (k,v) => setP(x=>({...x,[k]:v}));

  const errors = {
    area: validateNumber(p.area, {label:"Площадь", min:5, max:1000}),
  };
  const hasErrors = Object.values(errors).some(Boolean);

  async function submit(){
    if(hasErrors) return;
    setLoading(true); setError(null);
    try{
      const r = await apiCalculate("insulation", p);
      onResult(r);
    }catch(e){
      setError(e.message);
    }finally{
      setLoading(false);
    }
  }

  return (
    <div>
      <InfoBox>Расчёт по площади и требуемой толщине. Запас 5%.</InfoBox>
      <FieldRow label="Площадь (м²)" error={errors.area}>
        <input type="number" inputMode="decimal" className={errors.area?"field-invalid":""} value={p.area} min="5" max="1000" step="5" onChange={e=>up("area",+e.target.value)}/>
      </FieldRow>
      <FieldRow label="Толщина слоя">
        <select value={p.thickness} onChange={e=>up("thickness",+e.target.value)}>
          <option value={0.05}>50 мм</option>
          <option value={0.10}>100 мм</option>
          <option value={0.15}>150 мм</option>
          <option value={0.20}>200 мм</option>
        </select>
      </FieldRow>
      <FieldRow label="Материал">
        <select value={p.material} onChange={e=>up("material",e.target.value)}>
          <option value="mineral">Минеральная вата КНАУФ</option>
          <option value="foam">Пенопласт ПСБ-25</option>
          <option value="epp">Пенополистирол XPS</option>
        </select>
      </FieldRow>
      {error && <ErrorBox message={error} onRetry={submit}/>}
      <button className="btn" style={{width:"100%",marginTop:"0.5rem"}} disabled={loading||hasErrors} onClick={submit}>
        {loading && <span className="spin"/>}{loading ? "Считаем..." : "Рассчитать →"}
      </button>
      {hasErrors && !loading && <div className="field-error" style={{textAlign:"center",marginTop:"8px"}}>Исправьте поля выше, чтобы продолжить</div>}
    </div>
  );
}

/* ── MATERIALS TABLE (по базовым ценам, шаг «Материалы») ── */
function MaterialsTable({items}){
  const[openNote,setOpenNote] = useState(null); // slug открытой подсказки, либо null
  const total = items.reduce((a,it)=>a+it.qty*it.base_price,0);
  const grouped = Object.entries(CAT_LABELS)
    .map(([k,label])=>[label, items.filter(x=>x.category===k)])
    .filter(([,g])=>g.length>0);
  return (
    <div>
      {grouped.map(([label,group])=>(
        <div key={label} style={{marginBottom:"1rem"}}>
          <div style={{fontSize:"11px",fontWeight:"600",color:"var(--text3)",textTransform:"uppercase",letterSpacing:"0.6px",marginBottom:"6px"}}>{label}</div>
          {group.map((it,i)=>{
            const isOpen = openNote === it.product_slug;
            return (
              <div key={i} style={{borderBottom:"0.5px solid var(--border)"}}>
                <div style={{display:"grid",gridTemplateColumns:"1fr 70px 80px 90px",gap:"6px",alignItems:"center",padding:"8px 0"}}>
                  <span style={{fontSize:"13px",display:"flex",alignItems:"center",gap:"4px"}}>
                    {it.name}
                    {it.note && (
                      <button
                        onClick={()=>setOpenNote(isOpen ? null : it.product_slug)}
                        aria-label="Как посчитано это количество"
                        aria-expanded={isOpen}
                        style={{
                          background: isOpen ? "var(--text)" : "var(--surface2)",
                          color: isOpen ? "var(--accent-fg)" : "var(--text3)",
                          border:"none",borderRadius:"50%",width:"20px",height:"20px",minHeight:"20px",
                          fontSize:"11px",fontWeight:"700",flexShrink:0,lineHeight:1,
                          display:"inline-flex",alignItems:"center",justifyContent:"center",padding:0,
                        }}>?</button>
                    )}
                  </span>
                  <span style={{fontSize:"13px",color:"var(--text2)",textAlign:"right"}}>{it.qty}&nbsp;{it.unit}</span>
                  <span style={{fontSize:"13px",color:"var(--text2)",textAlign:"right"}}>{fmt(it.base_price)}</span>
                  <span style={{fontSize:"13px",fontWeight:"500",textAlign:"right"}}>{fmt(it.qty*it.base_price)}</span>
                </div>
                {isOpen && it.note && (
                  <div style={{fontSize:"12px",color:"var(--text2)",background:"var(--surface2)",borderRadius:"var(--r-md)",padding:"10px 12px",marginBottom:"8px",lineHeight:1.5}}>
                    {it.note}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",paddingTop:"12px",borderTop:"1.5px solid var(--text)"}}>
        <span style={{fontWeight:"500"}}>Итого (справочно, до выбора поставщика)</span>
        <span style={{fontSize:"22px",fontWeight:"600"}}>{fmt(total)}</span>
      </div>
    </div>
  );
}

/* ── PRICED ITEMS TABLE (реальные цены конкретного поставщика) ── */
function PricedItemsTable({itemsPriced, total}){
  return (
    <div>
      {itemsPriced.map((it,i)=>(
        <div key={i} style={{display:"grid",gridTemplateColumns:"1fr 70px 80px 90px",gap:"6px",alignItems:"center",padding:"8px 0",borderBottom:"0.5px solid var(--border)"}}>
          <span style={{fontSize:"13px"}}>
            {it.name}
            {!it.in_stock && <span style={{fontSize:"11px",color:"var(--amber-fg)",marginLeft:"6px"}}>под заказ</span>}
          </span>
          <span style={{fontSize:"13px",color:"var(--text2)",textAlign:"right"}}>{it.qty}&nbsp;{it.unit}</span>
          <span style={{fontSize:"13px",color:"var(--text2)",textAlign:"right"}}>{fmt(it.price)}</span>
          <span style={{fontSize:"13px",fontWeight:"500",textAlign:"right"}}>{fmt(it.subtotal)}</span>
        </div>
      ))}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",paddingTop:"12px",borderTop:"1.5px solid var(--text)"}}>
        <span style={{fontWeight:"500"}}>Итого</span>
        <span style={{fontSize:"22px",fontWeight:"600"}}>{fmt(total)}</span>
      </div>
    </div>
  );
}

/* ── SUPPLIER CARDS (реальные предложения из ответа API) ── */
function SupplierCards({offers, selected, onSelect}){
  const badgeFor = (offer, i) => {
    if(i===0) return {text:"Лучшее предложение", bg:"var(--green-bg)", fg:"var(--green-fg)"};
    if(offer.supplier.delivery_days===0) return {text:"Самовывоз", bg:"var(--amber-bg)", fg:"var(--amber-fg)"};
    return {text:"Есть в наличии", bg:"var(--blue-bg)", fg:"var(--blue-fg)"};
  };

  if(!offers || offers.length===0){
    return <ErrorBox message="Нет доступных поставщиков для этого расчёта. Попробуйте другой материал."/>;
  }

  return (
    <div style={{display:"flex",flexDirection:"column",gap:"10px"}}>
      {offers.map((offer,i)=>{
        const bs = badgeFor(offer,i);
        const isSelected = selected?.supplier.id === offer.supplier.id;
        return (
          <div key={offer.supplier.id} onClick={()=>onSelect(offer)}
            style={{
              padding:"1rem 1.25rem",borderRadius:"var(--r-lg)",cursor:"pointer",
              background:"var(--surface)",
              border: isSelected ? "2px solid var(--text)" : "0.5px solid var(--border)",
              transition:"border-color 0.15s",
            }}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:"8px"}}>
              <div>
                <div style={{display:"flex",alignItems:"center",gap:"8px",flexWrap:"wrap"}}>
                  <span style={{fontWeight:"600",fontSize:"15px"}}>{offer.supplier.name}</span>
                  <span style={{fontSize:"11px",fontWeight:"500",padding:"3px 9px",borderRadius:"20px",background:bs.bg,color:bs.fg}}>{bs.text}</span>
                </div>
                <div style={{fontSize:"12px",color:"var(--text3)",marginTop:"3px"}}>
                  {offer.supplier.region} · {offer.supplier.delivery_days===0?"самовывоз":`доставка ${offer.supplier.delivery_days} дн.`}
                </div>
              </div>
              <div style={{textAlign:"right",flexShrink:0,marginLeft:"12px"}}>
                <div style={{fontSize:"20px",fontWeight:"700"}}>{fmt(offer.total)}</div>
                <div style={{fontSize:"11px",color:"var(--text3)"}}>{Math.round(offer.coverage*100)}% позиций в наличии</div>
              </div>
            </div>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",paddingTop:"8px",borderTop:"0.5px solid var(--border)"}}>
              <span style={{fontSize:"12px",color:"var(--text2)"}}>
                Мин. заказ {offer.supplier.min_order_rub===0?"без лимита":fmt(offer.supplier.min_order_rub)}
              </span>
              <span style={{fontSize:"12px",color:"var(--text2)"}}>{offer.supplier.phone}</span>
            </div>
            {formatPriceDate(offer.prices_updated_at) && (
              <div style={{fontSize:"11px",color:"var(--text3)",marginTop:"6px"}}>
                Цены обновлены: {formatPriceDate(offer.prices_updated_at)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── QUOTE VIEW ───────────────────────────────── */
function QuoteView({calcId, calcType, offer, onBack, onNew}){
  const[quote,setQuote] = useState(null);
  const[quoteLoading,setQuoteLoading] = useState(true);
  const[quoteError,setQuoteError] = useState(null);

  const[name,setName] = useState("");
  const[phone,setPhone] = useState("");
  const[sending,setSending] = useState(false);
  const[sent,setSent] = useState(false);
  const[sendError,setSendError] = useState(null);

  const typeNames = {roofing:"Кровля",facade:"Фасад",insulation:"Утепление"};
  const typeName = typeNames[calcType]||"Материалы";

  async function loadQuote(){
    setQuoteLoading(true); setQuoteError(null);
    try{
      const q = await apiCreateQuote(calcId, offer.supplier.id);
      setQuote(q);
    }catch(e){
      setQuoteError(e.message);
    }finally{
      setQuoteLoading(false);
    }
  }

  React.useEffect(()=>{ loadQuote(); }, []);

  async function sendRequest(){
    if(!name||!phone) return;
    setSending(true); setSendError(null);
    try{
      await apiSendRequest({
        quote_id: quote.quote_id, supplier_id: offer.supplier.id, name, phone,
        source: LEAD_SOURCE, page_url: PAGE_URL,
      });
      setSent(true);
    }catch(e){
      setSendError(e.message);
    }finally{
      setSending(false);
    }
  }

  return (
    <div style={{maxWidth:"720px",margin:"0 auto",padding:"20px"}}>
      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:"1.5rem"}}>
        <div>
          <div style={{fontSize:"11px",color:"var(--text3)",letterSpacing:"0.5px",textTransform:"uppercase"}}>
            {quote ? quote.number : "..."}
          </div>
          <h1 style={{fontSize:"22px",fontWeight:"700",letterSpacing:"-0.5px",marginTop:"4px"}}>Коммерческое предложение</h1>
          <div style={{fontSize:"13px",color:"var(--text2)",marginTop:"2px"}}>Тип: {typeName}</div>
        </div>
        <button className="btn-ghost" onClick={onBack} style={{flexShrink:0}}>← Назад</button>
      </div>

      {quoteLoading && (
        <div className="card" style={{textAlign:"center",color:"var(--text2)",fontSize:"14px"}}>
          <span className="spin" style={{borderTopColor:"var(--text)",borderColor:"rgba(0,0,0,0.15)"}}/>
          Формируем смету...
        </div>
      )}

      {quoteError && <ErrorBox message={quoteError} onRetry={loadQuote}/>}

      {quote && (
        <React.Fragment>
          {/* Summary cards */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"10px",marginBottom:"1.25rem"}}>
            {[
              {label:"Поставщик",    value:offer.supplier.name,   sub:offer.supplier.region},
              {label:"Доставка",     value:offer.supplier.delivery_days===0?"Самовывоз":`${offer.supplier.delivery_days} дня`, sub:offer.supplier.phone},
              {label:"Сумма сметы",  value:fmt(quote.total),      sub:`${Math.round(offer.coverage*100)}% в наличии`},
            ].map(({label,value,sub})=>(
              <div key={label} style={{background:"var(--surface2)",borderRadius:"var(--r-md)",padding:"12px"}}>
                <div style={{fontSize:"12px",color:"var(--text3)"}}>{label}</div>
                <div style={{fontWeight:"600",fontSize:"15px",marginTop:"4px",lineHeight:1.2}}>{value}</div>
                <div style={{fontSize:"11px",color:"var(--text3)",marginTop:"2px"}}>{sub}</div>
              </div>
            ))}
          </div>

          {/* Spec table */}
          <div className="card" style={{marginBottom:"1rem"}}>
            <div style={{fontSize:"12px",fontWeight:"600",color:"var(--text3)",textTransform:"uppercase",letterSpacing:"0.5px",marginBottom:"14px"}}>Спецификация</div>
            <PricedItemsTable itemsPriced={quote.items} total={quote.total}/>
          </div>

          {/* Request form */}
          {!sent ? (
            <div className="card" style={{marginBottom:"1rem"}}>
              <div style={{fontWeight:"600",fontSize:"15px",marginBottom:"12px"}}>Оставить заявку поставщику</div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"10px",marginBottom:"12px"}}>
                <input placeholder="Ваше имя" value={name} onChange={e=>setName(e.target.value)}/>
                <input placeholder="Телефон" value={phone} onChange={e=>setPhone(e.target.value)} type="tel" inputMode="tel"/>
              </div>
              {sendError && <ErrorBox message={sendError}/>}
              <button className="btn" style={{width:"100%"}} disabled={!name||!phone||sending} onClick={sendRequest}>
                {sending && <span className="spin"/>}
                {sending ? "Отправляем..." : `Отправить заявку → ${offer.supplier.name}`}
              </button>
              {(!name||!phone)&&<div style={{fontSize:"12px",color:"var(--text3)",marginTop:"6px",textAlign:"center"}}>Заполните имя и телефон</div>}
            </div>
          ) : (
            <div style={{padding:"1rem 1.25rem",background:"var(--green-bg)",border:"0.5px solid var(--green-border)",borderRadius:"var(--r-lg)",marginBottom:"1rem",display:"flex",alignItems:"center",gap:"12px"}}>
              <div style={{fontSize:"24px"}}>✓</div>
              <div>
                <div style={{fontWeight:"600",color:"var(--green-fg)"}}>Заявка отправлена!</div>
                <div style={{fontSize:"13px",color:"var(--green-fg)",marginTop:"2px"}}>Менеджер {offer.supplier.name} свяжется с вами по номеру {phone} в течение 2 часов.</div>
              </div>
            </div>
          )}

          {/* Actions */}
          <StickyTotal label="Итого по смете" amount={fmt(quote.total)}>
            <div style={{display:"flex",gap:"10px"}}>
              <a className="btn-ghost" style={{flex:1,textAlign:"center",textDecoration:"none",display:"flex"}}
                 href={`${API_BASE}/api/quotes/${quote.quote_id}/pdf`} target="_blank" rel="noreferrer">
                ⬇ Скачать PDF
              </a>
              <button className="btn" style={{flex:1}} onClick={onNew}>Новый расчёт</button>
            </div>
          </StickyTotal>
        </React.Fragment>
      )}
    </div>
  );
}

/* ── CALC TYPES ───────────────────────────────── */
const CALC_TYPES = [
  {id:"roofing",   label:"Кровля",    icon:"🏠", desc:"Металлочерепица, профнастил, мягкая кровля, все комплектующие"},
  {id:"facade",    label:"Фасад",     icon:"🧱", desc:"Сайдинг, фасадные панели, хаубер, крепёж и углы"},
  {id:"insulation",label:"Утепление", icon:"❄️", desc:"Минвата, пенопласт, пенополистирол XPS, крепёж"},
];

/* ── STEPS MAP ────────────────────────────────── */
const STEPS = ["Параметры","Материалы","Поставщик","Смета"];

/* ── MAIN APP ─────────────────────────────────── */
const DEFAULT_ROOFING = {length:10,width:8,angle:30,material:"metal_tile_grand"};
const DEFAULT_FACADE = {length:10,width:8,height:3,windows:6,doors:2,material:"siding"};
const DEFAULT_INSULATION = {area:80,thickness:0.15,material:"mineral"};

function App(){
  const[screen,setScreen] = useState("home");    // home | calc | quote
  const[calcType,setCalcType] = useState(null);
  const[step,setStep] = useState(0);
  const[calcResult,setCalcResult] = useState(null);  // {calc_id, items, base_total, suppliers}
  const[offer,setOffer] = useState(null);             // выбранное предложение поставщика

  // Состояние полей форм живёт в App, а не в самих формах — это значит,
  // что переход на шаг «Материалы»/«Поставщик» и возврат назад (кнопкой
  // «← Изменить» или кликом по StepBar) не сбрасывает введённые данные.
  const[roofingParams,setRoofingParams] = useState(DEFAULT_ROOFING);
  const[facadeParams,setFacadeParams] = useState(DEFAULT_FACADE);
  const[insulationParams,setInsulationParams] = useState(DEFAULT_INSULATION);

  function startCalc(type){
    setCalcType(type); setStep(0); setCalcResult(null); setOffer(null); setScreen("calc");
    if(type==="roofing") setRoofingParams(DEFAULT_ROOFING);
    if(type==="facade") setFacadeParams(DEFAULT_FACADE);
    if(type==="insulation") setInsulationParams(DEFAULT_INSULATION);
  }
  function onResult(r){ setCalcResult(r); setStep(1); }
  function toQuote(){ if(offer) setScreen("quote"); }
  function goToStep(i){
    // Назад — можно всегда. Вперёд — только если для целевого шага уже есть данные.
    if(i===0 || (calcResult && i<=2)) setStep(i);
  }
  function reset(){ setScreen("home"); setCalcType(null); setStep(0); setCalcResult(null); setOffer(null); }

  /* ── HOME ──
     В embed-режиме (виджет на platforma-msk.ru) убираем крупный бренд-блок
     и блок "Что вы получите" — на встраивающей странице уже есть шапка
     сайта, дублировать не нужно. Экономим вертикальное место в iframe. */
  if(screen==="home") return (
    <div style={{maxWidth:"720px",margin:"0 auto",padding: EMBED ? "12px 16px 20px" : "24px 20px"}}>
      {!EMBED && (
        <div style={{marginBottom:"32px"}}>
          <div style={{fontWeight:"700",fontSize:"24px",letterSpacing:"-0.8px"}}>PLATFORMA</div>
          <div style={{color:"var(--text2)",fontSize:"14px",marginTop:"2px"}}>Кровельные и фасадные материалы · Богородский р-н МО</div>
        </div>
      )}

      <h1 style={{fontSize: EMBED ? "22px" : "28px",fontWeight:"700",letterSpacing:"-1px",lineHeight:1.2,marginBottom:"8px"}}>
        Рассчитайте материалы<br/>за 2 минуты
      </h1>
      <p style={{color:"var(--text2)",fontSize:"15px",marginBottom: EMBED ? "20px" : "28px"}}>
        Точная спецификация с запасом, сравнение цен реальных поставщиков и готовая PDF-смета. Бесплатно.
      </p>

      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",gap:"12px",marginBottom: EMBED ? "8px" : "36px"}}>
        {CALC_TYPES.map(t=>(
          <div key={t.id} onClick={()=>startCalc(t.id)} className="card"
            style={{cursor:"pointer",transition:"transform 0.12s,box-shadow 0.12s",userSelect:"none"}}
            onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)"}}
            onMouseLeave={e=>{e.currentTarget.style.transform=""}}>
            <div style={{fontSize:"28px",marginBottom:"10px"}}>{t.icon}</div>
            <div style={{fontWeight:"700",fontSize:"16px",marginBottom:"4px"}}>{t.label}</div>
            <div style={{fontSize:"13px",color:"var(--text2)",marginBottom:"16px",lineHeight:1.4}}>{t.desc}</div>
            <div style={{fontSize:"13px",fontWeight:"500",color:"var(--text)"}}>Рассчитать →</div>
          </div>
        ))}
      </div>

      {!EMBED && (
        <div style={{borderTop:"0.5px solid var(--border)",paddingTop:"24px"}}>
          <div style={{fontSize:"12px",color:"var(--text3)",marginBottom:"12px",textTransform:"uppercase",letterSpacing:"0.5px"}}>Что вы получите</div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))",gap:"10px"}}>
            {[
              ["📐","Точный расчёт","с запасом и всеми комплектующими"],
              ["🏪","Реальные поставщики","живое сравнение цен по региону"],
              ["📄","PDF смета","как коммерческое предложение"],
              ["🚚","Доставка","по Московской области"],
            ].map(([ic,t,d])=>(
              <div key={t} style={{padding:"12px",background:"var(--surface2)",borderRadius:"var(--r-md)"}}>
                <div style={{fontSize:"18px",marginBottom:"6px"}}>{ic}</div>
                <div style={{fontWeight:"600",fontSize:"13px"}}>{t}</div>
                <div style={{fontSize:"12px",color:"var(--text3)",marginTop:"2px",lineHeight:1.3}}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {EMBED && (
        <div style={{fontSize:"11px",color:"var(--text3)",textAlign:"center",marginTop:"4px"}}>
          Калькулятор · <a href="https://platforma-msk.ru" target="_blank" rel="noreferrer" style={{color:"var(--text3)"}}>PLATFORMA</a>
        </div>
      )}
    </div>
  );

  /* ── QUOTE ── */
  if(screen==="quote") return (
    <QuoteView calcId={calcResult.calc_id} calcType={calcType} offer={offer} onBack={()=>setScreen("calc")} onNew={reset}/>
  );

  /* ── CALCULATOR ── */
  const ct = CALC_TYPES.find(t=>t.id===calcType);
  return (
    <div style={{maxWidth:"720px",margin:"0 auto",padding:"20px"}}>
      {/* Header */}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"1.25rem"}}>
        <div style={{display:"flex",alignItems:"center",gap:"10px"}}>
          <span style={{fontSize:"22px"}}>{ct?.icon}</span>
          <div>
            <div style={{fontWeight:"700",fontSize:"16px"}}>{ct?.label}</div>
            <div style={{fontSize:"12px",color:"var(--text3)"}}>PLATFORMA</div>
          </div>
        </div>
        <button className="btn-ghost" style={{fontSize:"13px",padding:"7px 14px"}} onClick={reset}>✕ Закрыть</button>
      </div>

      <StepBar steps={STEPS} current={step} onStepClick={goToStep}/>

      <div className="card">
        {/* Step 0 — Form */}
        {step===0 && (
          calcType==="roofing"    ? <RoofingForm    onResult={onResult} params={roofingParams} setParams={setRoofingParams}/> :
          calcType==="facade"     ? <FacadeForm     onResult={onResult} params={facadeParams} setParams={setFacadeParams}/> :
                                    <InsulationForm  onResult={onResult} params={insulationParams} setParams={setInsulationParams}/>
        )}

        {/* Step 1 — Materials */}
        {step===1 && calcResult && (
          <div>
            <div style={{fontWeight:"600",fontSize:"15px",marginBottom:"16px"}}>Спецификация материалов</div>
            <MaterialsTable items={calcResult.items}/>
            <StickyTotal
              label="Итого (справочно, до выбора поставщика)"
              amount={fmt(calcResult.items.reduce((a,it)=>a+it.qty*it.base_price,0))}>
              <div style={{display:"flex",gap:"8px"}}>
                <button className="btn-ghost" style={{flex:1}} onClick={()=>goToStep(0)}>← Изменить</button>
                <button className="btn" style={{flex:2}} onClick={()=>setStep(2)}>Выбрать поставщика →</button>
              </div>
            </StickyTotal>
          </div>
        )}

        {/* Step 2 — Suppliers */}
        {step===2 && calcResult && (
          <div>
            <div style={{fontWeight:"600",fontSize:"15px",marginBottom:"14px"}}>Сравнение поставщиков</div>
            <SupplierCards offers={calcResult.suppliers} selected={offer} onSelect={setOffer}/>
            <StickyTotal
              label={offer ? `Итого · ${offer.supplier.name}` : "Выберите поставщика"}
              amount={offer ? fmt(offer.total) : "—"}>
              <div style={{display:"flex",gap:"8px"}}>
                <button className="btn-ghost" style={{flex:1}} onClick={()=>goToStep(1)}>← Назад</button>
                <button className="btn" style={{flex:2,opacity:offer?1:0.35}} disabled={!offer} onClick={toQuote}>
                  Сформировать смету →
                </button>
              </div>
            </StickyTotal>
          </div>
        )}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);

/* ── EMBED: сообщаем родительской странице высоту контента ──
   Виджет живёт в iframe с фиксированной высотой снаружи, а контент
   калькулятора по шагам разный (форма короче сметы). Шлём postMessage
   с реальной высотой при каждом изменении DOM — встраивающая страница
   слушает это сообщение и подгоняет высоту iframe (см. сниппет в
   инструкции по установке / DEPLOY.md). */
if(EMBED && typeof window!=="undefined" && typeof ResizeObserver!=="undefined"){
  let lastH = 0;
  const reportHeight = () => {
    const h = document.documentElement.scrollHeight;
    if(Math.abs(h-lastH) > 4){
      lastH = h;
      window.parent.postMessage({type:"platforma-widget-resize", height:h}, "*");
    }
  };
  new ResizeObserver(reportHeight).observe(document.body);
  window.addEventListener("load", reportHeight);
  setTimeout(reportHeight, 300);
}
