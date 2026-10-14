import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Footer from "@/components/Footer";
import { site } from "@/lib/data";

const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-space-grotesk", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Credit Risk Scorecard & Cut-off Strategy", template: "%s · Credit Risk Cut-off" },
  description:
    "An independent analysis of the public Home Credit Default Risk dataset: segment risk, a WoE/IV points scorecard and an approval cut-off strategy.",
  authors: [{ name: site.author }],
};

// Runs before paint so the stored theme applies without a flash.
const themeScript = `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" className={spaceGrotesk.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="font-sans">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-panel focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <Sidebar author={site.author} />
        <div className="min-[900px]:pl-[300px]">
          <main id="main" className="px-4 pb-16 pt-24 min-[900px]:px-[60px] min-[900px]:pt-20">
            {children}
          </main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
