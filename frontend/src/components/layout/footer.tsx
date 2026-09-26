import Link from "next/link";

import { brand } from "@/config/brand";

export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-md space-y-2">
            <p className="text-sm font-semibold">{brand.shortName}</p>
            <p className="text-sm text-muted-foreground">{brand.footerText}</p>
          </div>
          <div className="flex gap-6 text-sm text-muted-foreground">
            <Link href="/login" className="hover:text-foreground">
              Login
            </Link>
            <a href={`mailto:${brand.supportEmail}`} className="hover:text-foreground">
              Support
            </a>
          </div>
        </div>
        <p className="mt-8 max-w-3xl text-xs leading-relaxed text-muted-foreground">
          {brand.disclaimer}
        </p>
        <p className="mt-4 text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} {brand.shortName}. Private beta - not for public distribution.
        </p>
      </div>
    </footer>
  );
}
