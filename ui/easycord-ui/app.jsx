/* global React, ReactDOM, DeployForm, BotDashboard, Icon */
const { useState, useEffect } = React;

function App() {
  const [config, setConfig] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === "dark" ? "light" : "dark");

  const handleStop = async () => {
    if (window.pywebview?.api) {
      await window.pywebview.api.stop_bot();
    }
    setConfig(null);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark v-block">E</div>
          <span>EasyCord</span>
          <span className="brand-version">v6.0.0</span>
        </div>

        <div className="topbar-spacer" />

        <div className="row gap-12">
          <button className="icon-btn" onClick={toggleTheme} title="Toggle theme">
            {theme === "dark" ? <Icon.Sparkles /> : <Icon.Activity />}
          </button>
          <div className="workspace-pill">
            <div className="avatar">CC</div>
            <span>Command Center</span>
          </div>
        </div>
      </header>

      <main className="content">
        {!config ? (
          <DeployForm onStart={setConfig} />
        ) : (
          <BotDashboard config={config} onStop={handleStop} />
        )}
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
