import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniBrain — Command Center",
  description: "Personal Autonomous AI Operating System with F.R.I.D.A.Y. Voice",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}

