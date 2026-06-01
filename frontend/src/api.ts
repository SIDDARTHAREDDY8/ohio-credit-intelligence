// All requests go through the Vite dev proxy (/api -> http://localhost:8000).

const BASE = "/api";

export interface ShapFactor {
  feature: string;
  shap_value: number;
  feature_value: number | string;
  direction: "increases_risk" | "decreases_risk";
}

export interface DecisionResponse {
  applicant_id: string;
  score: number;
  tier: number;
  decision: "APPROVE" | "REVIEW" | "DECLINE";
  default_probability: number;
  top_shap_factors: ShapFactor[];
  adverse_action_notice: string | null;
  fairness_flags: string[];
  model_version: string;
  scored_at: string;
}

export interface DecisionRow {
  applicant_id: string;
  loan_amount: number;
  annual_income: number;
  dti: number;
  fico_score: number;
  risk_score: number;
  risk_tier: number;
  decision: string;
  model_version: string;
  created_at: string;
}

export interface FairnessRow {
  race_label: string;
  sex_label: string;
  total_applications: number;
  approvals: number;
  approval_rate_pct: number;
}

export interface DriftRow {
  id: number;
  psi_score: number;
  status: string;
  week_start: string;
  logged_at: string;
}

export interface Health {
  status: string;
  model_loaded: boolean;
  model_version: string;
  uptime_seconds: number;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} returned ${res.status}`);
  return res.json();
}

export const getDecisions = (limit = 50) =>
  getJson<DecisionRow[]>(`/decisions?limit=${limit}`);
export const getFairness = () => getJson<FairnessRow[]>("/fairness");
export const getDrift = () => getJson<DriftRow[]>("/drift");
export const getHealth = () => getJson<Health>("/health");

export async function scoreApplicant(
  payload: Record<string, unknown>
): Promise<DecisionResponse> {
  const res = await fetch(`${BASE}/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Scoring failed (${res.status}): ${text}`);
  }
  return res.json();
}
