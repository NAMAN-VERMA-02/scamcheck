"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Analyse" },
  { href: "/benchmark", label: "Benchmark Lab" },
  { href: "/robustness", label: "Robustness Lab" },
  { href: "/method", label: "Method" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav aria-label="Main">
      <ul className="nav">
        {LINKS.map((l) => (
          <li key={l.href}>
            <Link href={l.href} aria-current={path === l.href ? "page" : undefined}>
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
