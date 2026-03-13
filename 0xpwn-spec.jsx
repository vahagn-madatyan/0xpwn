import { useState } from "react";

// ═══════════════════════════════════════════════════════════════
// DESIGN SYSTEM
// ═══════════════════════════════════════════════════════════════
const C = {
  bg: "#05080f", surface: "#0c1120", alt: "#0a0f1c", border: "#1a2340",
  text: "#e2e8f0", dim: "#5a6888", green: "#00ff87", red: "#ff3e3e",
  cyan: "#00e5ff", purple: "#b44dff", orange: "#ff8a00", yellow: "#ffe14d",
  blue: "#4d8eff", pink: "#ff4da6", greenDim: "#00ff8720",
};
const mono = "'JetBrains Mono','Fira Code',monospace";
const sans = "'Segoe UI',-apple-system,sans-serif";

const TABS = ["Architecture", "Agent Pipeline", "Business", "Capabilities", "Tech Spec", "Brand", "Mermaid"];

const B = (color, text) => <span key={text} style={{ display: "inline-block", padding: "3px 9px", borderRadius: 4, fontSize: 10, fontWeight: 600, background: color + "25", color, fontFamily: mono, letterSpacing: 0.3 }}>{text}</span>;
const Card = ({ children, color, style = {} }) => <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden", borderTop: color ? `3px solid ${color}` : undefined, ...style }}>{children}</div>;
const Head = ({ children, color }) => <div style={{ padding: "10px 16px", background: C.alt, borderBottom: `1px solid ${C.border}`, fontFamily: mono, fontSize: 11, fontWeight: 700, color: color || C.green, letterSpacing: 1.5, display: "flex", alignItems: "center", gap: 8 }}>{children}</div>;
const Sec = ({ title, color }) => <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: color || C.green, letterSpacing: 1.5, marginTop: 12 }}>{title}</div>;

