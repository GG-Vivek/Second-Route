import {
  Blend,
  Camera,
  Gamepad2,
  Headphones,
  Laptop,
  Refrigerator,
  Smartphone,
  Snowflake,
  Sparkles,
  Tablet,
  Tv,
  WashingMachine,
  Wind,
  type LucideIcon,
} from 'lucide-react'

/**
 * The icon for each kind of device on the window (F11.3).
 *
 * A category the window does not know still gets an icon, so a new kind added
 * to the catalogue shows up before anyone has drawn it one.
 */
const ICONS: Record<string, LucideIcon> = {
  laptop: Laptop,
  phone: Smartphone,
  tablet: Tablet,
  tv: Tv,
  refrigerator: Refrigerator,
  washer: WashingMachine,
  console: Gamepad2,
  audio: Headphones,
  camera: Camera,
  mixer: Blend,
  ac: Snowflake,
  purifier: Sparkles,
  hairdryer: Wind,
}

/** The icon for a category, with a generic one for anything unknown. */
export function categoryIcon(key: string): LucideIcon {
  return ICONS[key] ?? Laptop
}
