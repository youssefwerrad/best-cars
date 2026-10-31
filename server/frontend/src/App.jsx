import { useEffect, useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { AuthContext, api } from "./lib";
import { Compare, Dealer, Dealers, Home, Login, Moderation, PostReview, Register, SavedDealers } from "./pages";

export default function App() {
  const [user, setUser] = useState("");
  const [isStaff, setIsStaff] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    api("whoami").then((r) => { setUser(r.userName || ""); setIsStaff(Boolean(r.isStaff)); }).finally(() => setReady(true));
  }, []);
  const logout = async () => { await api("logout", {}); setUser(""); setIsStaff(false); };

  return (
    <AuthContext.Provider value={{ user, setUser, ready, isStaff, setIsStaff }}>
      <BrowserRouter>
        <header className="site-header">
          <nav className="site-nav" aria-label="Main navigation">
            <Link className="brand" to="/" aria-label="Best Cars home">
              <span className="brand-mark" aria-hidden="true">
                <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">
                  <defs>
                    <linearGradient id="brandGradient" x1="0%" x2="100%" y1="0%" y2="100%">
                      <stop offset="0%" stopColor="#10d8c8"/>
                      <stop offset="100%" stopColor="#0c8a80"/>
                    </linearGradient>
                  </defs>
                  <rect x="4" y="4" width="40" height="40" rx="12" fill="url(#brandGradient)"/>
                  <path d="M15 31V17H18.9L24.8 25.7V17H32.5V31H28.6L22.7 22.3V31H15Z" fill="white"/>
                  <circle cx="33.5" cy="15.5" r="3.5" fill="#dffaf5"/>
                </svg>
              </span>
              <span>Best Cars<span className="brand-subtitle">DEALER REVIEWS</span></span>
            </Link>
            <div className="nav-links">
              <NavLink to="/" end>Home</NavLink>
              <NavLink to="/dealers">Dealers</NavLink>
              {user && <NavLink to="/saved">Saved</NavLink>}
              {isStaff && <NavLink to="/moderation">Moderation</NavLink>}
            </div>
            <div className="account-links">
              {user ? (
                <><span className="account-name">{user}</span><button className="nav-button" onClick={logout}>Log out</button></>
              ) : (
                <><NavLink className="login-link" to="/login">Log in</NavLink><NavLink className="button button-small" to="/register">Create account</NavLink></>
              )}
            </div>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dealers" element={<Dealers />} />
            <Route path="/dealer/:id" element={<Dealer />} />
            <Route path="/postreview/:id" element={<PostReview />} />
            <Route path="/saved" element={<SavedDealers />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/moderation" element={<Moderation />} />
            <Route path="*" element={<section className="page-shell empty-state"><h1>Page not found</h1><p>The page you’re looking for doesn’t exist.</p><Link className="button" to="/">Back to home</Link></section>} />
          </Routes>
        </main>
        <footer className="site-footer">
          <span>Best Cars</span>
          <span>Find your next drive with confidence.</span>
        </footer>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
