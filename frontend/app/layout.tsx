import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "ClosetWise — AI Outfit Planner",
  description:
    "Style what I already own. Private wardrobe planning with explainable recommendations.",
};
export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