// ═══════════════════════════════════════════════════════════════
// TAB 1: ARCHITECTURE
// ═══════════════════════════════════════════════════════════════
function ArchitectureTab() {
  const [view, setView] = useState("system");
  const views = { system: "System Overview", cli: "CLI Stack", deploy: "Deployment Modes" };

  return <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
    <div style={{ display: "flex", gap: 8 }}>
      {Object.entries(views).map(([k, v]) => <button key={k} onClick={() => setView(k)} style={{
        padding: "7px 14px", borderRadius: 6, border: `1px solid ${view === k ? C.green : C.border}`,
        background: view === k ? C.green + "15" : C.surface, color: view === k ? C.green : C.dim,
        fontSize: 11, fontFamily: mono, cursor: "pointer", fontWeight: 600,
      }}>{v}</button>)}
    </div>

    {view === "system" && <Card>
      <Head color={C.green}>SYSTEM ARCHITECTURE — End-to-End Data Flow</Head>
      <div style={{ padding: 20 }}>
        <svg viewBox="0 0 900 640" style={{ width: "100%", height: "auto" }}>
          <defs>
            <marker id="a" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="7" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 3.5L0 7z" fill={C.green} /></marker>
            <marker id="ac" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="7" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 3.5L0 7z" fill={C.cyan} /></marker>
            <marker id="ao" viewBox="0 0 10 7" refX="10" refY="3.5" markerWidth="7" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 3.5L0 7z" fill={C.orange} /></marker>
          </defs>
          {/* Grid */}
          {Array.from({length:24}).map((_,i)=><line key={`v${i}`} x1={i*40} y1={0} x2={i*40} y2={640} stroke={C.border} strokeOpacity={0.25}/>)}
          {Array.from({length:17}).map((_,i)=><line key={`h${i}`} x1={0} y1={i*40} x2={900} y2={i*40} stroke={C.border} strokeOpacity={0.25}/>)}

          {/* USER LAYER */}
          <rect x={20} y={10} width={860} height={65} rx={8} fill={C.surface} stroke={C.green} strokeWidth={1.5}/>
          <text x={40} y={32} fill={C.green} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>USER INTERFACE LAYER</text>
          {[{x:40,l:"Typer CLI"},{x:140,l:"Textual TUI"},{x:260,l:"REST API"},{x:360,l:"WebSocket"},{x:480,l:"CI/CD (GH Actions)"},{x:640,l:"Web GUI (v2)",d:true},{x:770,l:"MCP Server",d:true}].map((b,i)=>
            <g key={i}><rect x={b.x} y={42} width={b.l.length*7+16} height={22} rx={3} fill={b.d?C.yellow+"12":C.green+"12"} stroke={b.d?C.yellow+"40":C.green+"40"} strokeWidth={0.5} strokeDasharray={b.d?"3 2":"none"}/><text x={b.x+b.l.length*3.5+8} y={57} fill={b.d?C.yellow:C.green} fontSize={9} fontFamily="monospace" textAnchor="middle">{b.l}</text></g>
          )}

          {/* Arrow */}
          <line x1={450} y1={75} x2={450} y2={100} stroke={C.green} strokeWidth={1.5} markerEnd="url(#a)"/>

          {/* AGENT CORE */}
          <rect x={20} y={105} width={860} height={140} rx={8} fill={C.cyan+"08"} stroke={C.cyan} strokeWidth={1.5}/>
          <text x={40} y={128} fill={C.cyan} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>AGENT CORE — ReAct Loop + Multi-Agent Coordination</text>
          {[{x:40,l:"Planner",s:"Phase strategy",c:C.purple},{x:210,l:"Executor",s:"Tool orchestration",c:C.green},{x:400,l:"Perceptor",s:"Output parsing",c:C.cyan},{x:580,l:"Validator",s:"PoC verification",c:C.orange},{x:750,l:"Reporter",s:"Findings + reports",c:C.purple}].map((b,i)=>
            <g key={i}>
              <rect x={b.x} y={142} width={140} height={48} rx={6} fill={b.c+"12"} stroke={b.c} strokeWidth={0.8}/>
              <text x={b.x+70} y={162} fill={b.c} fontSize={11} fontWeight={700} fontFamily="monospace" textAnchor="middle">{b.l}</text>
              <text x={b.x+70} y={178} fill={C.dim} fontSize={8} fontFamily="monospace" textAnchor="middle">{b.s}</text>
              {i<4&&<line x1={b.x+140} y1={166} x2={b.x+170} y2={166} stroke={C.dim} strokeWidth={1} strokeDasharray="3 2" markerEnd="url(#a)"/>}
            </g>
          )}
          {/* State + Permissions */}
          <rect x={40} y={200} width={120} height={24} rx={3} fill={C.yellow+"10"}/><text x={100} y={216} fill={C.yellow} fontSize={9} fontFamily="monospace" textAnchor="middle">Budget Tracker</text>
          <rect x={175} y={200} width={120} height={24} rx={3} fill={C.red+"10"}/><text x={235} y={216} fill={C.red} fontSize={9} fontFamily="monospace" textAnchor="middle">Permissions</text>
          <rect x={310} y={200} width={120} height={24} rx={3} fill={C.blue+"10"}/><text x={370} y={216} fill={C.blue} fontSize={9} fontFamily="monospace" textAnchor="middle">State Manager</text>
          <rect x={445} y={200} width={130} height={24} rx={3} fill={C.pink+"10"}/><text x={510} y={216} fill={C.pink} fontSize={9} fontFamily="monospace" textAnchor="middle">Stuck Detector</text>
          <path d="M 850 166 Q 880 166 880 230 Q 880 240 40 240 Q 25 240 25 166 L 40 166" fill="none" stroke={C.purple} strokeWidth={0.8} strokeDasharray="4 3"/>
          <text x={450} y={237} fill={C.purple} fontSize={8} fontFamily="monospace" textAnchor="middle" opacity={0.6}>feedback loop → re-plan if needed</text>

          {/* Arrows down */}
          <line x1={250} y1={245} x2={250} y2={275} stroke={C.cyan} strokeWidth={1.5} markerEnd="url(#ac)"/>
          <line x1={650} y1={245} x2={650} y2={275} stroke={C.orange} strokeWidth={1.5} markerEnd="url(#ao)"/>

          {/* LLM LAYER */}
          <rect x={20} y={280} width={420} height={100} rx={8} fill={C.surface} stroke={C.purple} strokeWidth={1.5}/>
          <text x={40} y={302} fill={C.purple} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>LLM LAYER — LiteLLM (100+ providers)</text>
          {[{x:40,l:"OpenAI / Codex 5.3",c:C.green},{x:190,l:"Anthropic Claude",c:C.cyan},{x:320,l:"Ollama (local)",c:C.orange}].map((p,i)=>
            <g key={i}><rect x={p.x} y={314} width={130} height={26} rx={4} fill={p.c+"12"} stroke={p.c} strokeWidth={0.6}/><text x={p.x+65} y={331} fill={p.c} fontSize={9} fontFamily="monospace" textAnchor="middle">{p.l}</text></g>
          )}
          {[{x:40,l:"Gemini"},{x:110,l:"DeepSeek"},{x:190,l:"Mistral"},{x:260,l:"Groq"},{x:320,l:"vLLM"},{x:370,l:"Bedrock"}].map((p,i)=>
            <g key={i}><rect x={p.x} y={348} width={60} height={18} rx={3} fill={C.dim+"10"}/><text x={p.x+30} y={360} fill={C.dim} fontSize={7} fontFamily="monospace" textAnchor="middle">{p.l}</text></g>
          )}

          {/* DOCKER SANDBOX */}
          <rect x={460} y={280} width={420} height={100} rx={8} fill={C.surface} stroke={C.orange} strokeWidth={1.5}/>
          <text x={480} y={302} fill={C.orange} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>DOCKER SANDBOX — Kali Linux</text>
          {["nmap","nuclei","sqlmap","ffuf","httpx","nikto","subfinder","gobuster"].map((t,i)=>
            <g key={i}><rect x={480+i%4*100} y={314+Math.floor(i/4)*30} width={85} height={22} rx={3} fill={C.orange+"12"} stroke={C.orange+"30"} strokeWidth={0.5}/><text x={480+i%4*100+42} y={329+Math.floor(i/4)*30} fill={C.orange} fontSize={9} fontFamily="monospace" textAnchor="middle">{t}</text></g>
          )}

          {/* Arrows */}
          <line x1={230} y1={380} x2={230} y2={410} stroke={C.border} strokeWidth={1} strokeDasharray="3 2"/>
          <line x1={670} y1={380} x2={670} y2={410} stroke={C.border} strokeWidth={1} strokeDasharray="3 2"/>

          {/* PERSISTENCE */}
          <rect x={20} y={415} width={860} height={65} rx={8} fill={C.alt} stroke={C.border} strokeWidth={1}/>
          <text x={40} y={436} fill={C.dim} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>PERSISTENCE LAYER</text>
          {[{x:40,l:"SQLite",s:"local sessions",c:C.blue},{x:190,l:"PostgreSQL",s:"cloud tier",c:C.cyan},{x:360,l:"Redis",s:"state/cache",c:C.red},{x:510,l:"S3 / R2",s:"artifacts",c:C.yellow},{x:660,l:"Neo4j",s:"knowledge graph",c:C.purple}].map((s,i)=>
            <g key={i}><rect x={s.x} y={444} width={130} height={24} rx={4} fill={s.c+"10"} stroke={s.c+"30"} strokeWidth={0.5}/><text x={s.x+30} y={460} fill={s.c} fontSize={9} fontWeight={600} fontFamily="monospace">{s.l}</text><text x={s.x+80} y={460} fill={C.dim} fontSize={7} fontFamily="monospace">{s.s}</text></g>
          )}

          {/* REPORTING */}
          <rect x={20} y={500} width={420} height={55} rx={8} fill={C.surface} stroke={C.purple} strokeWidth={1}/>
          <text x={40} y={520} fill={C.purple} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>REPORTING ENGINE</text>
          {["JSON","SARIF","HTML","PDF","Markdown"].map((f,i)=>
            <g key={i}><rect x={40+i*78} y={530} width={68} height={18} rx={3} fill={C.purple+"12"}/><text x={74+i*78} y={542} fill={C.purple} fontSize={8} fontFamily="monospace" textAnchor="middle">{f}</text></g>
          )}

          {/* COMPLIANCE */}
          <rect x={460} y={500} width={420} height={55} rx={8} fill={C.surface} stroke={C.yellow} strokeWidth={1}/>
          <text x={480} y={520} fill={C.yellow} fontSize={10} fontWeight={700} fontFamily="monospace" letterSpacing={1.5}>COMPLIANCE MAPPING</text>
          {["PCI DSS 4.0","DORA","NIS2","SOC 2","FedRAMP"].map((f,i)=>
            <g key={i}><rect x={480+i*78} y={530} width={68} height={18} rx={3} fill={C.yellow+"12"}/><text x={514+i*78} y={542} fill={C.yellow} fontSize={8} fontFamily="monospace" textAnchor="middle">{f}</text></g>
          )}

          {/* TARGET */}
          <rect x={330} y={585} width={240} height={35} rx={17} fill={C.red+"12"} stroke={C.red} strokeWidth={1}/>
          <text x={450} y={607} fill={C.red} fontSize={11} fontWeight={700} fontFamily="monospace" textAnchor="middle">TARGET ENVIRONMENT</text>
          <line x1={670} y1={380} x2={450} y2={585} stroke={C.red} strokeWidth={0.8} strokeDasharray="4 3" opacity={0.3}/>
        </svg>
      </div>
    </Card>}

    {view === "cli" && <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card><Head color={C.green}>CLI STACK — Python Package Architecture</Head><div style={{ padding: 20 }}>
        <svg viewBox="0 0 900 420" style={{ width: "100%", height: "auto" }}>
          {Array.from({length:24}).map((_,i)=><line key={`v${i}`} x1={i*40} y1={0} x2={i*40} y2={420} stroke={C.border} strokeOpacity={0.2}/>)}
          {/* Entry points */}
          <text x={450} y={20} fill={C.green} fontSize={10} fontWeight={700} fontFamily="monospace" textAnchor="middle" letterSpacing={2}>ENTRY POINTS</text>
          {[{x:100,l:"pip install 0xpwn"},{x:340,l:"docker run ghcr.io/0xpwn"},{x:620,l:"python -m oxpwn"},{x:820,l:"REST API"}].map((e,i)=>
            <g key={i}><rect x={e.x-60} y={30} width={120} height={24} rx={12} fill={C.green+"15"} stroke={C.green} strokeWidth={0.8}/><text x={e.x} y={46} fill={C.green} fontSize={8} fontFamily="monospace" textAnchor="middle">{e.l}</text></g>
          )}
          <line x1={450} y1={54} x2={450} y2={72} stroke={C.green} strokeWidth={1} markerEnd="url(#a)"/>

          {/* CLI Layer */}
          <rect x={30} y={76} width={840} height={50} rx={6} fill={C.surface} stroke={C.cyan} strokeWidth={1}/>
          <text x={50} y={96} fill={C.cyan} fontSize={10} fontWeight={700} fontFamily="monospace">oxpwn/cli.py — Typer Commands</text>
          {["scan","config","sessions","resume","report","serve"].map((c,i)=>
            <g key={i}><rect x={50+i*136} y={102} width={120} height={18} rx={3} fill={C.cyan+"10"}/><text x={110+i*136} y={114} fill={C.cyan} fontSize={8} fontFamily="monospace" textAnchor="middle">{c}</text></g>
          )}

          {/* Config */}
          <rect x={30} y={140} width={200} height={44} rx={6} fill={C.surface} stroke={C.yellow} strokeWidth={1}/>
          <text x={50} y={158} fill={C.yellow} fontSize={9} fontWeight={700} fontFamily="monospace">config.py</text>
          <text x={50} y={174} fill={C.dim} fontSize={8} fontFamily="monospace">Pydantic + YAML + env vars</text>

          {/* UI */}
          <rect x={250} y={140} width={200} height={44} rx={6} fill={C.surface} stroke={C.green} strokeWidth={1}/>
          <text x={270} y={158} fill={C.green} fontSize={9} fontWeight={700} fontFamily="monospace">ui/ — Rich + Textual</text>
          <text x={270} y={174} fill={C.dim} fontSize={8} fontFamily="monospace">banner, display, TUI</text>

          {/* Permissions */}
          <rect x={470} y={140} width={200} height={44} rx={6} fill={C.surface} stroke={C.red} strokeWidth={1}/>
          <text x={490} y={158} fill={C.red} fontSize={9} fontWeight={700} fontFamily="monospace">permissions/tiers.py</text>
          <text x={490} y={174} fill={C.dim} fontSize={8} fontFamily="monospace">auto → prompt → always-ask</text>

          {/* Storage */}
          <rect x={690} y={140} width={180} height={44} rx={6} fill={C.surface} stroke={C.blue} strokeWidth={1}/>
          <text x={710} y={158} fill={C.blue} fontSize={9} fontWeight={700} fontFamily="monospace">storage/</text>
          <text x={710} y={174} fill={C.dim} fontSize={8} fontFamily="monospace">SQLite + sessions</text>

          <line x1={450} y1={184} x2={450} y2={206} stroke={C.green} strokeWidth={1} markerEnd="url(#a)"/>

          {/* Agent Core */}
          <rect x={30} y={210} width={840} height={70} rx={6} fill={C.cyan+"06"} stroke={C.cyan} strokeWidth={1.5}/>
          <text x={50} y={232} fill={C.cyan} fontSize={10} fontWeight={700} fontFamily="monospace">agent/ — ReAct Loop + Multi-Agent</text>
          {[{x:50,l:"loop.py",s:"~200 LOC core",c:C.green},{x:210,l:"planner.py",s:"Phase strategy",c:C.purple},{x:390,l:"validator.py",s:"PoC verify",c:C.orange},{x:560,l:"state.py",s:"Pydantic models",c:C.blue},{x:720,l:"prompts/",s:"Jinja2 templates",c:C.yellow}].map((m,i)=>
            <g key={i}><rect x={m.x} y={240} width={140} height={30} rx={4} fill={m.c+"10"} stroke={m.c+"30"} strokeWidth={0.5}/><text x={m.x+70} y={254} fill={m.c} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">{m.l}</text><text x={m.x+70} y={266} fill={C.dim} fontSize={7} fontFamily="monospace" textAnchor="middle">{m.s}</text></g>
          )}

          <line x1={250} y1={280} x2={250} y2={305} stroke={C.purple} strokeWidth={1} markerEnd="url(#a)"/>
          <line x1={650} y1={280} x2={650} y2={305} stroke={C.orange} strokeWidth={1} markerEnd="url(#ao)"/>

          {/* LLM */}
          <rect x={30} y={310} width={420} height={50} rx={6} fill={C.surface} stroke={C.purple} strokeWidth={1}/>
          <text x={50} y={330} fill={C.purple} fontSize={9} fontWeight={700} fontFamily="monospace">llm/ — LiteLLM Wrapper</text>
          {["client.py","cost.py","models.py"].map((f,i)=>
            <g key={i}><rect x={50+i*130} y={338} width={110} height={16} rx={3} fill={C.purple+"10"}/><text x={105+i*130} y={350} fill={C.purple} fontSize={8} fontFamily="monospace" textAnchor="middle">{f}</text></g>
          )}

          {/* Sandbox */}
          <rect x={470} y={310} width={400} height={50} rx={6} fill={C.surface} stroke={C.orange} strokeWidth={1}/>
          <text x={490} y={330} fill={C.orange} fontSize={9} fontWeight={700} fontFamily="monospace">sandbox/ — Docker SDK</text>
          {["runtime.py","tools.py","parser.py"].map((f,i)=>
            <g key={i}><rect x={490+i*120} y={338} width={100} height={16} rx={3} fill={C.orange+"10"}/><text x={540+i*120} y={350} fill={C.orange} fontSize={8} fontFamily="monospace" textAnchor="middle">{f}</text></g>
          )}

          {/* Reporting */}
          <rect x={30} y={375} width={840} height={35} rx={6} fill={C.surface} stroke={C.purple+"60"} strokeWidth={1}/>
          <text x={50} y={397} fill={C.purple} fontSize={9} fontWeight={700} fontFamily="monospace">reporting/</text>
          {["findings.py","json_report.py","sarif.py","markdown.py","html.py","pdf.py","compliance.py"].map((f,i)=>
            <g key={i}><text x={170+i*95} y={397} fill={C.dim} fontSize={8} fontFamily="monospace">{f}</text></g>
          )}
        </svg>
      </div></Card>
    </div>}

    {view === "deploy" && <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <Card color={C.green}><Head color={C.green}>FREE — Local / Self-Hosted</Head><div style={{ padding: 20 }}>
        <svg viewBox="0 0 380 280" style={{ width: "100%", height: "auto" }}>
          <rect x={0} y={0} width={380} height={280} fill={C.alt} rx={6}/>
          <text x={190} y={20} fill={C.dim} fontSize={9} fontFamily="monospace" textAnchor="middle">User's Machine / Docker Host</text>
          <rect x={15} y={30} width={350} height={40} rx={5} fill={C.green+"12"} stroke={C.green} strokeWidth={0.8}/>
          <text x={190} y={48} fill={C.green} fontSize={10} fontWeight={700} fontFamily="monospace" textAnchor="middle">0xpwn CLI</text>
          <text x={190} y={62} fill={C.dim} fontSize={8} fontFamily="monospace" textAnchor="middle">Typer + Rich + Agent Core</text>
          <line x1={190} y1={70} x2={190} y2={88} stroke={C.green} strokeWidth={1}/>
          <rect x={15} y={90} width={165} height={36} rx={5} fill={C.purple+"12"} stroke={C.purple} strokeWidth={0.8}/>
          <text x={97} y={108} fill={C.purple} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">LiteLLM</text>
          <text x={97} y={120} fill={C.dim} fontSize={7} fontFamily="monospace" textAnchor="middle">→ Ollama / BYO key</text>
          <rect x={200} y={90} width={165} height={36} rx={5} fill={C.orange+"12"} stroke={C.orange} strokeWidth={0.8}/>
          <text x={282} y={108} fill={C.orange} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">Docker Sandbox</text>
          <text x={282} y={120} fill={C.dim} fontSize={7} fontFamily="monospace" textAnchor="middle">Kali + tools</text>
          <rect x={15} y={140} width={350} height={40} rx={5} fill={C.alt} stroke={C.border} strokeWidth={0.8}/>
          <text x={190} y={158} fill={C.dim} fontSize={9} fontFamily="monospace" textAnchor="middle">Local Storage</text>
          <text x={80} y={172} fill={C.blue} fontSize={8} fontFamily="monospace" textAnchor="middle">SQLite</text>
          <text x={190} y={172} fill={C.yellow} fontSize={8} fontFamily="monospace" textAnchor="middle">~/.0xpwn/</text>
          <text x={300} y={172} fill={C.cyan} fontSize={8} fontFamily="monospace" textAnchor="middle">JSON reports</text>
          <rect x={100} y={200} width={180} height={30} rx={15} fill={C.red+"12"} stroke={C.red} strokeWidth={0.8}/>
          <text x={190} y={220} fill={C.red} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">Target Network</text>
          <text x={190} y={258} fill={C.green} fontSize={9} fontWeight={700} fontFamily="monospace" textAnchor="middle">pip install 0xpwn</text>
          <text x={190} y={272} fill={C.dim} fontSize={8} fontFamily="monospace" textAnchor="middle">Zero cloud dependency • Fully offline capable</text>
        </svg>
      </div></Card>

      <Card color={C.cyan}><Head color={C.cyan}>PRO / ENTERPRISE — Cloud Hosted</Head><div style={{ padding: 20 }}>
        <svg viewBox="0 0 380 280" style={{ width: "100%", height: "auto" }}>
          <rect x={0} y={0} width={380} height={280} fill={C.alt} rx={6}/>
          <text x={190} y={20} fill={C.dim} fontSize={9} fontFamily="monospace" textAnchor="middle">AWS / Fly.io / Railway</text>
          <rect x={15} y={30} width={165} height={36} rx={5} fill={C.cyan+"12"} stroke={C.cyan} strokeWidth={0.8}/>
          <text x={97} y={48} fill={C.cyan} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">FastAPI Gateway</text>
          <text x={97} y={60} fill={C.dim} fontSize={7} fontFamily="monospace" textAnchor="middle">REST + WebSocket</text>
          <rect x={200} y={30} width={165} height={36} rx={5} fill={C.purple+"12"} stroke={C.purple} strokeWidth={0.8}/>
          <text x={282} y={48} fill={C.purple} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">Temporal</text>
          <text x={282} y={60} fill={C.dim} fontSize={7} fontFamily="monospace" textAnchor="middle">Workflow orchestration</text>
          <rect x={15} y={80} width={350} height={50} rx={5} fill={C.orange+"08"} stroke={C.orange} strokeWidth={0.8}/>
          <text x={190} y={98} fill={C.orange} fontSize={9} fontWeight={700} fontFamily="monospace" textAnchor="middle">ECS / Fargate Workers</text>
          {["Agent Core","Tool Runner","Reporter"].map((w,i)=><g key={i}><rect x={30+i*120} y={106} width={100} height={18} rx={3} fill={C.orange+"15"}/><text x={80+i*120} y={118} fill={C.orange} fontSize={7} fontFamily="monospace" textAnchor="middle">{w}</text></g>)}
          <rect x={15} y={145} width={350} height={50} rx={5} fill={C.alt} stroke={C.border} strokeWidth={0.8}/>
          <text x={190} y={163} fill={C.dim} fontSize={9} fontFamily="monospace" textAnchor="middle">Managed Services</text>
          {[{l:"PostgreSQL",c:C.cyan},{l:"Redis",c:C.red},{l:"S3/R2",c:C.yellow},{l:"Neo4j",c:C.purple}].map((s,i)=><g key={i}><rect x={20+i*88} y={170} width={78} height={18} rx={3} fill={s.c+"12"}/><text x={59+i*88} y={183} fill={s.c} fontSize={7} fontFamily="monospace" textAnchor="middle">{s.l}</text></g>)}
          <rect x={100} y={210} width={180} height={30} rx={15} fill={C.red+"12"} stroke={C.red} strokeWidth={0.8}/>
          <text x={190} y={230} fill={C.red} fontSize={9} fontWeight={600} fontFamily="monospace" textAnchor="middle">Target Network</text>
          <text x={190} y={258} fill={C.cyan} fontSize={9} fontWeight={700} fontFamily="monospace" textAnchor="middle">app.0xpwn.dev</text>
          <text x={190} y={272} fill={C.dim} fontSize={8} fontFamily="monospace" textAnchor="middle">Persistent sessions • Team RBAC • SSO</text>
        </svg>
      </div></Card>
    </div>}

    {/* Key Design Decisions */}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
      {[
        {t:"Modular Monolith",d:"Single process locally → decomposable microservices for cloud. No premature splitting.",c:C.green,i:"⬡"},
        {t:"LiteLLM Abstraction",d:"Swap between Codex 5.3, Claude, Ollama with zero code changes. 100+ providers.",c:C.purple,i:"◆"},
        {t:"Docker Sandbox",d:"Every tool in isolated Kali containers. Host machine never exposed. Auto-cleanup.",c:C.orange,i:"◈"},
        {t:"Event-Sourced State",d:"Every action, finding, decision logged immutably. Full audit trail and replay.",c:C.cyan,i:"◉"},
      ].map((d,i)=><Card key={i} style={{padding:16}}><div style={{display:"flex",gap:10,alignItems:"flex-start"}}><div style={{fontSize:20,color:d.c}}>{d.i}</div><div><div style={{fontWeight:700,fontSize:12,color:d.c,fontFamily:mono,marginBottom:4}}>{d.t}</div><div style={{fontSize:11,color:C.dim,lineHeight:1.6}}>{d.d}</div></div></div></Card>)}
    </div>
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// TAB 2: AGENT PIPELINE
// ═══════════════════════════════════════════════════════════════
function PipelineTab() {
  const phases = [
    {n:"01",name:"RECONNAISSANCE",time:"2-5 min",c:C.cyan,icon:"🔍",what:"Maps the entire attack surface",
      tools:["subfinder","amass","httpx","katana","whois","nmap"],
      details:["Subdomain enumeration","Live host detection","Port scanning + fingerprinting","Tech stack detection","Hidden endpoint crawling","DNS analysis + zone transfer","OSINT (WHOIS, cert transparency)"]},
    {n:"02",name:"SCANNING",time:"5-15 min",c:C.green,icon:"📡",what:"Targeted vulnerability scans from recon intelligence",
      tools:["nuclei","nikto","ffuf","gobuster","zaproxy"],
      details:["9000+ nuclei templates","Web server audit","Directory bruteforcing","Authenticated proxy scanning","CVE correlation","Cross-tool deduplication","Custom template generation"]},
    {n:"03",name:"EXPLOITATION",time:"5-30 min",c:C.orange,icon:"💥",what:"Generates and executes proof-of-concept exploits",
      tools:["sqlmap","metasploit","curl","custom scripts","browser"],
      details:["SQL injection (all techniques)","XSS via browser automation","AI-written custom exploits","Auth bypass (JWT, session, OAuth)","File upload exploitation","SSRF chain construction","Multi-step exploit chaining"]},
    {n:"04",name:"VALIDATION",time:"2-5 min",c:C.red,icon:"✅",what:"Independent verification — every finding must be real",
      tools:["validation agent","browser","curl"],
      details:["Separate agent reproduces each exploit","Screenshot + response capture","CVSS v3.1 scoring","False positive elimination","Impact assessment","Exploit reliability rating"]},
    {n:"05",name:"REPORTING",time:"1-3 min",c:C.purple,icon:"📄",what:"Professional reports with remediation guidance",
      tools:["jinja2","weasyprint","json","sarif"],
      details:["Executive summary","Technical repro steps per vuln","CVSS scores + CWE classification","Prioritized remediation","Compliance framework mapping","JSON/SARIF for CI/CD","Evidence attachments"]},
  ];

  return <div style={{display:"flex",flexDirection:"column",gap:16}}>
    {/* ReAct Loop */}
    <Card><Head color={C.green}>ReAct AGENT LOOP — Per Phase</Head><div style={{padding:20,textAlign:"center"}}>
      <div style={{display:"flex",justifyContent:"center",alignItems:"center",gap:0,flexWrap:"wrap"}}>
        {["LLM Reasons","→","Selects Tool","→","Permission Check","→","Execute in Sandbox","→","Parse Output","→","Update State"].map((s,i)=>
          <span key={i} style={{padding:i%2===1?"0 4px":"7px 12px",background:i%2===1?"none":C.green+"12",borderRadius:i%2===1?0:5,color:i%2===1?C.dim:C.green,fontSize:11,fontFamily:mono,fontWeight:i%2===1?400:600}}>{s}</span>
        )}
      </div>
      <div style={{marginTop:10,display:"flex",justifyContent:"center",gap:14}}>
        {B(C.yellow,"Max 20 iter/phase")}{B(C.red,"Stuck detect @ 3 repeats")}{B(C.purple,"Human gate for exploits")}{B(C.orange,"Budget enforcement")}
      </div>
    </div></Card>

    {phases.map((p,i)=><Card key={i} style={{borderLeft:`4px solid ${p.c}`}}><div style={{padding:18}}>
      <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:8}}>
        <span style={{fontSize:26}}>{p.icon}</span>
        <div style={{flex:1}}>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <span style={{fontFamily:mono,fontSize:11,color:C.dim}}>{p.n}</span>
            <span style={{fontFamily:mono,fontSize:15,fontWeight:800,color:p.c}}>{p.name}</span>
            {B(p.c,p.time)}
          </div>
          <div style={{fontSize:12,color:C.text,fontWeight:600,marginTop:2}}>{p.what}</div>
        </div>
        <div style={{display:"flex",gap:4,flexWrap:"wrap"}}>{p.tools.map(t=>B(p.c,t))}</div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:3}}>
        {p.details.map((d,j)=><div key={j} style={{display:"flex",gap:6,padding:"3px 0"}}><span style={{color:p.c,fontSize:9,marginTop:3}}>▸</span><span style={{fontSize:11,color:C.dim,lineHeight:1.5}}>{d}</span></div>)}
      </div>
    </div></Card>)}

    {/* Permissions */}
    <Card><Head color={C.red}>TIERED PERMISSION MODEL</Head><div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12,padding:16}}>
      {[{l:"AUTO-APPROVE",d:"nmap, subfinder, httpx, whois, katana — safe read-only recon",c:C.green,i:"✓"},
        {l:"PROMPT ONCE",d:"nuclei, nikto, ffuf, gobuster — active scanning, ask once per tool",c:C.yellow,i:"?"},
        {l:"ALWAYS ASK",d:"sqlmap, metasploit, custom exploits — exploitation requires explicit approval",c:C.red,i:"!"}
      ].map((l,i)=><div key={i} style={{padding:16,background:l.c+"08",border:`1px solid ${l.c}25`,borderRadius:8,textAlign:"center"}}>
        <div style={{fontSize:22,marginBottom:4}}>{l.i}</div>
        <div style={{fontSize:11,fontWeight:700,color:l.c,fontFamily:mono,marginBottom:6}}>{l.l}</div>
        <div style={{fontSize:10,color:C.dim,lineHeight:1.5}}>{l.d}</div>
      </div>)}
    </div></Card>
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// TAB 3: BUSINESS MODEL
// ═══════════════════════════════════════════════════════════════
function BusinessTab() {
  const features = [
    {cat:"CORE ENGINE",items:[
      {f:"ReAct agent loop + multi-agent",free:true,pro:true},
      {f:"LiteLLM (100+ providers, Ollama local)",free:true,pro:true},
      {f:"Docker sandbox (Kali tools)",free:true,pro:true},
      {f:"BYO API key",free:true,pro:true},
      {f:"Tiered permission system",free:true,pro:true},
      {f:"Budget/cost tracking per scan",free:true,pro:true},
      {f:"Multi-model orchestration (route by phase)",free:false,pro:true},
    ]},{cat:"SCANNING",items:[
      {f:"5 core tools (nmap, nuclei, httpx, subfinder, ffuf)",free:true,pro:true},
      {f:"Full 25+ tool suite",free:false,pro:true},
      {f:"Multi-target campaigns",free:false,pro:true},
      {f:"Parallel tool execution",free:false,pro:true},
      {f:"Post-exploitation modules (linpeas, bloodhound)",free:false,pro:true},
      {f:"Cloud infra pentesting (AWS/GCP/Azure)",free:false,pro:true},
      {f:"AD / internal network modules",free:false,pro:true},
    ]},{cat:"REPORTING",items:[
      {f:"JSON findings output",free:true,pro:true},
      {f:"SARIF for GitHub Security tab",free:true,pro:true},
      {f:"Markdown report",free:true,pro:true},
      {f:"HTML executive report",free:false,pro:true},
      {f:"PDF with CVSS scoring + remediation",free:false,pro:true},
      {f:"PCI DSS 4.0 compliance mapping",free:false,pro:true},
      {f:"DORA / NIS2 / SOC 2 / FedRAMP templates",free:false,pro:true},
    ]},{cat:"PLATFORM",items:[
      {f:"CLI + Rich terminal output",free:true,pro:true},
      {f:"Textual TUI (interactive dashboard)",free:true,pro:true},
      {f:"GitHub Actions CI/CD integration",free:true,pro:true},
      {f:"SQLite session persistence + resume",free:true,pro:true},
      {f:"Community plugin system (@tool decorator)",free:true,pro:true},
      {f:"MCP server + client protocol",free:true,pro:true},
      {f:"REST API server mode",free:false,pro:true},
      {f:"Cloud-hosted persistent sessions",free:false,pro:true},
      {f:"Web dashboard + real-time WebSocket",free:false,pro:true},
      {f:"Team RBAC + SSO (SAML/OIDC)",free:false,pro:true},
      {f:"Knowledge graph (cross-engagement learning)",free:false,pro:true},
      {f:"Audit log exports + evidence vault",free:false,pro:true},
    ]},
  ];
  const fc = features.flatMap(c=>c.items);
  const freeC = fc.filter(i=>i.free).length;
  const proC = fc.filter(i=>!i.free).length;

  return <div style={{display:"flex",flexDirection:"column",gap:20}}>
    {/* Pricing Tiers */}
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:16}}>
      {[
        {tier:"FREE / OPEN SOURCE",price:"$0",sub:"forever",color:C.green,cta:"pip install 0xpwn",
          features:[`${freeC} features included`,"BYO API key","Single target scans","Local execution","JSON + SARIF + Markdown","Community support","Apache 2.0 license"]},
        {tier:"PRO",price:"$49",sub:"/mo per seat",color:C.cyan,cta:"14-day free trial",
          features:["Everything in Free",`+ ${proC} pro features`,"Full 25+ tool suite","Cloud hosted sessions","PDF + HTML + compliance reports","Priority support","Managed LLM credits option"]},
        {tier:"ENTERPRISE",price:"Custom",sub:"annual contract",color:C.purple,cta:"Contact sales",
          features:["Everything in Pro","SSO / SAML / OIDC","Team RBAC + audit logs","On-prem deployment option","Knowledge graph persistence","Custom compliance templates","Dedicated support + SLA"]},
      ].map((t,i)=><Card key={i} color={t.color}><div style={{padding:20,textAlign:"center"}}>
        <div style={{fontSize:11,fontWeight:700,color:t.color,fontFamily:mono,letterSpacing:1}}>{t.tier}</div>
        <div style={{fontSize:36,fontWeight:800,color:C.text,fontFamily:mono,lineHeight:1,marginTop:8}}>{t.price}</div>
        <div style={{fontSize:11,color:C.dim,marginBottom:16}}>{t.sub}</div>
        {t.features.map((f,j)=><div key={j} style={{fontSize:11,color:C.dim,padding:"4px 0",borderBottom:`1px solid ${C.border}30`}}>{f}</div>)}
        <div style={{marginTop:14,padding:"8px 16px",background:t.color+"15",borderRadius:6,fontSize:11,color:t.color,fontFamily:mono,fontWeight:600}}>{t.cta}</div>
      </div></Card>)}
    </div>

    {/* Feature Matrix */}
    <Card><Head color={C.green}>COMPLETE FEATURE MATRIX — Free vs Pro</Head>
      {features.map((cat,ci)=><div key={ci}>
        <div style={{padding:"8px 16px",background:C.alt,fontSize:10,fontWeight:700,color:C.dim,fontFamily:mono,letterSpacing:1.5,display:"flex",justifyContent:"space-between"}}>
          <span>{cat.cat}</span>
          <div style={{display:"flex",gap:24}}><span style={{color:C.green,width:50,textAlign:"center"}}>Free</span><span style={{color:C.cyan,width:50,textAlign:"center"}}>Pro</span></div>
        </div>
        {cat.items.map((item,ii)=><div key={ii} style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"6px 16px",borderBottom:`1px solid ${C.border}08`}}>
          <span style={{fontSize:12,color:item.free?C.text:C.dim}}>{item.f}</span>
          <div style={{display:"flex",gap:24}}><span style={{width:50,textAlign:"center",fontSize:13}}>{item.free?"✅":"—"}</span><span style={{width:50,textAlign:"center",fontSize:13}}>✅</span></div>
        </div>)}
      </div>)}
    </Card>

    {/* GTM Strategy */}
    <Card color={C.yellow}><Head color={C.yellow}>GO-TO-MARKET — Open-Core Playbook</Head><div style={{padding:20}}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        {[
          {t:"Adoption Funnel",pts:["pip install → scan → get results → share","GitHub stars + HN launch + security Twitter","Community nuclei-style templates","CTF integration (HackTheBox API)","Free tier is genuinely useful standalone"],c:C.green},
          {t:"Revenue Drivers",pts:["Compliance reports (PCI DSS, DORA, NIS2)","Cloud hosting with persistent sessions","Team RBAC + SSO for enterprise","Managed LLM credits (no BYO key needed)","On-prem deployment + support SLA"],c:C.cyan},
          {t:"Competitive Moat",pts:["PoC validation = zero false positives","Budget controls (nobody else has this)","MCP protocol = ecosystem integration","Open source trust + auditability","Compliance mapping as upsell"],c:C.purple},
          {t:"Market Signals",pts:["$2.7B pentest market, 13% CAGR","4.8M unfilled cybersecurity positions","PCI DSS 4.0 mandates recurring tests","DORA requires annual EU testing","Cyber insurance requires pentest evidence"],c:C.orange},
        ].map((s,i)=><div key={i}><div style={{fontFamily:mono,fontSize:12,fontWeight:700,color:s.c,marginBottom:8}}>{s.t}</div>{s.pts.map((p,j)=><div key={j} style={{fontSize:11,color:C.dim,lineHeight:1.4,padding:"2px 0",display:"flex",gap:6}}><span style={{color:s.c}}>▸</span>{p}</div>)}</div>)}
      </div>
    </div></Card>
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// TAB 4: CAPABILITIES
// ═══════════════════════════════════════════════════════════════
function CapabilitiesTab() {
  const vulns = [
    {cat:"Injection",items:["SQL Injection (Union, Blind, Time, Error)","NoSQL Injection","Command / OS Injection","LDAP Injection","Template Injection (SSTI)"],c:C.red},
    {cat:"Broken Auth & Access",items:["IDOR","Broken Access Control","Authentication Bypass","Session Fixation / Hijacking","JWT Manipulation","OAuth misconfiguration","Privilege Escalation"],c:C.orange},
    {cat:"XSS & Client-Side",items:["Stored XSS","Reflected XSS","DOM-based XSS","CSRF","Clickjacking","Open Redirects","CORS Misconfiguration"],c:C.yellow},
    {cat:"Data Exposure",items:["Sensitive Data in Responses","Path Traversal","LFI / RFI","Info Disclosure","Hardcoded Secrets","Insecure File Upload"],c:C.cyan},
    {cat:"Infrastructure",items:["Server Misconfigs","Missing Security Headers","TLS/SSL Weaknesses","Outdated Software (CVE)","Default Credentials","DNS Zone Transfer"],c:C.purple},
    {cat:"API-Specific",items:["BOLA","Mass Assignment","Rate Limiting Bypass","GraphQL Introspection","Parameter Tampering","API Key Exposure"],c:C.green},
  ];

  return <div style={{display:"flex",flexDirection:"column",gap:20}}>
    {/* Stats */}
    <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:10}}>
      {[{v:"25+",l:"Security Tools",c:C.green},{v:"100+",l:"LLM Providers",c:C.cyan},{v:"40+",l:"Vuln Classes",c:C.red},{v:"5",l:"Report Formats",c:C.purple},{v:"5",l:"Compliance Frameworks",c:C.yellow},{v:"<$1",l:"Avg Scan Cost",c:C.orange}].map((s,i)=>
        <div key={i} style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:8,padding:12,textAlign:"center"}}>
          <div style={{fontSize:24,fontWeight:800,color:s.c,fontFamily:mono}}>{s.v}</div>
          <div style={{fontSize:9,color:C.dim,marginTop:2}}>{s.l}</div>
        </div>
      )}
    </div>

    {/* Tool Suite */}
    <Card><Head color={C.orange}>INTEGRATED TOOL SUITE</Head><div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10,padding:16}}>
      {[
        {cat:"Recon",tools:["subfinder","amass","httpx","katana","whois","dnsutils"],c:C.cyan},
        {cat:"Scanning",tools:["nmap","nuclei","nikto","ffuf","gobuster","zaproxy"],c:C.green},
        {cat:"Exploit",tools:["sqlmap","metasploit","curl","custom AI scripts"],c:C.orange},
        {cat:"Analysis",tools:["semgrep","trufflehog","jwt_tool","python3","browser"],c:C.purple},
        {cat:"Post-Exploit",tools:["linpeas","bloodhound","crackmapexec","impacket"],c:C.red},
      ].map((g,gi)=><div key={gi}>
        <div style={{fontFamily:mono,fontSize:9,fontWeight:700,color:g.c,letterSpacing:1,marginBottom:6}}>{g.cat.toUpperCase()}</div>
        {g.tools.map((t,ti)=><div key={ti} style={{padding:"4px 6px",marginBottom:3,background:g.c+"10",borderRadius:3,fontSize:10,fontFamily:mono,color:g.c}}>{t}</div>)}
      </div>)}
    </div></Card>

    {/* Vuln Coverage */}
    <Sec title="VULNERABILITY COVERAGE — 40+ CLASSES" color={C.red}/>
    <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12}}>
      {vulns.map((v,vi)=><Card key={vi} color={v.c}><div style={{padding:14}}>
        <div style={{fontFamily:mono,fontSize:10,fontWeight:700,color:v.c,marginBottom:8,letterSpacing:0.5}}>{v.cat}</div>
        {v.items.map((item,ii)=><div key={ii} style={{fontSize:10,color:C.dim,lineHeight:1.4,padding:"2px 0",display:"flex",gap:5}}><span style={{color:v.c,fontSize:7,marginTop:3}}>●</span>{item}</div>)}
      </div></Card>)}
    </div>

    {/* Competitive */}
    <Card color={C.green}><Head color={C.green}>WHY 0xPWN — Competitive Advantage (Gap Analysis)</Head><div style={{padding:16}}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        {[
          {vs:"vs Strix (20.5k ★)",pts:["+ Budget/cost controls (Strix has none)","+ Tiered permissions (Strix runs freely)","+ SQLite persistence + resume","+ SARIF/PDF/compliance reports","+ MCP protocol integration","+ Plugin system (@tool decorator)","± Same Docker sandbox pattern","± Same LiteLLM + Textual stack"],c:C.green},
          {vs:"vs Shannon (96% XBOW)",pts:["+ Multi-model support (Shannon = Claude only)","+ Open source CLI (Shannon = AGPL)","+ Budget controls","+ Broader scope (Shannon = web only)","− Shannon has higher benchmark score","− Shannon has Temporal orchestration"],c:C.cyan},
          {vs:"vs Manual Pentesting",pts:["+ Hours instead of weeks","+ $1 instead of $10K+","+ Consistent methodology","+ Available 24/7","+ Compliance reports built-in","− Can't do business logic (yet)","− No social engineering"],c:C.purple},
          {vs:"vs DAST Scanners (Burp/ZAP)",pts:["+ AI chains multi-step exploits","+ Understands application context","+ Generates custom exploits","+ Validates every finding with PoC","+ Natural language instructions","− Less mature than Burp Suite","− Smaller vuln template library"],c:C.orange},
        ].map((v,i)=><div key={i}><div style={{fontFamily:mono,fontSize:11,fontWeight:700,color:v.c,marginBottom:6}}>{v.vs}</div>{v.pts.map((p,j)=><div key={j} style={{fontSize:10,color:p.startsWith("−")?C.red:p.startsWith("±")?C.yellow:C.dim,lineHeight:1.3,padding:"2px 0"}}>{p}</div>)}</div>)}
      </div>
    </div></Card>
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// TAB 5: TECH SPEC
// ═══════════════════════════════════════════════════════════════
function SpecTab() {
  return <div style={{display:"flex",flexDirection:"column",gap:16}}>
    <Card><Head color={C.green}>TECHNOLOGY STACK</Head><div style={{padding:16}}>
      {[
        {cat:"CLI & Interface",c:C.green,items:[{n:"Python 3.12+",r:"Primary — security ecosystem + AI libs"},{n:"Typer",r:"CLI — type hints, auto-help"},{n:"Rich",r:"Terminal formatting, tables, progress"},{n:"Textual",r:"Full TUI with CSS styling + async"},{n:"uv",r:"Package manager — near-instant installs"}]},
        {cat:"AI / LLM",c:C.purple,items:[{n:"LiteLLM",r:"100+ providers, unified tool calling"},{n:"Codex 5.3 / Claude / Ollama",r:"Primary models — swap per engagement"},{n:"Pydantic v2",r:"Structured output, tool schemas, state models"},{n:"Jinja2",r:"System prompt templates with phase context"}]},
        {cat:"Execution",c:C.orange,items:[{n:"Docker SDK (python)",r:"Container lifecycle — spawn, exec, destroy"},{n:"Ubuntu 24.04 / Kali base",r:"Sandbox image with 25+ tools (~800MB)"},{n:"asyncio",r:"Async tool execution with timeout + streaming"},{n:"xmltodict",r:"nmap XML parser; JSON for nuclei/httpx/ffuf"}]},
        {cat:"Persistence",c:C.cyan,items:[{n:"SQLite (aiosqlite)",r:"Local sessions, findings, audit log"},{n:"PostgreSQL",r:"Cloud tier — users, teams, shared state"},{n:"Redis",r:"State checkpointing, pub/sub for real-time"},{n:"Neo4j / Graphiti",r:"Knowledge graph — cross-engagement learning (v2)"}]},
        {cat:"Cloud / Infra",c:C.blue,items:[{n:"ECS / Fargate",r:"Container orchestration, no time limits"},{n:"Temporal.io",r:"Durable workflows, human-in-the-loop"},{n:"FastAPI",r:"REST + WebSocket API gateway"},{n:"Fly.io / Railway",r:"MVP deployment — simple container hosting"}]},
        {cat:"Testing",c:C.yellow,items:[{n:"OWASP Juice Shop",r:"Primary target — Score Board API validation"},{n:"DVWA",r:"Graduated difficulty levels"},{n:"pytest + GitHub Actions",r:"Unit + integration CI pipeline"},{n:"CloudGoat",r:"AWS cloud pentest validation (v2)"}]},
      ].map((cat,ci)=><div key={ci} style={{marginBottom:ci<5?16:0}}>
        <div style={{fontFamily:mono,fontSize:10,fontWeight:700,color:cat.c,letterSpacing:1,marginBottom:6}}>{cat.cat.toUpperCase()}</div>
        {cat.items.map((item,ii)=><div key={ii} style={{display:"flex",gap:10,padding:"3px 0"}}>
          <span style={{fontSize:12,fontWeight:700,color:C.text,fontFamily:mono,minWidth:180}}>{item.n}</span>
          <span style={{fontSize:11,color:C.dim}}>{item.r}</span>
        </div>)}
      </div>)}
    </div></Card>

    <Card><Head color={C.cyan}>DIRECTORY STRUCTURE</Head><div style={{padding:16}}>
      <pre style={{margin:0,fontFamily:mono,fontSize:11,color:C.dim,lineHeight:1.7}}>{`src/oxpwn/
├── cli.py              # Typer commands: scan, config, sessions, resume, report, serve
├── config.py           # Pydantic settings + YAML + env vars
├── agent/
│   ├── loop.py         # Core ReAct loop (~200 LOC)
│   ├── planner.py      # 5-phase strategy
│   ├── validator.py    # Independent PoC verification agent
│   ├── state.py        # AgentState + Finding Pydantic models
│   └── prompts/        # Jinja2 system prompts per phase
├── llm/
│   ├── client.py       # LiteLLM async wrapper
│   ├── cost.py         # Token tracking + budget enforcement
│   └── models.py       # Provider configs + context limits
├── sandbox/
│   ├── runtime.py      # DockerRuntime: create → exec → destroy
│   ├── tools.py        # Tool definitions (OpenAI function schemas)
│   └── parser.py       # Structured output extraction per tool
├── permissions/
│   └── tiers.py        # Auto-approve / prompt-once / always-ask
├── reporting/
│   ├── json_report.py  # Structured JSON
│   ├── sarif.py        # SARIF 2.1.0 for GitHub Security
│   ├── markdown.py     # Clean markdown report
│   ├── html.py         # Executive HTML report (Pro)
│   ├── pdf.py          # PDF with CVSS (Pro)
│   └── compliance.py   # PCI/DORA/NIS2/SOC2 mapping (Pro)
├── storage/
│   ├── database.py     # SQLite via aiosqlite
│   └── sessions.py     # CRUD + resume logic
└── ui/
    ├── banner.py       # ASCII art + version
    ├── display.py      # Rich console helpers
    └── tui.py          # Textual TUI (interactive mode)`}</pre>
    </div></Card>

    <Card><Head color={C.red}>CODING RULES</Head><div style={{padding:16}}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
        {[
          {cat:"Code Standards",rules:["Python 3.12+ — type unions, match, Annotated","Async everywhere — all I/O is async","Pydantic v2 for all data models","Type hints on every function — no Any","No LangChain — LiteLLM + custom loop","No global state — constructor injection","Rich for output — never bare print()","structlog for logging"],c:C.green},
          {cat:"Prompt Engineering",rules:["Jinja2 templates in agent/prompts/","Parse tool output → JSON before feeding LLM","Running findings_summary updated each iteration","XML tags for structured extraction","Include phase + remaining budget in system msg","Track what tools already ran (prevent re-runs)"],c:C.purple},
          {cat:"Security",rules:["Never execute on host — Docker sandbox only","Scope enforcement — block out-of-scope targets","No credential storage in code","Container cleanup after every scan","Strip ANSI codes from tool output","Audit log every action immutably"],c:C.red},
          {cat:"Patterns Borrowed",rules:["Strix: AbstractRuntime, tool_server in sandbox","CAI: @function_tool decorator (reimplemented)","MAPTA: Validation agent (proof-by-exploitation)","MAPTA: Early-stopping at ~40 calls / $0.30","PentAGI: Reflector (text → tool redirect)","PentAGI: Lightweight Kali Docker image"],c:C.cyan},
        ].map((s,i)=><div key={i}>
          <div style={{fontFamily:mono,fontSize:10,fontWeight:700,color:s.c,letterSpacing:1,marginBottom:8}}>{s.cat.toUpperCase()}</div>
          {s.rules.map((r,j)=><div key={j} style={{fontSize:10,color:C.dim,lineHeight:1.4,padding:"2px 0",display:"flex",gap:6}}><span style={{color:s.c,flexShrink:0}}>▸</span>{r}</div>)}
        </div>)}
      </div>
    </div></Card>
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// TAB 6: BRAND
// ═══════════════════════════════════════════════════════════════
function BrandTab() {
  return <div style={{display:"flex",flexDirection:"column",gap:24}}>
    <div style={{textAlign:"center",padding:"40px 0 32px"}}>
      <div style={{fontFamily:mono,fontSize:72,fontWeight:800,letterSpacing:-4}}>
        <span style={{color:C.green,textShadow:`0 0 60px ${C.green}40`}}>0x</span><span style={{color:C.text}}>pwn</span>
      </div>
      <div style={{fontFamily:mono,fontSize:14,color:C.dim,marginTop:8,letterSpacing:4}}>AUTONOMOUS AI PENTESTING AGENT</div>
      <div style={{marginTop:16,display:"flex",justifyContent:"center",gap:10}}>
        {["Apache 2.0","Python 3.12+","LiteLLM","Docker","Build Fresh"].map((t,i)=><span key={i} style={{padding:"4px 10px",borderRadius:4,fontSize:10,fontFamily:mono,background:i===0?C.greenDim:C.border+"80",color:i===0?C.green:C.dim,fontWeight:600}}>{t}</span>)}
      </div>
    </div>

    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
      <Card><Head>TAGLINES</Head><div style={{padding:16}}>
        {[{l:"The AI that pwns so you don't have to.",n:"README hero"},{l:"Autonomous pentesting. Zero false positives.",n:"Landing page"},{l:"Your AI red team operator.",n:"Social"},{l:"Find real vulns. Ship real PoCs.",n:"Dev audience"}].map((t,i)=>
          <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"8px 0",borderBottom:i<3?`1px solid ${C.border}30`:"none"}}>
            <span style={{fontSize:13,color:C.text,fontFamily:mono,fontWeight:600}}>"{t.l}"</span>
            <span style={{fontSize:9,color:C.dim}}>{t.n}</span>
          </div>
        )}
      </div></Card>

      <Card><Head>AVAILABILITY</Head><div style={{padding:16}}>
        {[{p:"GitHub",h:"github.com/0xpwn",s:"✅"},{p:"PyPI",h:"pip install 0xpwn",s:"✅"},{p:"npm",h:"npx 0xpwn",s:"✅"},{p:"Domain",h:"0xpwn.dev",s:"✅"}].map((p,i)=>
          <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"8px 10px",background:C.alt,borderRadius:4,marginBottom:6}}>
            <div><span style={{fontSize:12,fontWeight:600,color:C.text}}>{p.p}</span><span style={{fontSize:10,color:C.dim,marginLeft:8}}>{p.h}</span></div>
            <span>{p.s}</span>
          </div>
        )}
      </div></Card>
    </div>

    {/* Colors */}
    <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:10}}>
      {[{n:"Primary",h:"#00ff87",c:C.green},{n:"Background",h:"#05080f",c:C.bg},{n:"Critical",h:"#ff3e3e",c:C.red},{n:"Warning",h:"#ffe14d",c:C.yellow},{n:"Info",h:"#00e5ff",c:C.cyan},{n:"Accent",h:"#b44dff",c:C.purple}].map((col,i)=>
        <div key={i} style={{textAlign:"center"}}><div style={{width:"100%",height:40,borderRadius:6,background:col.c,border:i===1?`1px solid ${C.border}`:"none"}}/><div style={{fontSize:9,fontFamily:mono,color:C.text,marginTop:4}}>{col.n}</div><div style={{fontSize:8,fontFamily:mono,color:C.dim}}>{col.h}</div></div>
      )}
    </div>

    {/* CLI Preview */}
    <Card><Head>CLI PREVIEW</Head>
      <pre style={{padding:16,margin:0,fontFamily:mono,fontSize:12,lineHeight:1.8,overflowX:"auto"}}>
        <span style={{color:C.green}}>❯ </span><span style={{color:C.text}}>0xpwn scan --target https://juice-shop.example.com --budget 5.00</span>{"\n\n"}
        <span style={{color:C.green}}>{"  ██████╗ ██╗  ██╗██████╗ ██╗    ██╗███╗   ██╗\n"}</span>
        <span style={{color:C.green}}>{"  ██╔═══██╗╚██╗██╔╝██╔══██╗██║    ██║████╗  ██║\n"}</span>
        <span style={{color:C.green}}>{"  ██║   ██║ ╚███╔╝ ██████╔╝██║ █╗ ██║██╔██╗ ██║\n"}</span>
        <span style={{color:C.green}}>{"  ██║   ██║ ██╔██╗ ██╔═══╝ ██║███╗██║██║╚██╗██║\n"}</span>
        <span style={{color:C.green}}>{"  ╚██████╔╝██╔╝ ██╗██║     ╚███╔███╔╝██║ ╚████║\n"}</span>
        <span style={{color:C.green}}>{"   ╚═════╝ ╚═╝  ╚═╝╚═╝      ╚══╝╚══╝ ╚═╝  ╚═══╝\n"}</span>{"\n"}
        <span style={{color:C.dim}}>{"  v0.1.0 • model: codex-5.3 • budget: $5.00\n\n"}</span>
        <span style={{color:C.yellow}}>{"  ⚡ Phase 1/5: RECONNAISSANCE\n"}</span>
        <span style={{color:C.dim}}>{"     ├── subfinder → 23 subdomains\n"}</span>
        <span style={{color:C.dim}}>{"     └── nmap → 3 open ports\n\n"}</span>
        <span style={{color:C.red}}>{"  ┌─ CRITICAL ──────────────────────────────────┐\n"}</span>
        <span style={{color:C.red}}>{"  │  SQL Injection in /rest/products/search      │\n"}</span>
        <span style={{color:C.red}}>{"  │  CVSS: 9.8 • PoC verified ✓                 │\n"}</span>
        <span style={{color:C.red}}>{"  └──────────────────────────────────────────────┘\n\n"}</span>
        <span style={{color:C.green}}>{"  ✓ 2 findings • $0.47 spent • 4m 12s\n"}</span>
      </pre>
    </Card>
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// TAB 7: MERMAID DIAGRAMS
// ═══════════════════════════════════════════════════════════════
function MermaidTab() {
  const [copied, setCopied] = useState(null);
  const copy = (text, id) => { navigator.clipboard?.writeText(text); setCopied(id); setTimeout(()=>setCopied(null), 2000); };

  const diagrams = [
    {title:"System Architecture — End-to-End",id:"sys",code:`graph TD
    subgraph UI["🖥️ User Interface Layer"]
        CLI["Typer CLI"] --> CORE
        TUI["Textual TUI"] --> CORE
        API["REST API"] --> CORE
        WS["WebSocket"] --> CORE
        CICD["GitHub Actions"] --> CORE
    end

    subgraph CORE["🤖 Agent Core — ReAct Loop"]
        PLANNER["Planner\\n(Phase Strategy)"]
        EXECUTOR["Executor\\n(Tool Orchestration)"]
        PERCEPTOR["Perceptor\\n(Output Parsing)"]
        VALIDATOR["Validator\\n(PoC Verification)"]
        REPORTER["Reporter\\n(Findings + Reports)"]
        PLANNER --> EXECUTOR --> PERCEPTOR --> VALIDATOR --> REPORTER
        REPORTER -.->|feedback| PLANNER
    end

    subgraph CONTROLS["🔒 Controls"]
        BUDGET["Budget Tracker"]
        PERMS["Permission Tiers"]
        STATE["State Manager"]
        STUCK["Stuck Detector"]
    end

    subgraph LLM["🧠 LLM Layer — LiteLLM"]
        OPENAI["OpenAI / Codex 5.3"]
        CLAUDE["Anthropic Claude"]
        OLLAMA["Ollama (Local)"]
        GEMINI["Gemini / Mistral / DeepSeek"]
    end

    subgraph SANDBOX["🐳 Docker Sandbox — Kali Linux"]
        NMAP["nmap"] & NUCLEI["nuclei"] & SQLMAP["sqlmap"]
        FFUF["ffuf"] & HTTPX["httpx"] & NIKTO["nikto"]
        SUBFINDER["subfinder"] & GOBUSTER["gobuster"]
    end

    subgraph STORAGE["💾 Persistence"]
        SQLITE["SQLite\\n(local)"]
        POSTGRES["PostgreSQL\\n(cloud)"]
        REDIS["Redis\\n(state)"]
        NEO4J["Neo4j\\n(knowledge graph)"]
    end

    subgraph REPORTS["📊 Reporting"]
        JSON["JSON"] & SARIF["SARIF"] & HTML["HTML"]
        PDF["PDF"] & MD["Markdown"]
    end

    subgraph COMPLIANCE["🏛️ Compliance"]
        PCI["PCI DSS 4.0"] & DORA["DORA"]
        NIS2["NIS2"] & SOC2["SOC 2"]
    end

    CORE --> LLM
    CORE --> SANDBOX
    CORE --> STORAGE
    CORE --> REPORTS
    REPORTS --> COMPLIANCE
    CONTROLS --> CORE
    SANDBOX --> TARGET["🎯 Target Environment"]`},

    {title:"CLI Command Architecture",id:"cli",code:`graph LR
    subgraph ENTRY["Entry Points"]
        PIP["pip install 0xpwn"]
        DOCKER["docker run 0xpwn"]
        PYMOD["python -m oxpwn"]
    end

    PIP --> CLI
    DOCKER --> CLI
    PYMOD --> CLI

    subgraph CLI["oxpwn/cli.py — Typer"]
        SCAN["scan\\n--target --mode --budget"]
        CONFIG["config\\nset / show"]
        SESSIONS["sessions\\nlist"]
        RESUME["resume\\n<session-id>"]
        REPORT["report\\n--format --session"]
        SERVE["serve\\n--port"]
    end

    SCAN --> AGENT["agent/loop.py\\nReAct Loop"]
    AGENT --> LLM["llm/client.py\\nLiteLLM"]
    AGENT --> SANDBOX["sandbox/runtime.py\\nDocker SDK"]
    AGENT --> PERMS["permissions/tiers.py"]
    AGENT --> STATE["storage/database.py\\nSQLite"]
    AGENT --> REPORTING["reporting/\\njson | sarif | pdf"]`},

    {title:"Agent ReAct Loop — Per Phase",id:"react",code:`graph TD
    START([Phase Start]) --> PLAN[LLM Plans Next Action]
    PLAN --> TOOL{Tool Call?}
    TOOL -->|No| DONE([Phase Complete])
    TOOL -->|Yes| PERM{Permission\\nCheck}
    PERM -->|Denied| DENIED[Feed Denial to LLM] --> PLAN
    PERM -->|Approved| BUDGET{Budget\\nCheck}
    BUDGET -->|Exceeded| STOP([Budget Limit Hit])
    BUDGET -->|OK| EXEC[Execute in Docker Sandbox]
    EXEC --> PARSE[Parse Structured Output]
    PARSE --> STUCK{Stuck?\\n3 identical actions}
    STUCK -->|Yes| REDIRECT[Force Different Approach] --> PLAN
    STUCK -->|No| UPDATE[Update State + Findings]
    UPDATE --> ITER{Max Iterations?}
    ITER -->|Yes| DONE
    ITER -->|No| PLAN`},

    {title:"Deployment Architecture — Free vs Cloud",id:"deploy",code:`graph TB
    subgraph FREE["🆓 Free Tier — Local"]
        F_CLI["0xpwn CLI"] --> F_AGENT["Agent Core"]
        F_AGENT --> F_LLM["LiteLLM\\n→ Ollama / BYO Key"]
        F_AGENT --> F_DOCKER["Docker Sandbox\\nKali + Tools"]
        F_AGENT --> F_SQLITE["SQLite\\n~/.0xpwn/sessions.db"]
        F_DOCKER --> F_TARGET["Target"]
    end

    subgraph CLOUD["☁️ Pro/Enterprise — Cloud"]
        C_GW["FastAPI Gateway\\nREST + WebSocket"] --> C_TEMPORAL["Temporal\\nWorkflow Orchestration"]
        C_TEMPORAL --> C_WORKERS["ECS/Fargate Workers"]
        C_WORKERS --> C_AGENT["Agent Core"]
        C_AGENT --> C_LLM["LiteLLM\\nManaged Credits"]
        C_AGENT --> C_DOCKER["Docker Sandbox\\nEphemeral Containers"]
        C_AGENT --> C_PG["PostgreSQL + pgvector"]
        C_AGENT --> C_REDIS["Redis\\nState + Pub/Sub"]
        C_DOCKER --> C_TARGET["Target"]
        C_GW --> C_WEB["Web Dashboard"]
        C_GW --> C_SSO["SSO / SAML"]
    end`},

    {title:"Freemium Feature Gating",id:"biz",code:`graph LR
    subgraph FREE["🆓 Free (Open Source)"]
        F1["5 core tools"]
        F2["BYO API key"]
        F3["JSON + SARIF + Markdown"]
        F4["SQLite persistence"]
        F5["CLI + TUI"]
        F6["GitHub Actions CI"]
        F7["MCP protocol"]
        F8["Community plugins"]
    end

    subgraph PRO["💎 Pro ($49/mo)"]
        P1["25+ tools"]
        P2["Managed LLM credits"]
        P3["HTML + PDF reports"]
        P4["Compliance mapping"]
        P5["Cloud sessions"]
        P6["Multi-target campaigns"]
        P7["REST API server"]
        P8["Parallel execution"]
    end

    subgraph ENT["🏢 Enterprise (Custom)"]
        E1["SSO / SAML / OIDC"]
        E2["Team RBAC"]
        E3["Audit log exports"]
        E4["Knowledge graph"]
        E5["On-prem deployment"]
        E6["Custom compliance"]
        E7["Dedicated support + SLA"]
        E8["Web dashboard"]
    end

    FREE --> PRO --> ENT`},
  ];

  return <div style={{display:"flex",flexDirection:"column",gap:16}}>
    <p style={{fontSize:12,color:C.dim,lineHeight:1.6}}>Copy these Mermaid diagrams into any Mermaid renderer (GitHub README, Notion, mermaid.live, VS Code extension) to get visual architecture diagrams.</p>
    {diagrams.map((d,i)=><Card key={i}>
      <Head color={[C.green,C.cyan,C.purple,C.orange,C.yellow][i%5]}>
        <span style={{flex:1}}>{d.title}</span>
        <button onClick={()=>copy(d.code,d.id)} style={{padding:"4px 10px",borderRadius:4,border:`1px solid ${C.border}`,background:copied===d.id?C.green+"20":C.alt,color:copied===d.id?C.green:C.dim,fontSize:10,fontFamily:mono,cursor:"pointer"}}>{copied===d.id?"✓ Copied":"Copy"}</button>
      </Head>
      <pre style={{padding:16,margin:0,fontFamily:mono,fontSize:11,color:C.dim,lineHeight:1.6,overflowX:"auto",maxHeight:300}}>{d.code}</pre>
    </Card>)}
  </div>;
}

