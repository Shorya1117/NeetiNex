import "./App.css";

function App() {
  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-icon">N</div>

          <div>
            <h2>NeetiNex</h2>
            <span>Government Scheme Assistant</span>
          </div>
        </div>

        <nav className="navigation">
          <button className="nav-item active">
            <span>⌂</span>
            Dashboard
          </button>

          <button className="nav-item">
            <span>⌕</span>
            Find Schemes
          </button>

          <button className="nav-item">
            <span>◉</span>
            Eligibility Check
          </button>

          <button className="nav-item">
            <span>▣</span>
            My Documents
          </button>

          <button className="nav-item">
            <span>◉</span>
            Voice Assistant
          </button>
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <span>⚙</span>
            Settings
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <main className="main-content">
        {/* Header */}
        <header className="header">
          <div>
            <h1>Government Scheme Assistant</h1>
            <p>Find the right government schemes for your needs.</p>
          </div>

          <div className="profile">
            <div className="language">EN</div>
            <div className="avatar">S</div>
          </div>
        </header>

        {/* Welcome */}
        <section className="welcome-card">
          <div>
            <span className="badge">AI Powered</span>

            <h2>How can NeetiNex help you today?</h2>

            <p>
              Describe your requirement in simple language and discover
              relevant Central and Rajasthan Government schemes.
            </p>
          </div>

          <div className="welcome-icon">🏛️</div>
        </section>

        {/* Quick Actions */}
        <section>
          <h2 className="section-title">Explore Services</h2>

          <div className="cards">
            <div className="service-card">
              <div className="card-icon">🔎</div>
              <h3>Find Schemes</h3>
              <p>
                Tell us what support you need and discover relevant schemes.
              </p>
              <button>Explore →</button>
            </div>

            <div className="service-card">
              <div className="card-icon">✓</div>
              <h3>Check Eligibility</h3>
              <p>
                Check whether you may be eligible based on official criteria.
              </p>
              <button>Check →</button>
            </div>

            <div className="service-card">
              <div className="card-icon">📄</div>
              <h3>Understand Document</h3>
              <p>
                Upload an official scheme document and ask questions about it.
              </p>
              <button>Upload →</button>
            </div>
          </div>
        </section>

        {/* Chat Section */}
        <section className="chat-section">
          <div className="chat-header">
            <div>
              <h2>Ask NeetiNex</h2>
              <p>Powered by verified government information</p>
            </div>

            <span className="status">
              <span className="status-dot"></span>
              Online
            </span>
          </div>

          <div className="chat-box">
            <div className="assistant-message">
              <div className="message-avatar">N</div>

              <div className="message">
                Hello! I can help you find and understand government schemes.

                <br />
                <br />

                For example, you can ask:

                <ul>
                  <li>I need financial support for higher education.</li>
                  <li>Which schemes are available for farmers?</li>
                  <li>Am I eligible for a Rajasthan government scheme?</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="chat-input">
            <input
              type="text"
              placeholder="Ask about government schemes..."
            />

            <button className="voice-button">🎤</button>

            <button className="send-button">Send</button>
          </div>

          <p className="source-note">
            NeetiNex provides information based on verified government sources
            where available.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;