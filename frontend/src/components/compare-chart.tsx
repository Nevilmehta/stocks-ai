"use client";

import { useEffect, useRef } from "react";
import { ColorType, LineSeries, createChart, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { useTheme } from "next-themes";

import type { CompareRow } from "@/types";

const SERIES_COLORS = ["#2563eb", "#dc2626", "#16a34a"];

function timeFor(dateStr: string): UTCTimestamp {
  return (new Date(dateStr + "T00:00:00Z").getTime() / 1000) as UTCTimestamp;
}

export function CompareChart({ rows }: { rows: CompareRow[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!containerRef.current) return;
    const isDark = resolvedTheme === "dark";
    const textColor = isDark ? "#e5e5e5" : "#0a0a0a";
    const gridColor = isDark ? "#1f1f1f" : "#f1f1f1";
    const borderColor = isDark ? "#2a2a2a" : "#e5e5e5";

    const chart: IChartApi = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor },
      timeScale: { borderColor },
      autoSize: true,
    });

    rows.forEach((row, index) => {
      if (row.history.length === 0) return;
      const basePrice = row.history[0].close;
      const series = chart.addSeries(LineSeries, {
        color: SERIES_COLORS[index % SERIES_COLORS.length],
        lineWidth: 2,
        title: row.symbol,
      });
      series.setData(
        row.history.map((point) => ({
          time: timeFor(point.date),
          value: ((point.close - basePrice) / basePrice) * 100,
        })),
      );
    });

    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [rows, resolvedTheme]);

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-4">
        {rows.map((row, index) => (
          <div key={row.symbol} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: SERIES_COLORS[index % SERIES_COLORS.length] }}
            />
            {row.symbol}
          </div>
        ))}
      </div>
      <div ref={containerRef} className="h-[320px] w-full" />
      <p className="mt-2 text-xs text-muted-foreground">
        Percentage change from the start of the 1-year window shown, indexed to 0%.
      </p>
    </div>
  );
}
