import { NavLink } from "react-router-dom";

export default function NavBar() {
  return (
    <nav className="navbar">
      <div className="navbar-brand">Ohio Credit Intelligence</div>
      <div className="navbar-links">
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/score">Score Applicant</NavLink>
        <NavLink to="/monitoring">Monitoring</NavLink>
      </div>
    </nav>
  );
}
