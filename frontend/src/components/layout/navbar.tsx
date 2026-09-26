"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, History, LineChart, ListChecks, LogOut, Scale, ShieldCheck, SlidersHorizontal } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { GlobalSearch } from "@/components/layout/global-search";
import { ThemeToggle } from "@/components/theme-toggle";
import { brand } from "@/config/brand";
import { useAuth } from "@/context/auth-context";

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function Navbar() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <LineChart className="h-4 w-4" />
          </span>
          <span className="text-lg">{brand.shortName}</span>
        </Link>

        <div className="flex items-center gap-2">
          <ThemeToggle />

          {isLoading ? null : user ? (
            <>
              <GlobalSearch />
              <Button asChild variant="ghost" className="hidden sm:inline-flex">
                <Link href="/dashboard">Dashboard</Link>
              </Button>
              <Button asChild variant="ghost" className="hidden sm:inline-flex">
                <Link href="/research">Research</Link>
              </Button>
              <Button asChild variant="ghost" className="hidden lg:inline-flex">
                <Link href="/watchlist">Watchlist</Link>
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full p-0">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback>{initials(user.display_name)}</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="flex flex-col">
                    <span className="font-medium">{user.display_name}</span>
                    <span className="text-xs font-normal text-muted-foreground">{user.email}</span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/dashboard">Dashboard</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/research" className="flex items-center gap-2">
                      <Bot className="h-4 w-4" /> Research
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/research/history" className="flex items-center gap-2">
                      <History className="h-4 w-4" /> Research history
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild className="lg:hidden">
                    <Link href="/watchlist" className="flex items-center gap-2">
                      <ListChecks className="h-4 w-4" /> Watchlist
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/compare" className="flex items-center gap-2">
                      <Scale className="h-4 w-4" /> Compare
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/screener" className="flex items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4" /> Screener
                    </Link>
                  </DropdownMenuItem>
                  {user.role === "admin" && (
                    <DropdownMenuItem asChild>
                      <Link href="/admin" className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4" /> Admin
                      </Link>
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                    <LogOut className="h-4 w-4" /> Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <Button asChild>
              <Link href="/login">Login</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
