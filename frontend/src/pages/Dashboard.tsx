// Eastern Time display - v2
import { useEffect, useState } from "react";
import { getDecisions, type DecisionRow } from "../api";

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

function fmtMoney(n: number): string {
  return "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    timeZone: "America/New_York",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

export default function Dashboard() {
  const [rows, setRows] = useState<DecisionRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDecisions(50)
      .then(setRows)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const today = rows.filter((r) => isToday(r.created_at));
  const totalToday = today.length;
  const approvalRate =
    totalToday === 0
      ? 0
      : (today.filter((r) => r.decision === "APPROVE").length / totalToday) * 100;
  const avgScore =
    totalToday === 0
      ? 0
      : today.reduce((s, r) => s + Number(r.risk_score), 0) / totalToday;

  return (
    <div className="page">
      <h1 className="page-title">Credit Decision Dashboard</h1>

      <div className="figures">
        <div>
          <div className="figure-value">{totalToday}</div>
          <div className="figure-label">Total decisions today</div>
        </div>
        <div>
          <div className="figure-value">{approvalRate.toFixed(1)}%</div>
          <div className="figure-label">Approval rate today</div>
        </div>
        <div>
          <div className="figure-value">{avgScore.toFixed(1)}</div>
          <div className="figure-label">Average risk score today</div>
        </div>
      </div>

      <hr className="divider" />

      {loading && <p>Loading decisions...</p>}
      {error && <p>Unable to load decisions: {error}</p>}

      {!loading && !error && (
        <table className="data">
          <thead>
            <tr>
              <th>Applicant ID</th>
              <th className="num">Loan Amount</th>
              <th className="num">FICO</th>
              <th className="num">Risk Score</th>
              <th className="num">Tier</th>
              <th>Decision</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7}>No decisions recorded yet.</td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.applicant_id}>
                <td>{r.applicant_id.slice(0, 8)}</td>
                <td className="num">{fmtMoney(r.loan_amount)}</td>
                <td className="num">{r.fico_score}</td>
                <td className="num">{Number(r.risk_score).toFixed(1)}</td>
                <td className="num">{r.risk_tier}</td>
                <td>{r.decision}</td>
                <td>{fmtTime(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
