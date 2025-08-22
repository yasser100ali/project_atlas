import "./globals.css";
import "katex/dist/katex.min.css";
import { GeistSans } from "geist/font/sans";
import { Toaster } from "sonner";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata = {
  title: "AI SDK Python Streaming Preview",
  description:
    "Use the Data Stream Protocol to stream chat completions from a Python endpoint (FastAPI) and display them using the useChat hook in your Next.js application.",
  openGraph: {
    images: [
      {
        url: "/og?title=AI SDK Python Streaming Preview",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: [
      {
        url: "/og?title=AI SDK Python Streaming Preview",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head></head>
      <body className={cn(GeistSans.className, "antialiased dark")}> 
        {/* Sidebar now owns controls; nothing fixed here on mobile */}
        <div className="hidden md:flex fixed left-4 bottom-4 z-50 items-center gap-2"></div>
        <Toaster position="top-center" richColors />
        {children}
      </body>
    </html>
  );
}
