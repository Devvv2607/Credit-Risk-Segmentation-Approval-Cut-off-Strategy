"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Database,
  FlaskConical,
  Home,
  Menu,
  Moon,
  RefreshCw,
  SlidersHorizontal,
  Sun,
  Table,
  User,
  X,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Home", icon: Home },
  { href: "/analysis/", label: "Analysis", icon: BarChart3 },
  { href: "/simulator/", label: "Simulator", icon: SlidersHorizontal },
  { href: "/scorecard/", label: "Scorecard", icon: Table },
  { href: "/methodology/", label: "Methodology", icon: FlaskConical },
  { href: "/data/", label: "Data & Sources", icon: Database },
  { href: "/reproducibility/", label: "Reproducibility", icon: RefreshCw },
  { href: "/about/", label: "About", icon: User },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light");
  }, []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* storage may be unavailable; the toggle still works for this visit */
    }
  };
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === "dark"}
      className="flex items-center gap-3 rounded-md px-1 py-1 text-[16px] text-muted hover:text-ink"
    >
      {theme === "dark" ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
      {theme === "dark" ? "Light theme" : "Dark theme"}
    </button>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const norm = (p: string) => (p.endsWith("/") ? p : `${p}/`);
  return (
    <ul className="space-y-1">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : norm(pathname).startsWith(href);
        return (
          <li key={href}>
            <Link
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-md px-1 py-[7px] text-[18px] no-underline transition-colors ${
                active ? "font-bold text-ink" : "text-muted hover:text-ink"
              }`}
            >
              <Icon size={20} aria-hidden strokeWidth={active ? 2.4 : 1.8} />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export default function Sidebar({ author }: { author: string }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
  }, [open]);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[300px] flex-col border-r border-border bg-bg px-10 py-10 min-[900px]:flex">
        <Link href="/" className="no-underline">
          <div className="text-[22px] font-bold leading-tight text-ink">{author}</div>
          <div className="text-[18px] text-muted">Analysis</div>
        </Link>
        <nav aria-label="Main" className="flex flex-1 items-center">
          <NavList />
        </nav>
        <ThemeToggle />
      </aside>

      {/* Mobile top bar */}
      <header className="fixed inset-x-0 top-0 z-30 flex items-center justify-between border-b border-border bg-bg px-4 py-3 min-[900px]:hidden">
        <Link href="/" className="no-underline">
          <span className="text-[18px] font-bold text-ink">{author}</span>{" "}
          <span className="text-[16px] text-muted">Analysis</span>
        </Link>
        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((o) => !o)}
          className="rounded-md p-2 text-ink"
        >
          {open ? <X size={22} aria-hidden /> : <Menu size={22} aria-hidden />}
        </button>
      </header>
      {open && (
        <div id="mobile-nav" className="fixed inset-0 z-20 flex flex-col bg-bg px-4 pb-8 pt-20 min-[900px]:hidden">
          <nav aria-label="Main">
            <NavList onNavigate={() => setOpen(false)} />
          </nav>
          <div className="mt-8">
            <ThemeToggle />
          </div>
        </div>
      )}
    </>
  );
}
