/* global React, Icon, Sparkline, useInterval */
const { useState, useEffect, useRef } = React;

// ─── Bot Dashboard ──────────────────────────────────────
function BotDashboard({ config, onStop }) {
  const [stats, setStats] = useState({ status: "offline", uptime: 0, latency: 0, guilds: 0, memory: 0 });
  const [logs, setLogs] = useState([]);
  const [latencyHistory, setLatency] = useState(new Array(20).fill(0));
  const [memHistory, setMemory] = useState(new Array(20).fill(0));

  useInterval(async () => {
    if (window.pywebview?.api) {
      const data = await window.pywebview.api.get_status();
      setStats(data);
      setLatency(h => [...h.slice(1), data.latency]);
      setMemory(h => [...h.slice(1), data.memory || 0]);

      const newLogs = await window.pywebview.api.get_logs();
      setLogs(newLogs);
    }
  }, 2000);

  const fmtUptime = (s) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m ${Math.floor(s % 60)}s`;
  };

  return (
    <div className="col gap-24">
      <div className="spread">
        <div className="col gap-8">
          <h1 className="h1">Command Center</h1>
          <div className="badge ok">
            <div className="pulse" /> {stats.status.toUpperCase()}
          </div>
        </div>
        <button className="btn btn-sm" onClick={onStop}>
          <Icon.Stop /> Stop Bot
        </button>
      </div>

      {stats.status === "stopping" && (
        <div className="badge warn" style={{ width: "100%", justifyContent: "center", padding: 8 }}>
          Shutting down...
        </div>
      )}

      <div className="stat-row">
        <div className="stat">
          <div className="label">API Latency</div>
          <div className="value">{Math.round(stats.latency)}ms</div>
          <Sparkline data={latencyHistory} color="var(--accent)" />
        </div>
        <div className="stat">
          <div className="label">Memory</div>
          <div className="value">{stats.memory?.toFixed(1) || 0}MB</div>
          <Sparkline data={memHistory} color="var(--ok)" />
        </div>
        <div className="stat">
          <div className="label">Uptime</div>
          <div className="value" style={{ fontSize: 18 }}>{fmtUptime(stats.uptime)}</div>
        </div>
        <div className="stat">
          <div className="label">Guilds</div>
          <div className="value">{stats.guilds}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <Icon.Logs />
          <h3>System Logs</h3>
        </div>
        <div className="card-pad">
          <div className="logs">
            {logs.length === 0 && <div className="subtle">Waiting for logs...</div>}
            {logs.map((l, i) => (
              <div key={i} className="log-line">
                <span className="log-time">{l.time}</span>
                <span className={`log-level ${l.level}`}>{l.level}</span>
                <span className="log-msg">{l.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Deploy Form (Command Center Entry) ───────────────────
function DeployForm({ onStart }) {
  const [token, setToken] = useState("");
  const [guildId, setGuildId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStart = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    if (window.pywebview?.api) {
      const resp = await window.pywebview.api.start_bot(token, guildId);
      if (resp.error) {
        setError(resp.error);
        setLoading(false);
      } else {
        onStart({ token, guildId });
      }
    } else {
      // Mock for browser dev
      setTimeout(() => onStart({ token, guildId }), 1500);
    }
  };

  return (
    <div className="wizard-panel" style={{ maxWidth: 600, margin: "40px auto" }}>
      <div className="col gap-24">
        <div className="col gap-8">
          <h2 className="h2">Initialize Bot</h2>
          <p className="muted">Enter your Discord credentials to launch the Command Center.</p>
        </div>

        {error && (
          <div className="badge err" style={{ width: "100%", justifyContent: "center", padding: 10 }}>
            {error}
          </div>
        )}

        <div className="field">
          <label className="field-label">Bot Token</label>
          <input
            type="password"
            className="input mono"
            placeholder="MTE..."
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <p className="field-hint">Never share your token with anyone.</p>
        </div>

        <div className="field">
          <label className="field-label">Development Guild ID (Optional)</label>
          <input
            type="text"
            className="input mono"
            placeholder="123456789..."
            value={guildId}
            onChange={(e) => setGuildId(e.target.value)}
          />
        </div>

        <button 
          className="btn btn-accent btn-lg" 
          onClick={handleStart}
          disabled={!token || loading}
        >
          {loading ? "Starting..." : "Launch Command Center"}
        </button>
      </div>
    </div>
  );
}

Object.assign(window, { DeployForm, BotDashboard });
