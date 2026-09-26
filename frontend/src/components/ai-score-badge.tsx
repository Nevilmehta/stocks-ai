import { Badge } from "@/components/ui/badge";

const LABEL_CLASSES: Record<string, string> = {
  "Very Strong": "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  Strong: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  Balanced: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  Weak: "border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-400",
  "Very Weak": "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400",
};

export function AIScoreBadge({ score, label }: { score: number | null; label: string | null }) {
  if (score === null || !label) {
    return <span className="text-xs text-muted-foreground">Data unavailable</span>;
  }
  return (
    <Badge className={LABEL_CLASSES[label] ?? LABEL_CLASSES.Balanced}>
      {score} &middot; {label}
    </Badge>
  );
}
