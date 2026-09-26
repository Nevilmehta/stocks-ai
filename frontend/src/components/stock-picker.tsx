"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Search, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { api } from "@/lib/api";
import type { Company } from "@/types";

export function StockPicker({
  selected,
  onChange,
  max = 3,
}: {
  selected: Company[];
  onChange: (companies: Company[]) => void;
  max?: number;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length === 0) {
      setResults([]);
      return;
    }
    setIsLoading(true);
    debounceRef.current = setTimeout(() => {
      api
        .get<Company[]>(`/api/stocks/search?q=${encodeURIComponent(query.trim())}`)
        .then(setResults)
        .finally(() => setIsLoading(false));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  const addCompany = (company: Company) => {
    if (selected.some((c) => c.symbol === company.symbol) || selected.length >= max) return;
    onChange([...selected, company]);
    setQuery("");
    setResults([]);
  };

  const removeCompany = (symbol: string) => {
    onChange(selected.filter((c) => c.symbol !== symbol));
  };

  const selectedSymbols = new Set(selected.map((c) => c.symbol));
  const filteredResults = results.filter((c) => !selectedSymbols.has(c.symbol));
  const isOpen = query.trim().length > 0;

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-2">
        {selected.map((company) => (
          <Badge key={company.symbol} variant="secondary" className="gap-1.5 py-1.5 pl-3 pr-1.5 text-sm">
            {company.symbol}
            <button
              onClick={() => removeCompany(company.symbol)}
              className="rounded-full p-0.5 hover:bg-muted-foreground/20"
              aria-label={`Remove ${company.symbol}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        {selected.length === 0 && (
          <span className="text-sm text-muted-foreground">No companies selected yet.</span>
        )}
      </div>

      {selected.length < max && (
        <Popover open={isOpen}>
          <PopoverAnchor asChild>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={`Add a company (${selected.length}/${max})...`}
                className="pl-9"
              />
            </div>
          </PopoverAnchor>
          <PopoverContent
            align="start"
            onOpenAutoFocus={(event) => event.preventDefault()}
            className="w-[var(--radix-popper-anchor-width)] p-1"
          >
            {isLoading ? (
              <div className="flex items-center justify-center py-3">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            ) : filteredResults.length === 0 ? (
              <p className="px-2 py-3 text-center text-sm text-muted-foreground">No matches.</p>
            ) : (
              filteredResults.map((company) => (
                <button
                  key={company.symbol}
                  onClick={() => addCompany(company)}
                  className="flex w-full flex-col items-start rounded-md px-3 py-1.5 text-left text-sm hover:bg-accent"
                >
                  <span className="font-medium">
                    {company.symbol}{" "}
                    <span className="font-normal text-muted-foreground">&middot; {company.name}</span>
                  </span>
                </button>
              ))
            )}
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
}
