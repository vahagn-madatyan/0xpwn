import { useState } from "react";

const C = {
  bg: "#0a0e17", surface: "#111827", surfaceAlt: "#0d1424",
  border: "#1e293b", text: "#e2e8f0", textDim: "#64748b",
  green: "#22c55e", red: "#ef4444", yellow: "#facc15",
  cyan: "#22d3ee", purple: "#a78bfa", orange: "#fb923c",
  accent: "#00e5a0", blue: "#60a5fa", pink: "#f472b6",
};

const TABS = ["Gap Analysis", "Priority Build", "Effort Matrix"];

const badge = (color, text) => (
  <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 99, fontSize: 10, fontWeight: 600, background: color + "18", color, letterSpacing: 0.3, fontFamily: "'JetBrains Mono', monospace" }}>{text}</span>
);

// Full feature inventory with Strix status
const FEATURES = [
  {
    category: "CORE AGENT ENGINE",
    items: [
      { feature: "ReAct / agent loop", strix: "full", note: "Multi-agent coordination graph with agent_loop()" },
      { feature: "LiteLLM multi-provider", strix: "full", note: "Supports OpenAI, Anthropic, Ollama, custom endpoints" },
      { feature: "Docker sandbox (Kali)", strix: "full", note: "DockerRuntime with NET_ADMIN/NET_RAW, health checks" },
      { feature: "Multi-target scanning", strix: "full", note: "Multiple -t flags, source + deployed app combos" },
      { feature: "Scan modes (quick/deep)", strix: "full", note: "STRIX_REASONING_EFFORT + --scan-mode flag" },
      { feature: "Thinking block chaining", strix: "full", note: "v0.6.0 preserves reasoning across steps" },
      { feature: "Sub-agent spawning", strix: "full", note: "Root agent → specialized sub-agents with 1-5 skills" },
      { feature: "Stuck detection", strix: "full", note: "Todo tool + dedup prevents looping" },
      { feature: "Tiered permission model", strix: "none", note: "No auto-approve/prompt/block tiers — agent runs freely", gap: true, effort: "M", priority: "high" },
      { feature: "Validation agent (PoC verify)", strix: "none", note: "No separate verification step — single agent validates inline", gap: true, effort: "L", priority: "high" },
      { feature: "Multi-model orchestration", strix: "none", note: "Single model per run — can't use Claude for analysis + GPT for planning", gap: true, effort: "M", priority: "medium" },
      { feature: "Cost tracking / budget caps", strix: "none", note: "No token counting, no spend limits, no early-stopping thresholds", gap: true, effort: "S", priority: "high" },
    ]
  },
  {
    category: "CLI & USER INTERFACE",
    items: [
      { feature: "Textual TUI (interactive)", strix: "full", note: "Split-pane with agent activity, findings, tool output" },
      { feature: "Non-interactive CLI mode", strix: "full", note: "-n flag with streaming output, non-zero exit on vulns" },
      { feature: "Standalone binary", strix: "full", note: "v0.5.0 added binary distribution alongside pipx" },
      { feature: "Config persistence", strix: "full", note: "~/.strix/cli-config.json auto-saved" },
      { feature: "Instruction files (scope/ROE)", strix: "full", note: "--instruction-file flag for rules of engagement" },
      { feature: "REST API server", strix: "none", note: "No HTTP API — CLI/TUI only, can't integrate programmatically", gap: true, effort: "L", priority: "medium" },
      { feature: "WebSocket real-time events", strix: "none", note: "No streaming API for external consumers or web UI", gap: true, effort: "L", priority: "low" },
      { feature: "Web GUI", strix: "partial", note: "app.strix.ai exists (closed-source) — we'd need our own", gap: true, effort: "XL", priority: "low" },
    ]
  },
  {
    category: "PERSISTENCE & STATE",
    items: [
      { feature: "Session results storage", strix: "partial", note: "File-based in strix_runs/<name> — no database", gap: true, effort: "M", priority: "high" },
      { feature: "Session resume", strix: "none", note: "PR #219 open but not merged — scans can't resume after interrupt", gap: true, effort: "M", priority: "high" },
      { feature: "SQLite local database", strix: "none", note: "No structured persistence — findings only in file output", gap: true, effort: "M", priority: "high" },
      { feature: "PostgreSQL cloud tier", strix: "none", note: "No cloud database support", gap: true, effort: "L", priority: "medium" },
      { feature: "Knowledge graph (Neo4j)", strix: "none", note: "No cross-engagement learning or semantic memory", gap: true, effort: "XL", priority: "low" },
      { feature: "Event-sourced audit log", strix: "none", note: "No immutable action log — traces exist but aren't structured for audit", gap: true, effort: "M", priority: "medium" },
    ]
  },
  {
    category: "REPORTING & COMPLIANCE",
    items: [
      { feature: "Text/Markdown findings", strix: "full", note: "Structured findings with description, impact, evidence, remediation" },
      { feature: "LLM-based deduplication", strix: "full", note: "v0.6.0 added finding dedup to reduce noise" },
      { feature: "JSON output", strix: "partial", note: "Findings saved but no standardized JSON schema", gap: true, effort: "S", priority: "high" },
      { feature: "SARIF output (CI/CD)", strix: "none", note: "No SARIF — GitHub Security tab integration missing", gap: true, effort: "S", priority: "high" },
      { feature: "HTML report", strix: "none", note: "No formatted HTML report generation", gap: true, effort: "M", priority: "medium" },
      { feature: "PDF executive report", strix: "none", note: "No PDF — can't hand to auditors or management", gap: true, effort: "M", priority: "medium" },
      { feature: "CVSS scoring", strix: "partial", note: "Severity levels exist but no formal CVSS calculation" },
      { feature: "PCI DSS 4.0 mapping", strix: "none", note: "No compliance framework mapping whatsoever", gap: true, effort: "L", priority: "medium" },
      { feature: "DORA / NIS2 / SOC 2 templates", strix: "none", note: "No regulatory reporting templates", gap: true, effort: "L", priority: "low" },
    ]
  },
  {
    category: "PENTESTING DOMAINS",
    items: [
      { feature: "Web app (XSS, SQLi, SSRF, IDOR)", strix: "full", note: "Core strength — browser automation, HTTP proxy, sqlmap, etc." },
      { feature: "Source code review", strix: "full", note: "Semgrep, TruffleHog, static analysis in sandbox" },
      { feature: "API testing", strix: "full", note: "REST/GraphQL via ffuf, custom scripts, proxy" },
      { feature: "Authenticated / grey-box", strix: "full", note: "--instruction flag with credentials" },
      { feature: "Network recon (nmap, subfinder)", strix: "full", note: "Full tool suite in Kali sandbox" },
      { feature: "Post-exploitation modules", strix: "none", note: "No linpeas, bloodhound, mimikatz, lateral movement", gap: true, effort: "XL", priority: "medium" },
      { feature: "AD / internal network", strix: "none", note: "No Active Directory attack chains — zero tooling", gap: true, effort: "XL", priority: "medium" },
      { feature: "Cloud infra (AWS/GCP/Azure)", strix: "none", note: "No cloud misconfiguration testing", gap: true, effort: "XL", priority: "medium" },
      { feature: "Mobile app testing", strix: "none", note: "No Frida, MobSF, or mobile-specific tooling", gap: true, effort: "XL", priority: "low" },
    ]
  },
  {
    category: "EXTENSIBILITY & INTEGRATION",
    items: [
      { feature: "GitHub Actions CI/CD", strix: "full", note: "Native workflow YAML provided" },
      { feature: "Perplexity search integration", strix: "full", note: "Web search for CVE/vuln research during scans" },
      { feature: "MCP server (tool bridge)", strix: "none", note: "Can't expose tools to Claude Code, Codex CLI, or other agents", gap: true, effort: "L", priority: "high" },
      { feature: "MCP client (consume tools)", strix: "none", note: "Can't consume HexStrike's 150+ tools or pentestMCP", gap: true, effort: "L", priority: "high" },
      { feature: "Plugin / module system", strix: "none", note: "No user-extensible tool or module registration", gap: true, effort: "L", priority: "medium" },
      { feature: "HackTheBox API", strix: "none", note: "No programmatic CTF integration for testing/validation", gap: true, effort: "M", priority: "low" },
    ]
  },
  {
    category: "CLOUD & ENTERPRISE",
    items: [
      { feature: "Cloud-hosted sessions", strix: "partial", note: "app.strix.ai exists but is closed-source — need our own", gap: true, effort: "XL", priority: "low" },
      { feature: "Temporal workflow orchestration", strix: "none", note: "No durable execution or workflow management", gap: true, effort: "XL", priority: "low" },
      { feature: "Team RBAC", strix: "none", note: "Single-user only", gap: true, effort: "L", priority: "low" },
      { feature: "SSO (SAML/OIDC)", strix: "none", note: "No enterprise auth", gap: true, effort: "L", priority: "low" },
      { feature: "Scope enforcement", strix: "partial", note: "Instruction files but no hard IP/domain blocking", gap: true, effort: "M", priority: "high" },
      { feature: "Freemium feature gating", strix: "none", note: "No license keys, feature flags, or tier enforcement", gap: true, effort: "M", priority: "medium" },
    ]
  },
];

