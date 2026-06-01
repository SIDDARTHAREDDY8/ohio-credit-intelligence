import { Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import Dashboard from "./pages/Dashboard";
import ScoreApplicant from "./pages/ScoreApplicant";
import Monitoring from "./pages/Monitoring";

export default function App() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/score" element={<ScoreApplicant />} />
        <Route path="/monitoring" element={<Monitoring />} />
      </Routes>
    </>
  );
}
