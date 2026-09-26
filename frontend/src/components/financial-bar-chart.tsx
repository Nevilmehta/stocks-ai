interface BarDatum {
  label: string;
  value: number;
}

/** Small dependency-free trend bar chart with period labels underneath. */
export function FinancialBarChart({ data }: { data: BarDatum[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">Data unavailable</p>;
  }

  const values = data.map((d) => d.value);
  const maxValue = Math.max(...values, 0);
  const minValue = Math.min(...values, 0);
  const range = maxValue - minValue || 1;

  return (
    <div className="flex h-[140px] items-end gap-1.5">
      {data.map((point) => {
        const heightPercent = ((point.value - minValue) / range) * 100;
        const isNegative = point.value < 0;
        return (
          <div key={point.label} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
            <span className="text-[10px] tabular-nums text-muted-foreground">{point.value.toFixed(0)}</span>
            <div className="flex h-full w-full items-end">
              <div
                className={
                  isNegative
                    ? "w-full rounded-t-sm bg-destructive/70"
                    : "w-full rounded-t-sm bg-primary/70"
                }
                style={{ height: `${Math.max(heightPercent, 2)}%` }}
              />
            </div>
            <span className="max-w-full truncate text-[10px] text-muted-foreground" title={point.label}>
              {point.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
