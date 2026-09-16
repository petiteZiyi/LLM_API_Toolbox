import type { ReactNode } from "react";

type IconProps = { size?: number; className?: string };

function Svg({ size = 18, className, children }: IconProps & { children: ReactNode }) {
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>;
}

export function PlusIcon(props: IconProps) { return <Svg {...props}><path d="M12 5v14M5 12h14" /></Svg>; }
export function SearchIcon(props: IconProps) { return <Svg {...props}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></Svg>; }
export function SettingsIcon(props: IconProps) { return <Svg {...props}><path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M7 14v6" /></Svg>; }
export function GearIcon(props: IconProps) { return <Svg {...props}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></Svg>; }
export function SlidersIcon(props: IconProps) { return <Svg {...props}><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="9" cy="6" r="2" fill="currentColor" stroke="none" /><circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" /><circle cx="7" cy="18" r="2" fill="currentColor" stroke="none" /></Svg>; }
export function MenuIcon(props: IconProps) { return <Svg {...props}><path d="M4 7h16M4 12h16M4 17h16" /></Svg>; }
export function CloseIcon(props: IconProps) { return <Svg {...props}><path d="m6 6 12 12M18 6 6 18" /></Svg>; }
export function EditIcon(props: IconProps) { return <Svg {...props}><path d="M13.5 6.5 17.5 10.5M4 20l3.5-.7L19 7.8a2.1 2.1 0 0 0-3-3L4.7 16.3 4 20Z" /></Svg>; }
export function TrashIcon(props: IconProps) { return <Svg {...props}><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" /></Svg>; }
export function ChevronIcon(props: IconProps) { return <Svg {...props}><path d="m9 6 6 6-6 6" /></Svg>; }
export function ArrowUpIcon(props: IconProps) { return <Svg {...props}><path d="M12 19V5M6.5 10.5 12 5l5.5 5.5" /></Svg>; }
export function StopIcon(props: IconProps) { return <Svg {...props}><rect x="7" y="7" width="10" height="10" rx="1" fill="currentColor" stroke="none" /></Svg>; }
export function SparkleIcon(props: IconProps) { return <Svg {...props}><path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1L6.5 8.5l4.1-1.4L12 3ZM18.5 14l.7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z" /></Svg>; }
