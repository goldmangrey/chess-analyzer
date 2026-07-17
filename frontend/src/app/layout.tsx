import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chess AI Teacher",
  description:
    "Локальный анализ шахматных партий Chess.com с помощью Stockfish.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
