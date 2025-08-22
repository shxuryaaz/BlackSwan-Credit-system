import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'BlackSwan Credit Intelligence Platform',
  description: 'Real-time, explainable credit scoring platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        {children}
      </body>
    </html>
  )
}