// ═══════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════
export default function App() {
  const [tab, setTab] = useState(0);
  const tabs = [ArchitectureTab, PipelineTab, BusinessTab, CapabilitiesTab, SpecTab, BrandTab, MermaidTab];
  const T = tabs[tab];
  const tabColors = [C.green, C.cyan, C.yellow, C.red, C.purple, C.green, C.orange];

  return <div style={{minHeight:"100vh",background:C.bg,color:C.text,fontFamily:sans}}>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet"/>
    <div style={{padding:"18px 24px 0",borderBottom:`1px solid ${C.border}`}}>
      <div style={{display:"flex",alignItems:"baseline",gap:3,marginBottom:2}}>
        <span style={{fontFamily:mono,fontSize:20,fontWeight:800,color:C.green}}>0x</span>
        <span style={{fontFamily:mono,fontSize:20,fontWeight:800,color:C.text}}>pwn</span>
        <span style={{fontFamily:mono,fontSize:10,color:C.dim,marginLeft:10,fontWeight:600,letterSpacing:1}}>COMPLETE PRODUCT SPECIFICATION</span>
      </div>
      <div style={{display:"flex",gap:0,marginTop:10,overflowX:"auto"}}>
        {TABS.map((s,i)=><button key={i} onClick={()=>setTab(i)} style={{
          padding:"9px 14px",border:"none",cursor:"pointer",whiteSpace:"nowrap",
          background:tab===i?C.surface:"transparent",
          borderTop:tab===i?`2px solid ${tabColors[i]}`:"2px solid transparent",
          color:tab===i?tabColors[i]:C.dim,
          fontSize:11,fontWeight:tab===i?700:500,fontFamily:mono,
          borderRadius:"6px 6px 0 0",marginBottom:-1,borderBottom:"none",
        }}>{s}</button>)}
      </div>
    </div>
    <div style={{padding:"20px 24px 48px",maxWidth:960}}><T/></div>
  </div>;
}