const allItems = FEATURES.flatMap(c => c.items);
const gapItems = allItems.filter(i => i.gap);
const fullItems = allItems.filter(i => i.strix === "full");
const partialItems = allItems.filter(i => i.strix === "partial" && !i.gap);

function GapTab() {
  const [filter, setFilter] = useState("all");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Summary Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[
          { label: "Strix Has", count: fullItems.length, total: allItems.length, color: C.green, pct: Math.round(fullItems.length / allItems.length * 100) },
          { label: "Partial", count: partialItems.length + allItems.filter(i => i.strix === "partial" && i.gap).length, total: allItems.length, color: C.yellow, pct: Math.round((partialItems.length + allItems.filter(i => i.strix === "partial" && i.gap).length) / allItems.length * 100) },
          { label: "We Must Build", count: gapItems.length, total: allItems.length, color: C.red, pct: Math.round(gapItems.length / allItems.length * 100) },
          { label: "High Priority Gaps", count: gapItems.filter(i => i.priority === "high").length, total: gapItems.length, color: C.orange, pct: Math.round(gapItems.filter(i => i.priority === "high").length / gapItems.length * 100) },
        ].map((s, i) => (
          <div key={i} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16, textAlign: "center" }}>
            <div style={{ fontSize: 32, fontWeight: 800, color: s.color, fontFamily: "'JetBrains Mono', monospace" }}>{s.count}</div>
            <div style={{ fontSize: 11, color: C.textDim, marginTop: 2 }}>{s.label}</div>
            <div style={{ marginTop: 8, height: 4, background: C.border, borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${s.pct}%`, background: s.color, borderRadius: 2 }} />
            </div>
            <div style={{ fontSize: 10, color: s.color, marginTop: 4 }}>{s.pct}% of {s.total} features</div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div style={{ display: "flex", gap: 8 }}>
        {[["all", "All Features"], ["gaps", "Gaps Only"], ["high", "High Priority"], ["has", "Strix Has"]].map(([id, label]) => (
          <button key={id} onClick={() => setFilter(id)} style={{
            padding: "6px 14px", borderRadius: 6, border: `1px solid ${filter === id ? C.accent : C.border}`,
            background: filter === id ? C.accent + "15" : C.surface, color: filter === id ? C.accent : C.textDim,
            fontSize: 11, fontFamily: "'JetBrains Mono', monospace", cursor: "pointer", fontWeight: 600,
          }}>{label}</button>
        ))}
      </div>

      {/* Feature Matrix */}
      {FEATURES.map((cat, ci) => {
        const filtered = cat.items.filter(item => {
          if (filter === "gaps") return item.gap;
          if (filter === "high") return item.gap && item.priority === "high";
          if (filter === "has") return item.strix === "full";
          return true;
        });
        if (filtered.length === 0) return null;
        return (
          <div key={ci} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
            <div style={{ padding: "10px 16px", background: C.surfaceAlt, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: C.cyan, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>{cat.category}</span>
              <span style={{ fontSize: 10, color: C.textDim }}>
                {cat.items.filter(i => i.strix === "full").length}/{cat.items.length} covered
              </span>
            </div>
            {filtered.map((item, ii) => (
              <div key={ii} style={{
                display: "grid", gridTemplateColumns: "28px 1fr auto",
                alignItems: "start", gap: 10, padding: "10px 16px",
                borderBottom: `1px solid ${C.border}10`,
                background: item.gap ? C.red + "04" : "transparent",
              }}>
                <div style={{ paddingTop: 2 }}>
                  {item.strix === "full" ? "✅" : item.strix === "partial" ? "🟡" : "❌"}
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: item.gap ? C.text : C.textDim }}>{item.feature}</div>
                  <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.5, marginTop: 2 }}>{item.note}</div>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0, paddingTop: 2 }}>
                  {item.gap && badge(
                    item.priority === "high" ? C.red : item.priority === "medium" ? C.yellow : C.textDim,
                    item.priority?.toUpperCase()
                  )}
                  {item.effort && badge(
                    item.effort === "S" ? C.green : item.effort === "M" ? C.yellow : item.effort === "L" ? C.orange : C.red,
                    item.effort
                  )}
                </div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function PriorityTab() {
  const phases = [
    {
      phase: "PHASE 1 — Fork + Differentiate", time: "Weeks 1–3", color: C.accent,
      desc: "Fork Strix, add the features that immediately differentiate us from vanilla Strix and make it monetizable.",
      items: gapItems.filter(i => i.priority === "high").map(i => ({
        ...i, source: FEATURES.find(c => c.items.includes(i))?.category
      })),
    },
    {
      phase: "PHASE 2 — Monetization Layer", time: "Weeks 4–8", color: C.cyan,
      desc: "Build the reporting, compliance, and persistence features that justify a paid tier.",
      items: gapItems.filter(i => i.priority === "medium").map(i => ({
        ...i, source: FEATURES.find(c => c.items.includes(i))?.category
      })),
    },
    {
      phase: "PHASE 3 — Platform & Domains", time: "Weeks 9–16", color: C.purple,
      desc: "Expand into new pentesting domains and build the cloud/enterprise tier.",
      items: gapItems.filter(i => i.priority === "low").map(i => ({
        ...i, source: FEATURES.find(c => c.items.includes(i))?.category
      })),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: C.accent, fontFamily: "'JetBrains Mono', monospace", marginBottom: 8 }}>THE CORE THESIS</div>
        <p style={{ fontSize: 13, color: C.text, lineHeight: 1.8, margin: 0 }}>
          Strix covers <strong style={{ color: C.green }}>{fullItems.length} of {allItems.length} features</strong> we planned — that's {Math.round(fullItems.length / allItems.length * 100)}% of the architecture for free.
          The <strong style={{ color: C.red }}>{gapItems.length} gaps</strong> cluster in four areas that Strix deliberately punts on:
          <strong style={{ color: C.orange }}> persistence</strong> (no database, no resume),
          <strong style={{ color: C.yellow }}> reporting</strong> (no SARIF/PDF/compliance),
          <strong style={{ color: C.cyan }}> extensibility</strong> (no MCP, no plugins), and
          <strong style={{ color: C.purple }}> enterprise</strong> (no teams, no cloud hosting).
          These are exactly the features that make a freemium model work — Strix gives away the hard part (agent + sandbox), we build the monetizable wrapper.
        </p>
      </div>

      {phases.map((p, pi) => (
        <div key={pi} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, borderTop: `3px solid ${p.color}`, overflow: "hidden" }}>
          <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.border}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 15, fontWeight: 800, color: p.color, fontFamily: "'JetBrains Mono', monospace" }}>{p.phase}</span>
              <div style={{ display: "flex", gap: 8 }}>
                {badge(p.color, p.time)}
                {badge(p.color, `${p.items.length} features`)}
              </div>
            </div>
            <div style={{ fontSize: 12, color: C.textDim, marginTop: 6, lineHeight: 1.6 }}>{p.desc}</div>
          </div>
          <div style={{ padding: "4px 0" }}>
            {p.items.map((item, ii) => (
              <div key={ii} style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 12, padding: "10px 20px", borderBottom: `1px solid ${C.border}08`, alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: C.text }}>{item.feature}</span>
                  <span style={{ fontSize: 10, color: C.textDim, marginLeft: 8 }}>{item.source}</span>
                </div>
                {badge(
                  item.effort === "S" ? C.green : item.effort === "M" ? C.yellow : item.effort === "L" ? C.orange : C.red,
                  { S: "~2-3 days", M: "~1 week", L: "~2 weeks", XL: "~3-4 weeks" }[item.effort]
                )}
                {badge(
                  item.effort === "S" ? C.green : item.effort === "M" ? C.yellow : item.effort === "L" ? C.orange : C.red,
                  item.effort
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function EffortTab() {
  const effortGroups = { S: [], M: [], L: [], XL: [] };
  gapItems.forEach(i => { if (i.effort && effortGroups[i.effort]) effortGroups[i.effort].push(i); });

  const effortMeta = {
    S: { label: "Small (2-3 days)", color: C.green, desc: "Config changes, simple integrations, format adapters" },
    M: { label: "Medium (~1 week)", color: C.yellow, desc: "New modules with moderate complexity, database work" },
    L: { label: "Large (~2 weeks)", color: C.orange, desc: "New subsystems, protocol implementations, significant new features" },
    XL: { label: "Extra Large (3-4+ weeks)", color: C.red, desc: "New pentesting domains, cloud infrastructure, enterprise platform" },
  };

  const totalWeeks = Object.entries(effortGroups).reduce((sum, [size, items]) => {
    const weeks = { S: 0.4, M: 1, L: 2, XL: 3.5 };
    return sum + items.length * weeks[size];
  }, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {Object.entries(effortMeta).map(([size, meta]) => (
          <div key={size} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16, borderTop: `3px solid ${meta.color}` }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: meta.color, fontFamily: "'JetBrains Mono', monospace" }}>{effortGroups[size].length}</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: meta.color, marginTop: 2 }}>{meta.label}</div>
            <div style={{ fontSize: 10, color: C.textDim, marginTop: 4, lineHeight: 1.5 }}>{meta.desc}</div>
          </div>
        ))}
      </div>

      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20, textAlign: "center" }}>
        <div style={{ fontSize: 11, color: C.textDim, fontFamily: "'JetBrains Mono', monospace", marginBottom: 4 }}>TOTAL ESTIMATED BUILD EFFORT (ALL GAPS)</div>
        <div style={{ fontSize: 36, fontWeight: 800, color: C.accent, fontFamily: "'JetBrains Mono', monospace" }}>{Math.round(totalWeeks)} dev-weeks</div>
        <div style={{ fontSize: 12, color: C.textDim, marginTop: 4 }}>
          vs. ~20 weeks building from scratch — Strix saves ~{Math.round((20 - totalWeeks) / 20 * 100)}% of total effort
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: 20, marginTop: 16 }}>
          {[
            { label: "Phase 1 (High Priority)", weeks: gapItems.filter(i => i.priority === "high").reduce((s, i) => s + ({ S: 0.4, M: 1, L: 2, XL: 3.5 }[i.effort] || 0), 0), color: C.accent },
            { label: "Phase 2 (Medium)", weeks: gapItems.filter(i => i.priority === "medium").reduce((s, i) => s + ({ S: 0.4, M: 1, L: 2, XL: 3.5 }[i.effort] || 0), 0), color: C.cyan },
            { label: "Phase 3 (Low)", weeks: gapItems.filter(i => i.priority === "low").reduce((s, i) => s + ({ S: 0.4, M: 1, L: 2, XL: 3.5 }[i.effort] || 0), 0), color: C.purple },
          ].map((p, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: p.color, fontFamily: "'JetBrains Mono', monospace" }}>{Math.round(p.weeks)}w</div>
              <div style={{ fontSize: 10, color: C.textDim }}>{p.label}</div>
            </div>
          ))}
        </div>
      </div>

      {Object.entries(effortGroups).map(([size, items]) => (
        items.length > 0 && (
          <div key={size} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
            <div style={{ padding: "10px 16px", background: C.surfaceAlt, display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: effortMeta[size].color, fontFamily: "'JetBrains Mono', monospace" }}>{size} — {effortMeta[size].label}</span>
              <span style={{ fontSize: 10, color: C.textDim }}>{items.length} items</span>
            </div>
            {items.sort((a, b) => {
              const p = { high: 0, medium: 1, low: 2 };
              return (p[a.priority] || 2) - (p[b.priority] || 2);
            }).map((item, ii) => (
              <div key={ii} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 16px", borderBottom: `1px solid ${C.border}08` }}>
                <span style={{ fontSize: 12, color: C.text }}>{item.feature}</span>
                {badge(
                  item.priority === "high" ? C.red : item.priority === "medium" ? C.yellow : C.textDim,
                  item.priority?.toUpperCase()
                )}
              </div>
            ))}
          </div>
        )
      ))}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState(0);

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "'Segoe UI', -apple-system, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet" />

      <div style={{ padding: "24px 28px 0", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 18, fontWeight: 800 }}>Strix Fork Gap Analysis</span>
          {badge(C.accent, "usestrix/strix v0.8.2")}
          {badge(C.cyan, "Apache 2.0")}
          {badge(C.yellow, "20.5k ★")}
        </div>
        <p style={{ fontSize: 12, color: C.textDim, margin: "4px 0 14px" }}>
          What Strix already covers vs. what we need to build on top
        </p>
        <div style={{ display: "flex", gap: 0 }}>
          {TABS.map((t, i) => (
            <button key={i} onClick={() => setTab(i)} style={{
              padding: "10px 20px", border: "none", cursor: "pointer",
              background: tab === i ? C.surface : "transparent",
              borderTop: tab === i ? `2px solid ${C.accent}` : "2px solid transparent",
              borderBottom: tab === i ? `1px solid ${C.surface}` : "none",
              color: tab === i ? C.accent : C.textDim,
              fontSize: 12, fontWeight: tab === i ? 700 : 500,
              fontFamily: "'JetBrains Mono', monospace",
              borderRadius: "6px 6px 0 0", marginBottom: -1,
            }}>{t}</button>
          ))}
        </div>
      </div>

      <div style={{ padding: "20px 28px 48px", maxWidth: 960 }}>
        {tab === 0 && <GapTab />}
        {tab === 1 && <PriorityTab />}
        {tab === 2 && <EffortTab />}
      </div>
    </div>
  );
}
