"use client";

import { useEffect, useState, type ReactNode } from "react";
import { FlaskConical, History, Loader2, Save, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, api } from "@/lib/api";
import type {
  IndicatorKey,
  StrategyBacktestResponse,
  StrategyConfig,
  StrategyOut,
  StrategyPreviewResponse,
} from "@/types";

function NumberField({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step?: number;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-8"
      />
    </div>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4" />
      {label}
    </label>
  );
}

const INDICATOR_OPTIONS: { key: IndicatorKey; label: string }[] = [
  { key: "overall", label: "Overall (combines whichever indicators below are enabled)" },
  { key: "sma", label: "SMA" },
  { key: "ema", label: "EMA" },
  { key: "rsi", label: "RSI" },
  { key: "macd", label: "MACD" },
  { key: "bollinger", label: "Bollinger Bands" },
  { key: "fibonacci", label: "Fibonacci" },
];

function IndicatorSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border p-3">
      <h5 className="mb-2 text-sm font-medium">{title}</h5>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{children}</div>
    </div>
  );
}

export function StrategySettingsSection() {
  const [strategies, setStrategies] = useState<StrategyOut[]>([]);
  const [formConfig, setFormConfig] = useState<StrategyConfig | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [preview, setPreview] = useState<StrategyPreviewResponse | null>(null);
  const [backtest, setBacktest] = useState<StrategyBacktestResponse | null>(null);

  const loadAll = () => {
    setIsLoading(true);
    Promise.all([
      api.get<StrategyOut[]>("/api/admin/strategies"),
      api.get<StrategyConfig>("/api/admin/strategies/default-config"),
    ])
      .then(([strategyList, defaultConfig]) => {
        setStrategies(strategyList);
        setFormConfig((prev) => prev ?? defaultConfig);
      })
      .catch(() => toast.error("Failed to load strategies."))
      .finally(() => setIsLoading(false));
  };

  useEffect(loadAll, []);

  const activeStrategy = strategies.find((s) => s.is_active);

  const updateField = <K extends keyof StrategyConfig>(field: K, value: StrategyConfig[K]) => {
    setFormConfig((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const weightSum = formConfig
    ? formConfig.weight_financial_strength +
      formConfig.weight_growth +
      formConfig.weight_profitability +
      formConfig.weight_valuation +
      formConfig.weight_technical_momentum +
      formConfig.weight_risk
    : 0;
  const weightsValid = Math.abs(weightSum - 1) < 0.011;

  const handlePreview = async () => {
    if (!formConfig) return;
    setIsPreviewing(true);
    setBacktest(null);
    try {
      const response = await api.post<StrategyPreviewResponse>("/api/admin/strategies/preview", {
        config: formConfig,
      });
      setPreview(response);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Preview failed.");
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleBacktest = async () => {
    if (!formConfig) return;
    setIsBacktesting(true);
    setPreview(null);
    try {
      const response = await api.post<StrategyBacktestResponse>("/api/admin/strategies/backtest", {
        config: formConfig,
      });
      setBacktest(response);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Backtest failed.");
    } finally {
      setIsBacktesting(false);
    }
  };

  const handleSave = async () => {
    if (!formConfig || !name.trim()) {
      toast.error("Give the strategy a name first.");
      return;
    }
    if (!weightsValid) {
      toast.error("Score weights must sum to 100%.");
      return;
    }
    setIsSaving(true);
    try {
      const created = await api.post<StrategyOut>("/api/admin/strategies", {
        name,
        description,
        config: formConfig,
      });
      toast.success(`Saved "${created.name}". Activate it below to make it live.`);
      setName("");
      setDescription("");
      loadAll();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to save strategy.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleActivate = async (strategy: StrategyOut) => {
    try {
      await api.post(`/api/admin/strategies/${strategy.id}/activate`);
      toast.success(`Activated "${strategy.name}".`);
      loadAll();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to activate strategy.");
    }
  };

  if (isLoading || !formConfig) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Indicator &amp; strategy settings</CardTitle>
        </CardHeader>
        <CardContent>
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Indicator &amp; strategy settings</CardTitle>
        <CardDescription>
          Currently active: <strong>{activeStrategy?.name ?? "Default"}</strong>. Research GPT and every score
          on the site use whichever strategy is active.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h4 className="mb-2 text-sm font-medium">Indicators</h4>
          <p className="mb-3 text-xs text-muted-foreground">
            Each indicator here is enabled/configured independently. Enabling/disabling one is cosmetic for
            the AI Research Score (a disabled indicator still quietly feeds that score), but it IS what
            controls the Smart Indicator page - customers can only switch between indicators enabled here,
            never one you&apos;ve turned off.
          </p>

          <div className="mb-4 max-w-xs space-y-1.5">
            <Label className="text-xs text-muted-foreground">Default Smart Indicator page view</Label>
            <Select
              value={formConfig.default_smart_indicator}
              onValueChange={(value) => updateField("default_smart_indicator", value as IndicatorKey)}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {INDICATOR_OPTIONS.map((option) => (
                  <SelectItem key={option.key} value={option.key}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <IndicatorSection title="SMA">
              <ToggleField label="Enabled" checked={formConfig.enable_sma} onChange={(v) => updateField("enable_sma", v)} />
              <NumberField label="Short" value={formConfig.sma_short} onChange={(v) => updateField("sma_short", v)} />
              <NumberField label="Medium" value={formConfig.sma_medium} onChange={(v) => updateField("sma_medium", v)} />
              <NumberField label="Long" value={formConfig.sma_long} onChange={(v) => updateField("sma_long", v)} />
            </IndicatorSection>

            <IndicatorSection title="EMA">
              <ToggleField label="Enabled" checked={formConfig.enable_ema} onChange={(v) => updateField("enable_ema", v)} />
              <NumberField label="Short" value={formConfig.ema_short} onChange={(v) => updateField("ema_short", v)} />
              <NumberField label="Medium" value={formConfig.ema_medium} onChange={(v) => updateField("ema_medium", v)} />
              <NumberField label="Long" value={formConfig.ema_long} onChange={(v) => updateField("ema_long", v)} />
            </IndicatorSection>

            <IndicatorSection title="RSI">
              <ToggleField label="Enabled" checked={formConfig.enable_rsi} onChange={(v) => updateField("enable_rsi", v)} />
              <NumberField label="Period" value={formConfig.rsi_period} onChange={(v) => updateField("rsi_period", v)} />
              <NumberField
                label="Oversold"
                value={formConfig.rsi_oversold}
                onChange={(v) => updateField("rsi_oversold", v)}
              />
              <NumberField
                label="Overbought"
                value={formConfig.rsi_overbought}
                onChange={(v) => updateField("rsi_overbought", v)}
              />
            </IndicatorSection>

            <IndicatorSection title="MACD">
              <ToggleField label="Enabled" checked={formConfig.enable_macd} onChange={(v) => updateField("enable_macd", v)} />
              <NumberField label="Fast" value={formConfig.macd_fast} onChange={(v) => updateField("macd_fast", v)} />
              <NumberField label="Slow" value={formConfig.macd_slow} onChange={(v) => updateField("macd_slow", v)} />
              <NumberField label="Signal" value={formConfig.macd_signal} onChange={(v) => updateField("macd_signal", v)} />
            </IndicatorSection>

            <IndicatorSection title="Bollinger Bands">
              <ToggleField
                label="Enabled"
                checked={formConfig.enable_bollinger}
                onChange={(v) => updateField("enable_bollinger", v)}
              />
              <NumberField
                label="Period"
                value={formConfig.bollinger_period}
                onChange={(v) => updateField("bollinger_period", v)}
              />
              <NumberField
                label="Std-dev"
                value={formConfig.bollinger_num_std}
                step={0.1}
                onChange={(v) => updateField("bollinger_num_std", v)}
              />
            </IndicatorSection>

            <IndicatorSection title="Fibonacci">
              <ToggleField
                label="Enabled"
                checked={formConfig.enable_fibonacci}
                onChange={(v) => updateField("enable_fibonacci", v)}
              />
              <NumberField
                label="Lookback (days)"
                value={formConfig.fibonacci_lookback_days}
                onChange={(v) => updateField("fibonacci_lookback_days", v)}
              />
            </IndicatorSection>
          </div>
        </div>

        <div>
          <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
            AI score weights
            <Badge variant={weightsValid ? "secondary" : "destructive"}>{(weightSum * 100).toFixed(0)}%</Badge>
          </h4>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <NumberField
              label="Financial strength"
              value={formConfig.weight_financial_strength}
              step={0.01}
              onChange={(v) => updateField("weight_financial_strength", v)}
            />
            <NumberField
              label="Growth"
              value={formConfig.weight_growth}
              step={0.01}
              onChange={(v) => updateField("weight_growth", v)}
            />
            <NumberField
              label="Profitability"
              value={formConfig.weight_profitability}
              step={0.01}
              onChange={(v) => updateField("weight_profitability", v)}
            />
            <NumberField
              label="Valuation"
              value={formConfig.weight_valuation}
              step={0.01}
              onChange={(v) => updateField("weight_valuation", v)}
            />
            <NumberField
              label="Technical momentum"
              value={formConfig.weight_technical_momentum}
              step={0.01}
              onChange={(v) => updateField("weight_technical_momentum", v)}
            />
            <NumberField
              label="Risk"
              value={formConfig.weight_risk}
              step={0.01}
              onChange={(v) => updateField("weight_risk", v)}
            />
          </div>
        </div>

        <div>
          <h4 className="mb-2 text-sm font-medium">Thresholds</h4>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            <NumberField
              label="D/E good"
              value={formConfig.debt_to_equity_good}
              step={0.1}
              onChange={(v) => updateField("debt_to_equity_good", v)}
            />
            <NumberField
              label="D/E bad"
              value={formConfig.debt_to_equity_bad}
              step={0.1}
              onChange={(v) => updateField("debt_to_equity_bad", v)}
            />
            <NumberField label="ROE low" value={formConfig.roe_low} onChange={(v) => updateField("roe_low", v)} />
            <NumberField label="ROE high" value={formConfig.roe_high} onChange={(v) => updateField("roe_high", v)} />
            <NumberField label="ROCE low" value={formConfig.roce_low} onChange={(v) => updateField("roce_low", v)} />
            <NumberField label="ROCE high" value={formConfig.roce_high} onChange={(v) => updateField("roce_high", v)} />
            <NumberField
              label="P/E fallback low"
              value={formConfig.pe_fallback_low}
              onChange={(v) => updateField("pe_fallback_low", v)}
            />
            <NumberField
              label="P/E fallback high"
              value={formConfig.pe_fallback_high}
              onChange={(v) => updateField("pe_fallback_high", v)}
            />
            <NumberField
              label="Risk: Moderate cutoff"
              value={formConfig.risk_moderate_cutoff}
              onChange={(v) => updateField("risk_moderate_cutoff", v)}
            />
            <NumberField
              label="Risk: Low cutoff"
              value={formConfig.risk_low_cutoff}
              onChange={(v) => updateField("risk_low_cutoff", v)}
            />
            <NumberField
              label="Overall: Weak cutoff"
              value={formConfig.overall_weak_cutoff}
              onChange={(v) => updateField("overall_weak_cutoff", v)}
            />
            <NumberField
              label="Overall: Balanced cutoff"
              value={formConfig.overall_balanced_cutoff}
              onChange={(v) => updateField("overall_balanced_cutoff", v)}
            />
            <NumberField
              label="Overall: Strong cutoff"
              value={formConfig.overall_strong_cutoff}
              onChange={(v) => updateField("overall_strong_cutoff", v)}
            />
            <NumberField
              label="Overall: Very Strong cutoff"
              value={formConfig.overall_very_strong_cutoff}
              onChange={(v) => updateField("overall_very_strong_cutoff", v)}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-3 border-t pt-4">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Strategy name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Aggressive Growth" className="h-8 w-48" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Description</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional"
              className="h-8 w-64"
            />
          </div>
          <Button size="sm" variant="outline" className="gap-1.5" disabled={isPreviewing} onClick={handlePreview}>
            {isPreviewing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Preview
          </Button>
          <Button size="sm" variant="outline" className="gap-1.5" disabled={isBacktesting} onClick={handleBacktest}>
            {isBacktesting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FlaskConical className="h-3.5 w-3.5" />}
            Backtest
          </Button>
          <Button size="sm" className="gap-1.5" disabled={isSaving} onClick={handleSave}>
            {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
            Save strategy
          </Button>
        </div>

        {preview && (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead className="text-right">Active score</TableHead>
                  <TableHead className="text-right">Proposed score</TableHead>
                  <TableHead className="text-right">Delta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.results.map((row) => (
                  <TableRow key={row.symbol}>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.active_score ?? "-"} {row.active_label ? `(${row.active_label})` : ""}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.proposed_score ?? "-"} {row.proposed_label ? `(${row.proposed_label})` : ""}
                    </TableCell>
                    <TableCell
                      className={
                        "text-right tabular-nums font-medium " +
                        (row.delta && row.delta > 0
                          ? "text-emerald-600 dark:text-emerald-400"
                          : row.delta && row.delta < 0
                            ? "text-red-600 dark:text-red-400"
                            : "")
                      }
                    >
                      {row.delta !== null ? (row.delta > 0 ? `+${row.delta}` : row.delta) : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {backtest && (
          <div className="space-y-2">
            <p className="rounded-md border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-700 dark:text-amber-400">
              {backtest.caveat}
            </p>
            {backtest.checkpoints.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Not enough price history for a backtest yet (need roughly a year or more per company).
              </p>
            ) : (
              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-right">Active score</TableHead>
                      <TableHead className="text-right">Proposed score</TableHead>
                      <TableHead className="text-right">+30d return</TableHead>
                      <TableHead className="text-right">+90d return</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backtest.checkpoints.map((c, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{c.symbol}</TableCell>
                        <TableCell>{c.checkpoint_date}</TableCell>
                        <TableCell className="text-right tabular-nums">{c.active_score ?? "-"}</TableCell>
                        <TableCell className="text-right tabular-nums">{c.proposed_score ?? "-"}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {c.forward_return_30d !== null ? `${c.forward_return_30d.toFixed(2)}%` : "-"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {c.forward_return_90d !== null ? `${c.forward_return_90d.toFixed(2)}%` : "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        )}

        <div>
          <h4 className="mb-2 flex items-center gap-2 text-sm font-medium">
            <History className="h-4 w-4" /> Strategy history
          </h4>
          {strategies.length === 0 ? (
            <p className="text-sm text-muted-foreground">No strategies saved yet - the Default configuration is active.</p>
          ) : (
            <div className="space-y-1">
              {strategies.map((strategy) => (
                <div
                  key={strategy.id}
                  className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                >
                  <div>
                    <span className="font-medium">{strategy.name}</span>{" "}
                    {strategy.is_active && <Badge className="ml-1">Active</Badge>}
                    {strategy.description && (
                      <p className="text-xs text-muted-foreground">{strategy.description}</p>
                    )}
                  </div>
                  {!strategy.is_active && (
                    <Button size="sm" variant="outline" onClick={() => handleActivate(strategy)}>
                      Activate
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
