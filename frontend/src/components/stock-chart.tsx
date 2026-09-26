"use client";

import { useEffect, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PricePoint } from "@/types";

type ChartType = "area" | "candlestick";

const THEME_COLORS = {
  light: {
    background: "#ffffff",
    text: "#0a0a0a",
    grid: "#f1f1f1",
    border: "#e5e5e5",
    up: "#16a34a",
    down: "#dc2626",
    area: "#2563eb",
    areaTop: "rgba(37, 99, 235, 0.28)",
    areaBottom: "rgba(37, 99, 235, 0.02)",
  },
  dark: {
    background: "#0a0a0a",
    text: "#e5e5e5",
    grid: "#1f1f1f",
    border: "#2a2a2a",
    up: "#22c55e",
    down: "#ef4444",
    area: "#60a5fa",
    areaTop: "rgba(96, 165, 250, 0.28)",
    areaBottom: "rgba(96, 165, 250, 0.02)",
  },
};

export function StockChart({ data }: { data: PricePoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [chartType, setChartType] = useState<ChartType>("area");
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!containerRef.current) return;
    const colors = THEME_COLORS[resolvedTheme === "dark" ? "dark" : "light"];

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      rightPriceScale: { borderColor: colors.border },
      timeScale: { borderColor: colors.border, timeVisible: false },
      autoSize: true,
    });
    chartRef.current = chart;

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      color: colors.grid,
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volumeSeriesRef.current = volumeSeries;

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      volumeSeriesRef.current = null;
    };
    // Chart instance is rebuilt only when the theme changes (colors baked into options).
  }, [resolvedTheme]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const colors = THEME_COLORS[resolvedTheme === "dark" ? "dark" : "light"];

    if (seriesRef.current) {
      chart.removeSeries(seriesRef.current);
      seriesRef.current = null;
    }

    const series =
      chartType === "area"
        ? chart.addSeries(AreaSeries, {
            lineColor: colors.area,
            topColor: colors.areaTop,
            bottomColor: colors.areaBottom,
            lineWidth: 2,
          })
        : chart.addSeries(CandlestickSeries, {
            upColor: colors.up,
            downColor: colors.down,
            borderVisible: false,
            wickUpColor: colors.up,
            wickDownColor: colors.down,
          });
    seriesRef.current = series;

    const timeFor = (dateStr: string): UTCTimestamp =>
      (new Date(dateStr + "T00:00:00Z").getTime() / 1000) as UTCTimestamp;

    if (chartType === "area") {
      (series as ISeriesApi<"Area">).setData(
        data.map((point) => ({ time: timeFor(point.date), value: point.close })),
      );
    } else {
      (series as ISeriesApi<"Candlestick">).setData(
        data.map((point) => ({
          time: timeFor(point.date),
          open: point.open,
          high: point.high,
          low: point.low,
          close: point.close,
        })),
      );
    }

    volumeSeriesRef.current?.setData(
      data.map((point) => ({
        time: timeFor(point.date),
        value: point.volume,
        color: point.close >= point.open ? colors.up + "80" : colors.down + "80",
      })),
    );

    chart.timeScale().fitContent();
  }, [data, chartType, resolvedTheme]);

  return (
    <div>
      <div className="mb-3 flex justify-end gap-1">
        <Button
          size="sm"
          variant={chartType === "area" ? "default" : "outline"}
          onClick={() => setChartType("area")}
          className={cn("h-7 px-2.5 text-xs")}
        >
          Line
        </Button>
        <Button
          size="sm"
          variant={chartType === "candlestick" ? "default" : "outline"}
          onClick={() => setChartType("candlestick")}
          className={cn("h-7 px-2.5 text-xs")}
        >
          Candlestick
        </Button>
      </div>
      <div ref={containerRef} className="h-[360px] w-full sm:h-[420px]" />
    </div>
  );
}
