import { Badge } from "@/components/ui/badge";
import type { AIScore } from "@/types";

const LABEL_COLORS: Record<string, { ring: string; text: string; bg: string }> = {
  "Very Strong": { ring: "#059669", text: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-500/10" },
  Strong: { ring: "#16a34a", text: "text-emerald-700 dark:text-emerald-400", bg: "bg-emerald-500/10" },
  Balanced: { ring: "#d97706", text: "text-amber-700 dark:text-amber-400", bg: "bg-amber-500/10" },
  Weak: { ring: "#ea580c", text: "text-orange-700 dark:text-orange-400", bg: "bg-orange-500/10" },
  "Very Weak": { ring: "#dc2626", text: "text-red-700 dark:text-red-400", bg: "bg-red-500/10" },
};

const RISK_COLORS: Record<string, string> = {
  Low: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  Moderate: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  High: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400",
};

const SUBSCORE_LABELS: { key: keyof AIScore["subscores"]; label: string }[] = [
  { key: "financial_strength", label: "Financial Strength" },
  { key: "growth", label: "Growth" },
  { key: "profitability", label: "Profitability" },
  { key: "valuation", label: "Valuation" },
  { key: "technical_momentum", label: "Technical Momentum" },
];

function ScoreGauge({ score, colorHex }: { score: number; colorHex: string }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);

  return (
    <div className="relative flex h-36 w-36 shrink-0 items-center justify-center">
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={radius} fill="none" strokeWidth="10" className="stroke-muted" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          stroke={colorHex}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-semibold tabular-nums">{score}</span>
        <span className="text-xs text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}

function SubscoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

export function AIIndicator({ score }: { score: AIScore }) {
  const colors = LABEL_COLORS[score.label] ?? LABEL_COLORS.Balanced;

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
        <ScoreGauge score={score.overall_score} colorHex={colors.ring} />
        <div className="text-center sm:text-left">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            AI Research Score
          </p>
          <p className={`text-xl font-semibold ${colors.text}`}>{score.label} Research Profile</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Deterministic score from financial ratios, growth and technical indicators.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {SUBSCORE_LABELS.map(({ key, label }) => (
          <SubscoreBar key={key} label={label} value={score.subscores[key]} />
        ))}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Risk</span>
          <Badge className={RISK_COLORS[score.risk_label] ?? RISK_COLORS.Moderate}>{score.risk_label}</Badge>
        </div>
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">{score.methodology_note}</p>
    </div>
  );
}
