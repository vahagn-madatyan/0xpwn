import { useState } from "react";

const C = {
  bg: "#05080f", surface: "#0c1120", surfaceAlt: "#0a0f1c",
  border: "#1a2340", text: "#e2e8f0", textDim: "#5a6888",
  green: "#00ff87", greenDim: "#00ff8720", red: "#ff3e3e",
  cyan: "#00e5ff", purple: "#b44dff", orange: "#ff8a00",
  yellow: "#ffe14d", blue: "#4d8eff", pink: "#ff4da6",
};

const mono = "'JetBrains Mono', 'Fira Code', monospace";
const SECTIONS = ["Brand", "CLI Preview", "Features", "Capabilities", "README", "Install"];

const badge = (color, text, filled) => (
  <span key={text} style={{ display: "inline-block", padding: "3px 9px", borderRadius: filled ? 4 : 99, fontSize: 10, fontWeight: 600, background: color + (filled ? "30" : "15"), color, fontFamily: mono, letterSpacing: 0.3 }}>{text}</span>
);

const card = { background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, overflow: "hidden" };

// ── BRAND ────────────────────────────────────────────────────
function BrandTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <div style={{ textAlign: "center", padding: "48px 0 40px" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 3 }}>
          <span style={{ fontFamily: mono, fontSize: 72, fontWeight: 800, color: C.green, letterSpacing: -4, textShadow: `0 0 60px ${C.green}40, 0 0 120px ${C.green}15` }}>0x</span>
          <span style={{ fontFamily: mono, fontSize: 72, fontWeight: 800, color: C.text, letterSpacing: -4 }}>pwn</span>
        </div>
        <div style={{ fontFamily: mono, fontSize: 14, color: C.textDim, marginTop: 8, letterSpacing: 4 }}>AUTONOMOUS AI PENTESTING AGENT</div>
        <div style={{ marginTop: 20, display: "flex", justifyContent: "center", gap: 12 }}>
          {["Apache 2.0", "Python", "LiteLLM", "Docker", "Strix Fork"].map((t, i) => (
            <span key={i} style={{ padding: "4px 10px", borderRadius: 4, fontSize: 10, fontFamily: mono, background: i === 0 ? C.greenDim : C.border + "80", color: i === 0 ? C.green : C.textDim, fontWeight: 600 }}>{t}</span>
          ))}
        </div>
      </div>
      <div style={{ ...card, padding: 0 }}>
        <div style={{ padding: "10px 16px", background: C.surfaceAlt, borderBottom: `1px solid ${C.border}`, fontFamily: mono, fontSize: 11, fontWeight: 700, color: C.green, letterSpacing: 1.5 }}>TAGLINES</div>
        {[
          { line: "The AI that pwns so you don't have to.", note: "README hero" },
          { line: "Autonomous pentesting. Zero false positives.", note: "Landing page" },
          { line: "Your AI red team operator.", note: "Social / badges" },
          { line: "Find real vulns. Ship real PoCs.", note: "Dev audience" },
        ].map((t, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 16px", borderBottom: i < 3 ? `1px solid ${C.border}40` : "none" }}>
            <span style={{ fontSize: 15, color: C.text, fontFamily: mono, fontWeight: 600 }}>"{t.line}"</span>
            <span style={{ fontSize: 10, color: C.textDim }}>{t.note}</span>
          </div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12 }}>
        {[
          { name: "Primary", hex: "#00ff87", c: C.green }, { name: "Background", hex: "#05080f", c: C.bg },
          { name: "Critical", hex: "#ff3e3e", c: C.red }, { name: "Warning", hex: "#ffe14d", c: C.yellow },
          { name: "Info", hex: "#00e5ff", c: C.cyan }, { name: "Accent", hex: "#b44dff", c: C.purple },
        ].map((col, i) => (
          <div key={i} style={{ textAlign: "center" }}>
            <div style={{ width: "100%", height: 48, borderRadius: 8, background: col.c, border: i === 1 ? `1px solid ${C.border}` : "none" }} />
            <div style={{ fontSize: 10, fontFamily: mono, color: C.text, marginTop: 6 }}>{col.name}</div>
            <div style={{ fontSize: 9, fontFamily: mono, color: C.textDim }}>{col.hex}</div>
          </div>
        ))}
      </div>
      <div style={{ ...card, padding: 0 }}>
        <div style={{ padding: "10px 16px", background: C.surfaceAlt, borderBottom: `1px solid ${C.border}`, fontFamily: mono, fontSize: 11, fontWeight: 700, color: C.green, letterSpacing: 1.5 }}>AVAILABILITY</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8, padding: 16 }}>
          {[
            { p: "GitHub", h: "github.com/0xpwn", s: "✅" }, { p: "PyPI", h: "pip install 0xpwn", s: "✅" },
            { p: "npm", h: "npx 0xpwn", s: "✅" }, { p: "Domain", h: "0xpwn.dev", s: "✅" },
          ].map((p, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: C.surfaceAlt, borderRadius: 6 }}>
              <div><span style={{ fontSize: 12, fontWeight: 600, color: C.text }}>{p.p}</span><span style={{ fontSize: 11, color: C.textDim, marginLeft: 8 }}>{p.h}</span></div>
              <span style={{ fontSize: 11 }}>{p.s}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── CLI PREVIEW ──────────────────────────────────────────────
function CLITab() {
  const O = ({ children, color }) => <div style={{ color: color || C.textDim, lineHeight: 1.7 }}>{children}</div>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ ...card }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 16px", background: C.surfaceAlt, borderBottom: `1px solid ${C.border}` }}>
          <div style={{ width: 10, height: 10, borderRadius: 99, background: "#ff5f57" }} />
          <div style={{ width: 10, height: 10, borderRadius: 99, background: "#febc2e" }} />
          <div style={{ width: 10, height: 10, borderRadius: 99, background: "#28c840" }} />
          <span style={{ fontSize: 11, color: C.textDim, marginLeft: 8, fontFamily: mono }}>0xpwn — Terminal</span>
        </div>
        <pre style={{ padding: 20, margin: 0, fontFamily: mono, fontSize: 12.5, lineHeight: 1.8, overflowX: "auto" }}>
          <span style={{ color: C.green }}>❯ </span><span style={{ color: C.text }}>0xpwn scan --target https://juice-shop.example.com</span>{"\n\n"}
          <O color={C.green}>{"  ██████╗ ██╗  ██╗██████╗ ██╗    ██╗███╗   ██╗"}</O>
          <O color={C.green}>{"  ██╔═══██╗╚██╗██╔╝██╔══██╗██║    ██║████╗  ██║"}</O>
          <O color={C.green}>{"  ██║   ██║ ╚███╔╝ ██████╔╝██║ █╗ ██║██╔██╗ ██║"}</O>
          <O color={C.green}>{"  ██║   ██║ ██╔██╗ ██╔═══╝ ██║███╗██║██║╚██╗██║"}</O>
          <O color={C.green}>{"  ╚██████╔╝██╔╝ ██╗██║     ╚███╔███╔╝██║ ╚████║"}</O>
          <O color={C.green}>{"   ╚═════╝ ╚═╝  ╚═╝╚═╝      ╚══╝╚══╝ ╚═╝  ╚═══╝"}</O>
          {"\n"}
          <O color={C.textDim}>{"  v0.1.0 • autonomous AI pentesting agent"}</O>
          <O color={C.textDim}>{"  model: openai/codex-5.3 • sandbox: kali-docker • budget: $10.00"}</O>
          {"\n"}
          <O color={C.cyan}>{"  ┌─ Target ──────────────────────────────────────┐"}</O>
          <O color={C.cyan}>{"  │  https://juice-shop.example.com               │"}</O>
          <O color={C.cyan}>{"  │  Type: web application • Mode: deep            │"}</O>
          <O color={C.cyan}>{"  └────────────────────────────────────────────────┘"}</O>
          {"\n"}
          <O color={C.yellow}>{"  ⚡ Phase 1/5: RECONNAISSANCE"}</O>
          <O>{"     ├── subfinder → 23 subdomains discovered"}</O>
          <O>{"     ├── httpx → 18 live hosts confirmed"}</O>
          <O>{"     ├── nmap → 3 open ports (80, 443, 3000)"}</O>
          <O>{"     └── Tech: Node.js, Express, Angular, SQLite"}</O>
          {"\n"}
          <O color={C.yellow}>{"  ⚡ Phase 2/5: SCANNING"}</O>
          <O>{"     ├── nuclei → 7 potential vulnerabilities"}</O>
          <O>{"     ├── ffuf → 12 hidden endpoints found"}</O>
          <O>{"     └── nikto → 3 server misconfigurations"}</O>
          {"\n"}
          <O color={C.orange}>{"  ⚡ Phase 3/5: EXPLOITATION"}</O>
          <O color={C.red}>{"     ┌─ CRITICAL ─────────────────────────────────┐"}</O>
          <O color={C.red}>{"     │  SQL Injection in /rest/products/search     │"}</O>
          <O color={C.red}>{"     │  PoC: ' OR 1=1-- → 200 OK (full DB dump)   │"}</O>
          <O color={C.red}>{"     │  CVSS: 9.8 • CWE-89                        │"}</O>
          <O color={C.red}>{"     └────────────────────────────────────────────┘"}</O>
          <O color={C.orange}>{"     ┌─ HIGH ─────────────────────────────────────┐"}</O>
          <O color={C.orange}>{"     │  Stored XSS in /api/Users (username field) │"}</O>
          <O color={C.orange}>{"     │  PoC: <script>alert(1)</script> → executed  │"}</O>
          <O color={C.orange}>{"     │  CVSS: 7.5 • CWE-79                       │"}</O>
          <O color={C.orange}>{"     └────────────────────────────────────────────┘"}</O>
          {"\n"}
          <O color={C.green}>{"  ✓ Phase 4/5: VALIDATION — 2/2 exploits verified"}</O>
          <O color={C.green}>{"  ✓ Phase 5/5: REPORT GENERATED"}</O>
          {"\n"}
          <O color={C.text}>{"  ┌─ Summary ─────────────────────────────────────┐"}</O>
          <O color={C.text}>{"  │  🔴 Critical: 1  🟠 High: 1  🟡 Medium: 3    │"}</O>
          <O color={C.text}>{"  │  📄 Report: ./0xpwn_reports/juice-shop.json    │"}</O>
          <O color={C.text}>{"  │  💰 Cost: $0.47 (codex-5.3) • Time: 4m 12s    │"}</O>
          <O color={C.text}>{"  └────────────────────────────────────────────────┘"}</O>
        </pre>
      </div>
      <div style={{ ...card, padding: 20 }}>
        <div style={{ fontFamily: mono, fontSize: 11, fontWeight: 700, color: C.green, letterSpacing: 1.5, marginBottom: 14 }}>ALL CLI COMMANDS</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {[
            { cmd: "0xpwn scan --target <url>", desc: "Full autonomous pentest" },
            { cmd: "0xpwn scan -t ./ --mode quick", desc: "Quick source code review" },
            { cmd: "0xpwn scan -t <url> --budget 5.00", desc: "Cap LLM spend at $5" },
            { cmd: "0xpwn report --format pdf", desc: "Generate PDF report" },
            { cmd: "0xpwn config set model ollama/qwen3", desc: "Switch to local model" },
            { cmd: "0xpwn sessions list", desc: "Browse past scans" },
            { cmd: "0xpwn resume <session-id>", desc: "Resume interrupted scan" },
            { cmd: "0xpwn serve --port 8080", desc: "Start REST API server" },
          ].map((c, i) => (
            <div key={i} style={{ padding: "8px 12px", background: C.surfaceAlt, borderRadius: 6 }}>
              <div style={{ fontFamily: mono, fontSize: 11, color: C.green }}>{c.cmd}</div>
              <div style={{ fontSize: 10, color: C.textDim, marginTop: 2 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── FEATURES TAB ─────────────────────────────────────────────
function FeaturesTab() {
  const F = ({ icon, title, desc, tags, color }) => (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 20, borderTop: `3px solid ${color}`, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 26 }}>{icon}</span>
        <span style={{ fontFamily: mono, fontSize: 14, fontWeight: 700, color }}>{title}</span>
      </div>
      <div style={{ fontSize: 12, color: C.textDim, lineHeight: 1.7 }}>{desc}</div>
      <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginTop: "auto" }}>{tags.map(t => badge(color, t, true))}</div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Hero Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {[
          { val: "25+", label: "Security Tools", c: C.green },
          { val: "100+", label: "LLM Providers", c: C.cyan },
          { val: "5", label: "Pentest Phases", c: C.purple },
          { val: "0", label: "False Positives*", c: C.orange },
          { val: "< $1", label: "Per Scan (avg)", c: C.yellow },
        ].map((s, i) => (
          <div key={i} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16, textAlign: "center" }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: s.c, fontFamily: mono }}>{s.val}</div>
            <div style={{ fontSize: 10, color: C.textDim, marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.green, letterSpacing: 1.5 }}>CORE FEATURES</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <F icon="🤖" title="Autonomous Agent" color={C.green} desc="ReAct-based multi-agent system that plans, executes, and adapts. Spawns specialized sub-agents, detects loops, and chains multi-step exploits like a human pentester." tags={["ReAct loop", "Sub-agents", "Stuck detection", "Adaptive"]} />
        <F icon="🧠" title="Any LLM, Anywhere" color={C.cyan} desc="100+ providers via LiteLLM. Use Codex 5.3 for max power, Claude for analysis, or Ollama for fully offline private scans. Switch models with one config change." tags={["OpenAI", "Anthropic", "Ollama", "Gemini", "DeepSeek", "vLLM"]} />
        <F icon="🐳" title="Docker Sandbox" color={C.purple} desc="All tools run inside isolated Kali Linux containers. NET_ADMIN/NET_RAW capabilities, self-signed CA for HTTPS interception, auto-cleanup after every scan." tags={["Kali Linux", "Isolation", "HTTPS proxy", "Auto-cleanup"]} />
        <F icon="🎯" title="PoC-Validated Findings" color={C.orange} desc="Every vulnerability is proven exploitable before reporting. Dedicated validation agent reproduces each finding independently. Zero noise, zero false positives." tags={["Exploit verification", "Evidence capture", "Reproducible", "Zero noise"]} />
        <F icon="💰" title="Budget & Cost Control" color={C.yellow} desc="Set per-scan spend limits. Real-time token tracking. Early-stopping when findings plateau. Know the cost of every scan before it finishes." tags={["Budget caps", "Token tracking", "Early stopping", "Cost/finding"]} />
        <F icon="🔐" title="Tiered Permissions" color={C.red} desc="Three-tier approval model: auto-approve recon, prompt once for scanners, always ask for exploitation. Full control over what the agent can do." tags={["Auto-approve", "Prompt once", "Always ask", "Per-tool config"]} />
      </div>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.cyan, letterSpacing: 1.5, marginTop: 8 }}>SCANNING CAPABILITIES</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <F icon="🌐" title="Web App Pentesting" color={C.green} desc="SQL injection, XSS (stored/reflected/DOM), SSRF, IDOR, CSRF, auth bypass, broken access control, API abuse, file upload, and business logic flaws." tags={["OWASP Top 10", "REST/GraphQL", "WebSocket", "Auth flows"]} />
        <F icon="📡" title="Network Reconnaissance" color={C.cyan} desc="Automated attack surface mapping: subdomain enumeration, port scanning, service fingerprinting, tech detection, DNS analysis, certificate transparency, and OSINT." tags={["nmap", "subfinder", "httpx", "amass", "whois"]} />
        <F icon="💻" title="Source Code Review" color={C.purple} desc="Static and dynamic analysis of local codebases or GitHub repos. Hardcoded secrets, vulnerable dependencies, insecure patterns, and config weaknesses." tags={["Semgrep", "TruffleHog", "Git repos", "Dependency audit"]} />
        <F icon="🔓" title="Authentication Testing" color={C.orange} desc="Grey-box with credentials: session management, privilege escalation, JWT manipulation, OAuth bypass, password policy, and multi-step auth flow testing." tags={["JWT", "Session hijack", "Priv escalation", "OAuth"]} />
      </div>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.purple, letterSpacing: 1.5, marginTop: 8 }}>TOOL SUITE</div>
      <div style={{ ...card, padding: 20 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {[
            { cat: "Recon", tools: ["subfinder", "amass", "httpx", "katana", "whois", "dnsutils"], c: C.cyan },
            { cat: "Scanning", tools: ["nmap", "nuclei", "nikto", "ffuf", "gobuster", "zaproxy"], c: C.green },
            { cat: "Exploitation", tools: ["sqlmap", "metasploit", "curl", "custom scripts"], c: C.orange },
            { cat: "Analysis", tools: ["semgrep", "trufflehog", "jwt_tool", "python3", "browser"], c: C.purple },
          ].map((g, gi) => (
            <div key={gi}>
              <div style={{ fontFamily: mono, fontSize: 10, fontWeight: 700, color: g.c, letterSpacing: 1, marginBottom: 8 }}>{g.cat.toUpperCase()}</div>
              {g.tools.map((t, ti) => (
                <div key={ti} style={{ padding: "5px 8px", marginBottom: 4, background: g.c + "10", borderRadius: 4, fontSize: 11, fontFamily: mono, color: g.c }}>{t}</div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.orange, letterSpacing: 1.5, marginTop: 8 }}>REPORTING & OUTPUT</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <F icon="📊" title="Multi-Format Reports" color={C.green} desc="JSON, SARIF, HTML, PDF, Markdown. SARIF integrates with GitHub Security tab. PDF includes exec summary, technical details, and remediation." tags={["JSON", "SARIF", "HTML", "PDF", "Markdown"]} />
        <F icon="🏛️" title="Compliance Mapping" color={C.cyan} desc="Auto-map findings to compliance frameworks. Audit-ready evidence for PCI DSS 4.0, DORA, NIS2, SOC 2, and FedRAMP." tags={["PCI DSS 4.0", "DORA", "NIS2", "SOC 2"]} />
        <F icon="📈" title="CVSS Scoring" color={C.purple} desc="Automatic CVSS v3.1 scoring with attack vector, complexity, privileges, and impact. CWE mapping and severity-ranked remediation priorities." tags={["CVSS v3.1", "CWE mapping", "Severity ranking"]} />
      </div>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.yellow, letterSpacing: 1.5, marginTop: 8 }}>DEVELOPER EXPERIENCE</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <F icon="⚡" title="CI/CD Native" color={C.green} desc="GitHub Actions integration. Scan every PR, block merges on critical vulns. Non-interactive mode with JSON output and non-zero exit codes." tags={["GitHub Actions", "GitLab CI", "PR blocking", "Exit codes"]} />
        <F icon="🔌" title="MCP Protocol" color={C.cyan} desc="Expose tools as MCP server for Claude Code or Codex CLI. Consume external MCP tools like HexStrike's 150+ security wrappers." tags={["MCP server", "MCP client", "Claude Code", "Codex CLI"]} />
        <F icon="🧩" title="Plugin System" color={C.purple} desc="Extend with custom tools via Python @tool decorator. Community plugin registry. Import scanners, reporters, and custom exploit modules." tags={["@tool decorator", "Community plugins", "Custom scanners"]} />
        <F icon="💾" title="Session Persistence" color={C.orange} desc="SQLite storage for sessions, findings, and audit logs. Resume interrupted scans. Compare findings over time. Track remediation." tags={["SQLite", "Resume scans", "History", "Findings diff"]} />
      </div>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.pink, letterSpacing: 1.5, marginTop: 8 }}>COMING SOON</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        {[
          { icon: "🏢", title: "AD / Internal Networks", desc: "BloodHound, CrackMapExec, Impacket — automated Kerberoasting to Golden Ticket chains", c: C.pink },
          { icon: "☁️", title: "Cloud Pentesting", desc: "AWS, GCP, Azure misconfiguration detection using CloudGoat patterns", c: C.blue },
          { icon: "📱", title: "Mobile App Testing", desc: "Frida, MobSF integration for Android and iOS security assessment", c: C.yellow },
        ].map((f, i) => (
          <div key={i} style={{ background: C.surface, border: `1px dashed ${f.c}40`, borderRadius: 12, padding: 16, opacity: 0.8 }}>
            <div style={{ fontSize: 22, marginBottom: 6 }}>{f.icon}</div>
            <div style={{ fontFamily: mono, fontSize: 12, fontWeight: 700, color: f.c, marginBottom: 4 }}>{f.title}</div>
            <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.6 }}>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── CAPABILITIES TAB ─────────────────────────────────────────
function CapabilitiesTab() {
  const vulns = [
    { cat: "Injection", items: ["SQL Injection (Union, Blind, Time-based, Error-based)", "NoSQL Injection (MongoDB, CouchDB)", "Command Injection / OS Injection", "LDAP Injection", "Template Injection (SSTI)"], color: C.red },
    { cat: "Broken Auth & Access", items: ["IDOR (Insecure Direct Object References)", "Broken Access Control (horizontal + vertical)", "Authentication Bypass", "Session Fixation / Hijacking", "JWT Manipulation (alg:none, key confusion)", "OAuth / OpenID misconfigs", "Privilege Escalation"], color: C.orange },
    { cat: "XSS & Client-Side", items: ["Stored XSS", "Reflected XSS", "DOM-based XSS", "CSRF (Cross-Site Request Forgery)", "Clickjacking", "Open Redirects", "CORS Misconfiguration"], color: C.yellow },
    { cat: "Data Exposure", items: ["Sensitive Data in Responses", "Directory / Path Traversal", "Local File Inclusion (LFI)", "Remote File Inclusion (RFI)", "Info Disclosure (stack traces, debug)", "Hardcoded Secrets & API Keys", "Insecure File Upload"], color: C.cyan },
    { cat: "Infrastructure", items: ["Server Misconfigurations", "Missing Security Headers", "TLS/SSL Weaknesses", "Outdated Software (CVE matching)", "Default Credentials", "DNS Zone Transfer", "Open Ports & Unnecessary Services"], color: C.purple },
    { cat: "API-Specific", items: ["Broken Object Level Auth (BOLA)", "Mass Assignment", "Rate Limiting Bypass", "GraphQL Introspection Abuse", "REST Parameter Tampering", "API Key Exposure"], color: C.green },
  ];

  const phases = [
    { num: "01", name: "RECONNAISSANCE", time: "2-5 min", color: C.cyan, icon: "🔍", what: "Maps the entire attack surface autonomously",
      details: ["Subdomain enumeration via subfinder + amass", "Live host detection with httpx", "Port scanning & service fingerprinting via nmap", "Technology stack detection (frameworks, servers, databases)", "Hidden endpoint discovery with katana crawler", "DNS record analysis and zone transfer attempts", "OSINT gathering (WHOIS, certificate transparency logs)"] },
    { num: "02", name: "SCANNING", time: "5-15 min", color: C.green, icon: "📡", what: "Targeted vulnerability scans based on recon intelligence",
      details: ["Template-based scanning with nuclei (9000+ templates)", "Web server audit via nikto", "Directory and file bruteforcing with ffuf + gobuster", "ZAP proxy active scanning for auth sessions", "CVE correlation against detected software versions", "Cross-tool correlation to reduce false positives", "Custom nuclei templates for app-specific checks"] },
    { num: "03", name: "EXPLOITATION", time: "5-30 min", color: C.orange, icon: "💥", what: "Generates and executes proof-of-concept exploits",
      details: ["SQL injection exploitation via sqlmap (all techniques)", "XSS payload crafting via browser automation", "Custom exploit scripts written by AI in real-time", "Auth bypass attempts (JWT, session, OAuth)", "File upload vulnerability exploitation", "SSRF chain construction", "Multi-step exploit chaining for max impact"] },
    { num: "04", name: "VALIDATION", time: "2-5 min", color: C.red, icon: "✅", what: "Independent verification — every finding is real",
      details: ["Separate validation agent reproduces each exploit", "Screenshot and response capture as evidence", "CVSS v3.1 scoring based on actual exploitability", "False positive elimination — only verified vulns reported", "Impact assessment — what data/access was compromised", "Exploit reliability rating (consistent vs. intermittent)"] },
    { num: "05", name: "REPORTING", time: "1-3 min", color: C.purple, icon: "📄", what: "Professional, audit-ready reports with remediation",
      details: ["Executive summary with risk overview", "Technical details with repro steps per vuln", "CVSS scores and CWE classifications", "Prioritized remediation guidance", "Compliance mapping (PCI DSS, DORA, NIS2, SOC 2)", "JSON/SARIF for CI/CD + HTML/PDF for humans", "Evidence attachments (requests, responses, screenshots)"] },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <p style={{ fontSize: 14, color: C.textDim, lineHeight: 1.8, maxWidth: 800 }}>
        <span style={{ fontFamily: mono, color: C.green, fontWeight: 700 }}>0xpwn</span> runs the complete attack chain — from first recon packet to final PDF report — without human intervention. Here's exactly what it does and what it finds.
      </p>

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.green, letterSpacing: 1.5 }}>THE 5-PHASE ATTACK PIPELINE</div>
      {phases.map((p, i) => (
        <div key={i} style={{ ...card, borderLeft: `4px solid ${p.color}` }}>
          <div style={{ padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <span style={{ fontSize: 28 }}>{p.icon}</span>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontFamily: mono, fontSize: 11, color: C.textDim }}>{p.num}</span>
                  <span style={{ fontFamily: mono, fontSize: 16, fontWeight: 800, color: p.color }}>{p.name}</span>
                  {badge(p.color, p.time, true)}
                </div>
                <div style={{ fontSize: 13, color: C.text, marginTop: 2, fontWeight: 600 }}>{p.what}</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginTop: 8 }}>
              {p.details.map((d, j) => (
                <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "4px 0" }}>
                  <span style={{ color: p.color, fontSize: 10, marginTop: 3, flexShrink: 0 }}>▸</span>
                  <span style={{ fontSize: 11, color: C.textDim, lineHeight: 1.5 }}>{d}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}

      <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.red, letterSpacing: 1.5, marginTop: 8 }}>VULNERABILITY COVERAGE — 40+ CLASSES</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        {vulns.map((v, vi) => (
          <div key={vi} style={{ ...card, borderTop: `3px solid ${v.color}`, padding: 16 }}>
            <div style={{ fontFamily: mono, fontSize: 11, fontWeight: 700, color: v.color, marginBottom: 10, letterSpacing: 0.5 }}>{v.cat}</div>
            {v.items.map((item, ii) => (
              <div key={ii} style={{ fontSize: 11, color: C.textDim, lineHeight: 1.4, padding: "3px 0", display: "flex", gap: 6, alignItems: "flex-start" }}>
                <span style={{ color: v.color, fontSize: 8, marginTop: 3 }}>●</span>{item}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div style={{ ...card, padding: 24, borderTop: `3px solid ${C.green}` }}>
        <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: C.green, letterSpacing: 1.5, marginBottom: 16 }}>WHY 0xPWN vs THE REST</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {[
            { vs: "vs Manual Pentesting", pts: ["Hours instead of weeks", "Consistent methodology", "No scheduling delays", "$1 vs $10K+ per engagement", "Available 24/7"], c: C.green },
            { vs: "vs DAST Scanners", pts: ["AI chains multi-step exploits", "Understands app context", "Custom exploits in real-time", "Validates every finding with PoC", "Natural language instructions"], c: C.cyan },
            { vs: "vs Other AI Tools", pts: ["PoC validation = zero false positives", "Budget controls prevent surprises", "Tiered permissions = you're in control", "MCP protocol for ecosystem integration", "Open source — audit and extend"], c: C.purple },
            { vs: "vs Vuln Scanners (Nessus)", pts: ["Active exploitation, not just detection", "Business logic testing", "AI-driven attack chaining", "Context-aware prioritization", "Compliance-mapped reporting"], c: C.orange },
          ].map((v, i) => (
            <div key={i}>
              <div style={{ fontFamily: mono, fontSize: 12, fontWeight: 700, color: v.c, marginBottom: 8 }}>{v.vs}</div>
              {v.pts.map((p, j) => (
                <div key={j} style={{ fontSize: 11, color: C.textDim, lineHeight: 1.3, padding: "3px 0", display: "flex", gap: 6 }}>
                  <span style={{ color: v.c }}>✓</span>{p}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── README TAB ───────────────────────────────────────────────
function ReadmeTab() {
  return (
    <div style={{ ...card }}>
      <div style={{ padding: "10px 16px", background: C.surfaceAlt, borderBottom: `1px solid ${C.border}`, fontFamily: mono, fontSize: 11, color: C.textDim }}>📄 README.md</div>
      <div style={{ padding: "32px 40px" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontFamily: mono, fontSize: 48, fontWeight: 800 }}><span style={{ color: C.green }}>0x</span><span style={{ color: C.text }}>pwn</span></div>
          <div style={{ fontSize: 16, color: C.textDim, marginBottom: 16 }}>The AI that pwns so you don't have to.</div>
          <div style={{ display: "flex", justifyContent: "center", gap: 6 }}>
            {[{ l: "license", r: "Apache 2.0", rc: "#00ff87" }, { l: "python", r: "3.12+", rc: "#3776ab" }, { l: "pypi", r: "v0.1.0", rc: "#00e5ff" }, { l: "docker", r: "ready", rc: "#2496ed" }].map((b, i) => (
              <span key={i} style={{ display: "inline-flex", borderRadius: 4, overflow: "hidden", fontSize: 10, fontFamily: mono, fontWeight: 600 }}>
                <span style={{ background: "#555", color: "#fff", padding: "3px 6px" }}>{b.l}</span>
                <span style={{ background: b.rc, color: "#000", padding: "3px 6px" }}>{b.r}</span>
              </span>
            ))}
          </div>
        </div>
        <div style={{ fontSize: 14, color: C.text, lineHeight: 1.8, maxWidth: 640, margin: "0 auto", textAlign: "center" }}>
          <strong>0xpwn</strong> is an autonomous AI pentesting agent that uses LLMs to orchestrate real security tools inside Docker sandboxes. It finds real vulnerabilities, validates them with proof-of-concept exploits, and generates actionable reports.
        </div>
        <div style={{ marginTop: 28, background: C.surfaceAlt, borderRadius: 8, padding: 20, maxWidth: 500, margin: "28px auto 0" }}>
          <pre style={{ margin: 0, fontFamily: mono, fontSize: 12, color: C.text, lineHeight: 2 }}>{`pip install 0xpwn
export LLM_API_KEY="your-key"
0xpwn scan --target https://your-app.com`}</pre>
        </div>
        <div style={{ marginTop: 28, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, maxWidth: 640, margin: "28px auto 0" }}>
          {[
            { i: "🤖", t: "Multi-Model", d: "OpenAI, Anthropic, Ollama via LiteLLM" },
            { i: "🐳", t: "Sandboxed", d: "Isolated Kali Docker containers" },
            { i: "🎯", t: "Zero FPs", d: "Every finding validated with PoC" },
            { i: "💰", t: "Budget Control", d: "Set cost caps per scan" },
            { i: "📊", t: "Compliance", d: "PCI DSS, DORA, NIS2, SOC 2" },
            { i: "🔌", t: "MCP Protocol", d: "Claude Code + Codex integration" },
          ].map((f, i) => (
            <div key={i} style={{ textAlign: "center", padding: 12 }}>
              <div style={{ fontSize: 24, marginBottom: 6 }}>{f.i}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.text }}>{f.t}</div>
              <div style={{ fontSize: 10, color: C.textDim, marginTop: 4, lineHeight: 1.5 }}>{f.d}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── INSTALL TAB ──────────────────────────────────────────────
function InstallTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {[
          { t: "pip", cmd: "pip install 0xpwn", n: "Python 3.12+ and Docker", c: C.green },
          { t: "pipx", cmd: "pipx install 0xpwn", n: "Isolated environment", c: C.cyan },
          { t: "Docker", cmd: `docker run -v /var/run/docker.sock:/var/run/docker.sock \\\n  ghcr.io/0xpwn/0xpwn scan --target <url>`, n: "No Python needed", c: C.purple },
          { t: "Source", cmd: `git clone https://github.com/0xpwn/0xpwn\ncd 0xpwn && pip install -e ".[dev]"`, n: "For contributing", c: C.orange },
        ].map((m, i) => (
          <div key={i} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, borderTop: `3px solid ${m.c}`, padding: 20 }}>
            <div style={{ fontFamily: mono, fontSize: 13, fontWeight: 700, color: m.c, marginBottom: 12 }}>{m.t}</div>
            <pre style={{ margin: 0, fontFamily: mono, fontSize: 11.5, color: C.text, lineHeight: 1.8, background: C.surfaceAlt, padding: 12, borderRadius: 6 }}>{m.cmd}</pre>
            <div style={{ fontSize: 10, color: C.textDim, marginTop: 8 }}>{m.n}</div>
          </div>
        ))}
      </div>
      <div style={{ ...card }}>
        <div style={{ padding: "10px 16px", background: C.surfaceAlt, borderBottom: `1px solid ${C.border}`, fontFamily: mono, fontSize: 11, color: C.textDim }}>~/.0xpwn/config.yaml</div>
        <pre style={{ padding: 20, margin: 0, fontFamily: mono, fontSize: 12, lineHeight: 1.8, color: C.textDim }}>
          <span style={{ color: C.cyan }}>model</span><span style={{ color: C.text }}>:</span> openai/codex-5.3{"\n"}
          <span style={{ color: C.cyan }}>api_key</span><span style={{ color: C.text }}>:</span> sk-...{"\n\n"}
          <span style={{ color: C.cyan }}>permissions</span><span style={{ color: C.text }}>:</span>{"\n"}
          {"  "}<span style={{ color: C.green }}>auto_approve</span>: [nmap, subfinder, httpx, whois]{"\n"}
          {"  "}<span style={{ color: C.yellow }}>prompt_once</span>:  [nuclei, nikto, ffuf, gobuster]{"\n"}
          {"  "}<span style={{ color: C.red }}>always_ask</span>:   [sqlmap, metasploit, exploits]{"\n\n"}
          <span style={{ color: C.cyan }}>budget</span><span style={{ color: C.text }}>:</span>{"\n"}
          {"  "}max_cost: 10.00{"\n"}
          {"  "}max_iterations: 100{"\n\n"}
          <span style={{ color: C.cyan }}>reporting</span><span style={{ color: C.text }}>:</span>{"\n"}
          {"  "}format: [json, sarif, pdf]{"\n"}
          {"  "}compliance: [pci-dss-4.0]{"\n"}
          {"  "}output_dir: ./0xpwn_reports{"\n"}
        </pre>
      </div>
    </div>
  );
}

// ── MAIN ─────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState(2);
  const tabs = [BrandTab, CLITab, FeaturesTab, CapabilitiesTab, ReadmeTab, InstallTab];
  const T = tabs[tab];
  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "'Segoe UI', -apple-system, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet" />
      <div style={{ padding: "20px 28px 0", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 3, marginBottom: 4 }}>
          <span style={{ fontFamily: mono, fontSize: 22, fontWeight: 800, color: C.green }}>0x</span>
          <span style={{ fontFamily: mono, fontSize: 22, fontWeight: 800, color: C.text }}>pwn</span>
          <span style={{ fontFamily: mono, fontSize: 11, color: C.textDim, marginLeft: 12, fontWeight: 600 }}>BRAND + PRODUCT KIT</span>
        </div>
        <div style={{ display: "flex", gap: 0, marginTop: 12 }}>
          {SECTIONS.map((s, i) => (
            <button key={i} onClick={() => setTab(i)} style={{
              padding: "10px 16px", border: "none", cursor: "pointer",
              background: tab === i ? C.surface : "transparent",
              borderTop: tab === i ? `2px solid ${C.green}` : "2px solid transparent",
              color: tab === i ? C.green : C.textDim,
              fontSize: 11, fontWeight: tab === i ? 700 : 500, fontFamily: mono,
              borderRadius: "6px 6px 0 0", marginBottom: -1, borderBottom: "none",
            }}>{s}</button>
          ))}
        </div>
      </div>
      <div style={{ padding: "24px 28px 48px", maxWidth: 980 }}><T /></div>
    </div>
  );
}
