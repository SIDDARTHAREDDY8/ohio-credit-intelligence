import { useState } from "react";
import { scoreApplicant, type DecisionResponse } from "../api";

const INITIAL = {
  loan_amount: "15000",
  term_months: "36",
  annual_income: "55000",
  dti: "28.5",
  fico_score: "680",
  emp_length_years: "3",
  home_ownership: "RENT",
  loan_purpose: "debt_consolidation",
  delinq_2yrs: "0",
  open_accounts: "8",
  revolving_utilization: "0.45",
  grade: "C",
  sub_grade: "C3",
  verification_status: "Not Verified",
  int_rate: "13.5",
  installment: "503.0",
  revol_bal: "12000.0",
  pub_rec: "0",
  total_acc: "12",
};

type FormState = typeof INITIAL;

const PRESETS: Record<string, FormState> = {
  "Low Risk Applicant": {
    loan_amount: "8000",
    term_months: "36",
    annual_income: "95000",
    dti: "10.5",
    fico_score: "760",
    emp_length_years: "8",
    home_ownership: "MORTGAGE",
    loan_purpose: "home_improvement",
    delinq_2yrs: "0",
    open_accounts: "5",
    revolving_utilization: "0.15",
    grade: "A",
    sub_grade: "A2",
    verification_status: "Verified",
    int_rate: "7.5",
    installment: "248",
    revol_bal: "4500",
    pub_rec: "0",
    total_acc: "8",
  },
  "Medium Risk Applicant": {
    loan_amount: "15000",
    term_months: "36",
    annual_income: "55000",
    dti: "28.5",
    fico_score: "680",
    emp_length_years: "3",
    home_ownership: "RENT",
    loan_purpose: "debt_consolidation",
    delinq_2yrs: "0",
    open_accounts: "8",
    revolving_utilization: "0.45",
    grade: "C",
    sub_grade: "C3",
    verification_status: "Not Verified",
    int_rate: "13.5",
    installment: "503",
    revol_bal: "12000",
    pub_rec: "0",
    total_acc: "12",
  },
  "High Risk Applicant": {
    loan_amount: "35000",
    term_months: "60",
    annual_income: "28000",
    dti: "42.0",
    fico_score: "570",
    emp_length_years: "0",
    home_ownership: "RENT",
    loan_purpose: "other",
    delinq_2yrs: "4",
    open_accounts: "16",
    revolving_utilization: "0.95",
    grade: "F",
    sub_grade: "F4",
    verification_status: "Not Verified",
    int_rate: "27.5",
    installment: "850",
    revol_bal: "31000",
    pub_rec: "2",
    total_acc: "20",
  },
};

const NUMERIC_FIELDS = new Set<keyof FormState>([
  "loan_amount",
  "term_months",
  "annual_income",
  "dti",
  "fico_score",
  "emp_length_years",
  "delinq_2yrs",
  "open_accounts",
  "revolving_utilization",
  "int_rate",
  "installment",
  "revol_bal",
  "pub_rec",
  "total_acc",
]);

