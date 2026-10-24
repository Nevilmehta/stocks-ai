"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export interface MultiSelectOption {
  value: string;
  label: string;
  count?: number;
}

export function MultiSelectFilter({
  label,
  placeholder,
  options,
  selected,
  onChange,
}: {
  label: string;
  placeholder: string;
  options: MultiSelectOption[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);

  const toggle = (value: string) => {
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);
  };

  const triggerText =
    selected.length === 0
      ? placeholder
      : selected.length === 1
        ? (options.find((o) => o.value === selected[0])?.label ?? selected[0])
        : `${selected.length} selected`;

  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" className="w-full justify-between font-normal">
            <span className="truncate">{triggerText}</span>
            <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        {/* w-[var(--radix-popper-anchor-width)] matches the trigger's width -
            this is the shared Radix Popper primitive's variable name, not
            "--radix-popover-anchor-width" (a past bug in this codebase). */}
        <PopoverContent className="w-[var(--radix-popper-anchor-width)] p-0" align="start">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-xs text-muted-foreground">{selected.length} selected</span>
            {selected.length > 0 && (
              <button
                type="button"
                className="text-xs text-muted-foreground underline hover:text-foreground"
                onClick={() => onChange([])}
              >
                Clear
              </button>
            )}
          </div>
          <div className="max-h-72 overflow-y-auto p-1">
            {options.map((option) => (
              <label
                key={option.value}
                className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
              >
                <Checkbox checked={selected.includes(option.value)} onCheckedChange={() => toggle(option.value)} />
                <span className="flex-1 truncate">{option.label}</span>
                {option.count !== undefined && <span className="text-xs text-muted-foreground">{option.count}</span>}
              </label>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
