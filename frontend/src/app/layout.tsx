import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Last Mile Health RAG Platform",
  description: "PDF ingestion, grounded chat, and gold-standard evaluation console.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