export default function ScoreApplicant() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [result, setResult] = useState<DecisionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (key: keyof FormState, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const applyPreset = (name: keyof typeof PRESETS) => setForm({ ...PRESETS[name] });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    const payload: Record<string, unknown> = {};
    (Object.keys(form) as (keyof FormState)[]).forEach((k) => {
      payload[k] = NUMERIC_FIELDS.has(k) ? Number(form[k]) : form[k];
    });

    try {
      const res = await scoreApplicant(payload);
      setResult(res);
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">Loan Application Scoring</h1>

      <div className="two-col">
        <form onSubmit={onSubmit}>
          <div className="preset-section">
            <div className="preset-label">Demo Presets — click to auto-fill</div>
            <div className="preset-buttons">
              {(Object.keys(PRESETS) as (keyof typeof PRESETS)[]).map((name) => (
                <button
                  key={name}
                  type="button"
                  className="preset-button"
                  onClick={() => applyPreset(name)}
                >
                  {name}
                </button>
              ))}
            </div>
            <p className="preset-note">
              In production, credit bureau data and account history populate automatically.
              Manual entry is for demonstration purposes only.
            </p>
          </div>

          <div className="form-grid">
            <TextField label="Loan Amount" k="loan_amount" form={form} onChange={update} />
            <SelectField
              label="Term (months)"
              k="term_months"
              form={form}
              onChange={update}
              options={["36", "60"]}
            />
            <TextField label="Annual Income" k="annual_income" form={form} onChange={update} />
            <TextField label="Debt-to-Income (DTI)" k="dti" form={form} onChange={update} />
            <TextField label="FICO Score" k="fico_score" form={form} onChange={update} />
            <TextField
              label="Employment Length (years)"
              k="emp_length_years"
              form={form}
              onChange={update}
            />
            <SelectField
              label="Home Ownership"
              k="home_ownership"
              form={form}
              onChange={update}
              options={["RENT", "OWN", "MORTGAGE", "OTHER"]}
            />
            <TextField label="Loan Purpose" k="loan_purpose" form={form} onChange={update} />
            <TextField
              label="Delinquencies (2 yrs)"
              k="delinq_2yrs"
              form={form}
              onChange={update}
            />
            <TextField label="Open Accounts" k="open_accounts" form={form} onChange={update} />
            <TextField
              label="Revolving Utilization (0-1)"
              k="revolving_utilization"
              form={form}
              onChange={update}
            />
            <TextField label="Grade" k="grade" form={form} onChange={update} />
            <TextField label="Sub-grade" k="sub_grade" form={form} onChange={update} />
            <SelectField
              label="Verification Status"
              k="verification_status"
              form={form}
              onChange={update}
              options={["Not Verified", "Source Verified", "Verified"]}
            />
            <TextField label="Interest Rate" k="int_rate" form={form} onChange={update} />
            <TextField label="Installment" k="installment" form={form} onChange={update} />
            <TextField label="Revolving Balance" k="revol_bal" form={form} onChange={update} />
            <TextField label="Public Records" k="pub_rec" form={form} onChange={update} />
            <TextField label="Total Accounts" k="total_acc" form={form} onChange={update} />
          </div>

          <button className="submit-button" type="submit" disabled={submitting}>
            {submitting ? "Scoring..." : "Score Application"}
          </button>
        </form>

        <div>
          <h2 className="section-title">Result</h2>
          {!result && !error && <p className="muted">Submit an application to see the result.</p>}
          {error && <p>Error: {error}</p>}

          {result && (
            <div>
              <div className="result-score">{Number(result.score).toFixed(1)}</div>
              <div className="figure-label">Risk Score — Tier {result.tier}</div>
              <div className="result-decision">{result.decision}</div>

              <h2 className="section-title">Top Factors</h2>
              <table className="data">
                <thead>
                  <tr>
                    <th>Factor</th>
                    <th>Value</th>
                    <th>Impact</th>
                  </tr>
                </thead>
                <tbody>
                  {result.top_shap_factors.map((f) => (
                    <tr key={f.feature}>
                      <td>{f.feature}</td>
                      <td>{String(f.feature_value)}</td>
                      <td>
                        {f.direction === "increases_risk"
                          ? "Increases risk"
                          : "Decreases risk"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {result.adverse_action_notice && (
                <>
                  <h2 className="section-title">Adverse Action Notice</h2>
                  <div className="notice-box">{result.adverse_action_notice}</div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  k: keyof FormState;
  form: FormState;
  onChange: (k: keyof FormState, v: string) => void;
}

function TextField({ label, k, form, onChange }: FieldProps) {
  return (
    <div className="field">
      <label>{label}</label>
      <input value={form[k]} onChange={(e) => onChange(k, e.target.value)} />
    </div>
  );
}

function SelectField({
  label,
  k,
  form,
  onChange,
  options,
}: FieldProps & { options: string[] }) {
  return (
    <div className="field">
      <label>{label}</label>
      <select value={form[k]} onChange={(e) => onChange(k, e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
