import "./globals.css";
// import { Toaster } from "sonner"; // 第三方组件

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-cn">
      {/* <Toaster position="top-right" /> */}
      <body>{children}</body>
    </html>
  );
}
