import { useEffect, useState } from "react";
import {
  getDrift,
  getFairness,
  getHealth,
  type DriftRow,
  type FairnessRow,
  type Health,
} from "../api";

const MAJORITY_RACE = "White";
const MAJORITY_SEX = "Male";
const THRESHOLD = 0.8;

export default function Monitoring() {
  const [fairness, setFairness] = useState<FairnessRow[]>([]);
  const [drift, setDrift] = useState<DriftRow[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getFairness(), getDrift(), getHealth()])
      .then(([f, d, h]) => {
        setFairness(f);
        setDrift(d);
        setHealth(h);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const majority = fairness.find(
    (r) => r.race_label === MAJORITY_RACE && r.sex_label === MAJORITY_SEX
  );
  const majorityRate = majority ? majority.approval_rate_pct : 0;

  return (
    <div className="page">
      <h1 className="page-title">Model Monitoring</h1>

      {error && <p>Error: {error}</p>}

      <h2 className="section-title">Model Information</h2>
      <table className="data">
        <tbody>
          <tr>
            <th>Model Name</th>
            <td>ohio_credit_risk</td>
          </tr>
          <tr>
            <th>Version</th>
            <td>{health ? health.model_version : "—"}</td>
          </tr>
          <tr>
            <th>Status</th>
            <td>{health ? (health.model_loaded ? "Loaded" : "Not loaded") : "—"}</td>
          </tr>
        </tbody>
      </table>

      <h2 className="section-title">Fairness Audit</h2>
      <table className="data">
        <thead>
          <tr>
            <th>Demographic Group</th>
            <th className="num">Applications</th>
            <th className="num">Approval Rate</th>
            <th className="num">Disparity Ratio</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {fairness.length === 0 && (
            <tr>
              <td colSpan={5}>No fairness data available.</td>
            </tr>
          )}
          {fairness.map((r) => {
            const ratio = majorityRate > 0 ? r.approval_rate_pct / majorityRate : 0;
            const compliant = ratio >= THRESHOLD;
            return (
              <tr key={`${r.race_label}-${r.sex_label}`}>
                <td>
                  {r.race_label} / {r.sex_label}
                </td>
                <td className="num">{r.total_applications.toLocaleString("en-US")}</td>
                <td className="num">{Number(r.approval_rate_pct).toFixed(2)}%</td>
                <td className="num">{ratio.toFixed(3)}</td>
                <td>{compliant ? "Compliant" : "Violation"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="note">
        Disparity ratio below 0.80 indicates potential CFPB 4/5ths rule violation per the
        Equal Credit Opportunity Act
      </p>

      <h2 className="section-title">Score Drift (PSI)</h2>
      <table className="data">
        <thead>
          <tr>
            <th>Week Start</th>
            <th className="num">PSI Score</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {drift.length === 0 && (
            <tr>
              <td colSpan={3}>No drift readings recorded yet.</td>
            </tr>
          )}
          {drift.map((r) => (
            <tr key={r.id}>
              <td>{r.week_start}</td>
              <td className="num">{Number(r.psi_score).toFixed(4)}</td>
              <td>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
